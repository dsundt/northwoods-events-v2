# src/parsers/tec_html.py
"""
TEC (The Events Calendar) HTML adapter.

Surgical fix:
- Keep the 'tec_html' type working by delegating to the proven TEC REST logic
  whenever possible. This avoids re-scraping brittle HTML and keeps output
  identical to working TEC sources (Boulder Junction, Eagle River, Vilas).
- Signature now matches the runner: (source, start_date, end_date)

If a site truly lacks the REST endpoint, you *can* add a basic HTML fallback
later, but delegating to REST keeps behavior consistent and stable now.
"""

from urllib.parse import urlparse
from .tec_rest import fetch_tec_rest

def fetch_tec_html(source, start_date, end_date):
    """
    Delegate 'tec_html' to the REST parser. This stabilizes St. Germain
    and Oneida if they run TEC on WordPress but were mis-typed as HTML.
    """
    # We simply pass through to the same routine Boulder/Eagle/Vilas use.
    # No changes to main.py or other call sites required.
    return fetch_tec_rest(source, start_date, end_date)
