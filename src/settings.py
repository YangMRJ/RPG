"""
Settings — persists player preferences to settings.json
"""

import json
import os
from src.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT, RESOLUTIONS

SETTINGS_FILE = "settings.json"

_defaults = {
    "resolution":  [DEFAULT_WIDTH, DEFAULT_HEIGHT],
    "fullscreen":  False,
    "show_fps":    False,
    "vol_gui":     0.8,
    "vol_music":   0.6,
    "vol_sfx":     0.8,
}

_settings = dict(_defaults)


def load():
    global _settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            _settings = {**_defaults, **saved}
        except Exception:
            _settings = dict(_defaults)


def save():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(_settings, f, indent=2)


def get(key, default=None):
    return _settings.get(key, default)


def set(key, value):
    _settings[key] = value


def resolution():
    r = _settings.get("resolution", [DEFAULT_WIDTH, DEFAULT_HEIGHT])
    return tuple(r)


def fullscreen():
    return _settings.get("fullscreen", False)


def show_fps():
    return _settings.get("show_fps", False)


def vol_gui():
    return _settings.get("vol_gui", 0.8)


def vol_music():
    return _settings.get("vol_music", 0.6)


def vol_sfx():
    return _settings.get("vol_sfx", 0.8)
