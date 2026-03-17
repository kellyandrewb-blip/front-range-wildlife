"""
Front Range Wildlife Intelligence System
GBIF Cross-Reference -- Declining Insect Species Validation

Queries the GBIF API (Global Biodiversity Information Facility) for the 46 HIGH
CONFIDENCE insect species flagged as declining in our iNaturalist analysis.
Compares GBIF observation counts year-over-year to classify each species as
CORROBORATED, CONTRADICTED, or INSUFFICIENT DATA.

For CORROBORATED species, compares GBIF's prior-period count against iNaturalist's
to assess independence: if GBIF has ≤20% more records than iNaturalist, most of
GBIF's evidence is likely iNaturalist data repackaged (LIMITED INDEPENDENT DATA).
If GBIF has meaningfully more records, independent sources are contributing to
the corroboration (GENUINE MULTI-SOURCE).

API strategy:
- GET /v1/species/match?name={sci_name}
  One call per species to resolve the GBIF taxon key (usageKey).
- GET /v1/occurrence/search?taxonKey={key}&geometry={wkt}&eventDate={d1},{d2}&limit=1
  One call per species per period to get total observation count from response
  metadata. limit=1 minimizes payload -- only the 'count' field is needed.
  Total: ~138 API calls.

Authentication: None required. GBIF read endpoints are fully public and free.

Geographic note:
- iNaturalist used a true 80.5 km radius circle.
- GBIF is queried using a bounding box (rectangle) that approximates that circle.
  The box is slightly larger at the corners, so GBIF may see marginally more
  observations. A decline appearing in GBIF despite this broader coverage is
  a conservative -- and therefore stronger -- signal.
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

LAT = 39.5594
LON = -104.9719

# Bounding box WKT approximating the 50-mile (80.5 km) radius.
# GBIF geometry uses (longitude latitude) coordinate order.
# 80.5 km ≈ 0.725° lat, ≈ 0.940° lon at this location.
GEOMETRY_WKT = (
    "POLYGON(("
    "-105.912 38.834,"
    "-104.032 38.834,"
    "-104.032 40.284,"
    "-105.912 40.284,"
    "-105.912 38.834"
    "))"
)

# Species with fewer GBIF prior-period observations than this are marked
# INSUFFICIENT DATA -- too sparse to draw a meaningful comparison.
MIN_PRIOR_OBS = 5

# A decline is CORROBORATED if GBIF prior→current drops by this fraction or more.
# Matches the iNaturalist threshold used in the declining species report.
DECLINE_THRESHOLD = 0.40

# For CORROBORATED species: if GBIF prior count is within this fraction above
# the iNaturalist prior count, GBIF is mostly iNaturalist data repackaged.
# Flag as LIMITED INDEPENDENT DATA rather than GENUINE MULTI-SOURCE.
INDEPENDENCE_THRESHOLD = 0.20   # GBIF prior <= iNat prior * 1.20 → limited

REQUEST_PAUSE = 0.5             # seconds between API calls

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORT_PATH = REPORTS_DIR / "gbif_crossref.md"

GBIF_BASE = "https://api.gbif.org/v1"


# ---------------------------------------------------------------------------
# DATE RANGES  (mirrors the rolling 12-month window used in iNat scripts)
# ---------------------------------------------------------------------------

today         = date.today()
current_end   = today
current_start = today.replace(year=today.year - 1)
prior_end     = current_start - timedelta(days=1)
prior_start   = prior_end.replace(year=prior_end.year - 1)


# ---------------------------------------------------------------------------
# TARGET SPECIES
#
# The 46 HIGH CONFIDENCE insect species from the iNaturalist declining species
# report (run 2026-03-15). HIGH CONFIDENCE = 10+ independent observers in the
# prior period.
#
# Columns: (common_name, scientific_name, inat_prior, inat_current)
# inat_prior / inat_current are used to assess GBIF independence: if GBIF's
# count is close to iNaturalist's, GBIF isn't adding much new evidence.
# ---------------------------------------------------------------------------

SPECIES = [
    # (common_name,                        scientific_name,                inat_prior, inat_current)
    ("Condylostylus caudatus",             "Condylostylus caudatus",                51,    0),
    ("Diplotaxis",                         "Diplotaxis",                            35,    0),
    ("Chryxus arctic",                     "Oeneis chryxus",                        46,    1),
    ("Sphragisticus nebulosus",            "Sphragisticus nebulosus",               52,    5),
    ("Colorado hairstreak",                "Hypaurotis crysalus",                   25,    3),
    ("Strawberry crown moth",              "Synanthedon bibionipennis",             14,    2),
    ("White slant-line",                   "Tetracis cachexiata",                   12,    2),
    ("Charcoal seed bug",                  "Melacoryphus lateralis",                31,    6),
    ("Arctic fritillary",                  "Boloria chariclea",                     38,    8),
    ("Nessus sphinx",                      "Amphion floridensis",                   32,    7),
    ("Black swallowtail",                  "Papilio polyxenes",                    102,   24),
    ("Lycus sanguinipennis",               "Lycus sanguinipennis",                  31,    8),
    ("St. Lawrence tiger moth",            "Arctia parthenos",                      11,    3),
    ("Coral hairstreak",                   "Satyrium titus",                        18,    5),
    ("Alfalfa looper moth",                "Tathorhynchus exsiccata",               17,    5),
    ("Crocus geometer moths",              "Xanthotype",                            13,    4),
    ("Hedgerow hairstreak",                "Satyrium saepium",                      16,    5),
    ("Three-spotted flea beetle",          "Disonycha triangularis",                32,   10),
    ("Lesser house fly",                   "Fannia canicularis",                    17,    6),
    ("North American tarnished plant bug", "Lygus lineolaris",                      17,    6),
    ("Shiny blue bottle fly",              "Cynomya cadaverina",                    21,    8),
    ("Shortwing stonefly",                 "Claassenia sabulosa",                   13,    5),
    ("Fall webworm moth",                  "Hyphantria cunea",                      20,    8),
    ("Argus tortoise beetle",              "Chelymorpha cassidea",                  10,    4),
    ("Painted schinia moth",               "Schinia volupia",                       41,   17),
    ("Common house fly",                   "Musca domestica",                       25,   11),
    ("Douglas-fir tussock moth",           "Orgyia pseudotsugata",                195,   87),
    ("Snowberry clearwing",                "Hemaris diffinis",                      20,    9),
    ("Pallid-winged grasshopper",          "Trimerotropis pallidipennis",           24,   11),
    ("Parallel leafcutter bee",            "Megachile parallela",                   25,   12),
    ("Estigmene albida",                   "Estigmene albida",                      12,    6),
    ("Arctic blue",                        "Agriades glandon",                      60,   32),
    ("Four-spurred assassin bug",          "Zelus tetracanthus",                    13,    7),
    ("Poplar twiggall fly",                "Euhexomyza schineri",                   26,   14),
    ("Larder beetle",                      "Dermestes lardarius",                   11,    6),
    ("Indiscriminate cuckoo bumble bee",   "Bombus insularis",                      18,   10),
    ("Horace's duskywing",                 "Erynnis horatius",                      32,   18),
    ("Three-banded grasshopper",           "Hadrotettix trifasciatus",              16,    9),
    ("Thinker moth",                       "Lacinipolia meditata",                  23,   13),
    ("Draco skipper",                      "Polites draco",                         23,   13),
    ("Eastern black carpenter ant",        "Camponotus pennsylvanicus",             26,   15),
    ("Isabella tiger moth",                "Pyrrharctia isabella",                  62,   36),
    ("Club-horned grasshopper",            "Aeropedellus clavatus",                 12,    7),
    ("Pale green assassin bug",            "Zelus luridus",                        163,   97),
    ("Delaware skipper",                   "Anatrytone logan",                      30,   18),
    ("Ferruginous tiger crane fly",        "Nephrotoma ferruginea",                 15,    9),
]


# ---------------------------------------------------------------------------
# API HELPERS
# ---------------------------------------------------------------------------

def gbif_get(endpoint: str, params: dict = None) -> dict:
    """
    Make a single GET request to the GBIF API v1 and return parsed JSON.
    Retries once on 429 (rate limit) after a 30-second wait.
    """
    url = f"{GBIF_BASE}/{endpoint}"
    for attempt in range(2):
        resp = requests.get(url, params=params or {}, timeout=30)
        if resp.status_code == 429:
            print(f"\n  [rate limit] waiting 30s...", end=" ", flush=True)
            time.sleep(30)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()


def lookup_taxon_key(scientific_name: str) -> tuple:
    """
    Resolve a scientific name to a GBIF usageKey (numeric taxon identifier).

    Uses GET /v1/species/match which runs GBIF's internal name-matching against
    the GBIF backbone taxonomy.

    Returns (usageKey, match_type):
      match_type is one of EXACT, FUZZY, HIGHERRANK, or NONE.

    Accepted matches:
      EXACT       -- name matched exactly in the taxonomy
      HIGHERRANK  -- matched at genus level (correct for genus-only entries
                     like 'Diplotaxis' and 'Xanthotype'; the usageKey will
                     cover all species in that genus)
      FUZZY       -- accepted only if confidence >= 90 (likely a spelling
                     variant or synonym; low confidence fuzzy matches are
                     too unreliable to query against)

    Returns (None, reason_string) if no usable match found.
    """
    data       = gbif_get("species/match", {"name": scientific_name})
    match_type = data.get("matchType", "NONE")
    confidence = data.get("confidence", 0)
    usage_key  = data.get("usageKey")

    if match_type == "NONE" or usage_key is None:
        return None, "NONE"
    if match_type == "FUZZY" and confidence < 90:
        return None, f"FUZZY_LOW_CONF ({confidence}%)"
    return usage_key, match_type


def fetch_occurrence_count(taxon_key: int, d1: date, d2: date) -> int:
    """
    Return the total GBIF observation count for a taxon in our bounding box
    between d1 and d2 inclusive.

    Uses limit=1 so only one record is returned in the response body, but the
    response metadata always includes 'count' with the true total. This is the
    same pattern as iNaturalist's per_page=0 -- minimal payload, fast call.

    For genus-level taxon keys (e.g., Diplotaxis), GBIF includes observations
    of all species within that genus, which is consistent with how iNaturalist
    recorded these genus-level entries.
    """
    data = gbif_get("occurrence/search", {
        "taxonKey":  taxon_key,
        "geometry":  GEOMETRY_WKT,
        "eventDate": f"{d1.isoformat()},{d2.isoformat()}",
        "limit":     1,
    })
    return data.get("count", 0)


# ---------------------------------------------------------------------------
# CORE ANALYSIS
# ---------------------------------------------------------------------------

def build_results_table() -> pd.DataFrame:
    """
    For each of the 46 target species:
      1. Resolve scientific name to GBIF taxon key (1 API call)
      2. Fetch prior-period observation count (1 API call)
      3. Fetch current-period observation count (1 API call)
      4. Classify as CORROBORATED, CONTRADICTED, or INSUFFICIENT DATA
      5. For CORROBORATED: sub-classify independence based on GBIF vs iNat count

    Returns a DataFrame sorted by: GENUINE MULTI-SOURCE corroborated first,
    then LIMITED INDEPENDENT DATA corroborated, then CONTRADICTED, then
    INSUFFICIENT DATA. Within each group, sorted by worst GBIF decline first.
    """
    rows  = []
    total = len(SPECIES)

    for i, (common, sci, inat_prior, inat_current) in enumerate(SPECIES, start=1):
        print(f"  [{i:02d}/{total}] {common}...", end=" ", flush=True)

        # --- Taxon key lookup ---
        taxon_key, match_type = lookup_taxon_key(sci)
        time.sleep(REQUEST_PAUSE)

        if taxon_key is None:
            print(f"no GBIF match ({match_type})")
            rows.append(_row(common, sci, inat_prior, inat_current,
                             taxon_key=None, match_type=match_type,
                             gbif_prior=0, gbif_current=0,
                             classification="INSUFFICIENT DATA", independence=None))
            continue

        # --- Observation counts ---
        gbif_prior   = fetch_occurrence_count(taxon_key, prior_start, prior_end)
        time.sleep(REQUEST_PAUSE)
        gbif_current = fetch_occurrence_count(taxon_key, current_start, current_end)
        time.sleep(REQUEST_PAUSE)

        # --- Classification ---
        if gbif_prior < MIN_PRIOR_OBS:
            classification = "INSUFFICIENT DATA"
            independence   = None
            print(f"GBIF prior={gbif_prior} (insufficient)")

        else:
            pct_change = (gbif_current - gbif_prior) / gbif_prior

            if pct_change <= -DECLINE_THRESHOLD:
                classification = "CORROBORATED"
                # Independence check: is GBIF drawing on sources beyond iNaturalist?
                # If GBIF prior <= iNat prior * (1 + threshold), GBIF's extra
                # records are ≤20% above iNat -- mostly iNat data repackaged.
                if inat_prior > 0 and gbif_prior <= inat_prior * (1 + INDEPENDENCE_THRESHOLD):
                    independence = "LIMITED INDEPENDENT DATA"
                else:
                    independence = "GENUINE MULTI-SOURCE"
                print(f"CORROBORATED | GBIF {gbif_prior}->{gbif_current} "
                      f"({pct_change*100:+.1f}%) | {independence}")
            else:
                classification = "CONTRADICTED"
                independence   = None
                print(f"CONTRADICTED | GBIF {gbif_prior}->{gbif_current} "
                      f"({pct_change*100:+.1f}%)")

        rows.append(_row(common, sci, inat_prior, inat_current,
                         taxon_key=taxon_key, match_type=match_type,
                         gbif_prior=gbif_prior, gbif_current=gbif_current,
                         classification=classification, independence=independence))

    df = pd.DataFrame(rows)

    # Sort order: GENUINE MULTI-SOURCE → LIMITED INDEPENDENT DATA → CONTRADICTED
    # → INSUFFICIENT DATA. Within each group, worst GBIF % change first.
    group_order = {
        ("CORROBORATED",     "GENUINE MULTI-SOURCE"):     0,
        ("CORROBORATED",     "LIMITED INDEPENDENT DATA"):  1,
        ("CONTRADICTED",     None):                        2,
        ("INSUFFICIENT DATA", None):                       3,
    }
    df["_sort_group"] = df.apply(
        lambda r: group_order.get((r["classification"], r["independence"]), 9), axis=1
    )
    df["_sort_pct"] = df["gbif_pct_change"].fillna(0)
    df = (df.sort_values(["_sort_group", "_sort_pct"])
            .drop(columns=["_sort_group", "_sort_pct"])
            .reset_index(drop=True))
    return df


def _row(common, sci, inat_prior, inat_current,
         taxon_key, match_type, gbif_prior, gbif_current,
         classification, independence) -> dict:
    """Build one result row."""
    gbif_pct = (round((gbif_current - gbif_prior) / gbif_prior * 100, 1)
                if gbif_prior > 0 else None)
    inat_pct = (round((inat_current - inat_prior) / inat_prior * 100, 1)
                if inat_prior > 0 else None)
    return {
        "common_name":     common,
        "scientific_name": sci,
        "taxon_key":       taxon_key,
        "match_type":      match_type,
        "inat_prior":      inat_prior,
        "inat_current":    inat_current,
        "inat_pct_change": inat_pct,
        "gbif_prior":      gbif_prior,
        "gbif_current":    gbif_current,
        "gbif_pct_change": gbif_pct,
        "classification":  classification,
        "independence":    independence,
    }


# ---------------------------------------------------------------------------
# REPORT WRITER
# ---------------------------------------------------------------------------

def write_report(df: pd.DataFrame) -> None:

    corroborated = df[df["classification"] == "CORROBORATED"]
    contradicted = df[df["classification"] == "CONTRADICTED"]
    insufficient = df[df["classification"] == "INSUFFICIENT DATA"]
    genuine      = corroborated[corroborated["independence"] == "GENUINE MULTI-SOURCE"]
    limited      = corroborated[corroborated["independence"] == "LIMITED INDEPENDENT DATA"]

    lines = []

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    lines += [
        "# GBIF Cross-Reference Report -- Declining Insect Species",
        "",
        f"**Area:** Bounding box approximating 50-mile radius around Highlands Ranch, CO  ",
        f"**Prior period:** {prior_start} to {prior_end}  ",
        f"**Current period:** {current_start} to {current_end}  ",
        f"**GBIF data source:** Global Biodiversity Information Facility (gbif.org)  ",
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
        "Our iNaturalist declining species report flagged 46 HIGH CONFIDENCE insect "
        "species with 40%+ observation drops (HIGH CONFIDENCE = 10+ independent "
        "observers in the prior period). This report asks: does GBIF — the Global "
        "Biodiversity Information Facility, which aggregates observations from "
        "iNaturalist, museum collections, government biological surveys, university "
        "research programs, and dozens of other sources — show the same pattern?",
        "",
        "**Why GBIF matters:** A decline appearing in both iNaturalist and GBIF draws "
        "on a much broader evidence base. GBIF corroboration is especially meaningful "
        "when GBIF has substantially more records than iNaturalist — meaning independent "
        "sources are also recording the decline, not just iNaturalist repackaged.",
        "",
        "**The independence caveat:** GBIF aggregates iNaturalist data. For some "
        "species, most GBIF records in our area may simply be iNaturalist observations "
        "under a different roof. Those cases are flagged explicitly as "
        "LIMITED INDEPENDENT DATA.",
        "",
        "**Geographic approach:** GBIF is queried with a bounding box that approximates "
        "the 50-mile iNaturalist circle. The box is slightly larger at the corners, so "
        "GBIF may see marginally more observations. A decline appearing in GBIF despite "
        "this broader coverage is a conservative — and therefore stronger — signal.",
        "",
        "**Data lag note:** GBIF aggregates iNaturalist data on a delay of weeks to "
        "months. Very recent iNaturalist observations (especially in the last 1–3 months "
        "of the current period) may not yet appear in GBIF. This could cause GBIF "
        "current-period counts to be slightly lower than expected, making declines "
        "appear slightly worse in GBIF than they truly are. Interpret results near the "
        "40% threshold with this in mind.",
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
        f"- **{len(corroborated)} CORROBORATED** — GBIF also shows a 40%+ decline",
        f"  - **{len(genuine)} GENUINE MULTI-SOURCE** — GBIF has meaningfully more "
        f"records than iNaturalist; decline confirmed by independent sources",
        f"  - **{len(limited)} LIMITED INDEPENDENT DATA** — GBIF count is close to "
        f"iNaturalist count; corroboration is mostly iNaturalist data re-packaged",
        f"- **{len(contradicted)} CONTRADICTED** — GBIF shows a smaller decline or "
        f"growth; iNaturalist signal may be observer-driven",
        f"- **{len(insufficient)} INSUFFICIENT DATA** — fewer than {MIN_PRIOR_OBS} "
        f"GBIF records in the prior period, or no GBIF taxon match found",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # FULL RESULTS TABLE
    # ------------------------------------------------------------------
    lines += [
        "## Full Results — All 46 Species",
        "",
        "**iNat** = iNaturalist observation counts from the declining species report.  ",
        "**GBIF** = GBIF observation counts for the same geographic area and periods.  ",
        "**Independence** = whether GBIF's corroboration draws on data beyond iNaturalist.",
        "",
    ]

    table_rows = []
    for _, row in df.iterrows():
        gbif_chg = f"{row['gbif_pct_change']:+.1f}%" if row["gbif_pct_change"] is not None else "—"
        inat_chg = f"{row['inat_pct_change']:+.1f}%" if row["inat_pct_change"] is not None else "—"
        indep    = row["independence"] if row["independence"] else "—"
        table_rows.append([
            row["common_name"],
            f"{row['inat_prior']}→{row['inat_current']} ({inat_chg})",
            f"{row['gbif_prior']}→{row['gbif_current']} ({gbif_chg})",
            row["classification"],
            indep,
        ])

    lines.append(tabulate(
        table_rows,
        headers=["Species", "iNat prior→curr", "GBIF prior→curr",
                 "Classification", "Independence"],
        tablefmt="github",
    ))
    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # CORROBORATED — GENUINE MULTI-SOURCE
    # ------------------------------------------------------------------
    lines += [
        "## CORROBORATED — Genuine Multi-Source Decline",
        "",
    ]

    if genuine.empty:
        lines.append(
            "No species had both a GBIF-confirmed 40%+ decline and meaningfully more "
            "GBIF records than iNaturalist. All corroborated findings have limited "
            "independent evidence beyond iNaturalist for this region."
        )
    else:
        lines.append(
            f"The following {len(genuine)} species showed a 40%+ decline in GBIF "
            "AND had substantially more GBIF records than iNaturalist in the prior "
            "period. Independent sources — museum collections, government surveys, or "
            "other observation networks beyond iNaturalist — are also recording the "
            "decline. These are the strongest findings in this report."
        )
        lines.append("")
        for _, row in genuine.iterrows():
            extra     = row["gbif_prior"] - row["inat_prior"]
            extra_pct = round(extra / row["inat_prior"] * 100) if row["inat_prior"] > 0 else 0
            lines.append(
                f"- **{row['common_name']}** (*{row['scientific_name']}*): "
                f"iNat {row['inat_prior']}→{row['inat_current']} ({row['inat_pct_change']:+.1f}%) | "
                f"GBIF {row['gbif_prior']}→{row['gbif_current']} ({row['gbif_pct_change']:+.1f}%) | "
                f"GBIF has {extra:+,} records ({extra_pct}%) beyond iNaturalist"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # CORROBORATED — LIMITED INDEPENDENT DATA
    # ------------------------------------------------------------------
    lines += [
        "## CORROBORATED — Limited Independent Data",
        "",
    ]

    if limited.empty:
        lines.append("No corroborated species fell into the limited independence category.")
    else:
        lines.append(
            f"The following {len(limited)} species showed a 40%+ decline in both "
            "iNaturalist and GBIF, but GBIF's prior-period count is within 20% of "
            "iNaturalist's — meaning most GBIF records are likely iNaturalist "
            "observations repackaged. The decline signal is consistent across sources, "
            "but both sources trace back largely to iNaturalist observers."
        )
        lines.append("")
        for _, row in limited.iterrows():
            inat_share = (round(row["inat_prior"] / row["gbif_prior"] * 100)
                          if row["gbif_prior"] > 0 else 0)
            lines.append(
                f"- **{row['common_name']}** (*{row['scientific_name']}*): "
                f"iNat {row['inat_prior']}→{row['inat_current']} ({row['inat_pct_change']:+.1f}%) | "
                f"GBIF {row['gbif_prior']}→{row['gbif_current']} ({row['gbif_pct_change']:+.1f}%) | "
                f"iNaturalist = ~{inat_share}% of GBIF prior-period records"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # CONTRADICTED
    # ------------------------------------------------------------------
    lines += [
        "## CONTRADICTED — GBIF Does Not Show a Significant Decline",
        "",
    ]

    if contradicted.empty:
        lines.append("No species fell into the contradicted category.")
    else:
        lines.append(
            f"The following {len(contradicted)} species show a 40%+ decline in "
            "iNaturalist but less than a 40% decline (or growth) in GBIF. The "
            "iNaturalist signal may reflect reduced observer effort for these specific "
            "species rather than genuine population loss — or there may be taxonomic "
            "differences in how the two platforms classify observations."
        )
        lines.append("")
        for _, row in contradicted.iterrows():
            gbif_chg = (f"{row['gbif_pct_change']:+.1f}%"
                        if row["gbif_pct_change"] is not None else "—")
            lines.append(
                f"- **{row['common_name']}** (*{row['scientific_name']}*): "
                f"iNat {row['inat_pct_change']:+.1f}% | GBIF {gbif_chg}"
            )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # INSUFFICIENT DATA
    # ------------------------------------------------------------------
    lines += [
        "## INSUFFICIENT DATA",
        "",
        f"The following {len(insufficient)} species had fewer than {MIN_PRIOR_OBS} "
        "GBIF records in the prior period, or could not be matched to a GBIF taxon. "
        "This does not mean the species is stable — GBIF insect coverage in Colorado "
        "is limited outside of iNaturalist, so absence of GBIF data is a data gap, "
        "not a clean bill of health.",
        "",
    ]

    for _, row in insufficient.iterrows():
        if row["taxon_key"] is None:
            reason = f"no GBIF taxon match ({row['match_type']})"
        else:
            reason = f"only {row['gbif_prior']} GBIF records in prior period"
        lines.append(
            f"- **{row['common_name']}** (*{row['scientific_name']}*): {reason}"
        )

    lines += ["", "---", ""]

    # ------------------------------------------------------------------
    # PLAIN-ENGLISH INTERPRETATION
    # ------------------------------------------------------------------
    lines += ["## What This Means for Butterfly Pavilion", ""]

    n_genuine = len(genuine)
    n_limited = len(limited)

    if n_genuine >= 10:
        interp = (
            f"{n_genuine} insect species have genuine multi-source evidence of decline. "
            "Independent data from museum collections, government surveys, and other "
            "observation networks corroborates the iNaturalist findings. This is a "
            "strong conservation signal appropriate to share with state or federal partners."
        )
    elif n_genuine >= 5:
        interp = (
            f"{n_genuine} insect species have genuine multi-source evidence of decline — "
            f"a meaningful subset with strong cross-dataset support. An additional "
            f"{n_limited} are GBIF-confirmed but rely mostly on iNaturalist records. "
            f"Prioritize the {n_genuine} genuine multi-source species for conservation follow-up."
        )
    elif n_genuine > 0:
        interp = (
            f"Only {n_genuine} insect species have truly independent GBIF confirmation. "
            f"An additional {n_limited} are GBIF-confirmed but the evidence is mostly "
            "iNaturalist repackaged. Most iNaturalist insect declines lack confirmation "
            "from independent sources — which likely reflects limited non-iNaturalist "
            "insect survey coverage in Colorado, not necessarily that the species are fine."
        )
    else:
        interp = (
            "None of the 46 insect species have genuinely independent GBIF confirmation. "
            "GBIF records for these species in this region are either too sparse or "
            "predominantly sourced from iNaturalist itself. This is a significant data "
            "gap: it means we cannot independently verify the iNaturalist insect decline "
            "signals with currently available GBIF data."
        )

    lines += [
        interp,
        "",
        "### Why insect GBIF coverage is structurally limited",
        "",
        "Insects are historically underrepresented in museum collections and government "
        "surveys compared to birds, mammals, and plants. In the Colorado Front Range, "
        "iNaturalist is likely the dominant — and in many cases the only — source of "
        "insect occurrence records in GBIF. A lack of independent GBIF confirmation "
        "should not be read as evidence that these insects are stable. It more likely "
        "reflects a data gap than ecological reality.",
        "",
        "### Recommended next steps",
        "",
        "1. **Act on GENUINE MULTI-SOURCE species first** — these have the strongest "
        "evidence base and are appropriate to escalate to conservation partners.",
        "2. **Treat LIMITED INDEPENDENT DATA species as probable but unconfirmed** — "
        "consistent signal across sources, but both sources largely trace back to "
        "iNaturalist observers.",
        "3. **Do not dismiss CONTRADICTED or INSUFFICIENT DATA species** — for insects "
        "in Colorado, GBIF independence is structurally limited. These findings warrant "
        "entomological expert review, not dismissal.",
        "4. **Consider targeted field surveys** for the highest-declining GENUINE "
        "MULTI-SOURCE species to establish ground-truth population data independent "
        "of any observation platform.",
        "",
        "---",
        "",
        f"*Report generated by the Front Range Wildlife Intelligence System. "
        f"GBIF data © GBIF contributors (gbif.org, CC BY 4.0). "
        f"iNaturalist data © iNaturalist community contributors. "
        f"Analysis covers a bounding box approximating the 50-mile radius around "
        f"Highlands Ranch, CO (lat {LAT}, lon {LON}).*",
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
    print("GBIF Cross-Reference -- Declining Insect Species")
    print("=" * 60)
    print(f"Prior period  : {prior_start} -> {prior_end}")
    print(f"Current period: {current_start} -> {current_end}")
    print(f"Target species: {len(SPECIES)}")
    print(f"Auth required : none (GBIF is fully public)")
    print()

    n_calls = len(SPECIES) * 3   # taxon lookup + prior count + current count
    print(f"[1/2] Resolving taxon keys and fetching GBIF counts "
          f"(~{n_calls} API calls)...")
    print()

    df = build_results_table()

    n_genuine = len(df[(df["classification"] == "CORROBORATED") &
                       (df["independence"] == "GENUINE MULTI-SOURCE")])
    n_limited = len(df[(df["classification"] == "CORROBORATED") &
                       (df["independence"] == "LIMITED INDEPENDENT DATA")])
    n_cont    = len(df[df["classification"] == "CONTRADICTED"])
    n_insuf   = len(df[df["classification"] == "INSUFFICIENT DATA"])

    print(f"\n  Classification results:")
    print(f"    CORROBORATED                : {n_genuine + n_limited}")
    print(f"      GENUINE MULTI-SOURCE      : {n_genuine}")
    print(f"      LIMITED INDEPENDENT DATA  : {n_limited}")
    print(f"    CONTRADICTED                : {n_cont}")
    print(f"    INSUFFICIENT DATA           : {n_insuf}")
    print()

    print("[2/2] Writing report...")
    write_report(df)

    print()
    print("Done. Open reports/gbif_crossref.md to read the results.")


if __name__ == "__main__":
    main()
