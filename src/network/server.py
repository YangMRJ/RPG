"""
Game Server — WebSocket server síncrono (uma thread por cliente).
Requer: pip install websockets (>= 11)
"""

import json
import threading


class GameServer:
    def __init__(self, host="0.0.0.0", port=5740):
        self.host    = host
        self.port    = port
        self.running = False
        self._clients: dict = {}   # ws → {"name": str, "ready": bool}
        self._lock   = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Inicia o servidor em daemon thread. Retorna imediatamente."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        with self._lock:
            for ws in list(self._clients.keys()):
                try:
                    ws.close()
                except Exception:
                    pass
            self._clients.clear()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run(self):
        try:
            from websockets.sync.server import serve
        except ImportError:
            print("[Server] ERRO: pip install websockets")
            return

        self.running = True
        print(f"[Server] Ouvindo em {self.host}:{self.port}")
        try:
            with serve(self._handler, self.host, self.port) as server:
                server.serve_forever()
        except Exception as e:
            print(f"[Server] Encerrado: {e}")
        finally:
            self.running = False

    def _handler(self, ws):
        """Executado em thread própria para cada cliente conectado."""
        player = {"name": "Jogador", "ready": False}
        with self._lock:
            self._clients[ws] = player

        print(f"[Server] + cliente ({len(self._clients)} total)")
        self._send_player_list()

        try:
            for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                self._process(ws, msg)
        except Exception:
            pass
        finally:
            with self._lock:
                self._clients.pop(ws, None)
            print(f"[Server] - cliente ({len(self._clients)} restantes)")
            self._send_player_list()

    def _process(self, ws, msg: dict):
        kind = msg.get("type")
        with self._lock:
            player = self._clients.get(ws, {})

        if kind == "join":
            player["name"] = msg.get("name", "Jogador")
            self._send_player_list()

        elif kind == "chat":
            self._broadcast({
                "type":   "chat",
                "sender": player.get("name", "?"),
                "text":   msg.get("text", ""),
            })

        elif kind == "ready":
            player["ready"] = msg.get("value", False)
            self._send_player_list()

    def _broadcast(self, msg: dict):
        raw = json.dumps(msg, ensure_ascii=False)
        with self._lock:
            targets = list(self._clients.keys())
        dead = []
        for ws in targets:
            try:
                ws.send(raw)
            except Exception:
                dead.append(ws)
        if dead:
            with self._lock:
                for ws in dead:
                    self._clients.pop(ws, None)

    def _send_player_list(self):
        with self._lock:
            players = [{"name": p["name"], "ready": p["ready"]}
                       for p in self._clients.values()]
        self._broadcast({"type": "player_list", "players": players})
