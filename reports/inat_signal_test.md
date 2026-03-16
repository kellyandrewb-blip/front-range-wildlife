# iNaturalist Signal Test -- Front Range Wildlife

**Area:** 50-mile radius around Highlands Ranch, CO (lat 39.5594, lon -104.9719)
**Current period:** 2025-03-15 to 2026-03-15
**Prior period:** 2024-03-14 to 2025-03-14
**Report generated:** 2026-03-15

---

## Overview

- **268,242** research-grade observations in the current 12-month period
- **184,547** observations in the prior 12-month period
- **0** of the top 20 species show declining observation counts
- **0** species appear in the top 20 that had zero prior-period observations
- **6** month(s) flagged as potential data gaps

---

## Top 20 Most-Observed Species (Current Period)

These are the species with the most community observations in the last 12 months.
**Change %** compares to the prior 12-month period.
A declining trend may reflect a real population shift, reduced observer effort,
or seasonal timing changes -- each flagged species is worth investigating.

|   Rank | Common Name                    | Scientific Name       | Current   | Prior   | Change %   | Trend     |
|--------|--------------------------------|-----------------------|-----------|---------|------------|-----------|
|      1 | Mule deer                      | Odocoileus hemionus   | 1,330     | 1,259   | +5.6%      | stable/up |
|      2 | Great plains yucca             | Yucca glauca          | 1,284     | 574     | +123.7%    | stable/up |
|      3 | Showy milkweed                 | Asclepias speciosa    | 1,181     | 874     | +35.1%     | stable/up |
|      4 | Chokecherry                    | Prunus virginiana     | 1,147     | 728     | +57.6%     | stable/up |
|      5 | Great mullein                  | Verbascum thapsus     | 1,113     | 809     | +37.6%     | stable/up |
|      6 | Mallard                        | Anas platyrhynchos    | 1,094     | 888     | +23.2%     | stable/up |
|      7 | Red-tailed hawk                | Buteo jamaicensis     | 1,046     | 889     | +17.7%     | stable/up |
|      8 | Black-tailed prairie dog       | Cynomys ludovicianus  | 1,042     | 646     | +61.3%     | stable/up |
|      9 | Canada goose                   | Branta canadensis     | 1,010     | 717     | +40.9%     | stable/up |
|     10 | Western honey bee              | Apis mellifera        | 1,002     | 1,000   | +0.2%      | stable/up |
|     11 | Convergent lady beetle         | Hippodamia convergens | 958       | 607     | +57.8%     | stable/up |
|     12 | Black-billed magpie            | Pica hudsonia         | 953       | 756     | +26.1%     | stable/up |
|     13 | Eastern fox squirrel           | Sciurus niger         | 923       | 705     | +30.9%     | stable/up |
|     14 | Rocky mountains ponderosa pine | Pinus scopulorum      | 918       | 456     | +101.3%    | stable/up |
|     15 | Rubber rabbitbrush             | Ericameria nauseosa   | 902       | 588     | +53.4%     | stable/up |
|     16 | Plains pricklypear             | Opuntia polyacantha   | 844       | 456     | +85.1%     | stable/up |
|     17 | Common starlily                | Leucocrinum montanum  | 834       | 474     | +75.9%     | stable/up |
|     18 | Red-winged blackbird           | Agelaius phoeniceus   | 833       | 618     | +34.8%     | stable/up |
|     19 | American robin                 | Turdus migratorius    | 776       | 524     | +48.1%     | stable/up |
|     20 | Front range beardtongue        | Penstemon virens      | 770       | 427     | +80.3%     | stable/up |

---

## Declining Species -- Flagged for Review

No species in the top 20 showed a decline vs the prior period.

---

## Monthly Observation Counts and Data Gaps

Monthly average: **20,789 observations/month**

Months flagged as GAP had counts more than 50% below average. Low counts often reflect reduced observer activity (e.g. winter months) rather than genuine wildlife absence. Treat flagged months cautiously in trend analysis.

| Month   | Observations   | vs. Monthly Avg   | Flag   |
|---------|----------------|-------------------|--------|
| 2025-03 | 6,519          | -68.6%            | GAP    |
| 2025-04 | 23,009         | +10.7%            |        |
| 2025-05 | 41,005         | +97.2%            |        |
| 2025-06 | 51,826         | +149.3%           |        |
| 2025-07 | 47,292         | +127.5%           |        |
| 2025-08 | 35,713         | +71.8%            |        |
| 2025-09 | 30,757         | +47.9%            |        |
| 2025-10 | 13,424         | -35.4%            |        |
| 2025-11 | 5,556          | -73.3%            | GAP    |
| 2025-12 | 3,627          | -82.6%            | GAP    |
| 2026-01 | 4,102          | -80.3%            | GAP    |
| 2026-02 | 4,930          | -76.3%            | GAP    |
| 2026-03 | 2,501          | -88.0%            | GAP    |

---

## Plain-English Verdict

### Is this data worth building on?

With 268,242 observations, the iNaturalist data for this region is **excellent**. The Front Range has a highly active observer community. Species trends for the top 20 are meaningful and worth acting on. Recommend proceeding to build a full monthly-refresh pipeline.

### Recommended next steps

1. Share this report with a domain expert (e.g., Butterfly Pavilion naturalist) to sanity-check the species list and declining flags
2. Investigate any DECLINING species above -- cross-reference with eBird or GBIF to see if the trend holds across data sources
3. If data gaps cluster in winter months, this is expected -- observer activity drops seasonally in Colorado
4. If signal looks good, next step: build a scheduled pipeline that refreshes this report monthly and alerts on new declines
