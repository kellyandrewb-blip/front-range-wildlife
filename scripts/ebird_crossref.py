"""
Front Range Wildlife Intelligence System
eBird Cross-Reference -- Declining Bird Species Validation

Queries the eBird API (Cornell Lab of Ornithology) for the 18 HIGH CONFIDENCE
bird species flagged as declining in our iNaturalist analysis. Compares monthly
occurrence frequency across the same prior and current 12-month periods to
classify each species as CORROBORATED, CONTRADICTED, or INSUFFICIENT DATA.

API strategy:
- GET /v2/data/obs/geo/historic/{y}/{m}/{d}
  One call per monthly sample date (15th of each month) across both periods.
  Returns all species observed in a 50 km radius on that date.
  24 total API calls.

Geographic note:
- eBird's dist parameter is capped at 50 km (31 miles).
- iNaturalist used 80.5 km (50 miles). This is a smaller search area.
  Species with sparse eBird records may partly reflect the tighter radius,
  not genuine absence.

Authentication:
- Requires a free eBird API key stored in the EBIRD_API_KEY environment variable.
- Get one at https://ebird.org/api/keygen
"""

import os
import sys
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
RADIUS_KM = 50          # eBird caps dist at 50 km (iNaturalist used 80.5 km)

# A species needs at least this many total detections across all 24 sample
# dates (both periods combined) to have enough data for a comparison.
MIN_DETECTIONS = 2

# A decline is CORROBORATED if the species appeared on this many fewer
# sample months in the current period vs the prior period.
CORROBORATE_THRESHOLD = 2   # 2+ fewer months = meaningful eBird-level decline

REQUEST_PAUSE = 1.0         # seconds between API calls

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORT_PATH = REPORTS_DIR / "ebird_crossref.md"

EBIRD_BASE = "https://api.ebird.org/v2"


# ---------------------------------------------------------------------------
# API KEY
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("EBIRD_API_KEY")
if not API_KEY:
    print("ERROR: EBIRD_API_KEY environment variable is not set.")
    print("Get a free key at https://ebird.org/api/keygen")
    print("Then set it permanently in PowerShell:")
    print('  [System.Environment]::SetEnvironmentVariable("EBIRD_API_KEY", "your_key", "User")')
    sys.exit(1)

HEADERS = {"x-ebirdapitoken": API_KEY}


# ---------------------------------------------------------------------------
# TARGET SPECIES
#
# The 18 HIGH CONFIDENCE bird species from the iNaturalist declining species
# report (run 2026-03-15). HIGH CONFIDENCE = 10+ independent observers in the
# prior period, making observer-dropout an unlikely explanation.
#
# Keys: common name matching our iNaturalist report
# Values: eBird species codes (Cornell Lab taxonomy, validated at startup)
# ---------------------------------------------------------------------------

SPECIES = {
    "Yellow-billed Loon":             "yblloon",
    "Curve-billed Thrasher":          "cubtra",
    "Glossy Ibis":                    "gloibi",
    "White-winged Scoter":            "whwsco",
    "Varied Thrush":                  "varthr",
    "Swainson's Thrush":              "swathr",
    "Northern Shrike":                "norshr",
    "Cassin's Finch":                 "casfin",
    "Yellow-bellied Sapsucker":       "yebsap",
    "Eastern Screech-Owl":            "easowl1",
    "Virginia's Warbler":             "virwar",
    "Eared Grebe":                    "eargre",
    "Canyon Wren":                    "canwre",
    "Savannah Sparrow":               "savspa",
    "Barrow's Goldeneye":             "bargol",
    "Brown-capped Rosy-Finch":        "bcrfin",
    "Northern Rough-winged Swallow":  "norswi1",
    "American Barn Owl":              "brnowl",
}


# ---------------------------------------------------------------------------
# DATE RANGES  (mirrors the rolling 12-month window used in iNat scripts)
# ---------------------------------------------------------------------------

today         = date.today()
current_end   = today
current_start = today.replace(year=today.year - 1)
prior_end     = current_start - timedelta(days=1)
prior_start   = prior_end.replace(year=prior_end.year - 1)


