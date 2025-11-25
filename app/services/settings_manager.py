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
            settings = json.load(f)

        # Validate that settings is a dict
        if not isinstance(settings, dict):
            raise ValueError(f"Settings file must contain a JSON object, got {type(settings)}")

        # Validate run_frequency if present
        if "run_frequency" in settings:
            valid_frequencies = ["manual", "daily", "hourly"]
            if settings["run_frequency"] not in valid_frequencies:
                raise ValueError(
                    f"Invalid run_frequency: {settings['run_frequency']}. "
                    f"Must be one of: {', '.join(valid_frequencies)}"
                )

        return settings

    except (json.JSONDecodeError, ValueError) as e:
        # Log the error but return default settings
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to load settings from {SETTINGS_FILE}: {e}. Using defaults.")
        return {"run_frequency": "manual"}
    except Exception as e:
        # Catch other errors (file permissions, etc.)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error loading settings: {e}. Using defaults.")
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
