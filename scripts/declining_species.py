"""
Front Range Wildlife Intelligence System
Declining Species Detector -- iNaturalist API

Identifies species within 50 miles of Highlands Ranch, CO that showed
a meaningful drop in observations between the prior 12-month period and
the current 12-month period.

API strategy:
- /observations/species_counts  -> full ranked species list, both periods
- Both lists joined in memory to identify flagged species
- /observations/observers       -> unique observer count per flagged species,
                                   prior + current period (2 calls per species)
"""

import time
import requests
import pandas as pd
from datetime import date, timedelta
from tabulate import tabulate
from pathlib import Path


# ---------------------------------------------------------------------------
# CONFIGURATION  (adjust these to tune the analysis)
# ---------------------------------------------------------------------------

LAT       = 39.5594
LON       = -104.9719
RADIUS_KM = 80.5          # 50 miles in km

DECLINE_THRESHOLD = 0.40  # Flag species that dropped by this fraction or more (0.40 = 40%)
MIN_PRIOR_OBS     = 10    # Ignore species with fewer than this many prior-period observations

REQUEST_PAUSE = 0.5       # seconds between API calls (stay well within rate limit)

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORT_PATH = REPORTS_DIR / "declining_species.md"

# ---------------------------------------------------------------------------
# DATE RANGES  (current = last 12 months; prior = 12 months before that)
# ---------------------------------------------------------------------------

today         = date.today()
current_end   = today
current_start = today.replace(year=today.year - 1)
prior_end     = current_start - timedelta(days=1)
prior_start   = prior_end.replace(year=prior_end.year - 1)

# Shared location + quality parameters reused in every API request
LOCATION_PARAMS = {
    "lat":           LAT,
    "lng":           LON,
    "radius":        RADIUS_KM,
    "quality_grade": "research,needs_id",
}

# Maps iNaturalist's internal iconic_taxon_name to human-readable group labels
# used in the report. Anything not listed here falls into "Other".
TAXON_GROUP_MAP = {
    "Aves":        "Birds",
    "Insecta":     "Insects",
    "Plantae":     "Plants",
    "Mammalia":    "Mammals",
    "Arachnida":   "Arachnids",
    "Reptilia":    "Reptiles",
    "Amphibia":    "Amphibians",
    "Fungi":       "Fungi",
    "Actinopterygii": "Fish",
}

# Report section order for taxonomic groups
GROUP_ORDER = [
    "Birds", "Insects", "Plants", "Mammals",
    "Arachnids", "Reptiles", "Amphibians", "Fish", "Fungi", "Other",
]


# ---------------------------------------------------------------------------
# API HELPERS  (same pattern as inat_signal_test.py)
# ---------------------------------------------------------------------------

