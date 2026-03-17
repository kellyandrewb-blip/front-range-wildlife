"""
generate_pdf.py

Converts reports/declining_species.md into a professionally styled PDF
at reports/declining_species.pdf.

Run from the project root:
    python scripts/generate_pdf.py
"""

import os
import re
import markdown
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH   = os.path.join(PROJECT_ROOT, "reports", "declining_species.md")
OUTPUT_PATH  = os.path.join(PROJECT_ROOT, "reports", "declining_species.pdf")

# ---------------------------------------------------------------------------
# Read source markdown
# ---------------------------------------------------------------------------
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    md_text = f.read()

# Extract report date from the metadata block at the top of the file
date_match = re.search(r"\*\*Report generated:\*\*\s*(\S+)", md_text)
report_date = date_match.group(1) if date_match else "2026-03-16"

# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------
body_html = markdown.markdown(
    md_text,
    extensions=["tables", "nl2br"],
)

# ---------------------------------------------------------------------------
# Post-process: stamp CSS classes onto confidence-level table cells
# ---------------------------------------------------------------------------
body_html = body_html.replace(
    "<td>HIGH CONFIDENCE</td>",
    '<td class="conf-high">HIGH CONFIDENCE</td>',
)
body_html = body_html.replace(
    "<td>NEEDS REVIEW</td>",
    '<td class="conf-needs">NEEDS REVIEW</td>',
)
body_html = body_html.replace(
    "<td>OBSERVER EFFECT</td>",
    '<td class="conf-observer">OBSERVER EFFECT</td>',
)
body_html = body_html.replace(
    "<td>Disappeared</td>",
    '<td class="status-disappeared">Disappeared</td>',
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
/* ── Page layout ──────────────────────────────────────────────────────── */
@page {
    size: A4 landscape;
    margin: 18mm 14mm 22mm 14mm;

    @bottom-left {
        content: "Prepared for Butterfly Pavilion  ·  Front Range Wildlife Intelligence System";
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        font-size: 8pt;
        color: #6b7280;
    }
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        font-size: 8pt;
        color: #6b7280;
    }
}

/* ── Base typography ───────────────────────────────────────────────────── */
body {
    font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.5;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}

/* ── Report header banner ──────────────────────────────────────────────── */
.report-header {
    background-color: #2c5f2e;
    color: #ffffff;
    padding: 14px 18px 12px 18px;
    margin-bottom: 20px;
    border-radius: 3px;
}
.report-header .title {
    font-size: 17pt;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin: 0 0 3px 0;
}
.report-header .subtitle {
    font-size: 11pt;
    font-weight: 400;
    opacity: 0.88;
    margin: 0 0 6px 0;
}
.report-header .meta {
    font-size: 8.5pt;
    opacity: 0.75;
    margin: 0;
}

/* ── Headings ──────────────────────────────────────────────────────────── */
h1 { display: none; }   /* title is in the banner; suppress the MD h1 */

h2 {
    font-size: 12pt;
    font-weight: 700;
    color: #1e3a1f;
    border-bottom: 2px solid #2c5f2e;
    padding-bottom: 4px;
    margin-top: 24px;
    margin-bottom: 10px;
}

h3 {
    font-size: 10.5pt;
    font-weight: 700;
    color: #2c5f2e;
    border-left: 4px solid #2c5f2e;
    padding-left: 8px;
    margin-top: 20px;
    margin-bottom: 8px;
}

/* ── Body text ─────────────────────────────────────────────────────────── */
p {
    margin: 0 0 8px 0;
}

ul, ol {
    margin: 0 0 10px 0;
    padding-left: 20px;
}

li {
    margin-bottom: 3px;
}

em {
    font-style: italic;
    color: #374151;
    font-size: 9pt;
}

strong {
    font-weight: 700;
}

hr {
    border: none;
    border-top: 1px solid #d1d5db;
    margin: 16px 0;
}

/* ── Tables ────────────────────────────────────────────────────────────── */
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin-bottom: 16px;
    page-break-inside: auto;
}

thead tr {
    background-color: #2c5f2e;
    color: #ffffff;
}

thead th {
    padding: 6px 8px;
    text-align: left;
    font-weight: 700;
    font-size: 8pt;
    letter-spacing: 0.2px;
    border: none;
}

tbody tr:nth-child(odd) {
    background-color: #ffffff;
}

tbody tr:nth-child(even) {
    background-color: #f0f5ef;
}

tbody tr:hover {
    background-color: #e6f0e6;
}

tbody td {
    padding: 5px 8px;
    border-bottom: 1px solid #e5e7eb;
    vertical-align: middle;
}

/* ── Confidence badges ─────────────────────────────────────────────────── */
td.conf-high {
    background-color: #d1fae5;
    color: #065f46;
    font-weight: 700;
    white-space: nowrap;
}

td.conf-needs {
    background-color: #fef3c7;
    color: #92400e;
    font-weight: 600;
    white-space: nowrap;
}

td.conf-observer {
    background-color: #f3f4f6;
    color: #6b7280;
    white-space: nowrap;
}

/* ── Status: Disappeared ───────────────────────────────────────────────── */
td.status-disappeared {
    color: #991b1b;
    font-weight: 700;
}
"""

# ---------------------------------------------------------------------------
# Assemble full HTML document
# ---------------------------------------------------------------------------
html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
{CSS}
</style>
</head>
<body>

<div class="report-header">
  <div class="title">Front Range Wildlife Intelligence System</div>
  <div class="subtitle">Declining Species Report</div>
  <div class="meta">
    50-mile radius · Highlands Ranch, CO &nbsp;·&nbsp;
    Prior period: Mar 2024 – Mar 2025 &nbsp;·&nbsp;
    Current period: Mar 2025 – Mar 2026 &nbsp;·&nbsp;
    Generated: {report_date}
  </div>
</div>

{body_html}

</body>
</html>"""

# ---------------------------------------------------------------------------
# Render to PDF via Playwright (headless Chromium)
# ---------------------------------------------------------------------------
print("Rendering PDF — this may take 15–30 seconds...")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html_document, wait_until="networkidle")
    page.pdf(
        path=OUTPUT_PATH,
        format="A4",
        landscape=True,
        margin={"top": "18mm", "bottom": "22mm", "left": "14mm", "right": "14mm"},
        print_background=True,   # required for background colours (table stripes, badges, header)
    )
    browser.close()

# ---------------------------------------------------------------------------
# Report file size and page count
# ---------------------------------------------------------------------------
file_size_bytes = os.path.getsize(OUTPUT_PATH)
file_size_kb = file_size_bytes / 1024

# Count pages by scanning the PDF binary for page object markers
with open(OUTPUT_PATH, "rb") as f:
    pdf_bytes = f.read()
page_count = len(re.findall(rb'/Type\s*/Page[^s]', pdf_bytes))

print(f"\n  PDF saved to:  reports/declining_species.pdf")
print(f"  File size:     {file_size_kb:,.1f} KB  ({file_size_bytes:,} bytes)")
print(f"  Pages:         {page_count}")
