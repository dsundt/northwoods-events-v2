"""
Parser package public API.

We re-export only the fetchers that the build entrypoint (src/main.py) imports:
- fetch_tec_rest          (The Events Calendar REST sites)
- fetch_growthzone_html   (GrowthZone calendar pages)
- fetch_simpleview_html   (Simpleview event listings)

Keeping this file narrowly scoped prevents circular imports and accidental
breakage if individual parser modules gain extra internal dependencies.

If you add a new parser that main.py needs to import from `src.parsers`,
add it to the imports and __all__ below.
"""

from importlib import import_module

__all__ = [
    "fetch_tec_rest",
    "fetch_growthzone_html",
    "fetch_simpleview_html",
]

# Lazy, explicit re-exports to avoid circular imports during package init.
# This assumes the following modules exist alongside this file:
#   tec_rest.py         -> def fetch_tec_rest(...)
#   growthzone_html.py  -> def fetch_growthzone_html(...)
#   simpleview_html.py  -> def fetch_simpleview_html(...)

def _export(name: str, module: str, attr: str):
    try:
        globals()[name] = getattr(import_module(f".{module}", __name__), attr)
    except Exception as e:
        # Raise a clean ImportError that points to the missing symbol or module,
        # which makes GitHub Actions logs much easier to read.
        raise ImportError(
            f"Failed to expose '{attr}' from parsers.{module}: {e}"
        ) from e

_export("fetch_tec_rest", "tec_rest", "fetch_tec_rest")
_export("fetch_growthzone_html", "growthzone_html", "fetch_growthzone_html")
_export("fetch_simpleview_html", "simpleview_html", "fetch_simpleview_html")
