import datetime as dt
from urllib.parse import urljoin, urlencode

from src.fetch import get_json
from src.models import Event

API_PATH = "/wp-json/tribe/events/v1/events"

def iso_date(d):
    if isinstance(d, (dt.date, dt.datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)

def fetch_tec_rest(base_url: str, start_date, end_date, per_page=50, max_pages=8, tz_hint=None):
    """
    Fetch events from The Events Calendar REST API.
    Returns: list[Event], diagnostics dict
    """
    start = iso_date(start_date)
    end = iso_date(end_date)
    events = []
    pages_seen = 0
    diag = {"pages": [], "api_url": None}

    api_root = urljoin(base_url.rstrip("/") + "/", API_PATH.lstrip("/"))

    page = 1
    while page <= max_pages:
        params = {
            "start_date": start,
            "end_date": end,
            "per_page": per_page,
            "page": page,
        }
        url = f"{api_root}?{urlencode(params)}"
        if page == 1:
            diag["api_url"] = url

        data = get_json(url)
        diag["pages"].append({"page": page, "count": len(data.get("events", []))})

        for e in data.get("events", []):
            title = e.get("title")
            url_e = e.get("url") or e.get("website")
            start_iso = e.get("start_date")
            end_iso = e.get("end_date")
            venue = None
            loc = e.get("venue", {}) or {}
            if isinstance(loc, dict):
                venue = ", ".join(filter(None, [
                    loc.get("venue"),
                    loc.get("address"),
                    loc.get("city"),
                    loc.get("region"),
                ])) or None

            events.append(Event(
                title=title,
                start_utc=start_iso,   # Event class normalizes to UTC later
                end_utc=end_iso,
                url=url_e,
                location=venue,
                source_url=base_url,
                meta={"tec_rest_id": e.get("id")}
            ))

        pages_seen += 1
        total = data.get("total") or 0
        total_pages = data.get("total_pages") or 1
        if page >= total_pages:
            break
        page += 1

    return events, diag
