"""
Front Range Wildlife Intelligence System
Proof of Signal Test -- iNaturalist API

Queries iNaturalist for species observations within 50 miles of
Highlands Ranch, CO and produces a plain-English signal report.

API strategy:
- /observations/species_counts  -> ranked species totals (no pagination needed)
- /observations?per_page=0      -> total observation count for a date range
- Both called twice: once for current period, once for prior period
"""

import time
import requests
import pandas as pd
from datetime import date, timedelta
from tabulate import tabulate
from pathlib import Path


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

LAT       = 39.5594
LON       = -104.9719
RADIUS_KM = 80.5          # 50 miles in km
TOP_N     = 20

# Flag months more than this far below the monthly average as data gaps
GAP_THRESHOLD = 0.50      # 50%

REQUEST_PAUSE = 0.5       # seconds between API calls

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORT_PATH = REPORTS_DIR / "inat_signal_test.md"

# ---------------------------------------------------------------------------
# DATE RANGES
# ---------------------------------------------------------------------------

today         = date.today()
current_end   = today
current_start = today.replace(year=today.year - 1)
prior_end     = current_start - timedelta(days=1)
prior_start   = prior_end.replace(year=prior_end.year - 1)

print(f"Current period : {current_start} -> {current_end}")
print(f"Prior period   : {prior_start} -> {prior_end}")
print()

# Shared location parameters reused in every request
LOCATION_PARAMS = {
    "lat":    LAT,
    "lng":    LON,
    "radius": RADIUS_KM,
    "quality_grade": "research,needs_id",
}


# ---------------------------------------------------------------------------
# API HELPERS
# ---------------------------------------------------------------------------

def get(endpoint: str, params: dict) -> dict:
    """Make a single GET request to the iNaturalist API and return JSON."""
    url = f"https://api.inaturalist.org/v1/{endpoint}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_species_counts(d1: date, d2: date) -> pd.DataFrame:
    """
    Call /observations/species_counts for our area and date range.

    iNaturalist pre-aggregates the counts server-side, so we get back
    a ranked list of species with totals -- no need to page through
    individual observations.

    Returns a DataFrame: taxon_id, scientific_name, common_name,
                         display_name, count
    """
    all_rows  = []
    page      = 1
    per_page  = 500   # max allowed for this endpoint

    while True:
        print(f"  species_counts page {page}...", end=" ", flush=True)
        data = get("observations/species_counts", {
            **LOCATION_PARAMS,
            "d1": d1.isoformat(),
            "d2": d2.isoformat(),
            "per_page": per_page,
            "page": page,
        })
        results = data.get("results", [])
        total   = data.get("total_results", 0)
        print(f"{len(results)} species (total: {total})")

        for r in results:
            taxon  = r.get("taxon", {})
            common = taxon.get("preferred_common_name", "")
            sci    = taxon.get("name", "Unknown")
            all_rows.append({
                "taxon_id":        taxon.get("id"),
                "scientific_name": sci,
                "common_name":     common,
                "display_name":    common.capitalize() if common else sci,
                "count":           r.get("count", 0),
            })

        if len(all_rows) >= total or len(results) == 0:
            break
        page += 1
        time.sleep(REQUEST_PAUSE)

    df = pd.DataFrame(all_rows)
    return df.sort_values("count", ascending=False).reset_index(drop=True)


def fetch_total_observations(d1: date, d2: date) -> int:
    """Return the total observation count for a date range (single API call)."""
    data = get("observations", {
        **LOCATION_PARAMS,
        "d1":       d1.isoformat(),
        "d2":       d2.isoformat(),
        "per_page": 0,   # we only want the total count, not actual records
    })
    return data.get("total_results", 0)


def fetch_monthly_totals(d1: date, d2: date) -> pd.DataFrame:
    """
    Fetch total observation counts broken down by month.

    We loop over each calendar month in the date range and make one
    lightweight API call per month (per_page=0 means we only get the
    count, not the actual records -- very fast).
    """
    rows    = []
    current = d1.replace(day=1)

    while current <= d2:
        # Last day of this month
        if current.month == 12:
            month_end = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = current.replace(month=current.month + 1, day=1) - timedelta(days=1)

        month_end = min(month_end, d2)   # don't go past the overall end date

        count = fetch_total_observations(current, month_end)
        label = current.strftime("%Y-%m")
        print(f"  {label}: {count:,} observations")
        rows.append({"year_month": label, "count": count})

        # Advance to the first day of the next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)

        time.sleep(REQUEST_PAUSE)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

