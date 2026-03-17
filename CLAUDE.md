# Front Range Wildlife Intelligence System

## Project Description

This project connects free public ecological APIs to surface plain-English conservation insights for under-resourced organizations. The primary partner is the **Butterfly Pavilion** in Westminster, CO. The goal is to build a lightweight intelligence system that monitors wildlife observation trends across the Front Range — starting with iNaturalist data — and eventually delivers automated monthly reports that a non-technical conservation team can act on without needing a data analyst.

---

## Important Context

- **The user is not a developer.** Explain every technical decision as you go. Don't assume familiarity with APIs, Python, pandas, or git. When something surprising happens (like hitting an API limit), explain what it means and why the fix works before implementing it.
- **Always commit after each meaningful milestone.** Each commit message should describe what the code does *and* what it found or changed — future context matters.
- **Target partner:** Butterfly Pavilion, Westminster, CO — a non-profit focused on invertebrate conservation and environmental education. Keep their use case in mind: they need actionable, jargon-free insights, not raw data.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.12 | Primary language. Chosen for its dominance in data/science work and simple one-command execution. |
| `requests` | Makes HTTP calls to external APIs (e.g. iNaturalist). |
| `pandas` | Organizes observation data into tables for counting, sorting, and comparing. |
| `tabulate` | Formats pandas tables into clean Markdown for the output reports. |

Install all dependencies with:
```bash
pip install -r requirements.txt
```

---

## File Structure

```
front-range-wildlife/
│
├── CLAUDE.md                      # This file. Project context for Claude.
├── README.md                      # One-paragraph project description and run instructions.
├── requirements.txt               # Python library dependencies (pip install -r requirements.txt).
│
├── scripts/
│   ├── inat_signal_test.py        # Queries iNaturalist API, analyzes species trends,
│   │                              # and writes the signal test report.
│   ├── declining_species.py       # Identifies species with meaningful observation declines.
│   │                              # Compares prior vs. current 12-month periods across all
│   │                              # species with >= 10 prior observations. Groups results
│   │                              # by taxonomic category. Tunable via DECLINE_THRESHOLD
│   │                              # and MIN_PRIOR_OBS at the top of the file.
│   └── ebird_crossref.py          # Cross-references the 18 HIGH CONFIDENCE bird species
│                                  # from the declining species report against eBird data.
│                                  # Samples 15th of each month across both periods (24 API
│                                  # calls). Classifies each species as CORROBORATED,
│                                  # CONTRADICTED, or INSUFFICIENT DATA.
│                                  # Requires EBIRD_API_KEY environment variable.
│
└── reports/
    ├── inat_signal_test.md        # Auto-generated. Do not edit by hand.
    ├── declining_species.md       # Auto-generated. Do not edit by hand.
    └── ebird_crossref.md          # Auto-generated. Do not edit by hand.
```

---

## How to Run the Analysis

**Signal test** (proof of data quality, ~2–4 min):
```bash
cd C:\Users\User\front-range-wildlife
python scripts/inat_signal_test.py
```
Output saved to `reports/inat_signal_test.md`.

**Declining species detector** (~3 min):
```bash
cd C:\Users\User\front-range-wildlife
python scripts/declining_species.py
```
Output saved to `reports/declining_species.md`.

To adjust sensitivity, edit these two variables at the top of `declining_species.py`:
- `DECLINE_THRESHOLD = 0.40` — flag species that dropped by this fraction or more (0.40 = 40%)
- `MIN_PRIOR_OBS = 10` — ignore species with fewer prior-period observations than this

**eBird cross-reference** (~3 min, requires API key):
```bash
cd C:\Users\User\front-range-wildlife
python scripts/ebird_crossref.py
```
Output saved to `reports/ebird_crossref.md`.

