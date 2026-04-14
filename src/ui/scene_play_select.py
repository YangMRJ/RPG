"""
Scene: Play Select
Mestrar (host) | Jogar (join) com lista de lobbys salvos.
Tab navega entre inputs. Inputs separados por modo.
"""

import pygame
import json
import os
import threading
from src.constants import *
from src import fonts
from src.ui.widgets import (draw_panel, draw_text_centered, draw_text,
                             draw_ornament_line, Button, TextInput)
from src.ui.atmosphere import AtmosphereRenderer
from src.network.server import GameServer
from src.network.client import GameClient

LOBBIES_FILE = os.path.join("data", "lobbies.json")


def _load_lobbies():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(LOBBIES_FILE):
        return []
    try:
        with open(LOBBIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_lobbies(lobbies):
    os.makedirs("data", exist_ok=True)
    with open(LOBBIES_FILE, "w", encoding="utf-8") as f:
        json.dump(lobbies, f, indent=2, ensure_ascii=False)


class PlaySelectScene:
    def __init__(self, app):
        self.app         = app
        self.atm         = AtmosphereRenderer(*app.size)
        self._time       = 0.0
        self._hovered    = None
        self._mode       = None
        self._status     = ""
        self._connecting = False
        self._error      = ""

        # HOST inputs (separados do join)
        self._host_name  = TextInput(0, 0, 190, 38, placeholder="Seu nome", max_len=24)

        # JOIN inputs
        self._ip_input   = TextInput(0, 0, 160, 38, placeholder="IP", max_len=40)
        self._port_input = TextInput(0, 0, 100, 38, placeholder=str(DEFAULT_PORT), max_len=6)
        self._name_input = TextInput(0, 0, 260, 38, placeholder="Seu nome", max_len=24)

        # Tab order para join
        self._join_tab_order = [self._ip_input, self._port_input, self._name_input]

        # Buttons
        self._btn_connect = Button(0, 0, 130, 40, "Conectar", accent=True)
        self._btn_save    = Button(0, 0, 110, 32, "Salvar")
        self._btn_host    = Button(0, 0, 190, 44, "Iniciar Servidor", accent=True)
        self._btn_back    = Button(0, 0, 110, 36, "< Voltar")

        # Saved lobbies
        self._lobbies   = _load_lobbies()
        self._lobby_sel = -1

        self._build_layout()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        w, h = self.app.size
        cx = w // 2

        pw = min(840, w - 60)
        ph = min(500, h - 80)
        self._panel = pygame.Rect(cx - pw // 2, h // 2 - ph // 2, pw, ph)

        card_w = pw // 2 - 28
        card_h = ph - 90
        self._card_host = pygame.Rect(self._panel.x + 14,
                                      self._panel.y + 56, card_w, card_h)
        self._card_join = pygame.Rect(self._panel.x + 14 + card_w + 14,
                                      self._panel.y + 56, card_w, card_h)

        # HOST form layout
        hcx = self._card_host.centerx
        hy0 = self._card_host.y + 56
        self._host_name.rect  = pygame.Rect(hcx - 95, hy0,       190, 38)
        self._btn_host.rect   = pygame.Rect(hcx - 95, hy0 + 56,  190, 44)

        # JOIN form layout
        jx  = self._card_join.x + 12
        jy  = self._card_join.y + 50
        fw  = self._card_join.width - 24

        self._ip_input.rect   = pygame.Rect(jx,             jy,       fw - 116, 38)
        self._port_input.rect = pygame.Rect(jx + fw - 110,  jy,       106,      38)
        self._name_input.rect = pygame.Rect(jx,             jy + 52,  fw,       38)
        self._btn_save.rect   = pygame.Rect(jx,             jy + 104, 110,      32)
        self._btn_connect.rect = pygame.Rect(self._card_join.right - 142,
                                             jy + 100, 130, 40)

        # Saved lobbies list
        self._list_y0 = jy + 152
        self._list_x  = jx
        self._list_w  = fw

        # Back
        self._btn_back.rect = pygame.Rect(self._panel.x + 10,
                                          self._panel.y + 10, 110, 36)

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    # ── Active input tracking ─────────────────────────────────────────────────

    def _active_join_input_index(self):
        for i, inp in enumerate(self._join_tab_order):
            if inp.active:
                return i
        return -1

    def _tab_next(self):
        inputs = self._join_tab_order
        idx = self._active_join_input_index()
        # deactivate all
        for inp in inputs:
            inp.active = False
        # activate next
        next_idx = (idx + 1) % len(inputs)
        inputs[next_idx].active = True

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        # Global
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.change_scene(SCENE_MENU)

        if self._btn_back.handle_event(event):
            self.app.change_scene(SCENE_MENU)

        # Card select (only if not already in that mode)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._card_host.collidepoint(event.pos) and self._mode != "host":
                self._mode  = "host"
                self._error = ""
                self._status = ""
            elif self._card_join.collidepoint(event.pos) and self._mode != "join":
                self._mode  = "join"
                self._error = ""
                self._status = ""

        # Hover
        if event.type == pygame.MOUSEMOTION:
            if self._card_host.collidepoint(event.pos):
                self._hovered = "host"
            elif self._card_join.collidepoint(event.pos):
                self._hovered = "join"
            else:
                self._hovered = None

        # HOST mode events
        if self._mode == "host":
            # Tab no campo de nome do host nao faz nada (so tem 1)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                pass  # silencio
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self._host_name.active:
                    self._do_host()
            else:
                self._host_name.handle_event(event)
            if self._btn_host.handle_event(event):
                self._do_host()

        # JOIN mode events
        if self._mode == "join":
            # Tab navega entre inputs
            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                any_active = any(inp.active for inp in self._join_tab_order)
                if any_active:
                    self._tab_next()
                else:
                    self._join_tab_order[0].active = True
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                # Enter no ultimo campo = conectar
                if self._name_input.active:
                    self._do_join()
            else:
                self._ip_input.handle_event(event)
                self._port_input.handle_event(event)
                self._name_input.handle_event(event)

            if self._btn_save.handle_event(event):
                self._save_lobby()

            if self._btn_connect.handle_event(event):
                self._do_join()

            # Lobby list clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, (row_rect, del_rect) in enumerate(self._lobby_row_rects()):
                    if del_rect.collidepoint(event.pos):
                        self._lobbies.pop(i)
                        _save_lobbies(self._lobbies)
                        if self._lobby_sel >= len(self._lobbies):
                            self._lobby_sel = len(self._lobbies) - 1
                        break
                    elif row_rect.collidepoint(event.pos):
                        self._lobby_sel = i
                        lob = self._lobbies[i]
                        self._ip_input.text   = lob.get("ip", "")
                        self._port_input.text = str(lob.get("port", DEFAULT_PORT))
                        self._name_input.text = lob.get("name", "")
                        break

    # ── Lobby helpers ─────────────────────────────────────────────────────────

    def _save_lobby(self):
        ip = self._ip_input.text.strip()
        if not ip:
            self._error = "Digite o IP antes de salvar."
            return
        try:
            port = int(self._port_input.text.strip() or str(DEFAULT_PORT))
        except ValueError:
            self._error = "Porta invalida."
            return
        name = self._name_input.text.strip()
        for lob in self._lobbies:
            if lob.get("ip") == ip and lob.get("port") == port:
                lob["name"] = name
                _save_lobbies(self._lobbies)
                self._status = "Lobby atualizado."
                self._error  = ""
                return
        self._lobbies.append({"ip": ip, "port": port, "name": name})
        _save_lobbies(self._lobbies)
        self._status = f"Salvo: {ip}:{port}"
        self._error  = ""

    def _lobby_row_rects(self):
        rects = []
        row_h = 34
        for i in range(len(self._lobbies)):
            y    = self._list_y0 + i * row_h
            row  = pygame.Rect(self._list_x, y, self._list_w - 36, row_h - 2)
            delr = pygame.Rect(self._list_x + self._list_w - 32, y + 5, 24, 24)
            rects.append((row, delr))
        return rects

    # ── Connection ────────────────────────────────────────────────────────────

    def _do_host(self):
        if self._connecting:
            return
        self._connecting = True
        self._status = "Iniciando servidor..."
        self._error  = ""

        def run():
            import time
            try:
                port   = DEFAULT_PORT
                server = GameServer(port=port)
                self.app.server = server
                server.start()
                time.sleep(0.6)
                self._status = f"Porta {port} — conectando..."
                name   = self._host_name.text.strip() or "Mestre"
                client = GameClient("127.0.0.1", port, name)
                self.app.client = client
                client.connect()
                self._connecting = False
                pygame.event.post(pygame.event.Event(pygame.USEREVENT,
                    {"action": "goto", "scene": SCENE_LOBBY}))
            except Exception as e:
                self._error      = str(e)
                self._status     = ""
                self._connecting = False

        threading.Thread(target=run, daemon=True).start()

    def _do_join(self):
        if self._connecting:
            return
        ip = self._ip_input.text.strip() or "127.0.0.1"
        try:
            port = int(self._port_input.text.strip() or str(DEFAULT_PORT))
        except ValueError:
            self._error = "Porta invalida"
            return
        name = self._name_input.text.strip() or "Jogador"
        self._connecting = True
        self._status     = f"Conectando a {ip}:{port}..."
        self._error      = ""

        def run():
            try:
                client = GameClient(ip, port, name)
                client.connect()
                self.app.client  = client
                self._connecting = False
                pygame.event.post(pygame.event.Event(pygame.USEREVENT,
                    {"action": "goto", "scene": SCENE_LOBBY}))
            except Exception as e:
                self._error      = f"Falha: {e}"
                self._status     = ""
                self._connecting = False

        threading.Thread(target=run, daemon=True).start()

    # ── Update / Draw ─────────────────────────────────────────────────────────

    def update(self, dt):
        self._time += dt
        self.atm.update(dt)
        self._host_name.update(dt)
        self._ip_input.update(dt)
        self._port_input.update(dt)
        self._name_input.update(dt)

    def draw(self, surface):
        w, h = self.app.size
        self.atm.draw(surface)

        draw_panel(surface, self._panel, C_PANEL_DARK, C_BORDER, 1, radius=8, alpha=230)

        hfont = fonts.get("heading", 24)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)

        draw_text_centered(surface, "COMO DESEJA JOGAR?",
                           hfont, C_GOLD, w // 2, self._panel.y + 28)
        draw_ornament_line(surface, w // 2, self._panel.y + 50, 400)

        self._draw_card(surface, self._card_host, "host",
                        "MESTRAR",
                        ["Hospedar uma sessao", "Outros jogadores se", "conectam ao seu IP"])
        self._draw_card(surface, self._card_join, "join",
                        "JOGAR",
                        ["Entrar como jogador", "Informe o IP do", "mestre para conectar"])

        if self._mode == "host":
            self._draw_host_form(surface, bfont, sfont)
        if self._mode == "join":
            self._draw_join_form(surface, bfont, sfont)

        msg_y = self._panel.bottom - 26
        if self._status:
            draw_text_centered(surface, self._status, sfont, C_GOLD, w // 2, msg_y)
        if self._error:
            draw_text_centered(surface, self._error, sfont, C_TEXT_ACCENT, w // 2, msg_y)

        self._btn_back.draw(surface, sfont)

    def _draw_card(self, surface, rect, key, title, lines):
        selected = (self._mode == key)
        hovered  = (self._hovered == key)
        border   = C_BORDER_SEL if selected else (C_BORDER_HOV if hovered else C_BORDER)
        bg       = C_PANEL if selected else C_PANEL_DARK
        draw_panel(surface, rect, bg, border, 2, radius=6)
        hfont = fonts.get("heading", 19)
        bfont = fonts.get("body", FONT_BODY)
        draw_text_centered(surface, title, hfont,
                           C_GOLD_BRIGHT if selected else C_GOLD,
                           rect.centerx, rect.y + 22)
        if not selected:
            for i, line in enumerate(lines):
                draw_text_centered(surface, line, bfont, C_TEXT_DIM,
                                   rect.centerx, rect.y + 52 + i * 22)

    def _draw_host_form(self, surface, bfont, sfont):
        hcx = self._card_host.centerx
        nr  = self._host_name.rect
        draw_text(surface, "Seu nome:", sfont, C_TEXT_DIM,
                  nr.x, nr.y - 17)
        self._host_name.draw(surface, bfont)
        self._btn_host.draw(surface, bfont)

        # Dica de IP
        try:
            import socket
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "???"
        draw_text_centered(surface, f"Seu IP: {ip}", sfont, C_TEXT_DIM,
                           hcx, self._btn_host.rect.bottom + 18)
        draw_text_centered(surface, f"Porta: {DEFAULT_PORT}", sfont, C_TEXT_DIM,
                           hcx, self._btn_host.rect.bottom + 36)

    def _draw_join_form(self, surface, bfont, sfont):
        jx = self._card_join.x + 12
        jy = self._card_join.y + 50

        draw_text(surface, "IP:", sfont, C_TEXT_DIM, jx, jy - 16)
        draw_text(surface, "Porta:", sfont, C_TEXT_DIM,
                  self._port_input.rect.x, jy - 16)
        draw_text(surface, "Nome:", sfont, C_TEXT_DIM, jx, jy + 36)

        self._ip_input.draw(surface, bfont)
        self._port_input.draw(surface, bfont)
        self._name_input.draw(surface, bfont)
        self._btn_save.draw(surface, sfont)
        self._btn_connect.draw(surface, bfont)

        # Divider + lista
        lx   = self._list_x
        lw   = self._list_w
        ly0  = self._list_y0
        draw_ornament_line(surface, lx + lw // 2, ly0 - 10, lw)

        if not self._lobbies:
            draw_text_centered(surface, "Nenhum lobby salvo.",
                               sfont, C_TEXT_DIM,
                               self._card_join.centerx, ly0 + 14)
            return

        draw_text(surface, "Lobbies salvos:", sfont, C_TEXT_DIM, lx, ly0 - 24)

        clip = surface.get_clip()
        surface.set_clip(pygame.Rect(lx, ly0, lw,
                                     self._card_join.bottom - ly0 - 8))

        for i, (row_rect, del_rect) in enumerate(self._lobby_row_rects()):
            lob = self._lobbies[i]
            sel = (i == self._lobby_sel)
            draw_panel(surface, row_rect,
                       C_PANEL if sel else C_PANEL_DARK,
                       C_BORDER_SEL if sel else C_BORDER, 1, radius=4)
            label = f"{lob.get('ip','')}:{lob.get('port', DEFAULT_PORT)}"
            nm    = lob.get("name", "")
            if nm:
                label += f"  ({nm})"
            draw_text(surface, label, sfont,
                      C_TEXT_BRIGHT if sel else C_TEXT,
                      row_rect.x + 8,
                      row_rect.centery - sfont.get_height() // 2)
            draw_panel(surface, del_rect, C_PANEL_DARK, C_BORDER, 1, radius=3)
            draw_text_centered(surface, "x", sfont, C_TEXT_ACCENT,
                               del_rect.centerx, del_rect.centery)

        surface.set_clip(clip)