"""
D&D 5e point buy (PHB): custo cumulativo a partir do 8; orçamento total = 27.
Todos os atributos começam em 8 (custo 0) → 27 pontos para distribuir até soma = 27.
"""

from __future__ import annotations

# Custo cumulativo para atingir o valor a partir de 8 (point buy PHB)
_COST_FROM_8: dict[int, int] = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
}

MIN_SCORE = 8
MAX_SCORE = 15
POINT_BUY_TOTAL = 27
BASELINE = 8


def cost_from_8(score: int) -> int:
    return _COST_FROM_8[score]


def total_cost(scores: dict[str, int]) -> int:
    return sum(cost_from_8(s) for s in scores.values())


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def points_remaining(scores: dict[str, int]) -> int:
    """Quanto falta gastar do orçamento PHB (27 − soma dos custos). Zera quando a ficha é válida."""
    return POINT_BUY_TOTAL - total_cost(scores)


def is_valid_point_buy(scores: dict[str, int]) -> bool:
    return total_cost(scores) == POINT_BUY_TOTAL


def can_set(scores: dict[str, int], key: str, new_score: int) -> bool:
    if new_score not in _COST_FROM_8:
        return False
    trial = dict(scores)
    trial[key] = new_score
    return points_remaining(trial) >= 0


def try_delta(scores: dict[str, int], key: str, delta: int) -> bool:
    cur = scores[key]
    new_score = cur + delta
    if new_score < MIN_SCORE or new_score > MAX_SCORE:
        return False
    if not can_set(scores, key, new_score):
        return False
    scores[key] = new_score
    return True