Requires `EBIRD_API_KEY` set as a Windows environment variable (free key from https://ebird.org/api/keygen).
Set it once in PowerShell: `[System.Environment]::SetEnvironmentVariable("EBIRD_API_KEY", "your_key", "User")`

---

## eBird API — Key Facts

- **Free, but requires an API key.** Register at https://ebird.org/api/keygen — instant, no payment.
- **Base URL:** `https://api.ebird.org/v2/`
- **Authentication:** HTTP header `x-ebirdapitoken: YOUR_KEY` on every request.
- **Rate limit:** 10,000 requests per day. Our script uses ~120.
- **Historical data limitation:** Standard "recent" endpoints only look back 30 days. For 12-month comparisons, use `GET /v2/data/obs/{regionCode}/historic/{y}/{m}/{d}`. **Important:** a `geo/historic` lat/lng radius variant does not exist — historic queries require a region code (county or state) in the path, not coordinates.
- **Geographic approach for historic queries:** We query 5 counties (Douglas, Arapahoe, Jefferson, Denver, El Paso) and union the results per sample date. This approximates the 50-mile iNaturalist circle using county boundaries.
- **Key endpoints used:**
  - `GET /v2/ref/taxonomy/ebird?fmt=json&species=code1,code2,...` — validates species codes. One call with all codes comma-joined.
  - `GET /v2/data/obs/{regionCode}/historic/{y}/{m}/{d}` — all species observed in a county on a specific date. Used for monthly sampling.
- **Species codes:** Typically 6 lowercase characters (e.g., `norshr` = Northern Shrike). Validated at script startup. Three codes required correction during development: `yblloon`→`yebloo`, `cubtra`→`cubthr`, `norswi1`→`nrwswa`.

---

## iNaturalist API — Key Facts

- **Free.** No account or API key required for the queries we run.
- **Base URL:** `https://api.inaturalist.org/v1/`
- **Rate limit:** 100 requests per minute. Our script makes ~30–40 requests per run and includes a 0.5-second pause between calls — well within limits.
- **Radius search:** The API supports true circle-based queries using `lat`, `lng`, and `radius` (in kilometers). 50 miles = 80.5 km. This is more accurate than a bounding box.
- **Key endpoints used:**
  - `GET /observations/species_counts` — returns pre-aggregated species totals ranked by observation count. Used for top-20 analysis. Avoids the need to page through hundreds of thousands of individual records.
  - `GET /observations?per_page=0` — returns only the total count for a query, not actual records. Used for monthly gap analysis and overall totals.
- **Pagination limit:** iNaturalist caps unauthenticated queries at 10,000 records (50 pages × 200). This is why the script uses `species_counts` instead of fetching individual observations.
- **Date filtering:** `d1` and `d2` parameters accept `YYYY-MM-DD` format.
- **Quality filter:** Script uses `quality_grade=research,needs_id` to exclude casual/placeholder entries.

---

## GBIF Cross-Reference Results (run: 2026-03-16)

Of the 46 HIGH CONFIDENCE insect species from the declining species report, GBIF cross-reference produced:

- **29 CORROBORATED** — GBIF also shows a 40%+ decline
  - **1 GENUINE MULTI-SOURCE** — Horace's duskywing (*Erynnis horatius*): GBIF has 59% more records than iNaturalist in the prior period (51 vs 32), meaning independent sources confirm the decline
  - **28 LIMITED INDEPENDENT DATA** — GBIF-confirmed decline, but GBIF's counts are within 20% of iNaturalist's, meaning GBIF is mostly iNaturalist data repackaged
- **6 CONTRADICTED** — GBIF stable or smaller decline (Four-spurred assassin bug, Larder beetle, Indiscriminate cuckoo bumble bee, Pale green assassin bug, Delaware skipper, Ferruginous tiger crane fly)
- **11 INSUFFICIENT DATA** — too few GBIF records or no taxon match

**Key finding:** The near-total absence of GENUINE MULTI-SOURCE findings reflects a structural data gap: iNaturalist is the dominant source of insect occurrence records in GBIF for this region. GBIF corroboration for Colorado insects is mostly iNaturalist seen through two windows, not independent validation.

---

## eBird Cross-Reference Results (run: 2026-03-16)

Of the 25 bird species flagged by iNaturalist, 18 had HIGH CONFIDENCE (10+ independent observers). The eBird cross-reference reduced those 18 to **4 corroborated findings** — species where both datasets independently show a decline:

- **Yellow-billed Loon** — 5/12 prior months → 0/12 current on eBird; disappeared from both datasets
- **Curve-billed Thrasher** — 6/12 → 2/12 months on eBird; significant drop in a year-round resident
- **Brown-capped Rosy-Finch** — 4/12 → 0/12 months on eBird; disappeared from both datasets
- **Cassin's Finch** — 11/12 → 9/12 months on eBird; consistent decline across both sources

The remaining 14 species split as: **9 CONTRADICTED** (eBird stable or growing — iNaturalist declines likely observer-driven) and **5 INSUFFICIENT DATA** (Glossy Ibis, White-winged Scoter, Varied Thrush, Northern Shrike, Yellow-bellied Sapsucker — too sparse on eBird to judge).

**Interpretation:** Most iNaturalist bird declines were not confirmed by dedicated birding data. The 4 corroborated species are the priority for conservation follow-up.

---

## Declining Species Detector Results (run: 2026-03-15)

- **1,908** species analyzed (those with >= 10 observations in the prior period)
- **181** species flagged total: **22 disappeared entirely** (zero current observations), **159 declined 40% or more**
- **Insects dominate the decline list** — 83 of 181 flagged species, including 11 that disappeared entirely
- Other flagged groups: Plants 42, Birds 25, Arachnids 12, Fungi 11, Mammals 5
- Notable findings: Grass spiders (175 → 0), Black swallowtail (−76%), Northern leopard frog (−63%), Greater short-horned lizard (−73%), three gentian species all 70%+ down
- Threshold used: 40% decline, minimum 10 prior observations

---

## Signal Test Results (run: 2026-03-15)

These are the baseline findings from the first proof-of-signal run. Use these as a reference point when interpreting future runs.

- **268,242** research-grade observations in the current 12-month period (2025-03-15 to 2026-03-15)
- **184,547** observations in the prior 12-month period — a **+45% year-over-year increase** in observer activity
- **7,737** unique species observed within 50 miles of Highlands Ranch, CO
- **0 of the top 20 species are declining** — ecological signal is healthy
- Top observed species: mule deer, Great Plains yucca, showy milkweed, chokecherry, mallard, red-tailed hawk, black-tailed prairie dog, Canada goose, western honey bee
- **6 months flagged as data gaps** — all in winter (Nov–Mar). This is expected: observer activity drops seasonally in Colorado. It is not a structural data problem.
- **Verdict:** Data quality is excellent. The Front Range has one of the most active iNaturalist observer communities in the region. Recommend proceeding to build a full monthly-refresh pipeline.
