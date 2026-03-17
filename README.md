# Front Range Wildlife Intelligence System

A lightweight, open-source tool that pulls free public wildlife observation data from iNaturalist and turns it into plain-English conservation reports — no data analyst required.

Built with the **Butterfly Pavilion** (Westminster, CO) in mind, but designed for any conservation organization that wants real ecological intelligence without a research budget or dedicated data staff.

---

## The Problem It Solves

Most wildlife observation data is locked inside platforms that require technical expertise to query, filter, and interpret. Under-resourced conservation organizations — the ones doing the most critical local work — rarely have the staff to extract meaningful signal from that data.

This project automates the work of asking: *What's declining? How confident are we? And what should we pay attention to?* It queries multiple public ecological APIs, compares year-over-year observation trends across independent datasets, filters out noise caused by changes in observer behavior, and writes the findings to formatted reports that a non-technical conservationist can act on.

---

## What It Found (March 2026)

Within 50 miles of Highlands Ranch, CO:

**iNaturalist baseline:**
- **268,242** research-grade observations in the current 12-month period — up **+45%** year-over-year, indicating a highly active observer community
- **7,737** unique species recorded in the region
- **181 species flagged as declining** across 1,908 analyzed — including 22 that disappeared entirely from the record
- Insects dominate the concern list: **83 flagged species**, including the black swallowtail (−76%), Colorado hairstreak (−88%), and Douglas-fir tussock moth (−55%)
- Other flagged groups: Plants (42), Birds (25), Arachnids (12), Fungi (11), Mammals (5)
- All flagged species are rated by **confidence level** based on observer count, so you know which declines are statistically meaningful versus potentially explained by one person stopping their walks

**eBird cross-reference (birds):**
- Of 18 high-confidence bird declines, **4 were independently corroborated by eBird**: Yellow-billed Loon, Curve-billed Thrasher, Brown-capped Rosy-Finch, and Cassin's Finch
- 9 were contradicted — eBird showed those species stable or growing, suggesting the iNaturalist signal is observer-driven rather than ecological
- Two independent datasets agreeing is a meaningfully stronger signal than either alone

**GBIF cross-reference (insects):**
- Of 46 high-confidence insect declines, **29 were corroborated by GBIF** — but with an important caveat
- Only **1 species had genuine multi-source corroboration**: Horace's Duskywing, where GBIF holds substantially more records than iNaturalist, meaning independent sources confirm the decline
- The remaining 28 corroborated species are flagged as **limited independent data** — GBIF's insect coverage in Colorado is almost entirely sourced from iNaturalist, so GBIF agreement largely reflects the same observations seen through two windows, not independent validation
- This is an honest finding: it identifies a structural data gap in Colorado insect monitoring, not a verdict that the species are fine

---

## Installation

**Requirements:** Python 3.12+

```bash
# 1. Clone the repository
git clone https://github.com/kellyandrewb-blip/front-range-wildlife.git
cd front-range-wildlife

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install the Chromium browser used for PDF generation
#    (one-time download, ~175 MB)
playwright install chromium
```

---

## Running the Analysis

### Signal test — overall data quality and top species trends (~2–4 min)
```bash
python scripts/inat_signal_test.py
```
Output: `reports/inat_signal_test.md`

### Declining species detector — year-over-year species-level declines (~3 min)
```bash
python scripts/declining_species.py
```
Output: `reports/declining_species.md`

### eBird cross-reference — validate bird declines against Cornell Lab data (~3 min)
```bash
python scripts/ebird_crossref.py
```
Output: `reports/ebird_crossref.md`

Requires a free eBird API key. Register at [ebird.org/api/keygen](https://ebird.org/api/keygen), then set it once in PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable("EBIRD_API_KEY", "your_key_here", "User")
```

### GBIF cross-reference — validate insect declines against global biodiversity data (~3 min)
```bash
python scripts/gbif_crossref.py
```
Output: `reports/gbif_crossref.md`

No API key required. GBIF is fully public.

### Generate PDF report — professional PDF from the declining species report
```bash
python scripts/generate_pdf.py
```
Output: `reports/declining_species.pdf`

**Tuning the declining species detector:** Open `scripts/declining_species.py` and adjust the two variables at the top:
- `DECLINE_THRESHOLD = 0.40` — flag species that dropped by this fraction or more (0.40 = 40%)
- `MIN_PRIOR_OBS = 10` — ignore species seen fewer than this many times in the prior period

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.12 | Primary language |
| `requests` | HTTP calls to iNaturalist, eBird, and GBIF APIs |
| `pandas` | Organizes and compares observation data across periods |
| `tabulate` | Formats results as clean Markdown tables |
| `markdown` | Converts Markdown reports to HTML for PDF rendering |
| `playwright` | Headless Chromium — renders the HTML report to a styled PDF |

Data sources:
- [iNaturalist](https://www.inaturalist.org/) — free, no API key required
- [eBird](https://ebird.org/) (Cornell Lab of Ornithology) — free API key required
- [GBIF](https://www.gbif.org/) (Global Biodiversity Information Facility) — free, no API key required

---

## Open Source

This project is open source and at an early stage. If you work in conservation, ecological data, or are interested in building on this for your own region, feel free to open an issue or reach out directly.

Ideas for future direction:
- Support for additional regions or observation radii
- Automated monthly report delivery
- Richer trend visualizations
- Cross-reference for plants, amphibians, and other taxonomic groups

---

## Author

Built by Andrew Kelly. kellyandrewb@gmail.com.

---

*Built for the Butterfly Pavilion, Westminster, CO — and for every under-resourced organization doing important conservation work.*