def compare_periods(
    current_top: pd.DataFrame,
    prior_all:   pd.DataFrame,
) -> pd.DataFrame:
    """
    Join current top-N species against prior-period counts.
    Adds: prior_count, change, pct_change, declining
    """
    prior_lookup = prior_all.set_index("taxon_id")["count"].to_dict()

    rows = []
    for _, r in current_top.iterrows():
        prior = prior_lookup.get(r["taxon_id"], 0)
        change = r["count"] - prior
        pct    = round(change / prior * 100, 1) if prior > 0 else None
        rows.append({
            **r.to_dict(),
            "prior_count": prior,
            "change":      change,
            "pct_change":  pct,
            "declining":   change < 0,
        })

    return pd.DataFrame(rows)


def flag_monthly_gaps(monthly: pd.DataFrame):
    """Flag months more than GAP_THRESHOLD below the mean."""
    avg = monthly["count"].mean()
    monthly = monthly.copy()
    monthly["vs_avg_pct"]  = ((monthly["count"] - avg) / avg * 100).round(1)
    monthly["gap_flag"]    = monthly["count"] < avg * (1 - GAP_THRESHOLD)
    return monthly, avg


# ---------------------------------------------------------------------------
# REPORT WRITER
# ---------------------------------------------------------------------------

def write_report(
    total_current: int,
    total_prior:   int,
    comparison:    pd.DataFrame,
    monthly:       pd.DataFrame,
    monthly_avg:   float,
) -> None:

    declining   = comparison[comparison["declining"] & (comparison["prior_count"] > 0)]
    new_entries = comparison[comparison["prior_count"] == 0]
    gaps        = monthly[monthly["gap_flag"]]

    lines = []

    # Header
    lines += [
        "# iNaturalist Signal Test -- Front Range Wildlife",
        "",
        f"**Area:** 50-mile radius around Highlands Ranch, CO "
        f"(lat {LAT}, lon {LON})",
        f"**Current period:** {current_start} to {current_end}",
        f"**Prior period:** {prior_start} to {prior_end}",
        f"**Report generated:** {date.today()}",
        "",
        "---",
        "",
    ]

    # Overview
    lines += [
        "## Overview",
        "",
        f"- **{total_current:,}** research-grade observations in the current 12-month period",
        f"- **{total_prior:,}** observations in the prior 12-month period",
        f"- **{len(declining)}** of the top {TOP_N} species show declining observation counts",
        f"- **{len(new_entries)}** species appear in the top {TOP_N} that had zero prior-period observations",
        f"- **{len(gaps)}** month(s) flagged as potential data gaps",
        "",
        "---",
        "",
    ]

    # Top 20 table
    lines += [
        f"## Top {TOP_N} Most-Observed Species (Current Period)",
        "",
        "These are the species with the most community observations in the last 12 months.",
        "**Change %** compares to the prior 12-month period.",
        "A declining trend may reflect a real population shift, reduced observer effort,",
        "or seasonal timing changes -- each flagged species is worth investigating.",
        "",
    ]

    table_rows = []
    for i, row in comparison.iterrows():
        rank  = i + 1
        pct   = f"{row['pct_change']:+.1f}%" if row["pct_change"] is not None else "N/A (new)"
        if row["declining"] and row["prior_count"] > 0:
            trend = "DECLINING"
        elif row["prior_count"] == 0:
            trend = "NEW"
        else:
            trend = "stable/up"
        table_rows.append([
            rank,
            row["display_name"],
            row["scientific_name"],
            f"{row['count']:,}",
            f"{row['prior_count']:,}",
            pct,
            trend,
        ])

    lines.append(tabulate(
        table_rows,
        headers=["Rank", "Common Name", "Scientific Name", "Current", "Prior", "Change %", "Trend"],
        tablefmt="github",
    ))
    lines += ["", "---", ""]

    # Declining species narrative
    lines += ["## Declining Species -- Flagged for Review", ""]
    if declining.empty:
        lines.append("No species in the top 20 showed a decline vs the prior period.")
    else:
        lines.append(
            "The following top-20 species had *fewer* observations in the current period. "
            "This could reflect a real population trend, reduced observer coverage, "
            "or seasonal timing shifts. Each warrants closer review."
        )
        lines.append("")
        for _, row in declining.iterrows():
            pct = f"{row['pct_change']:+.1f}%" if row["pct_change"] is not None else ""
            lines.append(
                f"- **{row['display_name']}** (*{row['scientific_name']}*): "
                f"{row['prior_count']:,} -> {row['count']:,} observations ({pct})"
            )

    lines += ["", "---", ""]

    # Monthly gaps
    lines += [
        "## Monthly Observation Counts and Data Gaps",
        "",
        f"Monthly average: **{monthly_avg:,.0f} observations/month**",
        "",
        "Months flagged as GAP had counts more than 50% below average. "
        "Low counts often reflect reduced observer activity (e.g. winter months) "
        "rather than genuine wildlife absence. Treat flagged months cautiously in trend analysis.",
        "",
    ]

    gap_rows = []
    for _, row in monthly.iterrows():
        flag = "GAP" if row["gap_flag"] else ""
        gap_rows.append([
            row["year_month"],
            f"{row['count']:,}",
            f"{row['vs_avg_pct']:+.1f}%",
            flag,
        ])

    lines.append(tabulate(
        gap_rows,
        headers=["Month", "Observations", "vs. Monthly Avg", "Flag"],
        tablefmt="github",
    ))
    lines += ["", "---", ""]

    # Plain-English verdict
    lines += [
        "## Plain-English Verdict",
        "",
        "### Is this data worth building on?",
        "",
    ]

    if total_current < 500:
        verdict = (
            f"With only {total_current:,} observations, the signal is **thin**. "
            "Consider expanding the search radius or querying a broader region."
        )
    elif total_current < 5000:
        verdict = (
            f"With {total_current:,} observations, the data is **usable but limited**. "
            "Trends for the top species are probably reliable; rare species counts less so. "
            "Worth proceeding to the next phase."
        )
    else:
        verdict = (
            f"With {total_current:,} observations, the iNaturalist data for this region is **excellent**. "
            "The Front Range has a highly active observer community. Species trends for the "
            f"top {TOP_N} are meaningful and worth acting on. "
            "Recommend proceeding to build a full monthly-refresh pipeline."
        )

    lines.append(verdict)
    lines += [
        "",
        "### Recommended next steps",
        "",
        "1. Share this report with a domain expert (e.g., Butterfly Pavilion naturalist) "
        "to sanity-check the species list and declining flags",
        "2. Investigate any DECLINING species above -- cross-reference with eBird or "
        "GBIF to see if the trend holds across data sources",
        "3. If data gaps cluster in winter months, this is expected -- observer activity "
        "drops seasonally in Colorado",
        "4. If signal looks good, next step: build a scheduled pipeline that refreshes "
        "this report monthly and alerts on new declines",
        "",
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport saved -> {REPORT_PATH}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Front Range Wildlife Intelligence System")
    print("Proof of Signal Test -- iNaturalist API")
    print("=" * 60)
    print()

    # 1. Total counts (fast -- single call each)
    print("[1/5] Getting total observation counts...")
    total_current = fetch_total_observations(current_start, current_end)
    total_prior   = fetch_total_observations(prior_start,   prior_end)
    print(f"      Current period: {total_current:,}")
    print(f"      Prior period  : {total_prior:,}\n")

    # 2. Species counts -- current period
    print("[2/5] Fetching species counts (current period)...")
    current_species = fetch_species_counts(current_start, current_end)
    top20 = current_species.head(TOP_N).copy()
    print(f"      -> {len(current_species):,} unique species found\n")

    # 3. Species counts -- prior period (for comparison)
    print("[3/5] Fetching species counts (prior period)...")
    prior_species = fetch_species_counts(prior_start, prior_end)
    print(f"      -> {len(prior_species):,} unique species found\n")

    # 4. Monthly breakdown
    print("[4/5] Fetching monthly observation totals (current period)...")
    monthly_df = fetch_monthly_totals(current_start, current_end)
    monthly_df, monthly_avg = flag_monthly_gaps(monthly_df)
    print()

    # 5. Analyze and write report
    print("[5/5] Analyzing and writing report...")
    comparison = compare_periods(top20, prior_species)
    write_report(
        total_current = total_current,
        total_prior   = total_prior,
        comparison    = comparison,
        monthly       = monthly_df,
        monthly_avg   = monthly_avg,
    )

    print()
    print("Done. Open reports/inat_signal_test.md to read the results.")


if __name__ == "__main__":
    main()
