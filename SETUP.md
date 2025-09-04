# Northwoods Events v2 – Setup & Operations

## 1) Requirements
- Python 3.11+
- `pip install -r requirements.txt`
- Network egress for source domains

## 2) Configure sources
Edit `sources.yaml`. Every source has:
- `name`, `slug`, `type`, `url`
- Optional knobs: `days_ahead`, `months_ahead`, `allow_zero`, `max_events`

**Types**
- `tec_rest` – The Events Calendar (TEC) official REST API.
- `tec_auto` – Try TEC REST; on failure, fall back to HTML + JSON-LD.
- `growthzone_html` – GrowthZone calendar scraper (multi-month, JSON-LD aware).
- `simpleview_html` – Simpleview (Minocqua) list scraper + JSON-LD.

## 3) Run locally
```bash
python -m src.main
