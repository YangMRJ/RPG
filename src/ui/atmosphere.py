"""
Atmospheric background effects: floating dust motes, fog layers, flickering vignette.
All rendered directly on the main surface.
"""

import pygame
import random
import math
from src.constants import C_BG, C_BG2


class DustMote:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.reset()

    def reset(self):
        self.x   = random.uniform(0, self.w)
        self.y   = random.uniform(0, self.h)
        self.r   = random.uniform(0.8, 2.5)
        self.spd = random.uniform(4, 18)
        self.ang = random.uniform(-0.3, 0.3) + math.pi * 1.5   # drift upward
        self.a   = random.uniform(20, 70)
        self.da  = random.uniform(-8, 8)
        self.life = 1.0

    def update(self, dt):
        self.x  += math.cos(self.ang) * self.spd * dt
        self.y  += math.sin(self.ang) * self.spd * dt
        self.ang += random.uniform(-0.05, 0.05)
        if self.y < -10 or self.x < -10 or self.x > self.w + 10:
            self.reset()
            self.y = self.h + 5

    def draw(self, surface):
        col = (200, 180, 160, int(max(0, min(255, self.a))))
        tmp = pygame.Surface((int(self.r * 2) + 2, int(self.r * 2) + 2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, col, (int(self.r) + 1, int(self.r) + 1), int(self.r))
        surface.blit(tmp, (int(self.x - self.r), int(self.y - self.r)))


class AtmosphereRenderer:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self._motes = [DustMote(w, h) for _ in range(60)]
        self._time  = 0.0
        self._bg_surface   = None
        self._vign_surface = None
        self._rebuild(w, h)

    def _rebuild(self, w, h):
        self.w = w
        self.h = h
        # Static gradient background
        self._bg_surface = pygame.Surface((w, h))
        for y in range(h):
            t = y / h
            r = int(C_BG[0] + (C_BG2[0] - C_BG[0]) * t)
            g = int(C_BG[1] + (C_BG2[1] - C_BG[1]) * t)
            b = int(C_BG[2] + (C_BG2[2] - C_BG[2]) * t)
            pygame.draw.line(self._bg_surface, (r, g, b), (0, y), (w, y))

        # Vignette
        self._vign_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        max_r = math.hypot(cx, cy)
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                d = math.hypot(x - cx, y - cy)
                a = int(min(255, (d / max_r) ** 2.2 * 230))
                pygame.draw.rect(self._vign_surface, (0, 0, 0, a), (x, y, 2, 2))

    def resize(self, w, h):
        self._rebuild(w, h)
        for m in self._motes:
            m.w = w
            m.h = h

    def update(self, dt):
        self._time += dt
        for m in self._motes:
            m.update(dt)

    def draw(self, surface):
        surface.blit(self._bg_surface, (0, 0))
        for m in self._motes:
            m.draw(surface)
        surface.blit(self._vign_surface, (0, 0))
