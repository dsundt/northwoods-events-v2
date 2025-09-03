from typing import Optional
import time
import requests

DEFAULT_TIMEOUT = 20  # seconds
MAX_RETRIES = 3
BACKOFF_SEC = 2


def get(url: str, user_agent: Optional[str] = None) -> requests.Response:
    """
    Simple robust GET with retries and exponential backoff.
    Raises the last exception if all retries fail.
    """
    headers = {
        "User-Agent": user_agent or "NorthwoodsEventsBot/2.0 (+github)"
    }
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SEC * attempt)
            else:
                raise last_exc
    # Unreachable
    raise RuntimeError("Unreachable")