def sample_dates_for_period(start: date, end: date, n: int = 12) -> list:
    """
    Return n monthly sample dates (the 15th of each month) within the period.

    Starts from the first month where the 15th falls on or after `start`,
    then steps forward one month at a time until n dates are collected
    or `end` is reached.

    Using the 15th avoids edge effects at month boundaries and gives a
    consistent mid-month snapshot of eBird activity.
    """
    samples = []
    year, month = start.year, start.month

    # If the 15th of the start month falls before the period start, skip
    # to the following month so every sample date is inside the window.
    if date(year, month, 15) < start:
        month += 1
        if month > 12:
            month = 1
            year += 1

    while len(samples) < n:
        d = date(year, month, 15)
        if d > end:
            break
        samples.append(d)
        month += 1
        if month > 12:
            month = 1
            year += 1

    return samples


# ---------------------------------------------------------------------------
# API HELPERS
# ---------------------------------------------------------------------------

def ebird_get(endpoint: str, params: dict = None) -> list:
    """
    Make a single GET request to the eBird API v2 and return parsed JSON.

    Retries once on 429 (rate limit) after a 30-second wait.
    All other errors raise immediately.
    """
    url = f"{EBIRD_BASE}/{endpoint}"
    for attempt in range(2):
        resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=30)
        if resp.status_code == 429:
            print(f"\n  [rate limit] waiting 30s before retry...", end=" ", flush=True)
            time.sleep(30)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()


def validate_species_codes() -> dict:
    """
    Query the eBird taxonomy API to confirm each species code in SPECIES
    maps to a recognized eBird taxon.

    Uses a single API call with all 18 codes joined by comma — much faster
    than 18 individual calls.

    Returns a dict of {species_code: common_name_in_ebird} for all resolved
    codes. Prints a warning for any code that eBird doesn't recognize, or
    where the name differs from what we expect (different naming conventions
    between iNaturalist and eBird are common and usually harmless).
    """
    codes_param = ",".join(SPECIES.values())
    data = ebird_get("ref/taxonomy/ebird", {"fmt": "json", "species": codes_param})

    resolved = {entry["speciesCode"]: entry["comName"] for entry in data}

    print(f"  Taxonomy check: {len(resolved)}/{len(SPECIES)} codes resolved")

    for name, code in SPECIES.items():
        if code not in resolved:
            print(f"  WARNING: code '{code}' for '{name}' not found in eBird taxonomy.")
            print(f"           This species will be marked INSUFFICIENT DATA.")
        else:
            ebird_name = resolved[code]
            if ebird_name.lower() != name.lower():
                print(f"  NOTE: '{name}' maps to '{ebird_name}' in eBird "
                      f"(naming difference — proceeding normally).")

    return resolved


def fetch_species_on_date(d: date) -> set:
    """
    Call GET /v2/data/obs/geo/historic/{y}/{m}/{d} for our location.

    Returns a set of eBird species codes for every species observed anywhere
    in the 50 km radius on that specific date.

    maxResults=500 is well above the typical daily observation count for a
    50 km radius. detail=simple reduces payload — we only need speciesCode.
    """
    data = ebird_get(
        f"data/obs/geo/historic/{d.year}/{d.month}/{d.day}",
        {
            "lat":        LAT,
            "lng":        LON,
            "dist":       RADIUS_KM,
            "maxResults": 500,
            "detail":     "simple",
        }
    )
    # data is a list of observation records; extract unique species codes
    return {obs["speciesCode"] for obs in data if "speciesCode" in obs}


# ---------------------------------------------------------------------------
# CORE ANALYSIS
# ---------------------------------------------------------------------------

