# src/fetch.py
from __future__ import annotations
import time
from typing import Optional
import requests

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

def session(timeout: int = 30) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": _UA,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    s.timeout = timeout  # type: ignore[attr-defined]
    return s

def get(url: str, s: Optional[requests.Session] = None, retries: int = 2) -> requests.Response:
    s = s or session()
    last_exc = None
    for i in range(retries + 1):
        try:
            resp = s.get(url, timeout=getattr(s, "timeout", 30))
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            if i < retries:
                time.sleep(0.7 * (i + 1))
                continue
            raise last_exc
