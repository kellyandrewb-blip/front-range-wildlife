# eBird Cross-Reference Report -- Declining Bird Species

**Area:** Douglas, Arapahoe, Jefferson, Denver, and El Paso counties, CO  
**Prior period:** 2024-03-15 to 2025-03-15  
**Current period:** 2025-03-16 to 2026-03-16  
**eBird data source:** Cornell Lab of Ornithology (ebird.org)  
**iNaturalist baseline:** Declining Species Report (2026-03-15)  
**Report generated:** 2026-03-16

---

## How This Cross-Reference Works

Our iNaturalist declining species report flagged 25 bird species with 40%+ observation drops. 18 of those had 10+ independent observers (HIGH CONFIDENCE). This report asks: does eBird — a separate bird-specific observation network run by Cornell Lab — show the same pattern for the same species in the same area?

**Why this matters:** iNaturalist and eBird are independent datasets with different observer communities. If both show a decline for the same species, the signal is much stronger. If eBird shows the species is fine, the iNaturalist decline may reflect observer behavior rather than genuine ecological change.

**Sampling approach:** The eBird API does not support continuous 12-month range queries. Instead, we sampled the 15th of each calendar month across both periods — 12 prior dates and 12 current dates (24 sample dates, 5 county queries each = 120 total API calls). For each date, we recorded whether eBird had any observations of each target species across the region.

**The metric — monthly occurrence frequency:** How many of the 12 sampled months did a species appear on eBird? A drop of 2 or more months between periods is classified as CORROBORATED.

**Geographic approach:** The eBird API's historical endpoint uses county-level region codes rather than a lat/lng radius. We queried 5 core Front Range counties within the ~50-mile study area: Douglas (Highlands Ranch), Arapahoe (Cherry Creek), Jefferson (Foothills), Denver, and El Paso (Colorado Springs corridor). This covers comparable territory to the iNaturalist circle, though shaped by county boundaries rather than a perfect circle.

---

## Summary

- **4 CORROBORATED** — eBird also shows a decline; both datasets point in the same direction
- **9 CONTRADICTED** — eBird is stable or growing; iNaturalist decline may reflect observer behavior, not ecology
- **5 INSUFFICIENT DATA** — too few eBird records in this area to make a comparison

---

## Full Results — All 18 Species

**Prior / Current** = number of sampled months (out of 12) the species appeared on eBird. **Change** = current minus prior (negative = fewer months detected).

| Species                       |   Prior (of 12) |   Current (of 12) |   Change (months) | Classification    |
|-------------------------------|-----------------|-------------------|-------------------|-------------------|
| Yellow-billed Loon            |               5 |                 0 |                -5 | CORROBORATED      |
| Curve-billed Thrasher         |               6 |                 2 |                -4 | CORROBORATED      |
| Brown-capped Rosy-Finch       |               4 |                 0 |                -4 | CORROBORATED      |
| Cassin's Finch                |              11 |                 9 |                -2 | CORROBORATED      |
| Canyon Wren                   |               9 |                 8 |                -1 | CONTRADICTED      |
| Savannah Sparrow              |               4 |                 3 |                -1 | CONTRADICTED      |
| Northern Rough-winged Swallow |               6 |                 5 |                -1 | CONTRADICTED      |
| Swainson's Thrush             |               1 |                 1 |                +0 | CONTRADICTED      |
| American Barn Owl             |               1 |                 1 |                +0 | CONTRADICTED      |
| Virginia's Warbler            |               4 |                 5 |                +1 | CONTRADICTED      |
| Barrow's Goldeneye            |               1 |                 2 |                +1 | CONTRADICTED      |
| Eared Grebe                   |              10 |                12 |                +2 | CONTRADICTED      |
| Eastern Screech-Owl           |               4 |                 9 |                +5 | CONTRADICTED      |
| Yellow-bellied Sapsucker      |               1 |                 0 |                -1 | INSUFFICIENT DATA |
| Glossy Ibis                   |               0 |                 0 |                +0 | INSUFFICIENT DATA |
| White-winged Scoter           |               0 |                 0 |                +0 | INSUFFICIENT DATA |
| Varied Thrush                 |               0 |                 0 |                +0 | INSUFFICIENT DATA |
| Northern Shrike               |               0 |                 0 |                +0 | INSUFFICIENT DATA |

