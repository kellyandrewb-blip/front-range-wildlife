"""
Front Range Wildlife Intelligence System
RMNP Geographic Comparison — Regional vs. Local Decline Drivers

Tests whether the 5 species with genuine multi-source corroboration on the
Front Range are also declining in Rocky Mountain National Park (RMNP). The
hypothesis: if a species is declining in both the urban-edge Front Range AND
the protected wilderness of RMNP, the cause is more likely regional (climate
shift, migration corridor change) than local urban habitat pressure.

API strategy:
- GET /taxa?q={scientific_name}&rank=species&per_page=1
  One call per species to resolve the iNaturalist taxon ID.
- GET /observations?per_page=0&taxon_id={id}&lat=...&lng=...&radius=...&d1=...&d2=...
  Two calls per species (prior + current period) to get total observation
  counts at RMNP. 15 total API calls.

Geographic note:
- Front Range queries used an 80.5 km (50 mile) radius around Highlands Ranch,
  CO (lat 39.5594, lon -104.9719).
- RMNP queries use the same 80.5 km radius centered on Estes Park, CO
  (lat 40.3772, lon -105.5217), the eastern gateway to RMNP and the nearest
  major town to the park center. This provides a comparable geographic footprint.

Date ranges (fixed to match the original declining_species.md run):
- Prior:   2024-03-15 to 2025-03-15
- Current: 2025-03-16 to 2026-03-16
"""

import time
import requests
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

RMNP_LAT  = 40.3772    # Estes Park, CO — eastern gateway to RMNP
RMNP_LON  = -105.5217
RADIUS_KM = 80.5       # 50 miles — matches Front Range query footprint

MIN_RMNP_PRIOR    = 5     # fewer prior observations than this → INSUFFICIENT DATA
DECLINE_THRESHOLD = 0.40  # >=40% drop = declining (matches Front Range methodology)

REQUEST_PAUSE = 0.5   # seconds between API calls

INAT_BASE   = "https://api.inaturalist.org/v1"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORT_PATH = REPORTS_DIR / "rmnp_comparison.md"


# ---------------------------------------------------------------------------
# FIXED DATE RANGES
#
# These must match the original declining_species.md run (2026-03-15) exactly.
# Using rolling windows would shift the comparison window by ~2 days and make
# Front Range counts non-comparable to RMNP counts.
# ---------------------------------------------------------------------------

PRIOR_START   = date(2024, 3, 15)
PRIOR_END     = date(2025, 3, 15)
CURRENT_START = date(2025, 3, 16)
CURRENT_END   = date(2026, 3, 16)


# ---------------------------------------------------------------------------
# TARGET SPECIES
#
# The 5 species with genuine multi-source corroboration from the Front Range
# analysis: 4 birds corroborated by eBird, 1 insect corroborated by GBIF.
#
# Observation counts sourced from:
#   reports/declining_species.md  (run 2026-03-15)
#   reports/ebird_crossref.md     (run 2026-03-16) — bird corroboration
#   reports/gbif_crossref.md      (run 2026-03-16) — insect corroboration
#
# habitat_mismatch=True flags species that are not ecologically expected at
# RMNP. INSUFFICIENT DATA for these species does not mean "too few records to
# judge" — it means the comparison is structurally uninformative because the
# species has no suitable habitat in the comparison area. This distinction
# matters for interpreting results.
# ---------------------------------------------------------------------------

SPECIES = [
    {
        "common":           "Yellow-billed Loon",
        "sci":              "Gavia adamsii",
        "fr_prior":         15,
        "fr_current":       0,
        "habitat_mismatch": True,
        "mismatch_note": (
            "A large diving bird of arctic coastal waters and large northern lakes. "
            "Its Front Range presence represents rare winter visits to large reservoirs — "
            "habitat entirely absent from RMNP's mountain terrain. "
            "The comparison cannot be made: absence in RMNP would tell us nothing meaningful."
        ),
    },
    {
        "common":           "Curve-billed Thrasher",
        "sci":              "Toxostoma curvirostre",
        "fr_prior":         12,
        "fr_current":       0,
        "habitat_mismatch": True,
        "mismatch_note": (
            "A desert scrub species native to the Sonoran and Chihuahuan desert, reaching "
            "the northern edge of its range in dry urban-edge habitat on the Front Range. "
            "RMNP's montane and subalpine zones contain none of that habitat. "
            "The comparison cannot be made: this species is simply not expected there."
        ),
    },
    {
        "common":           "Brown-capped Rosy-Finch",
        "sci":              "Leucosticte australis",
        "fr_prior":         28,
        "fr_current":       16,
        "habitat_mismatch": False,
        "mismatch_note":    None,
    },
    {
        "common":           "Cassin's Finch",
        "sci":              "Haemorhous cassinii",
        "fr_prior":         17,
        "fr_current":       5,
        "habitat_mismatch": False,
        "mismatch_note":    None,
    },
    {
        "common":           "Horace's Duskywing",
        "sci":              "Erynnis horatius",
        "fr_prior":         32,
        "fr_current":       18,
        "habitat_mismatch": False,
        "mismatch_note":    None,
    },
]