def build_frequency_table(prior_dates: list, current_dates: list) -> pd.DataFrame:
    """
    For each of the 24 sample dates, fetch all eBird species and record
    whether each of the 18 target species was present (1) or absent (0).

    Returns a DataFrame with one row per target species, classified as:
      CORROBORATED     -- appeared on 2+ fewer current months than prior months
      CONTRADICTED     -- stable or grew on eBird despite iNaturalist decline
      INSUFFICIENT DATA -- fewer than MIN_DETECTIONS total across all 24 dates

    Columns:
      species_name, species_code,
      prior_detections   (months detected out of 12, prior period),
      current_detections (months detected out of 12, current period),
      freq_change        (current - prior, in months; negative = fewer),
      total_detections   (prior + current combined),
      classification
    """
    n_prior   = len(prior_dates)
    n_current = len(current_dates)
    all_dates = prior_dates + current_dates

    target_codes = set(SPECIES.values())

    # presence[code] builds up as a list of 0/1 values in date order:
    # first n_prior entries = prior period, remaining n_current = current period
    presence = {code: [] for code in target_codes}

    print(f"\n  Sampling {len(all_dates)} dates "
          f"({n_prior} prior + {n_current} current)...")
    print()

    for i, d in enumerate(all_dates, start=1):
        period_label = "prior  " if i <= n_prior else "current"
        print(f"  [{i:02d}/{len(all_dates)}] {d}  ({period_label})...",
              end=" ", flush=True)

        observed = fetch_species_on_date(d)
        n_targets_found = sum(1 for code in target_codes if code in observed)

        for code in target_codes:
            presence[code].append(1 if code in observed else 0)

        print(f"{len(observed):,} total species on eBird | "
              f"{n_targets_found}/18 targets detected")

        time.sleep(REQUEST_PAUSE)

    # Aggregate per-species counts and classify
    rows = []
    for name, code in SPECIES.items():
        record        = presence[code]
        prior_hits    = sum(record[:n_prior])
        current_hits  = sum(record[n_prior:])
        total_hits    = prior_hits + current_hits
        freq_change   = current_hits - prior_hits  # negative = fewer current months

        if total_hits < MIN_DETECTIONS:
            classification = "INSUFFICIENT DATA"
        elif freq_change <= -CORROBORATE_THRESHOLD:
            classification = "CORROBORATED"
        else:
            # Includes freq_change of 0, positive, or a small drop of -1
            classification = "CONTRADICTED"

        rows.append({
            "species_name":       name,
            "species_code":       code,
            "prior_detections":   prior_hits,
            "current_detections": current_hits,
            "freq_change":        freq_change,
            "total_detections":   total_hits,
            "classification":     classification,
        })

    df = pd.DataFrame(rows)

    # Sort: CORROBORATED first (worst decline leading), then CONTRADICTED,
    # then INSUFFICIENT DATA. Within CORROBORATED, most negative change first.
    sort_order = {"CORROBORATED": 0, "CONTRADICTED": 1, "INSUFFICIENT DATA": 2}
    df["_sort_key"] = df["classification"].map(sort_order)
    df = (df.sort_values(["_sort_key", "freq_change"])
            .drop(columns=["_sort_key"])
            .reset_index(drop=True))

    return df


# ---------------------------------------------------------------------------
# REPORT WRITER
# ---------------------------------------------------------------------------

