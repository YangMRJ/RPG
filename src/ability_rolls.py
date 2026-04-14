"""Rolagem clássica de atributos: 4d6, descarta o menor dado em cada conjunto."""

from __future__ import annotations

import random


def roll_4d6_drop_lowest() -> int:
    d = [random.randint(1, 6) for _ in range(4)]
    return sum(d) - min(d)


def roll_six_ability_scores() -> list[int]:
    return [roll_4d6_drop_lowest() for _ in range(6)]