# ---------------------------------------------------------------------------
# API HELPERS
# ---------------------------------------------------------------------------

def inat_get(endpoint: str, params: dict) -> dict:
    """
    GET request to iNaturalist API v1. Retries up to 3 times on rate limit (429).
    """
    url = f"{INAT_BASE}/{endpoint}"
    for attempt in range(3):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            print(f"\n  [rate limit] waiting 20s (attempt {attempt + 1}/3)...", end=" ", flush=True)
            time.sleep(20)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()


def resolve_taxon_id(scientific_name: str) -> int | None:
    """
    Resolve a scientific name to an iNaturalist taxon ID.
    Returns None if no match found.
    """
    data = inat_get("taxa", {"q": scientific_name, "rank": "species", "per_page": 1})
    results = data.get("results", [])
    if not results:
        return None
    return results[0]["id"]


def fetch_obs_count(taxon_id: int, d1: date, d2: date) -> int:
    """
    Return iNaturalist observation count for a taxon within 50 miles of RMNP.
    Uses per_page=0 so only metadata is returned — minimal payload, fast call.
    """
    data = inat_get("observations", {
        "taxon_id":      taxon_id,
        "lat":           RMNP_LAT,
        "lng":           RMNP_LON,
        "radius":        RADIUS_KM,
        "d1":            d1.isoformat(),
        "d2":            d2.isoformat(),
        "quality_grade": "research,needs_id",
        "per_page":      0,
    })
    return data.get("total_results", 0)


# ---------------------------------------------------------------------------
# CLASSIFICATION
# ---------------------------------------------------------------------------

def classify(sp: dict) -> str:
    if sp["habitat_mismatch"]:
        return "INSUFFICIENT DATA"
    rmnp_prior = sp["rmnp_prior"]
    if rmnp_prior < MIN_RMNP_PRIOR:
        return "INSUFFICIENT DATA"
    change = (sp["rmnp_current"] - rmnp_prior) / rmnp_prior
    if change <= -DECLINE_THRESHOLD:
        return "REGIONAL DECLINE"
    return "LOCAL PRESSURE"


def fmt_change(prior: int, current: int) -> str:
    if prior == 0:
        return "n/a"
    if current == 0:
        return "Disappeared (-100%)"
    pct = (current - prior) / prior * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


# ---------------------------------------------------------------------------
# REPORT GENERATION
# ---------------------------------------------------------------------------

