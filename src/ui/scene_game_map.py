"""
Scene: Game Map
Grid top-down com zoom (scroll do mouse) e panning (click+drag no meio/direito).
Sem tokens por enquanto.
"""

import pygame
import math
from src.constants import *
from src import fonts
from src.ui.widgets import draw_panel, draw_text, draw_text_centered, Button


# Tamanho base de cada celula do grid em pixels (antes do zoom)
BASE_CELL = 48

# Limites de zoom
ZOOM_MIN = 0.25
ZOOM_MAX = 4.0
ZOOM_STEP = 0.1

# Cor do grid
C_GRID_LINE   = (50, 38, 62)
C_GRID_LINE_5 = (80, 55, 90)   # a cada 5 celulas, linha mais visivel
C_MAP_BG      = (18, 13, 24)


class GameMapScene:
    def __init__(self, app):
        self.app    = app
        self._time  = 0.0

        # Camera: offset em pixels do mundo (canto superior esquerdo da tela = qual ponto do mundo)
        w, h = app.size
        self._cam_x  = 0.0   # offset do mundo em pixels-mundo
        self._cam_y  = 0.0
        self._zoom   = 1.0

        # Grid dimensions (must be set before _center_camera)
        self._grid_w     = 80
        self._grid_h     = 60

        # Centraliza a camera no inicio
        self._center_camera()

        # Panning
        self._panning    = False
        self._pan_start  = (0, 0)
        self._pan_cam_start = (0.0, 0.0)

        # UI
        self._btn_back   = Button(0, 0, 110, 34, "< Sair")
        self._btn_zoomin = Button(0, 0, 36,  36, "+")
        self._btn_zoomout= Button(0, 0, 36,  36, "-")
        self._btn_reset  = Button(0, 0, 80,  34, "Reset")
        self._show_coords= True

        # Superficie do grid (recriada ao zoom mudar)
        self._grid_surf  = None
        self._grid_zoom  = -1.0   # zoom com que o grid foi desenhado

        self._build_layout()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        w, h = self.app.size
        self._btn_back.rect    = pygame.Rect(10, 10, 110, 34)
        self._btn_zoomout.rect = pygame.Rect(w - 92, 10, 36, 36)
        self._btn_zoomin.rect  = pygame.Rect(w - 50, 10, 36, 36)
        self._btn_reset.rect   = pygame.Rect(w - 180, 10, 80, 34)

    def on_resize(self, w, h):
        self._build_layout()
        self._grid_surf = None  # forca recriacao

    def _center_camera(self):
        w, h = self.app.size
        world_w = self._grid_w * BASE_CELL
        world_h = self._grid_h * BASE_CELL
        self._cam_x = (world_w - w / self._zoom) / 2
        self._cam_y = (world_h - h / self._zoom) / 2

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _world_to_screen(self, wx, wy):
        sx = (wx - self._cam_x) * self._zoom
        sy = (wy - self._cam_y) * self._zoom
        return sx, sy

    def _screen_to_world(self, sx, sy):
        wx = sx / self._zoom + self._cam_x
        wy = sy / self._zoom + self._cam_y
        return wx, wy

    def _screen_to_cell(self, sx, sy):
        wx, wy = self._screen_to_world(sx, sy)
        return int(wx // BASE_CELL), int(wy // BASE_CELL)

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._leave()
            elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                self._zoom_at_center(ZOOM_STEP)
            elif event.key == pygame.K_MINUS:
                self._zoom_at_center(-ZOOM_STEP)
            elif event.key == pygame.K_0:
                self._reset_view()
            elif event.key == pygame.K_g:
                self._show_coords = not self._show_coords

        # Botoes UI
        if self._btn_back.handle_event(event):
            self._leave()
        if self._btn_zoomin.handle_event(event):
            self._zoom_at_center(ZOOM_STEP * 2)
        if self._btn_zoomout.handle_event(event):
            self._zoom_at_center(-ZOOM_STEP * 2)
        if self._btn_reset.handle_event(event):
            self._reset_view()

        # Zoom via scroll do mouse
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            delta  = ZOOM_STEP * event.y
            self._zoom_at_point(mx, my, delta)

        # Panning: botao do meio OU botao direito
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (2, 3):  # meio ou direito
                self._panning = True
                self._pan_start = event.pos
                self._pan_cam_start = (self._cam_x, self._cam_y)
            # Clique esquerdo fora dos botoes UI
            if event.button == 1:
                ui_rects = [self._btn_back.rect, self._btn_zoomin.rect,
                            self._btn_zoomout.rect, self._btn_reset.rect]
                if not any(r.collidepoint(event.pos) for r in ui_rects):
                    pass  # futuro: selecionar token

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button in (2, 3):
                self._panning = False

        if event.type == pygame.MOUSEMOTION:
            if self._panning:
                dx = (event.pos[0] - self._pan_start[0]) / self._zoom
                dy = (event.pos[1] - self._pan_start[1]) / self._zoom
                self._cam_x = self._pan_cam_start[0] - dx
                self._cam_y = self._pan_cam_start[1] - dy
                self._clamp_camera()

    def _zoom_at_point(self, sx, sy, delta):
        """Zoom centrado no ponto da tela (sx, sy)."""
        wx_before, wy_before = self._screen_to_world(sx, sy)
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom + delta))
        if new_zoom == self._zoom:
            return
        self._zoom = new_zoom
        # Reposiciona camera para o ponto continuar no mesmo lugar
        self._cam_x = wx_before - sx / self._zoom
        self._cam_y = wy_before - sy / self._zoom
        self._clamp_camera()
        self._grid_surf = None  # invalida cache

    def _zoom_at_center(self, delta):
        w, h = self.app.size
        self._zoom_at_point(w // 2, h // 2, delta)

    def _clamp_camera(self):
        world_w = self._grid_w * BASE_CELL
        world_h = self._grid_h * BASE_CELL
        w, h    = self.app.size
        view_w  = w / self._zoom
        view_h  = h / self._zoom
        self._cam_x = max(0, min(self._cam_x, world_w - view_w))
        self._cam_y = max(0, min(self._cam_y, world_h - view_h))

    def _reset_view(self):
        self._zoom = 1.0
        self._center_camera()
        self._grid_surf = None

    def _leave(self):
        self.app._scenes.pop("game_map", None)
        self.app.change_scene(SCENE_LOBBY)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        self._time += dt

        # Panning com WASD / setas quando nao ha input de texto
        keys   = pygame.key.get_pressed()
        speed  = 300 / self._zoom  # pixels-mundo por segundo
        moved  = False
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self._cam_x -= speed * dt; moved = True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self._cam_x += speed * dt; moved = True
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self._cam_y -= speed * dt; moved = True
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self._cam_y += speed * dt; moved = True
        if moved:
            self._clamp_camera()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface):
        w, h = self.app.size

        # Fundo do mapa
        surface.fill(C_MAP_BG)

        # Grid
        self._draw_grid(surface, w, h)

        # UI overlay
        self._draw_ui(surface, w, h)

    def _draw_grid(self, surface, w, h):
        cell = BASE_CELL * self._zoom  # tamanho da celula em pixels de tela

        # Primeira celula visivel
        start_cx = int(self._cam_x / BASE_CELL)
        start_cy = int(self._cam_y / BASE_CELL)
        # Quantidade de celulas visiveis + margem
        count_x  = int(w / cell) + 3
        count_y  = int(h / cell) + 3

        for cx in range(start_cx, min(start_cx + count_x, self._grid_w + 1)):
            sx, _ = self._world_to_screen(cx * BASE_CELL, 0)
            col   = C_GRID_LINE_5 if cx % 5 == 0 else C_GRID_LINE
            thick = 1 if cx % 5 != 0 else 1
            pygame.draw.line(surface, col,
                             (int(sx), 0), (int(sx), h), thick)

        for cy in range(start_cy, min(start_cy + count_y, self._grid_h + 1)):
            _, sy = self._world_to_screen(0, cy * BASE_CELL)
            col   = C_GRID_LINE_5 if cy % 5 == 0 else C_GRID_LINE
            pygame.draw.line(surface, col,
                             (0, int(sy)), (w, int(sy)), 1)

        # Coordenadas nas celulas (a cada 5, se zoom permitir)
        if self._show_coords and cell >= 20:
            sfont = fonts.get("body", max(8, min(14, int(cell * 0.25))))
            for cx in range(start_cx, min(start_cx + count_x, self._grid_w)):
                for cy in range(start_cy, min(start_cy + count_y, self._grid_h)):
                    if cx % 5 != 0 or cy % 5 != 0:
                        continue
                    sx, sy = self._world_to_screen(cx * BASE_CELL + 3,
                                                   cy * BASE_CELL + 2)
                    if 0 <= sx < w and 0 <= sy < h:
                        lbl  = f"{cx},{cy}"
                        surf = sfont.render(lbl, True, C_GRID_LINE_5)
                        surface.blit(surf, (int(sx), int(sy)))

        # Borda do mapa
        bx, by = self._world_to_screen(0, 0)
        bw = self._grid_w * BASE_CELL * self._zoom
        bh = self._grid_h * BASE_CELL * self._zoom
        pygame.draw.rect(surface, C_BORDER_HOV,
                         (int(bx), int(by), int(bw), int(bh)), 2)

    def _draw_ui(self, surface, w, h):
        sfont = fonts.get("body", FONT_SMALL)
        bfont = fonts.get("body", FONT_BODY)

        # Barra de topo semi-transparente
        bar = pygame.Surface((w, 54), pygame.SRCALPHA)
        bar.fill((10, 6, 14, 210))
        surface.blit(bar, (0, 0))

        self._btn_back.draw(surface, sfont)
        self._btn_zoomin.draw(surface, bfont)
        self._btn_zoomout.draw(surface, bfont)
        self._btn_reset.draw(surface, sfont)

        # Zoom %
        zoom_txt = f"{int(self._zoom * 100)}%"
        draw_text(surface, zoom_txt, sfont, C_TEXT_DIM,
                  self._btn_reset.rect.x - 52, 20)

        # Coordenada do mouse em celula
        mx, my = pygame.mouse.get_pos()
        if my > 54:
            cx, cy = self._screen_to_cell(mx, my)
            if 0 <= cx < self._grid_w and 0 <= cy < self._grid_h:
                coord_txt = f"Celula  {cx}, {cy}"
                draw_text(surface, coord_txt, sfont, C_TEXT_DIM,
                          w // 2 - 40, 20)

        # Hint na primeira vez
        draw_text(surface,
                  "Scroll: zoom   |   Clique dir / meio: mover   |   WASD / setas: mover   |   G: coords",
                  sfont, (60, 50, 70), 130, 37)

        # Status de rede
        client = getattr(self.app, "client", None)
        if client:
            n = len(getattr(client, "players", []))
            draw_text(surface, f"Jogadores: {n}", sfont, C_GOLD_BRIGHT,
                      w - 130, 37)