def get(endpoint: str, params: dict) -> dict:
    """
    Make a single GET request to the iNaturalist API and return JSON.

    Retries up to 3 times on 429 (rate limit) responses, waiting 20 seconds
    between attempts. All other errors raise immediately.
    """
    url = f"https://api.inaturalist.org/v1/{endpoint}"
    for attempt in range(3):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            wait = 20
            print(f"\n    [rate limit] waiting {wait}s before retry {attempt + 1}/3...",
                  end=" ", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    # If all retries exhausted, raise on the last response
    resp.raise_for_status()


def fetch_species_counts(d1: date, d2: date, label: str) -> pd.DataFrame:
    """
    Fetch the full ranked species list for our area and date range.

    Paginates through all pages at 500 species/page (iNaturalist's max).
    Captures iconic_taxon_name so we can group species by category later.

    Returns a DataFrame with columns:
        taxon_id, scientific_name, common_name, display_name,
        iconic_taxon_name, group, count
    """
    all_rows = []
    page     = 1
    per_page = 500

    while True:
        print(f"  [{label}] page {page}...", end=" ", flush=True)
        data = get("observations/species_counts", {
            **LOCATION_PARAMS,
            "d1":       d1.isoformat(),
            "d2":       d2.isoformat(),
            "per_page": per_page,
            "page":     page,
        })
        results = data.get("results", [])
        total   = data.get("total_results", 0)
        print(f"{len(results)} species (running total: {len(all_rows) + len(results):,} of {total:,})")

        for r in results:
            taxon       = r.get("taxon", {})
            common      = taxon.get("preferred_common_name", "")
            sci         = taxon.get("name", "Unknown")
            iconic      = taxon.get("iconic_taxon_name", "")
            group       = TAXON_GROUP_MAP.get(iconic, "Other")

            all_rows.append({
                "taxon_id":        taxon.get("id"),
                "scientific_name": sci,
                "common_name":     common,
                "display_name":    common.capitalize() if common else sci,
                "iconic_taxon_name": iconic,
                "group":           group,
                "count":           r.get("count", 0),
            })

        if len(all_rows) >= total or len(results) == 0:
            break
        page += 1
        time.sleep(REQUEST_PAUSE)

    df = pd.DataFrame(all_rows)
    return df.sort_values("count", ascending=False).reset_index(drop=True)


def fetch_regional_observers(d1: date, d2: date) -> int:
    """
    Return the total number of unique observers active in the region
    for a given date range. No taxon filter — this is the region-wide total.

    A single lightweight call: per_page=1 since we only need total_results.
    """
    data = get("observations/observers", {
        **LOCATION_PARAMS,
        "d1":       d1.isoformat(),
        "d2":       d2.isoformat(),
        "per_page": 1,
    })
    return data.get("total_results", 0)


def fetch_observer_counts(decline_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each flagged species, fetch the number of unique observers in both
    the prior and current periods.

    Uses GET /observations/observers with taxon_id + location + date params.
    We only need total_results from each response (the unique observer count),
    so per_page=1 keeps responses tiny.

    One call per species per period = len(decline_df) * 2 total calls.
    Returns the input DataFrame with two new columns added:
        prior_observers, current_observers
    """
    total     = len(decline_df)
    prior_obs  = {}
    current_obs = {}

    for i, (_, row) in enumerate(decline_df.iterrows(), start=1):
        tid  = row["taxon_id"]
        name = row["display_name"]
        print(f"  [{i}/{total}] {name}...", end=" ", flush=True)

        base_params = {**LOCATION_PARAMS, "taxon_id": tid, "per_page": 1}

        prior_data   = get("observations/observers", {**base_params,
                           "d1": prior_start.isoformat(), "d2": prior_end.isoformat()})
        time.sleep(0.7)   # slightly longer pause; observers endpoint is stricter than species_counts

        current_data = get("observations/observers", {**base_params,
                           "d1": current_start.isoformat(), "d2": current_end.isoformat()})
        time.sleep(0.7)

        prior_obs[tid]   = prior_data.get("total_results", 0)
        current_obs[tid] = current_data.get("total_results", 0)
        print(f"prior {prior_obs[tid]} observers / current {current_obs[tid]} observers")

    result = decline_df.copy()
    result["prior_observers"]   = result["taxon_id"].map(prior_obs)
    result["current_observers"] = result["taxon_id"].map(current_obs)
    return result


def assign_credibility(prior_observers: int) -> str:
    """
    Assign a credibility tier based on prior-period unique observer count.

    The tier tells conservation staff how much to trust the decline signal:
      HIGH CONFIDENCE  -- 10+ independent observers recorded this species;
                          a drop is unlikely to be one person stopping
      NEEDS REVIEW     -- 5-9 observers; some independent signal, warrants
                          a closer look before acting
      OBSERVER EFFECT  -- fewer than 5 observers; decline may be explained
                          by 1-2 people stopping participation
    """
    if prior_observers >= 10:
        return "HIGH CONFIDENCE"
    elif prior_observers >= 5:
        return "NEEDS REVIEW"
    else:
        return "OBSERVER EFFECT"


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

def build_decline_table(prior_df: pd.DataFrame, current_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join the two species lists and compute year-over-year change.

    Steps:
    1. Filter prior list to species with >= MIN_PRIOR_OBS observations
    2. For each of those species, look up its current count (0 if absent)
    3. Calculate pct_change and assign a status label

    Status labels:
        "Disappeared"  -- had prior observations, now has zero
        "Declining"    -- dropped by >= DECLINE_THRESHOLD
        (anything else is not flagged and excluded from the output)

    Returns only the flagged (Disappeared + Declining) rows,
    sorted by pct_change ascending (worst first).
    """
    # Build a fast lookup: taxon_id -> current count
    current_lookup = current_df.set_index("taxon_id")["count"].to_dict()

    rows = []
    for _, r in prior_df.iterrows():
        prior_count   = r["count"]
        current_count = current_lookup.get(r["taxon_id"], 0)
        change        = current_count - prior_count
        pct_change    = change / prior_count  # as a fraction, e.g. -0.55 = -55%

        if current_count == 0:
            status = "Disappeared"
        elif pct_change <= -DECLINE_THRESHOLD:
            status = "Declining"
        else:
            continue  # species is stable or growing -- skip

        rows.append({
            "taxon_id":        r["taxon_id"],
            "display_name":    r["display_name"],
            "scientific_name": r["scientific_name"],
            "group":           r["group"],
            "prior_count":     prior_count,
            "current_count":   current_count,
            "pct_change":      round(pct_change * 100, 1),  # convert to % for display
            "status":          status,
        })

    if not rows:
        return pd.DataFrame(columns=[
            "taxon_id", "display_name", "scientific_name", "group",
            "prior_count", "current_count", "pct_change", "status",
        ])

    result = pd.DataFrame(rows)
    # Sort: Disappeared first (pct_change = -100%), then by worst decline
    return result.sort_values("pct_change", ascending=True).reset_index(drop=True)


# ---------------------------------------------------------------------------
# REPORT WRITER
# ---------------------------------------------------------------------------

def write_report(
    prior_total:          int,
    current_total:        int,
    prior_analyzed:       int,
    decline_df:           pd.DataFrame,
    prior_observers_total:   int = 0,
    current_observers_total: int = 0,
) -> None:
    """
    Write declining_species.md.

    Sections:
    1. Header + summary numbers (including credibility tier breakdown)
    2. Ranked tables grouped by taxonomic category (with observer columns)
    3. High confidence findings — one-liner notes for HIGH CONFIDENCE species
    4. Plain-English interpretation
    5. Data limitations note
    """

    disappeared   = decline_df[decline_df["status"] == "Disappeared"]
    declining     = decline_df[decline_df["status"] == "Declining"]
    total_flagged = len(decline_df)

    # Credibility tier counts for summary
    n_high   = len(decline_df[decline_df["credibility"] == "HIGH CONFIDENCE"])
    n_review = len(decline_df[decline_df["credibility"] == "NEEDS REVIEW"])
    n_noise  = len(decline_df[decline_df["credibility"] == "OBSERVER EFFECT"])

    lines = []

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    lines += [
        "# Declining Species Report -- Front Range Wildlife",
        "",
        f"**Area:** 50-mile radius around Highlands Ranch, CO  ",
        f"**Prior period:** {prior_start} to {prior_end}  ",
        f"**Current period:** {current_start} to {current_end}  ",
        f"**Decline threshold:** {int(DECLINE_THRESHOLD * 100)}% or greater drop  ",
        f"**Minimum prior observations:** {MIN_PRIOR_OBS}  ",
        f"**Report generated:** {date.today()}",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # REGIONAL OBSERVER PARTICIPATION
    # ------------------------------------------------------------------
    if prior_observers_total > 0:
        obs_change     = current_observers_total - prior_observers_total
        obs_pct        = round(obs_change / prior_observers_total * 100, 1)
        obs_change_str = f"{obs_pct:+.1f}%"

        if obs_pct <= -10:
            obs_note = (
                f"Observer participation is down {abs(obs_pct):.0f}% region-wide. "
                "This is a meaningful drop in community activity and likely explains "
                "a portion of the species-level declines below — fewer people in the "
                "field means fewer sightings of everything, not just struggling species."
            )
        elif obs_pct >= 10:
            obs_note = (
                f"Observer participation is up {abs(obs_pct):.0f}% region-wide. "
                "More people in the field means more sightings overall, so any "
                "species-level declines below are occurring despite increased observer "
                "effort — making them more ecologically significant, not less."
            )
        else:
            obs_note = (
                f"Observer participation is roughly stable ({obs_change_str} region-wide). "
                "Overall effort has not changed meaningfully between periods, so "
                "species-level declines are less likely to be explained by fewer "
                "people submitting observations."
            )

        lines += [
            "## Regional Observer Participation",
            "",
            f"| Period | Unique Observers |",
            f"|--------|-----------------|",
            f"| Prior ({prior_start.strftime('%b %Y')} – {prior_end.strftime('%b %Y')}) "
            f"| {prior_observers_total:,} |",
            f"| Current ({current_start.strftime('%b %Y')} – {current_end.strftime('%b %Y')}) "
            f"| {current_observers_total:,} |",
            f"| Change | **{obs_change_str}** |",
            "",
            f"*{obs_note}*",
            "",
            "---",
            "",
        ]

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    lines += [
        "## Summary",
        "",
        f"- **{prior_total:,}** total observations in the prior period; "
        f"**{current_total:,}** in the current period",
        f"- **{prior_analyzed:,}** species had at least {MIN_PRIOR_OBS} observations "
        f"in the prior period and were analyzed for decline",
        f"- **{total_flagged}** species flagged: "
        f"**{len(disappeared)}** disappeared entirely, "
        f"**{len(declining)}** declined by {int(DECLINE_THRESHOLD * 100)}% or more",
        "",
        "**Credibility breakdown** (based on number of independent observers in the prior period):",
        f"- **HIGH CONFIDENCE ({n_high})** — 10+ prior observers; decline is unlikely to be "
        f"one person stopping",
        f"- **NEEDS REVIEW ({n_review})** — 5–9 prior observers; worth a closer look",
        f"- **OBSERVER EFFECT ({n_noise})** — fewer than 5 prior observers; decline may reflect "
        f"1–2 people stopping participation",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # RANKED TABLES BY TAXONOMIC GROUP
    # ------------------------------------------------------------------
    lines += [
        "## Flagged Species by Group",
        "",
        "Species are ranked within each group by severity of decline (worst first).  ",
        "**Disappeared** = had observations in the prior period, zero in the current period.  ",
        f"**Declining** = dropped by {int(DECLINE_THRESHOLD * 100)}% or more.  ",
        "**Prior/Curr Observers** = unique people who recorded this species each period.",
        "",
    ]

    present_groups = [g for g in GROUP_ORDER if g in decline_df["group"].values]

    if total_flagged == 0:
        lines.append(
            f"No species with at least {MIN_PRIOR_OBS} prior-period observations "
            f"declined by {int(DECLINE_THRESHOLD * 100)}% or more in the current period."
        )
    else:
        for group in present_groups:
            group_df = decline_df[decline_df["group"] == group]
            if group_df.empty:
                continue

            n_disappeared = len(group_df[group_df["status"] == "Disappeared"])
            n_declining   = len(group_df[group_df["status"] == "Declining"])
            n_high_group  = len(group_df[group_df["credibility"] == "HIGH CONFIDENCE"])
            summary_parts = []
            if n_disappeared:
                summary_parts.append(f"{n_disappeared} disappeared")
            if n_declining:
                summary_parts.append(f"{n_declining} declining")
            if n_high_group:
                summary_parts.append(f"{n_high_group} high confidence")

            lines += [
                f"### {group}  ({', '.join(summary_parts)})",
                "",
            ]

            table_rows = []
            for rank, (_, row) in enumerate(group_df.iterrows(), start=1):
                change_str = "Disappeared" if row["status"] == "Disappeared" \
                             else f"{row['pct_change']:+.1f}%"
                table_rows.append([
                    rank,
                    row["display_name"],
                    row["scientific_name"],
                    f"{row['prior_count']:,}",
                    f"{row['current_count']:,}",
                    change_str,
                    int(row["prior_observers"]),
                    int(row["current_observers"]),
                    row["status"],
                    row["credibility"],
                ])

            lines.append(tabulate(
                table_rows,
                headers=["#", "Common Name", "Scientific Name",
                         "Prior Obs", "Curr Obs", "Change",
                         "Prior Observers", "Curr Observers",
                         "Status", "Confidence"],
                tablefmt="github",
            ))
            lines += ["", ""]

    lines += ["---", ""]

    # ------------------------------------------------------------------
    # HIGH CONFIDENCE FINDINGS
    # ------------------------------------------------------------------
    high_conf_df = decline_df[decline_df["credibility"] == "HIGH CONFIDENCE"].copy()

    lines += [
        "## High Confidence Findings",
        "",
    ]

    if high_conf_df.empty:
        lines.append(
            "No flagged species had 10 or more prior observers. "
            "All declines should be treated cautiously."
        )
    else:
        lines.append(
            f"The following {len(high_conf_df)} species were recorded by 10 or more "
            "independent observers in the prior period. Their declines are less likely "
            "to be explained by a single person stopping participation."
        )
        lines.append("")
        for _, row in high_conf_df.iterrows():
            prior_obs_count = int(row["prior_observers"])
            if row["status"] == "Disappeared":
                obs_note = (
                    f"Recorded by **{prior_obs_count} independent observers** last year; "
                    f"now has **zero observations**. Less likely to be observer noise."
                )
            else:
                obs_note = (
                    f"Recorded by **{prior_obs_count} independent observers** last year; "
                    f"now down **{abs(row['pct_change']):.0f}%**. Less likely to be observer noise."
                )
            lines.append(
                f"- **{row['display_name']}** (*{row['scientific_name']}*): {obs_note}"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # PLAIN-ENGLISH INTERPRETATION
    # ------------------------------------------------------------------
    lines += [
        "## What These Declines May Mean",
        "",
        "A drop in observation counts does not automatically mean a species is disappearing. "
        "iNaturalist data reflects what community observers are recording — so a decline could mean "
        "any of the following:",
        "",
        "- **Real population loss** — the species is genuinely less common in this region. "
        "This is the most serious interpretation and warrants investigation.",
        "- **Reduced observer effort** — fewer people were out looking, or observers shifted to "
        "different areas or seasons. This often affects all species roughly equally.",
        "- **Range contraction** — the species may have shifted its range slightly, moving "
        "outside the 50-mile search radius.",
        "- **Phenological shift** — if a species peaks in a narrow seasonal window and that window "
        "shifted, it may appear less frequently even if the population is stable.",
        "",
        "**'Disappeared' species deserve the most attention.** A species dropping from dozens of "
        "observations to zero is a strong signal that something changed — even if that change "
        "turns out to be observer-driven rather than ecological.",
        "",
    ]

    if total_flagged > 0:
        group_counts = decline_df.groupby("group").size().sort_values(ascending=False)
        top_group    = group_counts.index[0]
        top_count    = group_counts.iloc[0]
        lines.append(
            f"In this report, **{top_group}** has the most flagged species ({top_count}). "
            "This may reflect a real ecological pattern, or it may reflect that this taxonomic "
            "group has the most observers and thus shows the most variance. Cross-referencing "
            "with other data sources is recommended before drawing conclusions."
        )
        lines.append("")

    lines += ["---", ""]

    # ------------------------------------------------------------------
    # DATA LIMITATIONS
    # ------------------------------------------------------------------
    lines += [
        "## Data Limitations",
        "",
        "This report is built on community science data. That comes with important caveats:",
        "",
        "**Observer bias.** Popular, visible species (large birds, deer, flowering plants) "
        "attract far more observers than small invertebrates, fungi, or nocturnal animals. "
        "A rare beetle with 12 prior observations and 0 current observations may not have "
        "disappeared — it may simply have never attracted consistent attention.",
        "",
        "**Effort is not controlled.** This analysis does not adjust for changes in the "
        "number of active observers or total observation effort between periods. "
        "An overall increase or decrease in local iNaturalist activity will affect all species.",
        "",
        "**Seasonal variation.** If the two comparison periods happen to differ in weather "
        "patterns or observer activity timing, apparent declines may be an artifact of timing "
        "rather than genuine change. Winter months (November–March) consistently show lower "
        "counts in Colorado.",
        "",
        "**This is a screening tool, not a verdict.** The purpose of this report is to surface "
        "species worth investigating further — not to confirm that any species is actually "
        "in trouble. Treat every flagged species as a question, not a conclusion.",
        "",
        "---",
        "",
        f"*Report generated by the Front Range Wildlife Intelligence System. "
        f"Data source: iNaturalist (inaturalist.org). "
        f"Analysis covers a 50-mile radius around Highlands Ranch, CO.*",
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Report saved -> {REPORT_PATH}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Front Range Wildlife Intelligence System")
    print("Declining Species Detector")
    print("=" * 60)
    print(f"Prior period  : {prior_start} -> {prior_end}")
    print(f"Current period: {current_start} -> {current_end}")
    print(f"Decline threshold : {int(DECLINE_THRESHOLD * 100)}%")
    print(f"Min prior obs     : {MIN_PRIOR_OBS}")
    print()

    # Step 1: Fetch prior-period species (full list, all pages)
    print("[1/4] Fetching all species from the PRIOR period...")
    prior_df = fetch_species_counts(prior_start, prior_end, label="prior")
    print(f"      -> {len(prior_df):,} total species found in prior period\n")

    # Step 2: Filter to species with enough observations to be meaningful
    prior_filtered = prior_df[prior_df["count"] >= MIN_PRIOR_OBS].copy()
    print(f"      -> {len(prior_filtered):,} species have >= {MIN_PRIOR_OBS} observations "
          f"(the rest are too noisy to analyze)\n")

    # Step 3: Fetch current-period species (full list, all pages)
    print("[2/4] Fetching all species from the CURRENT period...")
    current_df = fetch_species_counts(current_start, current_end, label="current")
    print(f"      -> {len(current_df):,} total species found in current period\n")

    # Step 4: Compute year-over-year changes and flag declines
    print("[3/4] Calculating year-over-year changes and flagging declines...")
    decline_df = build_decline_table(prior_filtered, current_df)

    disappeared = decline_df[decline_df["status"] == "Disappeared"]
    declining   = decline_df[decline_df["status"] == "Declining"]
    print(f"      -> {len(decline_df)} species flagged total")
    print(f"         {len(disappeared)} disappeared (0 current observations)")
    print(f"         {len(declining)} declined by >= {int(DECLINE_THRESHOLD * 100)}%\n")

    if not decline_df.empty:
        print("      Top 5 worst declines:")
        for _, row in decline_df.head(5).iterrows():
            if row["status"] == "Disappeared":
                change_str = "disappeared"
            else:
                change_str = f"{row['pct_change']:+.1f}%"
            print(f"         {row['display_name']} ({row['scientific_name']}): "
                  f"{row['prior_count']} -> {row['current_count']} ({change_str})")
        print()

    # Step 4: Fetch observer counts for each flagged species (2 calls per species)
    print(f"[4/5] Fetching observer counts for {len(decline_df)} flagged species "
          f"({len(decline_df) * 2} API calls)...")
    decline_df = fetch_observer_counts(decline_df)
    decline_df["credibility"] = decline_df["prior_observers"].apply(assign_credibility)

    n_high   = len(decline_df[decline_df["credibility"] == "HIGH CONFIDENCE"])
    n_review = len(decline_df[decline_df["credibility"] == "NEEDS REVIEW"])
    n_noise  = len(decline_df[decline_df["credibility"] == "OBSERVER EFFECT"])
    print(f"\n      Credibility breakdown:")
    print(f"         HIGH CONFIDENCE : {n_high}")
    print(f"         NEEDS REVIEW    : {n_review}")
    print(f"         OBSERVER EFFECT : {n_noise}\n")

    # Step 5: Fetch regional observer totals (2 lightweight calls)
    print("[5/5] Fetching regional observer totals and writing report...")
    prior_observers_total   = fetch_regional_observers(prior_start, prior_end)
    time.sleep(REQUEST_PAUSE)
    current_observers_total = fetch_regional_observers(current_start, current_end)
    obs_pct = round((current_observers_total - prior_observers_total)
                    / prior_observers_total * 100, 1) if prior_observers_total else 0
    print(f"      Prior observers : {prior_observers_total:,}")
    print(f"      Current observers: {current_observers_total:,}  ({obs_pct:+.1f}%)\n")

    prior_total   = prior_df["count"].sum() if not prior_df.empty else 0
    current_total = current_df["count"].sum() if not current_df.empty else 0

    write_report(
        prior_total             = prior_total,
        current_total           = current_total,
        prior_analyzed          = len(prior_filtered),
        decline_df              = decline_df,
        prior_observers_total   = prior_observers_total,
        current_observers_total = current_observers_total,
    )

    print()
    print("Done. Open reports/declining_species.md to read the results.")
    print()

    # Quick console summary
    if decline_df.empty:
        print("No significant declines detected at the current threshold.")
    else:
        by_group = decline_df.groupby("group").size().sort_values(ascending=False)
        print("Flagged species by group:")
        for group, count in by_group.items():
            print(f"  {group}: {count}")


if __name__ == "__main__":
    main()
