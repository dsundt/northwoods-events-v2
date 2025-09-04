from __future__ import annotations

import json
import time
from typing import Dict, Any
import requests

UA = "northwoods-events-v2/2.0 (+https://github.com/)"
TIMEOUT = 30
RETRIES = 3


def _req(method: str, url: str, **kw) -> requests.Response:
    headers = kw.pop("headers", {})
    headers.setdefault("user-agent", UA)
    for i in range(RETRIES):
        try:
            resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kw)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last = e
            time.sleep(1 + i)
    raise last  # type: ignore[name-defined]


def get(url: str) -> requests.Response:
    return _req("GET", url)


def get_json(url: str) -> Dict[str, Any]:
    r = _req("GET", url, headers={"accept": "application/json"})
    return r.json()
