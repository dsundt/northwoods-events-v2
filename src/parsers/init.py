# src/parsers/__init__.py
from importlib import import_module

__all__ = []

def _export(public_name: str, module_name: str, attr_name: str):
    mod = import_module(f"src.parsers.{module_name}")
    fn = getattr(mod, attr_name, None)
    if fn is None:
        raise ImportError(
            f"Failed to expose '{attr_name}' from parsers.{module_name}"
        )
    globals()[public_name] = fn
    __all__.append(public_name)

# Keep these stable; main.py imports from src.parsers
_export("fetch_tec_rest", "tec_rest", "fetch_tec_rest")
_export("fetch_tec_html", "tec_html", "fetch_tec_html")
_export("fetch_growthzone_html", "growthzone_html", "fetch_growthzone_html")
_export("fetch_simpleview_html", "simpleview_html", "fetch_simpleview_html")
