"""
Scene: Main Menu
Gothic title, animated menu items, mouse + keyboard navigation.
"""

import pygame
import math
from src.constants import *
from src import fonts
from src.ui.widgets import MenuItem, draw_text_centered, draw_ornament_line, draw_text
from src.ui.atmosphere import AtmosphereRenderer


_MENU_OPTIONS = [
    ("Jogar",        SCENE_PLAY_SELECT),
    ("Personagens",  SCENE_CHARACTERS),
    ("Compêndio",    SCENE_COMPENDIUM),
    ("Opções",       SCENE_OPTIONS),
    ("Sair",         "quit"),
]


class MenuScene:
    def __init__(self, app):
        self.app       = app
        self.atm       = AtmosphereRenderer(*app.size)
        self._time     = 0.0
        self._intro_t  = 0.0      # 0→1 intro animation
        self._items    = []
        self._sel      = 0        # keyboard selected index
        self._built_w  = 0
        self._built_h  = 0
        self._build_layout()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        w, h = self.app.size
        self._built_w, self._built_h = w, h
        item_w  = 360
        spacing = 64
        count   = len(_MENU_OPTIONS)
        total_h = count * spacing
        start_y = h // 2 + 30

        self._items = []
        for i, (label, action) in enumerate(_MENU_OPTIONS):
            cy = start_y + i * spacing - (total_h // 2) + spacing // 2
            self._items.append(MenuItem(label, action, cy, item_w, w // 2))

        if self._sel < len(self._items):
            self._items[self._sel].selected = True

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        w, h = self.app.size

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_sel(1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move_sel(-1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._activate(self._sel)

        elif event.type == pygame.MOUSEMOTION:
            for i, item in enumerate(self._items):
                if item.check_hover(event.pos):
                    self._set_sel(i)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, item in enumerate(self._items):
                if item.rect.collidepoint(event.pos):
                    self._activate(i)

    def _move_sel(self, delta):
        self._set_sel((self._sel + delta) % len(self._items))

    def _set_sel(self, idx):
        self._items[self._sel].selected = False
        self._sel = idx
        self._items[self._sel].selected = True

    def _activate(self, idx):
        action = self._items[idx].action
        if action == "quit":
            self.app.quit()
        else:
            self.app.change_scene(action)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        self._time    += dt
        self._intro_t  = min(1.0, self._intro_t + dt * 0.9)
        self.atm.update(dt)
        for item in self._items:
            item.update(dt)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface):
        w, h = self.app.size

        # Rebuild layout if window was resized
        if (w, h) != (self._built_w, self._built_h):
            self._build_layout()

        self.atm.draw(surface)
        self._draw_title(surface, w, h)
        self._draw_menu_items(surface)
        self._draw_footer(surface, w, h)

    def _draw_title(self, surface, w, h):
        intro = self._ease_out(self._intro_t)

        # ── "CURSE OF STRAHD" ────────────────────────────────────────────
        title_font    = fonts.get("title", FONT_TITLE)
        subtitle_font = fonts.get("heading", FONT_SUBTITLE - 4)
        eyebrow_font  = fonts.get("heading", 16)

        ty_base  = int(h * 0.22)
        alpha_title = int(min(255, intro * 2.5 * 255))

        # Glow behind title
        if intro > 0.1:
            glow_surf = pygame.Surface((w, 160), pygame.SRCALPHA)
            gw = int(500 * intro)
            for i in range(30):
                r_a = int((30 - i) * 3 * (alpha_title / 255))
                pygame.draw.ellipse(glow_surf, (140, 20, 30, r_a),
                                    (w // 2 - gw // 2 + i * 4,
                                     60 + i * 2,
                                     gw - i * 8, 40 - i))
            surface.blit(glow_surf, (0, ty_base - 40))

        # Eye-brow text
        top_text = eyebrow_font.render("UMA CAMPANHA D&D 5E", True,
                                       (*C_TEXT_DIM, alpha_title))
        surface.blit(top_text, top_text.get_rect(center=(w // 2, ty_base - 22)))

        # Main title
        title_surf = title_font.render("Curse of Strahd", True, C_TEXT_BRIGHT)
        title_surf.set_alpha(alpha_title)
        tr = title_surf.get_rect(center=(w // 2, ty_base))
        surface.blit(title_surf, tr)

        # Subtitle
        sub_surf = subtitle_font.render("Virtual Tabletop", True, C_GOLD)
        sub_surf.set_alpha(alpha_title)
        sr = sub_surf.get_rect(center=(w // 2, ty_base + 54))
        surface.blit(sub_surf, sr)

        # Ornament
        draw_ornament_line(surface, w // 2, ty_base + 84, 320, C_GOLD)

    def _draw_menu_items(self, surface):
        font = fonts.get("heading", FONT_MENU)
        for i, item in enumerate(self._items):
            # stagger intro
            t = max(0.0, min(1.0, (self._intro_t - 0.3 - i * 0.08) / 0.25))
            if t <= 0:
                continue
            item.draw(surface, font, self._time)

    def _draw_footer(self, surface, w, h):
        font = fonts.get("body", FONT_SMALL)
        col  = (*C_TEXT_DIM, 160)
        tmp  = pygame.Surface((w, 20), pygame.SRCALPHA)
        txt  = font.render("↑↓ / Mouse para navegar   ·   Enter / Clique para selecionar", True, C_TEXT_DIM)
        tmp.blit(txt, txt.get_rect(center=(w // 2, 10)))
        surface.blit(tmp, (0, h - 30))

    @staticmethod
    def _ease_out(t):
        return 1.0 - (1.0 - t) ** 3
