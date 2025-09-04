# v2 parser package initializer.
# Intentionally avoids side-effect imports to keep module loading predictable.
# Import concrete parsers explicitly from their modules, e.g.:
#   from src.parsers.tec_rest import fetch_tec_rest
#   from src.parsers.tec_html import fetch_tec_html
#   from src.parsers.growthzone_html import fetch_growthzone_html
#   from src.parsers.simpleview_html import fetch_simpleview_html
#   from src.parsers.ics_feed import fetch_ics

__all__ = []
