from __future__ import annotations
from typing import List, Tuple
from bs4 import BeautifulSoup

from src.fetch import get
from src.util import absurl, parse_first_jsonld_event, sanitize_event

def _collect_list_links(list_url: str, pages: int = 3) -> List[str]:
    out = []
    for p in range(1, pages + 1):
        # Many Simpleview sites accept ?page=X or ?skip=X – safest is ?page=X
        url = f"{list_url}?page={p}" if "?" not in list_url else f"{list_url}&page={p}"
        r = get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        # Simpleview cards:
        for a in soup.select("a[href*='/event/'], a.card a, .event-result a, .grid a"):
            href = a.get("href")
            if href:
                out.append(absurl(url, href))
    return list(dict.fromkeys(out))

def fetch_simpleview_html(source: dict, start_iso: str, end_iso: str) -> Tuple[List[dict], dict]:
    list_url = source["url"]
    links = _collect_list_links(list_url, pages=4)
    diag = {"list_links": len(links), "detail_hits": 0}
    items = []
    for href in links:
        try:
            r = get(href)
            soup = BeautifulSoup(r.text, "html.parser")
            j = parse_first_jsonld_event(soup, href)
            # Filter out landing pages without start date
            if j and j.get("start_utc"):
                diag["detail_hits"] += 1
                norm = sanitize_event(j, source["name"], source["name"])
                if norm:
                    items.append(norm)
        except Exception:
            continue
    return items, diag
