"""
Scene: Compendium
Tabbed A-I sections, each loading from data/compendium/<section>.json
"""

import pygame
import json
import os
from src.constants import *
from src import fonts
from src.ui.widgets import (draw_panel, draw_text, draw_text_centered,
                             draw_ornament_line, Button)
from src.ui.atmosphere import AtmosphereRenderer

COMP_DIR = os.path.join("data", "compendium")
_SECTIONS = COMPENDIUM_SECTIONS  # from constants


def _load_section(letter: str):
    path = os.path.join(COMP_DIR, f"section_{letter.lower()}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


class CompendiumScene:
    def __init__(self, app):
        self.app       = app
        self.atm       = AtmosphereRenderer(*app.size)
        self._time     = 0.0
        self._tab      = 0
        self._sel_item = -1
        self._scroll   = 0
        self._data     = {}   # cache
        self._btn_back = Button(0, 0, 130, 40, "← Voltar")
        self._build_layout()

    def _section_data(self):
        letter = _SECTIONS[self._tab][0]
        if letter not in self._data:
            self._data[letter] = _load_section(letter)
        return self._data[letter]

    def _build_layout(self):
        w, h = self.app.size
        pw = min(1000, w - 40)
        ph = h - 100
        self._panel = pygame.Rect(w // 2 - pw // 2, 70, pw, ph)
        self._btn_back.rect = pygame.Rect(self._panel.x + 10,
                                          self._panel.bottom - 50, 130, 40)
        tab_w = self._panel.width // len(_SECTIONS)
        self._tab_rects = [
            pygame.Rect(self._panel.x + i * tab_w, self._panel.y, tab_w, 44)
            for i in range(len(_SECTIONS))
        ]
        # list area
        self._list_rect = pygame.Rect(
            self._panel.x + 8, self._panel.y + 52,
            260, self._panel.height - 110
        )
        # detail area
        self._detail_rect = pygame.Rect(
            self._list_rect.right + 12, self._panel.y + 52,
            self._panel.right - self._list_rect.right - 20,
            self._panel.height - 110
        )

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.change_scene(SCENE_MENU)
        if self._btn_back.handle_event(event):
            self.app.change_scene(SCENE_MENU)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, tr in enumerate(self._tab_rects):
                if tr.collidepoint(event.pos):
                    self._tab = i
                    self._sel_item = -1
                    self._scroll   = 0

            for i, ir in enumerate(self._item_rects()):
                if ir.collidepoint(event.pos):
                    self._sel_item = i

        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, self._scroll - event.y * 3)

    def _item_rects(self):
        items = self._section_data()
        rects = []
        for i in range(len(items)):
            rects.append(pygame.Rect(
                self._list_rect.x,
                self._list_rect.y + i * 42 - self._scroll * 14,
                self._list_rect.width, 38
            ))
        return rects

    def update(self, dt):
        self._time += dt
        self.atm.update(dt)

    def draw(self, surface):
        w, h = self.app.size
        self.atm.draw(surface)
        draw_panel(surface, self._panel, C_PANEL_DARK, C_BORDER, 1, radius=8, alpha=230)

        hfont = fonts.get("heading", 18)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)

        # Tabs
        for i, (tr, (letter, name)) in enumerate(zip(self._tab_rects, _SECTIONS)):
            sel = (i == self._tab)
            bg  = C_PANEL if sel else C_PANEL_DARK
            brd = C_BORDER_SEL if sel else C_BORDER
            draw_panel(surface, tr, bg, brd, 1, radius=0)
            col = C_GOLD_BRIGHT if sel else C_TEXT_DIM
            draw_text_centered(surface, f"{letter} · {name}", sfont, col,
                               tr.centerx, tr.centery)

        # List panel
        draw_panel(surface, self._list_rect, C_PANEL_DARK, C_BORDER, 1, radius=5)
        clip = surface.get_clip()
        surface.set_clip(self._list_rect)
        items = self._section_data()
        for i, (ir, item) in enumerate(zip(self._item_rects(), items)):
            if ir.bottom < self._list_rect.top or ir.top > self._list_rect.bottom:
                continue
            sel = (i == self._sel_item)
            bg  = C_PANEL if sel else C_PANEL_DARK
            brd = C_BORDER_SEL if sel else C_BORDER
            draw_panel(surface, ir, bg, brd, 1, radius=4)
            draw_text(surface, item.get("name", "?"), bfont,
                      C_TEXT_BRIGHT if sel else C_TEXT,
                      ir.x + 10, ir.centery - bfont.get_height() // 2)
        surface.set_clip(clip)

        # Empty
        if not items:
            draw_text_centered(surface, "Nenhum item nesta seção ainda.", bfont,
                               C_TEXT_DIM, self._list_rect.centerx, self._list_rect.centery)

        # Detail panel
        draw_panel(surface, self._detail_rect, C_PANEL_DARK, C_BORDER, 1, radius=5)
        if 0 <= self._sel_item < len(items):
            item = items[self._sel_item]
            self._draw_detail(surface, item, hfont, bfont, sfont)
        else:
            draw_text_centered(surface, "Selecione um item", bfont, C_TEXT_DIM,
                               self._detail_rect.centerx, self._detail_rect.centery)

        self._btn_back.draw(surface, bfont)

    def _draw_detail(self, surface, item, hfont, bfont, sfont):
        x0 = self._detail_rect.x + 16
        y0 = self._detail_rect.y + 16
        draw_text(surface, item.get("name", "?"), hfont, C_GOLD_BRIGHT, x0, y0)
        draw_ornament_line(surface, self._detail_rect.centerx,
                           y0 + 30, self._detail_rect.width - 32)
        y = y0 + 44
        for key, label in [("type","Tipo"), ("rarity","Raridade"), ("source","Fonte")]:
            val = item.get(key)
            if val:
                draw_text(surface, f"{label}: {val}", sfont, C_TEXT_DIM, x0, y)
                y += 20
        y += 8
        desc = item.get("description", "")
        max_w = self._detail_rect.width - 32
        self._draw_wrapped(surface, desc, bfont, C_TEXT, x0, y, max_w,
                           self._detail_rect.bottom - 20)

    def _draw_wrapped(self, surface, text, font, color, x, y, max_w, max_y):
        words = text.split()
        line  = ""
        for word in words:
            test = line + (" " if line else "") + word
            if font.size(test)[0] > max_w:
                if y + font.get_height() > max_y:
                    break
                surf = font.render(line, True, color)
                surface.blit(surf, (x, y))
                y += font.get_height() + 2
                line = word
            else:
                line = test
        if line and y + font.get_height() <= max_y:
            surf = font.render(line, True, color)
            surface.blit(surf, (x, y))
