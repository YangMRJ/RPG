"""
Bônus de atributo raciais — D&D 5e (PHB).

Sub-raças padrão quando o menu não separa: Anão colina, Halfling pés-leves, Gnomo das rochas.

Humano: +1 em todos os seis atributos.
Meio-elfo: +2 CAR; +1 em dois entre FOR, DES, CON, INT, SAB (distintos).

A opção "variante" na UI (feito em vez de bônus racial) zera estes bônus na ficha — aplicado na cena, não aqui.
"""

from __future__ import annotations

ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")


def _zeroes() -> dict[str, int]:
    return {k: 0 for k in ABILITY_KEYS}


RACIAL_FIXED: dict[str, dict[str, int]] = {
    "Elfo": {"dex": 2},
    "Anão": {"con": 2, "wis": 1},
    "Halfling": {"dex": 2, "cha": 1},
    "Gnomo": {"int": 2, "con": 1},
    "Meio-Orc": {"str": 2, "con": 1},
    "Tiefling": {"cha": 2, "int": 1},
    "Draconato": {"str": 2, "cha": 1},
}


def racial_bonuses(
    race_display_name: str,
    half_elf_plus1: tuple[str, str] | None = None,
) -> dict[str, int]:
    out = _zeroes()
    if race_display_name == "Humano":
        for k in out:
            out[k] = 1
        return out

    if race_display_name == "Meio-Elfo":
        out["cha"] = 2
        if half_elf_plus1:
            a, b = half_elf_plus1
            if a in out and b in out and a != b:
                out[a] += 1
                out[b] += 1
        return out

    fixed = RACIAL_FIXED.get(race_display_name)
    if fixed:
        for k, v in fixed.items():
            out[k] += v
    return out
