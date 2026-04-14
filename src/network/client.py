"""
Game Client — WebSocket cliente síncrono.
Recv loop roda em daemon thread separada.
Requer: pip install websockets (>= 11)
"""

import json
import threading
import queue


class GameClient:
    def __init__(self, host: str, port: int, name: str):
        self.host      = host
        self.port      = port
        self.name      = name
        self.players   = []
        self.connected = False
        self.on_message = None    # callable(msg: dict) — chamado na thread de recv

        self._ws        = None
        self._send_q    = queue.Queue()   # thread-safe send queue
        self._lock      = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def connect(self):
        """
        Conecta ao servidor de forma BLOQUEANTE.
        Chame dentro de uma daemon thread.
        """
        try:
            from websockets.sync.client import connect as ws_connect
        except ImportError:
            raise RuntimeError("websockets não instalado. Execute: pip install websockets")

        uri = f"ws://{self.host}:{self.port}"
        try:
            self._ws = ws_connect(uri)
        except Exception as e:
            raise RuntimeError(f"Não foi possível conectar a {uri}: {e}")

        self.connected = True

        # Apresenta-se ao servidor
        self._raw_send({"type": "join", "name": self.name})

        # Thread de recebimento
        recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        recv_thread.start()

        # Thread de envio (drena a fila)
        send_thread = threading.Thread(target=self._send_loop, daemon=True)
        send_thread.start()

    def send(self, msg: dict):
        """Enfileira mensagem para envio (thread-safe)."""
        if self.connected:
            self._send_q.put(msg)

    def disconnect(self):
        self.connected = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    # ── Internal ─────────────────────────────────────────────────────────────

    def _raw_send(self, msg: dict):
        """Envia diretamente (chame apenas da thread dona do ws)."""
        if self._ws:
            try:
                self._ws.send(json.dumps(msg, ensure_ascii=False))
            except Exception:
                self.connected = False

    def _send_loop(self):
        """Drena _send_q e envia pelo websocket."""
        while self.connected:
            try:
                msg = self._send_q.get(timeout=0.1)
                self._raw_send(msg)
            except queue.Empty:
                continue
            except Exception:
                break
        self.connected = False

    def _recv_loop(self):
        """Recebe mensagens do servidor e despacha para on_message."""
        try:
            for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                # Atualiza estado local
                if msg.get("type") == "player_list":
                    with self._lock:
                        self.players = msg.get("players", [])

                # Notifica a aplicação
                if self.on_message:
                    try:
                        self.on_message(msg)
                    except Exception:
                        pass

        except Exception:
            pass
        finally:
            self.connected = False
