# Biological Signal Detection in Agricultural and Semi-Arid Watersheds
## A Methodological Summary for Ecological Researchers

**Andrew Kelly — Independent Researcher**
Dashboard: https://kellyandrewb-blip.github.io/front-range-wildlife/
GitHub: https://github.com/kellyandrewb-blip/front-range-wildlife

---

## What This Is

A platform that integrates USGS streamflow, EPA/WQP water quality data, and
iNaturalist community science observations to test whether biological signals —
particularly EPT (Ephemeroptera, Plecoptera, Trichoptera) insect activity — are
detectable in publicly available datasets across agricultural and semi-arid
watersheds. The methodology is open source, built entirely on public data, and
designed to be reproducible. This is proof-of-signal work, not a monitoring
replacement.

---

## Three-Location Cross-Validation

The core question was whether the method would produce climatically coherent
results across ecologically distinct sites — and whether different drivers would
emerge in different regions. They did.

| Site | Watershed Context | Primary Driver | Correlation | Notes |
|------|------------------|----------------|-------------|-------|
| Colorado Front Range (Plum Creek / Big Dry Creek) | Arid west, semi-urban | Discharge-dominant | Partial r = 0.729 | Strong hydrological signal; pesticide record gap since 2007 |
| Iowa South Skunk River | 67.8% row crops, 139 permitted CAFOs | Discharge-dominant with agricultural stress | Partial r = 0.497 | Atrazine episode June 2024 at 1.70 µg/L; largest observation gap in dataset |
| Maryland Patuxent River | Mid-Atlantic, thermally regulated | Temperature-dominant | r = 0.889 | Discharge adds nothing (partial r = 0.067, p = 0.71) |

The Patuxent result — where discharge is statistically irrelevant and temperature
explains nearly all variance — is not an anomaly. It is the expected outcome in a
thermally buffered mid-Atlantic system. A method that produced identical drivers
across these three sites would be a validity problem, not a feature. The
climatically differentiated outputs are the validation.

---

## Iowa South Skunk: Detailed Finding

The Iowa site produced the most ecologically complex result and warrants separate
attention.

**Discharge–insect lag correlation:** 22-month lag between discharge conditions
and EPT insect observation rates. Partial r = 0.497 after controlling for
seasonal observer activity.

**June 2024 atrazine episode:**
- Detected concentration: 1.70 µg/L (WQP single-point measurement)
- Predicted insect observations based on hydrological model: baseline
- Actual observations: 43% of predicted — the largest negative residual in the
  22-month dataset
- The gap is unambiguous in direction. Whether atrazine caused it is not
  established by a single detection.

**DNR BMIBI cross-validation:**
- Iowa DNR Benthic Macroinvertebrate Index of Biotic Integrity scores for this
  watershed: 55–66 (marginally impaired classification)
- This range is consistent with the iNaturalist EPT signal and corroborates the
  direction of the finding from an independent, field-verified source

**Watershed loading context:**
- 67.8% row crop land cover upstream
- 139 permitted CAFOs
- 128,415 animal units in the contributing drainage area

**Honest statement of the limitation:** This is n=1 for atrazine detection. The
directional signal is unambiguous. Causation is not established. A second
detection — especially one correlated with another observation gap — would
materially strengthen the claim.

---

## What This Method Cannot Do

These are structural limitations, not engineering gaps. Some are resolvable with
additional data; others are inherent to community science methodology.

**Observation density:** iNaturalist coverage is uneven. In low-observer-density
segments, the denominator is too small for segment-level analysis. This method
works at watershed scale, not reach scale.

**Composite denominator inversion:** Using total iNaturalist observations as the
activity denominator causes year-round taxa to appear suppressed during peak
seasonal periods (when specialist observers dominate). Taxon-specific
denominators are required for rigorous per-species analysis. The current
implementation uses a composite denominator; results should be interpreted at the
community level.

**Single atrazine detection:** One WQP snapshot is a data point, not a dataset.
The June 2024 episode is worth flagging and worth following. It is not sufficient
to establish a pesticide-insect relationship.

**No benthic survey data at Colorado sites:** BMIBI-style field sampling is the
most reliable water quality indicator available, and it is absent from the public
record for Plum Creek and Big Dry Creek. The pesticide monitoring record for this
corridor went dark after 2007 — chlorpyrifos, bifenthrin, and diazinon were
detected in earlier studies, none have been measured in the years the wildlife
data covers. The absence of monitoring is itself a finding, but it limits causal
inference.

---

## What Would Make This Stronger

These are the highest-value additions, in order of impact:

1. **Paired benthic survey data at the Colorado and Iowa sites.** A single BMIBI
   run at monitored reaches would allow direct calibration of the iNaturalist EPT
   signal against field-verified impairment scores — the same validation that
   exists for the Patuxent.

2. **Pesticide monitoring beyond single WQP snapshots.** The Iowa finding depends
   on one detection. Continuous or seasonal sampling at the South Skunk gauge
   would either confirm or refute the atrazine-observation gap relationship. For
   Colorado, any modern pesticide measurement in the study corridor would be new
   information.

3. **eBird cross-validation at Iowa and Colorado.** The Patuxent bird signal has
   been validated against eBird (4 of 18 iNaturalist-flagged declines
   independently corroborated). The same validation has not been run for Iowa or
   Colorado bird data. This is a gap in the multi-source corroboration chain.

---

## Contact and Access

**Andrew Kelly** — independent researcher
**Email:** kellyandrewb@gmail.com
**Dashboard:** https://kellyandrewb-blip.github.io/front-range-wildlife/
**GitHub:** https://github.com/kellyandrewb-blip/front-range-wildlife
(Full methodology, scripts, and data pipeline are publicly available)

Collaboration interest: benthic survey pairing, pesticide monitoring integration,
and eBird validation at non-Patuxent sites. I'm also interested in hearing from
researchers who have BMIBI data for any of the three study corridors.
