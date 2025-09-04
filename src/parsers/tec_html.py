# Fallback parser: TEC HTML (kept for completeness; REST is preferred).
from __future__ import annotations
from typing import List, Tuple, Dict, Any
from bs4 import BeautifulSoup
from src.models import Event
from src.fetch import get


def fetch_tec_html(url: str, start_date, end_date) -> tuple[list[Event], dict]:
    resp = get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    evs: List[Event] = []
    diag: Dict[str, Any] = {"note": "html fallback; prefer tec_rest"}

    for a in soup.select("a[href*='/event/']"):
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or not href:
            continue
        # List pages often omit dates; we skip if we can't infer
        evs.append(Event(title=title, start_utc=None, url=href))

    # Filter out items missing a start time
    evs = [e for e in evs if e.start_utc is not None]
    return evs, diag
