# Front Range Wildlife Intelligence System

A lightweight tool that queries public ecological APIs and surfaces plain-English conservation insights for under-resourced organizations like the Butterfly Pavilion in Westminster, CO.

## Current Phase: Proof of Signal

Querying the iNaturalist API for species observations within 50 miles of Highlands Ranch, CO to validate data quality before any further architecture decisions.

## How to Run

```bash
pip install -r requirements.txt
python scripts/inat_signal_test.py
```

Output is saved to `reports/inat_signal_test.md`.
