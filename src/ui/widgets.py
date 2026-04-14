"""
UI helpers shared across all scenes.
"""

import pygame
import math
from src.constants import *
from src import fonts


# ── Basic drawing helpers ─────────────────────────────────────────────────────

def draw_panel(surface, rect, color=C_PANEL, border_color=C_BORDER,
               border_width=1, radius=6, alpha=None):
    if alpha is not None:
        tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (*color, alpha), tmp.get_rect(), border_radius=radius)
        if border_width:
            pygame.draw.rect(tmp, (*border_color, min(alpha + 40, 255)),
                             tmp.get_rect(), border_width, border_radius=radius)
        surface.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)
        if border_width:
            pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)


def draw_text(surface, text, font, color, x, y, align="left"):
    rendered = font.render(text, True, color)
    r = rendered.get_rect()
    if align == "center":
        r.centerx = x; r.top = y
    elif align == "right":
        r.right = x; r.top = y
    else:
        r.left = x; r.top = y
    surface.blit(rendered, r)
    return r


def draw_text_centered(surface, text, font, color, cx, cy):
    rendered = font.render(text, True, color)
    r = rendered.get_rect(center=(cx, cy))
    surface.blit(rendered, r)
    return r


def draw_divider(surface, x1, y, x2, color=C_BORDER, thickness=1):
    pygame.draw.line(surface, color, (x1, y), (x2, y), thickness)


def draw_ornament_line(surface, cx, y, width, color=C_GOLD):
    hw = width // 2
    pygame.draw.line(surface, color, (cx - hw, y), (cx + hw, y), 1)
    diamond = [(cx, y - 4), (cx + 4, y), (cx, y + 4), (cx - 4, y)]
    pygame.draw.polygon(surface, color, diamond)


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def glow_alpha(t, speed=2.0):
    return int(140 + 60 * math.sin(t * speed * math.pi))


# ── MenuItem ──────────────────────────────────────────────────────────────────

