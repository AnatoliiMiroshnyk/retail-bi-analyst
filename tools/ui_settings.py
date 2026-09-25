"""
Persistent UI settings for Retail BI Analyst.

Stores theme, font size and language in a JSON file between runs.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


SETTINGS_PATH = Path.home() / ".retail_bi_ui_settings.json"


@dataclass
class UiSettings:
    theme: str = "light"          # "light" or "dark"
    font_size_pt: int = 10        # base font size
    language_code: str = "en"     # one of SUPPORTED_LANG_CODES


def load_settings() -> UiSettings:
    """
    Load UI settings from JSON file. Returns defaults on any error.
    """
    if not SETTINGS_PATH.exists():
        return UiSettings()

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return UiSettings(
            theme=data.get("theme", "light"),
            font_size_pt=int(data.get("font_size_pt", 10)),
            language_code=data.get("language_code", "en"),
        )
    except Exception:
        # fallback to defaults if file is corrupted or unreadable
        return UiSettings()


def save_settings(settings: UiSettings) -> None:
    """
    Save UI settings to JSON file.
    """
    try:
        SETTINGS_PATH.write_text(
            json.dumps(asdict(settings), indent=2),
            encoding="utf-8",
        )
    except Exception:
        # silently ignore persistence errors (e.g. read-only filesystem)
        pass