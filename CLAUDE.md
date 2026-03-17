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
- **Rate limit:** 10,000 requests per day. Our script uses ~25.
- **Radius search:** Supported via `lat`, `lng`, `dist` (km). The `dist` parameter is **capped at 50 km** (31 miles). iNaturalist uses 80.5 km — this is a known difference documented in the report.
- **Historical data limitation:** Standard endpoints only look back 30 days. For 12-month comparisons we use `GET /v2/data/obs/geo/historic/{y}/{m}/{d}`, which returns all observations submitted on a specific calendar date.
- **Key endpoints used:**
  - `GET /v2/ref/taxonomy/ebird?fmt=json&species=code1,code2,...` — validates species codes and returns common names. Used at startup to confirm our 18-species lookup table.
  - `GET /v2/data/obs/geo/historic/{y}/{m}/{d}` — all observations within a radius on a specific date. Used for monthly sampling.
- **Species codes:** 6-character lowercase codes (e.g., `norshr` = Northern Shrike). The 18-species lookup table is hardcoded in `ebird_crossref.py` and validated at runtime.

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