class MenuItem:
    def __init__(self, label, action, y_center, width, cx):
        self.label    = label
        self.action   = action
        self.cx       = cx
        self.y        = y_center
        self.width    = width
        self.height   = 52
        self.rect     = pygame.Rect(cx - width // 2, y_center - 26, width, 52)
        self.hovered  = False
        self.selected = False
        self._alpha   = 0.0

    def update(self, dt):
        target = 1.0 if (self.hovered or self.selected) else 0.0
        self._alpha += (target - self._alpha) * min(1.0, dt * 10.0)

    def draw(self, surface, font, time):
        a = self._alpha
        if a > 0.01:
            glow_rect = self.rect.inflate(int(20 * a), int(8 * a))
            draw_panel(surface, glow_rect,
                       color=lerp_color(C_PANEL, C_PANEL_DARK, 0.3),
                       border_color=lerp_color(C_BORDER, C_BORDER_SEL, a),
                       border_width=1, radius=4,
                       alpha=int(a * 160))

        if a > 0.05:
            marker_x_l = self.rect.left - int(22 * a)
            marker_x_r = self.rect.right + int(22 * a)
            my = self.y
            col = lerp_color(C_BORDER, C_GOLD_BRIGHT, a)
            pygame.draw.polygon(surface, col, [
                (marker_x_l, my - 5), (marker_x_l + 8, my), (marker_x_l, my + 5)
            ])
            pygame.draw.polygon(surface, col, [
                (marker_x_r, my - 5), (marker_x_r - 8, my), (marker_x_r, my + 5)
            ])

        text_col = lerp_color(C_TEXT, C_TEXT_BRIGHT, a)
        draw_text_centered(surface, self.label, font, text_col, self.cx, self.y)

    def check_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered


# ── Dropdown ──────────────────────────────────────────────────────────────────

class Dropdown:
    def __init__(self, x, y, w, h, options, selected_index=0):
        self.rect    = pygame.Rect(x, y, w, h)
        self.options = options
        self.index   = selected_index
        self.open    = False
        self._item_h = h

    @property
    def value(self):
        return self.options[self.index]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.open:
                for i, opt_rect in enumerate(self._option_rects()):
                    if opt_rect.collidepoint(event.pos):
                        old = self.index
                        self.index = i
                        self.open = False
                        return self.index != old
                self.open = False
            else:
                if self.rect.collidepoint(event.pos):
                    self.open = True
        return False

    def _option_rects(self):
        return [pygame.Rect(self.rect.x, self.rect.bottom + i * self._item_h,
                            self.rect.width, self._item_h)
                for i in range(len(self.options))]

    def draw(self, surface, font):
        border = C_BORDER_SEL if self.open else C_BORDER_HOV
        draw_panel(surface, self.rect, C_PANEL_DARK, border, 1, radius=4)
        draw_text(surface, str(self.options[self.index]), font, C_TEXT,
                  self.rect.x + 10, self.rect.centery - font.get_height() // 2)
        ax, ay = self.rect.right - 18, self.rect.centery
        pygame.draw.polygon(surface, C_GOLD,
                            [(ax, ay - 5), (ax + 10, ay - 5), (ax + 5, ay + 4)])
        if self.open:
            for i, opt_rect in enumerate(self._option_rects()):
                bg = C_BORDER if i == self.index else C_PANEL_DARK
                draw_panel(surface, opt_rect, bg, C_BORDER, 1, radius=0)
                col = C_GOLD_BRIGHT if i == self.index else C_TEXT
                draw_text(surface, str(self.options[i]), font, col,
                          opt_rect.x + 10, opt_rect.centery - font.get_height() // 2)


# ── Slider ────────────────────────────────────────────────────────────────────

class Slider:
    def __init__(self, x, y, w, h=20, value=0.8):
        self.track    = pygame.Rect(x, y + h // 2 - 3, w, 6)
        self.rect     = pygame.Rect(x, y, w, h)
        self.value    = value
        self._drag    = False
        self._handle_r = h // 2 + 2

    def _handle_cx(self):
        return int(self.track.x + self.value * self.track.width)

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hx = self._handle_cx()
            hy = self.track.centery
            if math.hypot(event.pos[0] - hx, event.pos[1] - hy) < self._handle_r + 6:
                self._drag = True
        if event.type == pygame.MOUSEBUTTONUP:
            self._drag = False
        if event.type == pygame.MOUSEMOTION and self._drag:
            rel = (event.pos[0] - self.track.x) / max(1, self.track.width)
            new_val = max(0.0, min(1.0, rel))
            changed = abs(new_val - self.value) > 0.001
            self.value = new_val
        return changed

    def draw(self, surface):
        pygame.draw.rect(surface, C_PANEL_DARK, self.track, border_radius=3)
        fill = pygame.Rect(self.track.x, self.track.y,
                           int(self.value * self.track.width), self.track.height)
        pygame.draw.rect(surface, C_CRIMSON, fill, border_radius=3)
        hx = self._handle_cx()
        hy = self.track.centery
        pygame.draw.circle(surface, C_GOLD_BRIGHT, (hx, hy), self._handle_r)
        pygame.draw.circle(surface, C_BORDER_SEL,  (hx, hy), self._handle_r, 2)


# ── TextInput ─────────────────────────────────────────────────────────────────

class TextInput:
    """Single-line text input. Tab, Ctrl+C, non-printable chars are ignored."""

    _IGNORED_KEYS = None  # built lazily after pygame.init()

    def __init__(self, x, y, w, h=40, placeholder="", max_len=64):
        self.rect        = pygame.Rect(x, y, w, h)
        self.placeholder = placeholder
        self.max_len     = max_len
        self.text        = ""
        self.active      = False
        self._cursor_t   = 0.0

    @classmethod
    def _get_ignored(cls):
        if cls._IGNORED_KEYS is None:
            cls._IGNORED_KEYS = {
                pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE,
                pygame.K_TAB,
                pygame.K_F1,  pygame.K_F2,  pygame.K_F3,  pygame.K_F4,
                pygame.K_F5,  pygame.K_F6,  pygame.K_F7,  pygame.K_F8,
                pygame.K_F9,  pygame.K_F10, pygame.K_F11, pygame.K_F12,
                pygame.K_UP,  pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                pygame.K_HOME, pygame.K_END, pygame.K_PAGEUP, pygame.K_PAGEDOWN,
                pygame.K_INSERT, pygame.K_DELETE, pygame.K_CAPSLOCK,
                pygame.K_LSHIFT, pygame.K_RSHIFT,
                pygame.K_LCTRL,  pygame.K_RCTRL,
                pygame.K_LALT,   pygame.K_RALT,
                pygame.K_LGUI,   pygame.K_RGUI,
                pygame.K_NUMLOCK, pygame.K_SCROLLOCK,
                pygame.K_PRINT, pygame.K_PAUSE,
            }
        return cls._IGNORED_KEYS

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            mods = pygame.key.get_mods()
            ctrl = bool(mods & (pygame.KMOD_CTRL | pygame.KMOD_META))

            if event.key == pygame.K_BACKSPACE:
                if ctrl:
                    # Ctrl+Backspace: apaga ultima palavra
                    txt = self.text.rstrip()
                    idx = txt.rfind(" ")
                    self.text = txt[:idx + 1] if idx >= 0 else ""
                else:
                    self.text = self.text[:-1]

            elif ctrl and event.key == pygame.K_v:
                # Ctrl+V: colar
                try:
                    if not pygame.scrap.get_init():
                        pygame.scrap.init()
                    clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clip:
                        pasted = clip.decode("utf-8", errors="ignore")
                        pasted = pasted.replace("\x00", "").replace("\r", "").replace("\n", "")
                        space = self.max_len - len(self.text)
                        self.text += pasted[:space]
                except Exception:
                    pass

            elif ctrl:
                pass  # ignora outros atalhos Ctrl silenciosamente

            elif event.key in self._get_ignored():
                pass  # ignora silenciosamente

            else:
                ch = event.unicode
                if ch and ord(ch) >= 32 and len(self.text) < self.max_len:
                    self.text += ch

            return True
        return False

    def update(self, dt):
        self._cursor_t += dt

    def draw(self, surface, font):
        border = C_BORDER_SEL if self.active else C_BORDER
        draw_panel(surface, self.rect, C_PANEL_DARK, border, 1, radius=4)
        display = self.text if self.text else self.placeholder
        col = C_TEXT if self.text else C_TEXT_DIM
        draw_text(surface, display, font, col,
                  self.rect.x + 10, self.rect.centery - font.get_height() // 2)
        if self.active and int(self._cursor_t * 2) % 2 == 0:
            tw = font.size(self.text)[0]
            cx = self.rect.x + 10 + tw + 2
            pygame.draw.line(surface, C_TEXT,
                             (cx, self.rect.y + 8), (cx, self.rect.bottom - 8), 1)


# ── Button ────────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, x, y, w, h, label, accent=False):
        self.rect    = pygame.Rect(x, y, w, h)
        self.label   = label
        self.accent  = accent
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    def draw(self, surface, font):
        if self.accent:
            bg  = C_CRIMSON_HOV if self.hovered else C_CRIMSON
            brd = C_BORDER_SEL
        else:
            bg  = C_PANEL if self.hovered else C_PANEL_DARK
            brd = C_BORDER_HOV if self.hovered else C_BORDER
        draw_panel(surface, self.rect, bg, brd, 1, radius=5)
        col = C_TEXT_BRIGHT if self.hovered else C_TEXT
        draw_text_centered(surface, self.label, font,
                           col, self.rect.centerx, self.rect.centery)