---

## CORROBORATED — Decline Confirmed by eBird

The following 4 species showed declining occurrence in eBird data, consistent with the iNaturalist findings. Two independent datasets pointing in the same direction is meaningful ecological signal.

- **Yellow-billed Loon**: appeared in 5/12 prior months → 0/12 current months (-5 months)
- **Curve-billed Thrasher**: appeared in 6/12 prior months → 2/12 current months (-4 months)
- **Brown-capped Rosy-Finch**: appeared in 4/12 prior months → 0/12 current months (-4 months)
- **Cassin's Finch**: appeared in 11/12 prior months → 9/12 current months (-2 months)

---

## CONTRADICTED — eBird Does Not Show a Decline

The following 9 species appear stable or growing on eBird despite showing a decline in iNaturalist. This is a flag for follow-up: the iNaturalist signal may reflect reduced observer effort rather than an actual population drop.

- **Canyon Wren**: appeared in 9/12 prior months → 8/12 current months (-1 months — small drop, below threshold)
- **Savannah Sparrow**: appeared in 4/12 prior months → 3/12 current months (-1 months — small drop, below threshold)
- **Northern Rough-winged Swallow**: appeared in 6/12 prior months → 5/12 current months (-1 months — small drop, below threshold)
- **Swainson's Thrush**: appeared in 1/12 prior months → 1/12 current months (+0 months — unchanged)
- **American Barn Owl**: appeared in 1/12 prior months → 1/12 current months (+0 months — unchanged)
- **Virginia's Warbler**: appeared in 4/12 prior months → 5/12 current months (+1 months — grew)
- **Barrow's Goldeneye**: appeared in 1/12 prior months → 2/12 current months (+1 months — grew)
- **Eared Grebe**: appeared in 10/12 prior months → 12/12 current months (+2 months — grew)
- **Eastern Screech-Owl**: appeared in 4/12 prior months → 9/12 current months (+5 months — grew)

---

## INSUFFICIENT DATA — Not Enough eBird Records to Compare

The following 5 species appeared on fewer than 2 total sample dates across both periods. This could mean the species is genuinely rare in this area on eBird, that birders rarely report it separately from more common species, or that it falls just outside the 50 km search radius. Do not interpret this as 'fine' — it means we cannot confirm or deny the iNaturalist signal with this data.

- **Yellow-bellied Sapsucker**: 1 total detection(s) across all 24 sample dates
- **Glossy Ibis**: 0 total detection(s) across all 24 sample dates
- **White-winged Scoter**: 0 total detection(s) across all 24 sample dates
- **Varied Thrush**: 0 total detection(s) across all 24 sample dates
- **Northern Shrike**: 0 total detection(s) across all 24 sample dates

---

## What This Means for Butterfly Pavilion

Only 4 of 18 species are confirmed by eBird. Most of the iNaturalist bird declines are not reflected in dedicated birding data. This suggests that the majority of the iNaturalist signals may reflect changes in observer behavior rather than genuine population drops. The corroborated species are worth investigating; the others need more evidence before drawing conservation conclusions.

### Recommended next steps

1. **Prioritize CORROBORATED species** — these have support from two independent datasets and are the strongest candidates for conservation action or further study.
2. **Follow up on CONTRADICTED species** — consult a local birding expert or cross-reference with GBIF or Colorado Parks & Wildlife survey data before dismissing the iNaturalist signal entirely.
3. **Treat INSUFFICIENT DATA carefully** — sparse eBird coverage in a 50 km radius does not mean the species is stable. For these species, the iNaturalist decline signal remains unconfirmed, not disproven.

---

*Report generated by the Front Range Wildlife Intelligence System. eBird data © Cornell Lab of Ornithology (ebird.org). iNaturalist data © iNaturalist community contributors. Analysis covers Douglas, Arapahoe, Jefferson, Denver, and El Paso counties, CO (centered on Highlands Ranch, lat 39.5594, lon -104.9719).*