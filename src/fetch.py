from __future__ import annotations
import time
from typing import Optional, Tuple
import requests

DEFAULT_HEADERS = {
    "User-Agent": "northwoods-events-v2 (+https://github.com/dsundt/northwoods-events-v2)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}

def get(url: str, headers: Optional[dict] = None, timeout: int = 30, retries: int = 3, backoff: float = 0.7) -> requests.Response:
    last_exc = None
    hdrs = {**DEFAULT_HEADERS, **(headers or {})}
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise last_exc
    # unreachable
    assert False

def json(url: str, **kw) -> Tuple[dict, requests.Response]:
    resp = get(url, **kw)
    return resp.json(), resp
