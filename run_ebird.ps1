$env:EBIRD_API_KEY = [System.Environment]::GetEnvironmentVariable("EBIRD_API_KEY", "User")
python scripts/ebird_crossref.py