def generate_report(species_data: list) -> str:
    run_date = date.today().isoformat()
    lines = []

    lines += [
        "# RMNP Geographic Comparison -- Regional vs. Local Decline Drivers",
        "",
        f"**Front Range area:** 50-mile radius around Highlands Ranch, CO (lat 39.5594, lon -104.9719)  ",
        f"**RMNP area:** 50-mile radius around Estes Park, CO (lat 40.3772, lon -105.5217)  ",
        f"**Prior period:** {PRIOR_START} to {PRIOR_END}  ",
        f"**Current period:** {CURRENT_START} to {CURRENT_END}  ",
        f"**Report generated:** {run_date}",
        "",
        "---",
        "",
        "## Why RMNP?",
        "",
        "Rocky Mountain National Park is the nearest large protected wilderness to the Front Range "
        "corridor and sits in the same latitude band (~40 N) with overlapping elevational gradients. "
        "Critically, it has minimal urban footprint, making it a reasonable control site for separating "
        "local habitat pressure from regional-scale drivers.",
        "",
        "The logic is straightforward: if a species is declining in *both* the urban-edge Front Range "
        "*and* the protected interior of RMNP, the cause is more likely regional -- climate shifts, "
        "drought, or changes in migratory corridors -- than anything specific to urban development. "
        "If a species is declining on the Front Range but holding steady in RMNP, local habitat "
        "pressure becomes a stronger explanation.",
        "",
        "**A note on habitat mismatch:** Two of the five species (Yellow-billed Loon and Curve-billed "
        "Thrasher) are structurally ill-suited for this comparison. Not because the RMNP record count "
        "is too small -- but because those species have no meaningful habitat within RMNP's range. "
        "INSUFFICIENT DATA for those two means *the comparison cannot be made*, not *the sample is "
        "too small to judge*. They require a different control site entirely.",
        "",
        "---",
        "",
        "## Results Summary",
        "",
        "| Species | FR Prior | FR Current | FR Change | RMNP Prior | RMNP Current | RMNP Change | Classification |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for sp in species_data:
        fr_change   = fmt_change(sp["fr_prior"], sp["fr_current"])
        rmnp_change = (
            "—" if sp["habitat_mismatch"]
            else fmt_change(sp["rmnp_prior"], sp["rmnp_current"])
        )
        rmnp_prior   = "—" if sp["habitat_mismatch"] else sp["rmnp_prior"]
        rmnp_current = "—" if sp["habitat_mismatch"] else sp["rmnp_current"]
        lines.append(
            f"| {sp['common']} | {sp['fr_prior']} | {sp['fr_current']} | {fr_change} "
            f"| {rmnp_prior} | {rmnp_current} | {rmnp_change} | {sp['classification']} |"
        )

    lines += ["", "---", "", "## Species Notes", ""]

    for sp in species_data:
        lines.append(f"### {sp['common']} (*{sp['sci']}*)")
        lines.append("")
        classification = sp["classification"]
        fr_change_str  = fmt_change(sp["fr_prior"], sp["fr_current"])

        if sp["habitat_mismatch"]:
            lines.append("**Classification: INSUFFICIENT DATA — habitat mismatch**")
            lines.append("")
            lines.append(sp["mismatch_note"])
            lines.append("")
            lines.append(
                f"Front Range showed {fr_change_str} ({sp['fr_prior']} to {sp['fr_current']} observations). "
                "To test whether this decline is driven by local factors, a comparison site with "
                "suitable habitat is needed. RMNP cannot serve that role for this species."
            )

        elif classification == "INSUFFICIENT DATA":
            rp = sp["rmnp_prior"]
            lines.append("**Classification: INSUFFICIENT DATA — sparse RMNP record**")
            lines.append("")
            lines.append(
                f"RMNP had only {rp} prior-period observation{'s' if rp != 1 else ''}, "
                f"below the minimum of {MIN_RMNP_PRIOR} needed for a reliable comparison. "
                f"Front Range showed {fr_change_str} ({sp['fr_prior']} to {sp['fr_current']} observations). "
                "The RMNP data is too sparse to classify the decline as regional or local. "
                "A comparison site with higher observer activity for this species would be needed."
            )

        elif classification == "REGIONAL DECLINE":
            rmnp_change_str = fmt_change(sp["rmnp_prior"], sp["rmnp_current"])
            lines.append("**Classification: REGIONAL DECLINE**")
            lines.append("")
            lines.append(
                f"Front Range: {sp['fr_prior']} to {sp['fr_current']} observations ({fr_change_str}). "
                f"RMNP: {sp['rmnp_prior']} to {sp['rmnp_current']} observations ({rmnp_change_str}). "
                "Both sites show a meaningful decline across the same period. This pattern is more "
                "consistent with a regional driver -- shifting climate conditions, drought stress, or "
                "changes in migratory routes -- than with urban habitat pressure on the Front Range. "
                "A local conservation response is unlikely to address the root cause here; the signal "
                "warrants attention at the range-wide level."
            )

        else:  # LOCAL PRESSURE
            rmnp_change_str = fmt_change(sp["rmnp_prior"], sp["rmnp_current"])
            lines.append("**Classification: LOCAL PRESSURE**")
            lines.append("")
            lines.append(
                f"Front Range: {sp['fr_prior']} to {sp['fr_current']} observations ({fr_change_str}). "
                f"RMNP: {sp['rmnp_prior']} to {sp['rmnp_current']} observations ({rmnp_change_str}). "
                "The Front Range is declining while RMNP appears stable or growing -- the pattern you "
                "would expect if something specific to the urban-edge environment is driving the decline. "
                "Habitat fragmentation, loss of key plant communities, pesticide exposure, or land-use "
                "change on the Front Range are worth investigating. The RMNP population suggests the "
                "species is not in regional trouble."
            )

        lines.append("")

    # Summary section
    regional_list  = [sp for sp in species_data if sp["classification"] == "REGIONAL DECLINE"]
    local_list     = [sp for sp in species_data if sp["classification"] == "LOCAL PRESSURE"]
    insufficient   = [sp for sp in species_data if sp["classification"] == "INSUFFICIENT DATA"]
    mismatch_list  = [sp for sp in species_data if sp["habitat_mismatch"]]
    sparse_list    = [sp for sp in insufficient if not sp["habitat_mismatch"]]

    lines += ["---", "", "## Conservation Implications", ""]

    lines.append(f"Of the 5 species with genuine multi-source corroboration:")
    lines.append("")
    lines.append(f"- **{len(regional_list)} REGIONAL DECLINE** -- declining in both Front Range and RMNP")
    lines.append(f"- **{len(local_list)} LOCAL PRESSURE** -- declining on Front Range, stable or growing in RMNP")
    lines.append(f"- **{len(insufficient)} INSUFFICIENT DATA** -- comparison not possible")
    if mismatch_list:
        names = ", ".join(sp["common"] for sp in mismatch_list)
        lines.append(f"  - {len(mismatch_list)} due to habitat mismatch ({names})")
    if sparse_list:
        names = ", ".join(sp["common"] for sp in sparse_list)
        lines.append(f"  - {len(sparse_list)} due to sparse RMNP records ({names})")
    lines.append("")

    if regional_list:
        names = ", ".join(f"**{sp['common']}**" for sp in regional_list)
        lines.append(
            f"The regional decline finding -- {names} -- is the most important result for "
            "conservation prioritization. When a species is declining across both an urban-edge "
            "corridor *and* a protected wilderness in the same time window, the cause is unlikely "
            "to be something a local land manager can address by improving a habitat patch. These "
            "species should be flagged for monitoring at the regional scale, with attention to "
            "range-wide population trends and climate vulnerability assessments."
        )
        lines.append("")

    if local_list:
        names = ", ".join(f"**{sp['common']}**" for sp in local_list)
        lines.append(
            f"The local pressure finding -- {names} -- points to a more tractable conservation "
            "problem. Stable or growing populations in RMNP suggest the species is not in regional "
            "trouble; something specific to the Front Range urban-edge environment is suppressing "
            "observations. Habitat fragmentation, loss of specific plant or scrub communities, or "
            "land-use changes in the corridor are worth investigating as likely causes."
        )
        lines.append("")

    if mismatch_list:
        lines.append(
            "Yellow-billed Loon and Curve-billed Thrasher remain unresolved by this comparison. "
            "Both disappeared from the Front Range record, but RMNP is an ecologically inappropriate "
            "reference site for either. Yellow-billed Loon would need a comparison against other "
            "large-reservoir or coastal winter habitat. Curve-billed Thrasher would need a comparison "
            "against undisturbed desert scrub habitat to the south or east. The disappearance of both "
            "species from the Front Range is real, but its cause cannot be diagnosed with this dataset."
        )
        lines.append("")

    lines += [
        "---",
        "",
        "*Data source: iNaturalist (research-grade and needs-ID observations). "
        "Front Range counts sourced from reports/declining_species.md (run 2026-03-15). "
        "RMNP counts queried live at report generation time.*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("RMNP Geographic Comparison")
    print(f"  RMNP center: Estes Park, CO ({RMNP_LAT}, {RMNP_LON}), {RADIUS_KM} km radius")
    print(f"  Prior:   {PRIOR_START} to {PRIOR_END}")
    print(f"  Current: {CURRENT_START} to {CURRENT_END}")
    print()

    # Step 1: resolve taxon IDs
    print("Resolving taxon IDs...")
    for sp in SPECIES:
        print(f"  {sp['common']} ({sp['sci']})...", end=" ", flush=True)
        taxon_id = resolve_taxon_id(sp["sci"])
        sp["taxon_id"] = taxon_id
        print(f"taxon_id={taxon_id}")
        time.sleep(REQUEST_PAUSE)
    print()

    # Step 2: fetch RMNP observation counts (skip habitat mismatches)
    print("Fetching RMNP observation counts...")
    for sp in SPECIES:
        if sp["habitat_mismatch"]:
            sp["rmnp_prior"]   = 0
            sp["rmnp_current"] = 0
            print(f"  {sp['common']}: skipped (habitat mismatch)")
            continue
        if sp["taxon_id"] is None:
            sp["rmnp_prior"]   = 0
            sp["rmnp_current"] = 0
            print(f"  {sp['common']}: skipped (no taxon ID resolved)")
            continue
        print(f"  {sp['common']}...", end=" ", flush=True)
        prior_count   = fetch_obs_count(sp["taxon_id"], PRIOR_START, PRIOR_END)
        time.sleep(REQUEST_PAUSE)
        current_count = fetch_obs_count(sp["taxon_id"], CURRENT_START, CURRENT_END)
        time.sleep(REQUEST_PAUSE)
        sp["rmnp_prior"]   = prior_count
        sp["rmnp_current"] = current_count
        print(f"prior={prior_count}, current={current_count}")
    print()

    # Step 3: classify
    print("Classifying...")
    for sp in SPECIES:
        sp["classification"] = classify(sp)
        print(f"  {sp['common']}: {sp['classification']}")
    print()

    # Step 4: write report
    print("Writing report...")
    report = generate_report(SPECIES)
    REPORTS_DIR.mkdir(exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"  Saved: {REPORT_PATH}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
