"""
Scene: Lobby
- Lista de jogadores com indicador verde/vermelho de pronto
- Mestre nao tem botao de pronto, tem botao de comecar com contagem
- Se nem todos prontos, confirmacao antes de comecar
- Ao comecar, vai pro mapa de grid
"""

import pygame
from src.constants import *
from src import fonts
from src.ui.widgets import (draw_panel, draw_text, draw_text_centered,
                             draw_ornament_line, Button, TextInput)
from src.ui.atmosphere import AtmosphereRenderer

# Cor verde e vermelha para status de pronto
C_READY     = (60, 200, 80)
C_NOT_READY = (200, 50, 50)
C_READY_DIM = (30, 120, 50)


class LobbyScene:
    def __init__(self, app):
        self.app   = app
        self.atm   = AtmosphereRenderer(*app.size)
        self._time = 0.0

        self._chat_input = TextInput(0, 0, 400, 38, placeholder="Mensagem...", max_len=200)
        self._btn_send   = Button(0, 0, 80,  38, "Enviar")
        self._btn_ready  = Button(0, 0, 150, 42, "Marcar Pronto", accent=True)
        self._btn_back   = Button(0, 0, 110, 38, "< Sair")
        self._btn_start  = Button(0, 0, 200, 44, "Comecar Sessao", accent=True)

        # Confirmacao de inicio
        self._confirm_open = False
        self._btn_confirm  = Button(0, 0, 140, 40, "Comecar sim", accent=True)
        self._btn_cancel   = Button(0, 0, 110, 40, "Cancelar")

        self._messages = []
        self._ready    = False

        self._build_layout()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        w, h = self.app.size

        self._panel_players = pygame.Rect(16, 76, 210, h - 110)
        cw = w - 246
        self._panel_chat    = pygame.Rect(242, 76, cw, h - 110)
        self._chat_log_rect = pygame.Rect(250, 84, cw - 16, h - 212)

        cy = h - 118
        self._chat_input.rect = pygame.Rect(250, cy, cw - 92, 38)
        self._btn_send.rect   = pygame.Rect(250 + cw - 84, cy, 76, 38)

        # Bottom bar
        self._btn_back.rect  = pygame.Rect(16, h - 52, 110, 38)
        self._btn_ready.rect = pygame.Rect(w - 360, h - 54, 150, 42)
        self._btn_start.rect = pygame.Rect(w - 220, h - 54, 200, 44)

        # Confirm dialog
        dw, dh = 420, 200
        self._dlg_rect = pygame.Rect(w // 2 - dw // 2, h // 2 - dh // 2, dw, dh)
        self._btn_confirm.rect = pygame.Rect(w // 2 + 10,  h // 2 + 30, 140, 40)
        self._btn_cancel.rect  = pygame.Rect(w // 2 - 130, h // 2 + 30, 110, 40)

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_host(self):
        return getattr(getattr(self.app, "server", None), "running", False)

    def _get_players(self):
        client = getattr(self.app, "client", None)
        return client.players if client else []

    def _host_name(self):
        """Nome do mestre (cliente local que hospeda o servidor)."""
        client = getattr(self.app, "client", None)
        if client and self._is_host():
            return client.name
        return None

    def _non_host_players(self):
        """Lista de jogadores excluindo o mestre."""
        players  = self._get_players()
        hname    = self._host_name()
        if hname is None:
            return players
        return [p for p in players if p.get("name") != hname]

    def _ready_count(self):
        return sum(1 for p in self._non_host_players() if p.get("ready", False))

    def _all_ready(self):
        players = self._non_host_players()
        if not players:
            return True   # sem jogadores = pode comecar
        return all(p.get("ready", False) for p in players)

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        # Confirmacao aberta — bloqueia o resto
        if self._confirm_open:
            if self._btn_confirm.handle_event(event):
                self._confirm_open = False
                self._go_to_map()
            if self._btn_cancel.handle_event(event):
                self._confirm_open = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._confirm_open = False
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._leave()

        if self._btn_back.handle_event(event):
            self._leave()

        # Chat — Enter envia
        self._chat_input.handle_event(event)
        if self._btn_send.handle_event(event):
            self._send_chat()
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
                and self._chat_input.active):
            self._send_chat()

        # Pronto (apenas jogadores, nao o mestre)
        if not self._is_host():
            if self._btn_ready.handle_event(event):
                self._ready = not self._ready
                client = getattr(self.app, "client", None)
                if client:
                    client.send({"type": "ready", "value": self._ready})

        # Comecar (apenas mestre)
        if self._is_host():
            if self._btn_start.handle_event(event):
                if self._all_ready():
                    self._go_to_map()
                else:
                    self._confirm_open = True

    def _send_chat(self):
        txt = self._chat_input.text.strip()
        if not txt:
            return
        client = getattr(self.app, "client", None)
        if client:
            client.send({"type": "chat", "text": txt})
        self._chat_input.text = ""

    def _leave(self):
        client = getattr(self.app, "client", None)
        if client:
            client.disconnect()
            self.app.client = None
        server = getattr(self.app, "server", None)
        if server:
            server.stop()
            self.app.server = None
        self.app.change_scene(SCENE_MENU)

    def _go_to_map(self):
        # Mestre avisa todos os clientes para ir ao mapa
        server = getattr(self.app, "server", None)
        if server:
            server._broadcast({"type": "start_game"})
        self.app._scenes.pop(SCENE_LOBBY, None)
        self.app.change_scene("game_map")

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        self._time += dt
        self.atm.update(dt)
        self._chat_input.update(dt)
        client = getattr(self.app, "client", None)
        if client and client.on_message is not self._on_net_message:
            client.on_message = self._on_net_message

    def _on_net_message(self, msg: dict):
        kind = msg.get("type")
        if kind == "chat":
            self._messages.append((msg.get("sender", "?"), msg.get("text", "")))
        elif kind == "start_game":
            # Jogadores recebem sinal do mestre para ir ao mapa
            if not self._is_host():
                pygame.event.post(pygame.event.Event(pygame.USEREVENT,
                    {"action": "goto", "scene": "game_map"}))

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface):
        w, h = self.app.size
        self.atm.draw(surface)

        hfont = fonts.get("heading", 22)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)

        draw_text_centered(surface, "LOBBY  -  CURSE OF STRAHD",
                           hfont, C_GOLD, w // 2, 40)
        draw_ornament_line(surface, w // 2, 62, 500)

        self._draw_players(surface, bfont, sfont)
        self._draw_chat(surface, bfont, sfont)
        self._draw_bottom_bar(surface, bfont, sfont)

        if self._confirm_open:
            self._draw_confirm(surface, w, h, bfont, sfont)

    def _draw_players(self, surface, bfont, sfont):
        panel = self._panel_players
        draw_panel(surface, panel, C_PANEL_DARK, C_BORDER, 1, radius=6)

        draw_text_centered(surface, "Jogadores",
                           fonts.get("heading", 15), C_GOLD_BRIGHT,
                           panel.centerx, panel.y + 16)

        players = self._get_players()
        ready_c = self._ready_count()

        for i, p in enumerate(players[:8]):
            py  = panel.y + 42 + i * 36
            rdy = p.get("ready", False)

            # Dot indicador
            dot_x = panel.x + 18
            dot_y = py + 9
            dot_col = C_READY if rdy else C_NOT_READY
            pygame.draw.circle(surface, dot_col, (dot_x, dot_y), 6)
            pygame.draw.circle(surface, (0, 0, 0), (dot_x, dot_y), 6, 1)

            # Nome
            name_col = C_TEXT_BRIGHT if rdy else C_TEXT
            draw_text(surface, p.get("name", "?"), bfont, name_col,
                      panel.x + 32, py)

            # "pronto" / "aguardando" em pequeno
            status_txt = "pronto" if rdy else "aguardando"
            status_col = C_READY_DIM if rdy else (80, 60, 60)
            draw_text(surface, status_txt, sfont, status_col,
                      panel.x + 32, py + 17)

        # Contagem no rodape do painel
        total = len(players)
        counter_txt = f"{ready_c}/{total} prontos"
        counter_col = C_READY if ready_c == total and total > 0 else C_TEXT_DIM
        draw_text_centered(surface, counter_txt, sfont, counter_col,
                           panel.centerx, panel.bottom - 22)

        # Linha separadora antes do rodape
        pygame.draw.line(surface, C_BORDER,
                         (panel.x + 8, panel.bottom - 36),
                         (panel.right - 8, panel.bottom - 36), 1)

        # Status de conexao
        client = getattr(self.app, "client", None)
        con_txt = "Conectado" if (client and client.connected) else "Desconectado"
        con_col = C_READY_DIM if (client and client.connected) else C_NOT_READY
        draw_text_centered(surface, f"* {con_txt}", sfont, con_col,
                           panel.centerx, panel.bottom - 10)

    def _draw_chat(self, surface, bfont, sfont):
        draw_panel(surface, self._panel_chat, C_PANEL_DARK, C_BORDER, 1, radius=6)

        clip = surface.get_clip()
        surface.set_clip(self._chat_log_rect)

        visible = self._messages[-28:]
        lh = sfont.get_height() + 3
        for i, (sender, text) in enumerate(visible):
            ly = self._chat_log_rect.y + i * lh
            sw = sfont.size(sender + ": ")[0]
            draw_text(surface, sender + ":", sfont, C_GOLD_BRIGHT,
                      self._chat_log_rect.x + 4, ly)
            draw_text(surface, text, sfont, C_TEXT,
                      self._chat_log_rect.x + 4 + sw, ly)

        surface.set_clip(clip)

        self._chat_input.draw(surface, bfont)
        self._btn_send.draw(surface, bfont)

    def _draw_bottom_bar(self, surface, bfont, sfont):
        self._btn_back.draw(surface, sfont)
        is_host = self._is_host()

        if is_host:
            # Botao comecar com contagem
            players   = self._non_host_players()
            ready_c   = self._ready_count()
            total     = len(players)
            all_rdy   = self._all_ready() and total > 0
            start_lbl = f"Comecar  [{ready_c}/{total}]"
            self._btn_start.label = start_lbl
            # Borda verde se todos prontos
            if all_rdy:
                old_border = C_BORDER_SEL
                pygame.draw.rect(surface, C_READY,
                                 self._btn_start.rect.inflate(4, 4), 2, border_radius=7)
            self._btn_start.draw(surface, bfont)
        else:
            # Botao pronto com cor dinamica
            lbl = "Nao Pronto" if self._ready else "Marcar Pronto"
            self._btn_ready.label = lbl
            # Muda cor de fundo manualmente
            bg  = C_READY_DIM if self._ready else C_CRIMSON
            brd = C_READY     if self._ready else C_BORDER_SEL
            draw_panel(surface, self._btn_ready.rect, bg, brd, 2, radius=5)
            draw_text_centered(surface, lbl, bfont, C_TEXT_BRIGHT,
                               self._btn_ready.rect.centerx,
                               self._btn_ready.rect.centery)

    def _draw_confirm(self, surface, w, h, bfont, sfont):
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        draw_panel(surface, self._dlg_rect, C_PANEL, C_BORDER_SEL, 2, radius=8)

        hfont = fonts.get("heading", 20)
        players = self._non_host_players()
        ready_c = self._ready_count()
        total   = len(players)
        not_rdy = total - ready_c

        draw_text_centered(surface, "Nem todos estao prontos",
                           hfont, C_TEXT_ACCENT,
                           w // 2, self._dlg_rect.y + 28)
        draw_text_centered(surface,
                           f"{not_rdy} jogador(es) ainda nao marcaram pronto.",
                           sfont, C_TEXT, w // 2, self._dlg_rect.y + 66)
        draw_text_centered(surface, "Deseja comecar mesmo assim?",
                           sfont, C_TEXT_DIM, w // 2, self._dlg_rect.y + 90)

        self._btn_confirm.draw(surface, bfont)
        self._btn_cancel.draw(surface, bfont)
