"""
Scene: Options
Resolution, fullscreen dropdowns; FPS toggle; GUI/Music/SFX sliders.
"""

import pygame
from src.constants import *
from src import fonts, settings
from src.ui.widgets import (draw_panel, draw_text, draw_text_centered,
                             draw_ornament_line, Button, Dropdown, Slider)
from src.ui.atmosphere import AtmosphereRenderer


_RES_LABELS = [f"{w}×{h}" for w, h in RESOLUTIONS]
_FS_LABELS  = ["Janela", "Tela Cheia"]


class OptionsScene:
    def __init__(self, app):
        self.app   = app
        self.atm   = AtmosphereRenderer(*app.size)
        self._time = 0.0

        cur_res   = settings.resolution()
        res_idx   = next((i for i, r in enumerate(RESOLUTIONS) if list(r) == list(cur_res)), 2)
        fs_idx    = 1 if settings.fullscreen() else 0

        self._dd_res  = Dropdown(0, 0, 220, 38, _RES_LABELS, res_idx)
        self._dd_fs   = Dropdown(0, 0, 180, 38, _FS_LABELS, fs_idx)
        self._sl_gui  = Slider(0, 0, 260, 24, settings.vol_gui())
        self._sl_mus  = Slider(0, 0, 260, 24, settings.vol_music())
        self._sl_sfx  = Slider(0, 0, 260, 24, settings.vol_sfx())

        self._fps_on  = settings.show_fps()
        self._fps_rect = pygame.Rect(0, 0, 26, 26)

        self._btn_apply = Button(0, 0, 160, 44, "Aplicar", accent=True)
        self._btn_back  = Button(0, 0, 130, 40, "← Voltar")

        self._build_layout()

    def _build_layout(self):
        w, h = self.app.size
        pw = min(640, w - 60)
        ph = min(500, h - 100)
        cx = w // 2
        self._panel = pygame.Rect(cx - pw // 2, h // 2 - ph // 2, pw, ph)

        lx  = self._panel.x + 30
        rx  = self._panel.x + pw // 2 + 20
        y0  = self._panel.y + 70

        row_h = 56

        # Row 0: Resolution
        self._dd_res.rect = pygame.Rect(rx, y0, 220, 38)
        # Row 1: Fullscreen
        self._dd_fs.rect  = pygame.Rect(rx, y0 + row_h, 180, 38)
        # Row 2: Show FPS checkbox
        self._fps_rect    = pygame.Rect(rx, y0 + row_h * 2 + 6, 26, 26)
        # Row 3: GUI vol
        self._sl_gui.track = pygame.Rect(rx, y0 + row_h * 3 + 12, 260, 6)
        self._sl_gui.rect  = pygame.Rect(rx, y0 + row_h * 3, 260, 24)
        # Row 4: Music vol
        self._sl_mus.track = pygame.Rect(rx, y0 + row_h * 4 + 12, 260, 6)
        self._sl_mus.rect  = pygame.Rect(rx, y0 + row_h * 4, 260, 24)
        # Row 5: SFX vol
        self._sl_sfx.track = pygame.Rect(rx, y0 + row_h * 5 + 12, 260, 6)
        self._sl_sfx.rect  = pygame.Rect(rx, y0 + row_h * 5, 260, 24)

        self._labels_y = [y0 + i * row_h + 10 for i in range(6)]
        self._label_x  = lx

        self._btn_apply.rect = pygame.Rect(cx - 85, self._panel.bottom - 60, 160, 44)
        self._btn_back.rect  = pygame.Rect(self._panel.x + 10, self._panel.y + 10, 130, 40)

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.change_scene(SCENE_MENU)

        if self._btn_back.handle_event(event):
            self.app.change_scene(SCENE_MENU)

        if self._btn_apply.handle_event(event):
            self._apply()

        # FPS toggle
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._fps_rect.collidepoint(event.pos):
                self._fps_on = not self._fps_on

        self._dd_res.handle_event(event)
        self._dd_fs.handle_event(event)
        self._sl_gui.handle_event(event)
        self._sl_mus.handle_event(event)
        self._sl_sfx.handle_event(event)

    def _apply(self):
        res = RESOLUTIONS[self._dd_res.index]
        fs  = (self._dd_fs.index == 1)
        settings.set("resolution",  list(res))
        settings.set("fullscreen",  fs)
        settings.set("show_fps",    self._fps_on)
        settings.set("vol_gui",     round(self._sl_gui.value, 2))
        settings.set("vol_music",   round(self._sl_mus.value, 2))
        settings.set("vol_sfx",     round(self._sl_sfx.value, 2))
        settings.save()
        self.app.apply_display_settings()

    def update(self, dt):
        self._time += dt
        self.atm.update(dt)

    def draw(self, surface):
        w, h = self.app.size
        self.atm.draw(surface)
        draw_panel(surface, self._panel, C_PANEL_DARK, C_BORDER, 1, radius=8, alpha=230)

        hfont = fonts.get("heading", 24)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)

        draw_text_centered(surface, "OPÇÕES", hfont, C_GOLD, w // 2,
                           self._panel.y + 28)
        draw_ornament_line(surface, w // 2, self._panel.y + 52, 400)

        lx = self._label_x
        labels = ["Resolução", "Modo de Tela", "Mostrar FPS",
                  "Volume GUI", "Volume Música", "Volume SFX"]
        for i, lbl in enumerate(labels):
            draw_text(surface, lbl, bfont, C_TEXT, lx, self._labels_y[i])

        # Dropdowns
        self._dd_res.draw(surface, sfont)
        self._dd_fs.draw(surface, sfont)

        # FPS checkbox
        pygame.draw.rect(surface, C_PANEL_DARK, self._fps_rect, border_radius=3)
        brd = C_BORDER_SEL if self._fps_on else C_BORDER
        pygame.draw.rect(surface, brd, self._fps_rect, 2, border_radius=3)
        if self._fps_on:
            pygame.draw.line(surface, C_GOLD,
                             (self._fps_rect.x + 4, self._fps_rect.centery),
                             (self._fps_rect.centerx - 1, self._fps_rect.bottom - 5), 2)
            pygame.draw.line(surface, C_GOLD,
                             (self._fps_rect.centerx - 1, self._fps_rect.bottom - 5),
                             (self._fps_rect.right - 4, self._fps_rect.y + 4), 2)

        # Sliders + percentage labels
        for sl, y_row in [(self._sl_gui, self._labels_y[3]),
                          (self._sl_mus, self._labels_y[4]),
                          (self._sl_sfx, self._labels_y[5])]:
            sl.draw(surface)
            pct = f"{int(sl.value * 100)}%"
            draw_text(surface, pct, sfont, C_TEXT_DIM,
                      sl.track.right + 10, y_row)

        self._btn_apply.draw(surface, bfont)
        self._btn_back.draw(surface, bfont)
