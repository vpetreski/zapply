"""Shared settings management for admin configuration."""

import json
from pathlib import Path

# Settings file path
SETTINGS_FILE = Path("data/admin_settings.json")


def load_settings() -> dict:
    """
    Load settings from JSON file.

    Returns:
        Dictionary with settings, defaults to manual run frequency if file doesn't exist
    """
    if not SETTINGS_FILE.exists():
        return {"run_frequency": "manual"}

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"run_frequency": "manual"}


def save_settings(settings: dict) -> None:
    """
    Save settings to JSON file.

    Args:
        settings: Dictionary of settings to save
    """
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
