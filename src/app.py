"""
App — central controller.
Manages the pygame window, scene switching, resize, FPS display.
"""

import pygame
import sys
from src.constants import *
from src import settings, fonts


class App:
    def __init__(self):
        settings.load()

        self.server = None
        self.client = None

        # Window
        self._init_display()
        self._clock = pygame.time.Clock()
        self._running = True

        # Scenes loaded lazily
        self._scenes: dict = {}
        self._current_scene = None
        self.change_scene(SCENE_MENU)

    # ── Display ───────────────────────────────────────────────────────────────

    def _init_display(self):
        w, h = settings.resolution()
        flags = pygame.RESIZABLE
        if settings.fullscreen():
            flags |= pygame.FULLSCREEN
        self._surface = pygame.display.set_mode((w, h), flags)
        pygame.display.set_caption(TITLE)
        self._w, self._h = w, h

    def apply_display_settings(self):
        fonts.clear_cache()
        self._init_display()
        if self._current_scene:
            scene = self._scenes.get(self._current_scene)
            if scene and hasattr(scene, "on_resize"):
                scene.on_resize(*self.size)

    @property
    def size(self):
        return self._surface.get_size()

    # ── Scene management ──────────────────────────────────────────────────────

    def change_scene(self, name: str):
        if name not in self._scenes:
            self._scenes[name] = self._make_scene(name)
        self._current_scene = name

    def _make_scene(self, name: str):
        if name == SCENE_MENU:
            from src.ui.scene_menu import MenuScene
            return MenuScene(self)
        if name == SCENE_PLAY_SELECT:
            from src.ui.scene_play_select import PlaySelectScene
            return PlaySelectScene(self)
        if name == SCENE_LOBBY:
            from src.ui.scene_lobby import LobbyScene
            return LobbyScene(self)
        if name == SCENE_CHARACTERS:
            from src.ui.scene_characters import CharactersScene
            return CharactersScene(self)
        if name == SCENE_CHAR_CREATE:
            from src.ui.scene_char_create import CharCreateScene
            return CharCreateScene(self)
        if name == SCENE_COMPENDIUM:
            from src.ui.scene_compendium import CompendiumScene
            return CompendiumScene(self)
        if name == SCENE_OPTIONS:
            from src.ui.scene_options import OptionsScene
            return OptionsScene(self)
        if name == "game_map":
            from src.ui.scene_game_map import GameMapScene
            return GameMapScene(self)
        raise ValueError(f"Unknown scene: {name}")

    def _invalidate_scene(self, name: str):
        """Force scene to be re-created next time it's visited."""
        self._scenes.pop(name, None)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while self._running:
            dt = self._clock.tick(TARGET_FPS) / 1000.0
            dt = min(dt, 0.05)  # cap dt

            self._handle_events()

            scene = self._scenes.get(self._current_scene)
            if scene:
                scene.update(dt)
                scene.draw(self._surface)

            self._draw_fps()
            pygame.display.flip()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            if event.type == pygame.VIDEORESIZE:
                w, h = max(MIN_WIDTH, event.w), max(MIN_HEIGHT, event.h)
                self._surface = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                scene = self._scenes.get(self._current_scene)
                if scene and hasattr(scene, "on_resize"):
                    scene.on_resize(w, h)

            # Custom events from network threads
            if event.type == pygame.USEREVENT:
                action = getattr(event, "action", None)
                if action == "goto":
                    target = getattr(event, "scene", None)
                    if target:
                        self._invalidate_scene(target)   # fresh lobby/game
                        self.change_scene(target)

            scene = self._scenes.get(self._current_scene)
            if scene:
                scene.handle_event(event)

    def _draw_fps(self):
        if not settings.show_fps():
            return
        fps  = self._clock.get_fps()
        font = fonts.get("body", 14)
        surf = font.render(f"FPS: {fps:.0f}", True, (100, 255, 100))
        self._surface.blit(surf, (8, 8))

    def quit(self):
        if self.server:
            self.server.stop()
        if self.client:
            self.client.disconnect()
        self._running = False
        pygame.quit()
        sys.exit()
