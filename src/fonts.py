"""
Font manager — centralises all font loading.
Falls back gracefully if custom fonts aren't present.

Recommended free fonts to place in assets/fonts/:
  - Pixelcastle.otf               (pixel title / headings, optional)
  - UnifrakturMaguntia-Book.ttf   (gothic title)
  - Cinzel-Regular.ttf             (menu / headings)
  - CinzelDecorative-Regular.ttf   (decorative)
  - EBGaramond-Regular.ttf         (body text)

All available at fonts.google.com
"""

import pygame
import os

_cache: dict = {}
_FONT_DIR = os.path.join("assets", "fonts")

# Map logical names → filename candidates (first found wins)
_FONT_MAP = {
    "title":     [r"C:\Users\03738044\Downloads\Alkhemikal.ttf", "Alkhemikal.ttf", "Pixelcastle.otf", "UnifrakturMaguntia-Book.ttf", "MedievalSharp.ttf"],
    "heading":   [r"C:\Users\03738044\Downloads\Alkhemikal.ttf", "Alkhemikal.ttf", "Pixelcastle.otf", "Cinzel-Regular.ttf", "CinzelDecorative-Regular.ttf"],
    "body":      [r"C:\Users\03738044\Downloads\Alkhemikal.ttf", "Alkhemikal.ttf", "EBGaramond-Regular.ttf", "Garamond.ttf"],
    "mono":      ["CutiveMono-Regular.ttf"],
}


from typing import Optional

def _resolve(logical: str) -> Optional[str]:
    candidates = _FONT_MAP.get(logical, [])
    for name in candidates:
        path = name if os.path.isabs(name) else os.path.join(_FONT_DIR, name)
        if os.path.exists(path):
            return path
    return None  # will use pygame default


def get(logical: str, size: int) -> pygame.font.Font:
    key = (logical, size)
    if key in _cache:
        return _cache[key]

    path = _resolve(logical)
    try:
        if path:
            font = pygame.font.Font(path, size)
        else:
            # Graceful fallback — use pygame's built-in sans
            font = pygame.font.SysFont("serif", size)
    except Exception:
        font = pygame.font.SysFont("serif", size)

    _cache[key] = font
    return font


def clear_cache():
    _cache.clear()