def write_report(
    freq_df:       pd.DataFrame,
    prior_dates:   list,
    current_dates: list,
) -> None:

    corroborated = freq_df[freq_df["classification"] == "CORROBORATED"]
    contradicted = freq_df[freq_df["classification"] == "CONTRADICTED"]
    insufficient = freq_df[freq_df["classification"] == "INSUFFICIENT DATA"]

    n_prior   = len(prior_dates)
    n_current = len(current_dates)

    lines = []

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    lines += [
        "# eBird Cross-Reference Report -- Declining Bird Species",
        "",
        f"**Area:** 50 km radius around Highlands Ranch, CO  ",
        f"**Prior period:** {prior_start} to {prior_end}  ",
        f"**Current period:** {current_start} to {current_end}  ",
        f"**eBird data source:** Cornell Lab of Ornithology (ebird.org)  ",
        f"**iNaturalist baseline:** Declining Species Report (2026-03-15)  ",
        f"**Report generated:** {date.today()}",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # HOW THIS WORKS
    # ------------------------------------------------------------------
    lines += [
        "## How This Cross-Reference Works",
        "",
        "Our iNaturalist declining species report flagged 25 bird species with 40%+ "
        "observation drops. 18 of those had 10+ independent observers (HIGH CONFIDENCE). "
        "This report asks: does eBird — a separate bird-specific observation network run "
        "by Cornell Lab — show the same pattern for the same species in the same area?",
        "",
        "**Why this matters:** iNaturalist and eBird are independent datasets with "
        "different observer communities. If both show a decline for the same species, "
        "the signal is much stronger. If eBird shows the species is fine, the iNaturalist "
        "decline may reflect observer behavior rather than genuine ecological change.",
        "",
        "**Sampling approach:** The eBird API does not support continuous 12-month range "
        "queries. Instead, we sampled the 15th of each calendar month across both periods — "
        f"{n_prior} prior dates and {n_current} current dates ({n_prior + n_current} total "
        "API calls). For each date, we recorded whether eBird had any observations of each "
        "target species within 50 km of Highlands Ranch.",
        "",
        "**The metric — monthly occurrence frequency:** How many of the 12 sampled months "
        "did a species appear on eBird? A drop of 2 or more months between periods is "
        "classified as CORROBORATED.",
        "",
        "**Geographic difference:** eBird's radius is capped at 50 km (31 miles). "
        "The iNaturalist analysis used 80.5 km (50 miles). Some species may have "
        "fewer eBird records simply because of this smaller search area — we note this "
        "in the INSUFFICIENT DATA section.",
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
        f"- **{len(corroborated)} CORROBORATED** — eBird also shows a decline; "
        "both datasets point in the same direction",
        f"- **{len(contradicted)} CONTRADICTED** — eBird is stable or growing; "
        "iNaturalist decline may reflect observer behavior, not ecology",
        f"- **{len(insufficient)} INSUFFICIENT DATA** — too few eBird records in "
        "this area to make a comparison",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # FULL RESULTS TABLE
    # ------------------------------------------------------------------
    lines += [
        "## Full Results — All 18 Species",
        "",
        "**Prior / Current** = number of sampled months (out of 12) the species "
        "appeared on eBird. **Change** = current minus prior (negative = fewer months detected).",
        "",
    ]

    table_rows = []
    for _, row in freq_df.iterrows():
        change_str = f"{row['freq_change']:+d}"
        table_rows.append([
            row["species_name"],
            row["prior_detections"],
            row["current_detections"],
            change_str,
            row["classification"],
        ])

    lines.append(tabulate(
        table_rows,
        headers=["Species", "Prior (of 12)", "Current (of 12)", "Change (months)", "Classification"],
        tablefmt="github",
    ))
    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # CORROBORATED
    # ------------------------------------------------------------------
    lines += [
        "## CORROBORATED — Decline Confirmed by eBird",
        "",
    ]

    if corroborated.empty:
        lines.append(
            "None of the 18 species showed a matching decline in eBird data. "
            "This is a meaningful result: it suggests the iNaturalist bird declines "
            "may be driven by observer behavior rather than genuine ecological change. "
            "Cross-referencing with a third data source (e.g., GBIF or state wildlife "
            "surveys) is recommended before drawing conservation conclusions."
        )
    else:
        lines.append(
            f"The following {len(corroborated)} species showed declining occurrence "
            "in eBird data, consistent with the iNaturalist findings. Two independent "
            "datasets pointing in the same direction is meaningful ecological signal."
        )
        lines.append("")
        for _, row in corroborated.iterrows():
            lines.append(
                f"- **{row['species_name']}**: appeared in {row['prior_detections']}/12 "
                f"prior months → {row['current_detections']}/12 current months "
                f"({row['freq_change']:+d} months)"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # CONTRADICTED
    # ------------------------------------------------------------------
    lines += [
        "## CONTRADICTED — eBird Does Not Show a Decline",
        "",
    ]

    if contradicted.empty:
        lines.append("No species fell into the stable or growing category.")
    else:
        lines.append(
            f"The following {len(contradicted)} species appear stable or growing on "
            "eBird despite showing a decline in iNaturalist. This is a flag for "
            "follow-up: the iNaturalist signal may reflect reduced observer effort "
            "rather than an actual population drop."
        )
        lines.append("")
        for _, row in contradicted.iterrows():
            if row["freq_change"] > 0:
                direction = "grew"
            elif row["freq_change"] == 0:
                direction = "unchanged"
            else:
                direction = "small drop, below threshold"
            lines.append(
                f"- **{row['species_name']}**: appeared in {row['prior_detections']}/12 "
                f"prior months → {row['current_detections']}/12 current months "
                f"({row['freq_change']:+d} months — {direction})"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # INSUFFICIENT DATA
    # ------------------------------------------------------------------
    lines += [
        "## INSUFFICIENT DATA — Not Enough eBird Records to Compare",
        "",
    ]

    if insufficient.empty:
        lines.append("All 18 species had enough eBird data for a comparison.")
    else:
        lines.append(
            f"The following {len(insufficient)} species appeared on fewer than "
            f"{MIN_DETECTIONS} total sample dates across both periods. This could mean "
            "the species is genuinely rare in this area on eBird, that birders rarely "
            "report it separately from more common species, or that it falls just outside "
            "the 50 km search radius. Do not interpret this as 'fine' — it means we "
            "cannot confirm or deny the iNaturalist signal with this data."
        )
        lines.append("")
        for _, row in insufficient.iterrows():
            lines.append(
                f"- **{row['species_name']}**: {row['total_detections']} total "
                f"detection(s) across all 24 sample dates"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # PLAIN-ENGLISH INTERPRETATION
    # ------------------------------------------------------------------
    lines += [
        "## What This Means for Butterfly Pavilion",
        "",
    ]

    n_corr = len(corroborated)

    if n_corr >= 10:
        interpretation = (
            f"A strong majority of the flagged species ({n_corr} of 18) are confirmed "
            "by eBird data. Two independent observation networks agree on a pattern of "
            "decline across the Front Range. This is credible ecological signal that "
            "warrants serious attention from conservation staff and is appropriate to "
            "share with partners, funders, or state wildlife agencies."
        )
    elif n_corr >= 5:
        interpretation = (
            f"{n_corr} of 18 species are corroborated by eBird — a meaningful subset "
            "with cross-dataset support. These species should be prioritized for further "
            "investigation. The remaining contradicted or data-poor species are uncertain "
            "and should not be reported as confirmed declines without additional evidence."
        )
    elif n_corr > 0:
        interpretation = (
            f"Only {n_corr} of 18 species are confirmed by eBird. Most of the "
            "iNaturalist bird declines are not reflected in dedicated birding data. "
            "This suggests that the majority of the iNaturalist signals may reflect "
            "changes in observer behavior rather than genuine population drops. "
            "The corroborated species are worth investigating; the others need more "
            "evidence before drawing conservation conclusions."
        )
    else:
        interpretation = (
            "None of the 18 iNaturalist-flagged bird species showed a matching "
            "decline in eBird. This is a strong indicator that the iNaturalist bird "
            "declines are observer-driven, not ecological. These specific findings "
            "should not be used as conservation evidence without investigation from "
            "a third data source or direct field observation."
        )

    lines += [
        interpretation,
        "",
        "### Recommended next steps",
        "",
        "1. **Prioritize CORROBORATED species** — these have support from two independent "
        "datasets and are the strongest candidates for conservation action or further study.",
        "2. **Follow up on CONTRADICTED species** — consult a local birding expert or "
        "cross-reference with GBIF or Colorado Parks & Wildlife survey data before "
        "dismissing the iNaturalist signal entirely.",
        "3. **Treat INSUFFICIENT DATA carefully** — sparse eBird coverage in a 50 km "
        "radius does not mean the species is stable. For these species, the iNaturalist "
        "decline signal remains unconfirmed, not disproven.",
        "",
        "---",
        "",
        f"*Report generated by the Front Range Wildlife Intelligence System. "
        f"eBird data © Cornell Lab of Ornithology (ebird.org). "
        f"iNaturalist data © iNaturalist community contributors. "
        f"Analysis covers a 50 km radius around Highlands Ranch, CO "
        f"(lat {LAT}, lon {LON}).*",
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
    print("eBird Cross-Reference -- Declining Bird Species")
    print("=" * 60)
    print(f"Prior period  : {prior_start} -> {prior_end}")
    print(f"Current period: {current_start} -> {current_end}")
    print(f"Search radius : {RADIUS_KM} km  (eBird max; iNat used 80.5 km)")
    print(f"Target species: {len(SPECIES)}")
    print()

    # Step 1: Confirm all 18 species codes against eBird taxonomy
    print("[1/3] Validating species codes against eBird taxonomy...")
    validate_species_codes()
    print()

    # Step 2: Build sample date lists and fetch observation data
    prior_dates   = sample_dates_for_period(prior_start, prior_end)
    current_dates = sample_dates_for_period(current_start, current_end)

    print(f"[2/3] Fetching eBird historic observations "
          f"({len(prior_dates) + len(current_dates)} API calls)...")
    print(f"      Prior samples  : {prior_dates[0]} to {prior_dates[-1]}")
    print(f"      Current samples: {current_dates[0]} to {current_dates[-1]}")

    freq_df = build_frequency_table(prior_dates, current_dates)

    n_corr  = len(freq_df[freq_df["classification"] == "CORROBORATED"])
    n_cont  = len(freq_df[freq_df["classification"] == "CONTRADICTED"])
    n_insuf = len(freq_df[freq_df["classification"] == "INSUFFICIENT DATA"])

    print(f"\n  Classification results:")
    print(f"    CORROBORATED    : {n_corr}")
    print(f"    CONTRADICTED    : {n_cont}")
    print(f"    INSUFFICIENT DATA: {n_insuf}")
    print()

    # Step 3: Write the report
    print("[3/3] Writing report...")
    write_report(freq_df, prior_dates, current_dates)

    print()
    print("Done. Open reports/ebird_crossref.md to read the results.")


if __name__ == "__main__":
    main()
