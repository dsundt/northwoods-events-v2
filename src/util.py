from __future__ import annotations
import os
import re

PUBLIC_DIR = "public"
BY_SOURCE_DIR = os.path.join(PUBLIC_DIR, "by-source")
DEBUG_DIR = os.path.join(PUBLIC_DIR, "debug")


def ensure_dirs():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    os.makedirs(BY_SOURCE_DIR, exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)


def slugify(name: str) -> str:
    s = name.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9\- ]", "-", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    s = re.sub(r"-+", "-", s)
    return s or "source"
