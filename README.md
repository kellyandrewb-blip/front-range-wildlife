# Front Range Wildlife Intelligence System

A lightweight, open-source tool that pulls free public wildlife observation data from iNaturalist and turns it into plain-English conservation reports — no data analyst required.

Built with the **Butterfly Pavilion** (Westminster, CO) in mind, but designed for any conservation organization that wants real ecological intelligence without a research budget or dedicated data staff.

---

## The Problem It Solves

Most wildlife observation data is locked inside platforms that require technical expertise to query, filter, and interpret. Under-resourced conservation organizations — the ones doing the most critical local work — rarely have the staff to extract meaningful signal from that data.

This project automates the work of asking: *What's declining? How confident are we? And what should we pay attention to?* It queries the iNaturalist API (free, no account required), compares year-over-year observation trends, filters out noise caused by changes in observer behavior, and writes the findings to a formatted report that a non-technical conservationist can act on.

---

## What It Found (First Run — March 2026)

Within 50 miles of Highlands Ranch, CO:

- **268,242** research-grade observations in the current 12-month period — up **+45%** year-over-year, indicating a highly active observer community
- **7,737** unique species recorded in the region
- **181 species flagged as declining** across 1,908 analyzed — including 22 that disappeared entirely from the record
- Insects dominate the concern list: **83 flagged species**, including the black swallowtail (−76%), Colorado hairstreak (−88%), and Douglas-fir tussock moth (−55%)
- Other flagged groups: Plants (42), Birds (25), Arachnids (12), Fungi (11), Mammals (5)
- Notable individual findings: northern leopard frog −63%, greater short-horned lizard −73%, three gentian species all down 70%+
- Winter observation gaps (November–March) are seasonal and expected — not a data quality problem
- All flagged species are rated by **confidence level** based on observer count, so you know which declines are statistically meaningful versus potentially explained by one person stopping their walks

---

## Installation

**Requirements:** Python 3.12+

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/front-range-wildlife.git
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
| `requests` | HTTP calls to the iNaturalist API |
| `pandas` | Organizes and compares observation data across periods |
| `tabulate` | Formats results as clean Markdown tables |
| `markdown` | Converts Markdown reports to HTML for PDF rendering |
| `playwright` | Headless Chromium — renders the HTML report to a styled PDF |

Data source: [iNaturalist](https://www.inaturalist.org/) — free, no API key required.

---

## Open Source

This project is open source and at an early stage. If you work in conservation, ecological data, or are interested in building on this for your own region, feel free to open an issue or reach out directly.

Ideas for future direction:
- Support for additional regions or observation radii
- Additional ecological APIs (eBird, GBIF, etc.)
- Richer trend visualizations
- Automated monthly report delivery

---

## Author

Built by Andrew Kelly. kellyandrewb@gmail.com.

---

*Built for the Butterfly Pavilion, Westminster, CO — and for every under-resourced organization doing important conservation work.*
