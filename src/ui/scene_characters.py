"""
Scene: Characters
List of saved characters, create new, delete with confirmation.
"""

import pygame
import json
import os
from src.constants import *
from src import fonts
from src.ui.widgets import (draw_panel, draw_text, draw_text_centered,
                             draw_ornament_line, Button, TextInput)
from src.ui.atmosphere import AtmosphereRenderer

CHARS_FILE = os.path.join("data", "characters", "characters.json")


def _load_chars():
    os.makedirs(os.path.dirname(CHARS_FILE), exist_ok=True)
    if not os.path.exists(CHARS_FILE):
        return []
    with open(CHARS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_chars(chars):
    os.makedirs(os.path.dirname(CHARS_FILE), exist_ok=True)
    with open(CHARS_FILE, "w", encoding="utf-8") as f:
        json.dump(chars, f, indent=2, ensure_ascii=False)


class CharactersScene:
    def __init__(self, app):
        self.app    = app
        self.atm    = AtmosphereRenderer(*app.size)
        self._time  = 0.0
        self._chars = _load_chars()
        self._sel   = -1

        # Confirm delete dialog
        self._confirm_open  = False
        self._confirm_input = TextInput(0, 0, 220, 40, placeholder="Digite DELETE")
        self._btn_confirm   = Button(0, 0, 140, 40, "Confirmar", accent=True)
        self._btn_cancel    = Button(0, 0, 110, 40, "Cancelar")

        self._btn_back   = Button(0, 0, 130, 40, "← Voltar")
        self._btn_new    = Button(0, 0, 160, 42, "+ Novo Personagem", accent=True)
        self._btn_delete = Button(0, 0, 120, 38, "Deletar")

        self._build_layout()

    def _build_layout(self):
        w, h = self.app.size
        self._w, self._h = w, h

        pw = min(860, w - 60)
        ph = h - 120
        self._panel = pygame.Rect(w // 2 - pw // 2, 80, pw, ph)

        self._btn_back.rect  = pygame.Rect(self._panel.x + 10, self._panel.y + 10, 130, 40)
        self._btn_new.rect   = pygame.Rect(self._panel.right - 175, self._panel.y + 10, 160, 40)
        self._btn_delete.rect = pygame.Rect(self._panel.right - 175,
                                            self._panel.bottom - 52, 120, 38)

        # Confirm dialog centre
        dw, dh = 400, 220
        dcx = w // 2
        dcy = h // 2
        self._dlg_rect = pygame.Rect(dcx - dw // 2, dcy - dh // 2, dw, dh)
        self._confirm_input.rect = pygame.Rect(dcx - 110, dcy - 20, 220, 40)
        self._btn_confirm.rect   = pygame.Rect(dcx + 10, dcy + 36, 140, 40)
        self._btn_cancel.rect    = pygame.Rect(dcx - 160, dcy + 36, 110, 40)

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    def handle_event(self, event):
        if self._confirm_open:
            self._confirm_input.handle_event(event)
            if self._btn_cancel.handle_event(event):
                self._confirm_open = False
                self._confirm_input.text = ""
            if self._btn_confirm.handle_event(event):
                if self._confirm_input.text.strip().upper() == "DELETE":
                    self._chars.pop(self._sel)
                    _save_chars(self._chars)
                    self._sel = -1
                    self._confirm_open = False
                    self._confirm_input.text = ""
            return  # block events below while dialog is open

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.change_scene(SCENE_MENU)

        if self._btn_back.handle_event(event):
            self.app.change_scene(SCENE_MENU)

        if self._btn_new.handle_event(event):
            self.app.change_scene(SCENE_CHAR_CREATE)

        if self._btn_delete.handle_event(event) and self._sel >= 0:
            self._confirm_open = True
            self._confirm_input.text = ""

        # List item click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._char_rects()):
                if rect.collidepoint(event.pos):
                    self._sel = i

    def _char_rects(self):
        rects = []
        lx = self._panel.x + 10
        ly = self._panel.y + 62
        lw = self._panel.width - 20
        for i in range(len(self._chars)):
            rects.append(pygame.Rect(lx, ly + i * 58, lw, 52))
        return rects

    def update(self, dt):
        self._time += dt
        self.atm.update(dt)
        self._confirm_input.update(dt)

    def draw(self, surface):
        w, h = self.app.size
        self.atm.draw(surface)
        draw_panel(surface, self._panel, C_PANEL_DARK, C_BORDER, 1, radius=8, alpha=230)

        hfont = fonts.get("heading", 24)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)

        draw_text_centered(surface, "PERSONAGENS", hfont, C_GOLD, w // 2, self._panel.y + 30)
        draw_ornament_line(surface, w // 2, self._panel.y + 54, 400)

        self._btn_back.draw(surface, bfont)
        self._btn_new.draw(surface, bfont)

        # Character list
        for i, (rect, char) in enumerate(zip(self._char_rects(), self._chars)):
            sel = (i == self._sel)
            bg  = C_PANEL if sel else C_PANEL_DARK
            brd = C_BORDER_SEL if sel else C_BORDER
            draw_panel(surface, rect, bg, brd, 1, radius=5)
            name  = char.get("name", "Sem nome")
            klass = char.get("class", "?")
            race  = char.get("race", "?")
            anc   = char.get("background")
            lvl   = char.get("level", 1)
            draw_text(surface, name, fonts.get("heading", 18), C_TEXT_BRIGHT,
                      rect.x + 16, rect.y + 8)
            sub = f"{race} · {klass}"
            if anc:
                sub += f" · {anc}"
            sub += f" · Nv {lvl}"
            draw_text(surface, sub, sfont, C_TEXT_DIM,
                      rect.x + 16, rect.y + 30)

        # Empty state
        if not self._chars:
            draw_text_centered(surface,
                               "Nenhum personagem. Crie um novo!",
                               bfont, C_TEXT_DIM, w // 2, h // 2)

        if self._sel >= 0:
            self._btn_delete.draw(surface, bfont)

        # Confirm dialog
        if self._confirm_open:
            self._draw_confirm(surface, w, h)

    def _draw_confirm(self, surface, w, h):
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        draw_panel(surface, self._dlg_rect, C_PANEL, C_BORDER_SEL, 2, radius=8)
        hfont = fonts.get("heading", 20)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)

        draw_text_centered(surface, "⚠  DELETAR PERSONAGEM", hfont, C_TEXT_ACCENT,
                           w // 2, self._dlg_rect.y + 28)
        name = self._chars[self._sel].get("name", "?") if self._sel >= 0 else "?"
        draw_text_centered(surface, f'"{name}"', bfont, C_TEXT, w // 2,
                           self._dlg_rect.y + 64)
        draw_text_centered(surface, 'Digite  DELETE  para confirmar:', sfont, C_TEXT_DIM,
                           w // 2, self._dlg_rect.y + 94)

        self._confirm_input.draw(surface, bfont)
        self._btn_confirm.draw(surface, bfont)
        self._btn_cancel.draw(surface, bfont)
