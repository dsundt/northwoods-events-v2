# Northwoods Events – Version 2.0

A clean, resilient calendar aggregation pipeline that collects events from:
- Public **ICS** feeds
- **The Events Calendar (TEC)** HTML
- **GrowthZone** HTML
- **AI1EC** HTML

Outputs:
- `public/combined.ics`
- `public/by-source/<slug>.ics`
- `public/report.json`
- `public/index.html`

## How it works

1. GitHub Actions workflow runs daily (09:15 UTC) and on demand.
2. `src/main.py` loads `config/sources.yaml`.
3. Each enabled source is fetched (with retries/timeouts), parsed, normalized to UTC.
4. Outputs written to `public/` and deployed to GitHub Pages.

## Setup (Web UI only)

1. Upload the provided files to your repository.
2. Edit `config/sources.yaml` and add real sources (`enabled: true` to activate).
3. Enable Actions and Pages (Settings → Pages → Source: GitHub Actions).
4. Run the workflow manually from **Actions** to test the pipeline.
5. Visit the Pages URL to access `index.html`, `combined.ics`, and `report.json`.

## Notes

- Times are normalized to **UTC** to avoid VTIMEZONE/DST issues.
- Stable `uid` per event enables deduplication across sources.
- `report.json` is always written to aid troubleshooting.
- Workflow calls `python -m src.main` for import reliability.
