"""
Scene: Character Creation
Point buy ou rolagem 4d6; bônus raciais PHB ou variante (feito, sem bônus racial de atributo).
"""

from __future__ import annotations

import pygame
import json
import os
from src.constants import *
from src import fonts
from src import point_buy
from src import dnd_level1_bonuses as dnd1
from src import ability_rolls
from src.ui.widgets import (draw_panel, draw_text, draw_text_centered,
                             draw_ornament_line, Button, TextInput, Dropdown)
from src.ui.atmosphere import AtmosphereRenderer

CHARS_FILE = os.path.join("data", "characters", "characters.json")

_RACES = [
    "Humano", "Elfo", "Anão", "Halfling", "Gnomo",
    "Meio-Elfo", "Meio-Orc", "Tiefling", "Draconato",
]
_CLASSES = [
    "Bárbaro", "Bardo", "Clérigo", "Druida", "Guerreiro",
    "Monge", "Paladino", "Patrulheiro", "Ladino",
    "Feiticeiro", "Bruxo", "Mago",
]
_BACKGROUNDS = [
    "Acólito", "Artesão de Guilda", "Charlatão", "Criminoso",
    "Eremita", "Herói do Povo", "Homem de Armas", "Marinheiro",
    "Morador de Rua", "Nobre", "Órfão", "Sábio", "Selvagem",
]

_ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")
_ABILITY_LABELS = {
    "str": "FOR", "dex": "DES", "con": "CON",
    "int": "INT", "wis": "SAB", "cha": "CAR",
}

_HE_LABELS = ["FOR", "DES", "CON", "INT", "SAB"]
_HE_KEYS = ["str", "dex", "con", "int", "wis"]

VARIANTE_BTN_W = 92
VARIANTE_GAP = 8

_ROLL_DD_LABELS = ["—"] + ["Dado %d" % (i + 1) for i in range(6)]


def _load_chars():
    os.makedirs(os.path.dirname(CHARS_FILE), exist_ok=True)
    if not os.path.exists(CHARS_FILE):
        return []
    with open(CHARS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_chars(chars):
    os.makedirs(os.path.dirname(CHARS_FILE), exist_ok=True)
    with open(CHARS_FILE, "w", encoding="utf-8") as f:
        json.dump(chars, f, indent=2, ensure_ascii=False)


def _mod_str(m: int) -> str:
    return f"+{m}" if m >= 0 else str(m)


def _fmt_bonus(n: int) -> str:
    return "+%d" % n if n >= 0 else str(n)


class CharCreateScene:
    def __init__(self, app):
        self.app = app
        self.atm = AtmosphereRenderer(*app.size)
        self._time = 0.0
        self._error = ""

        self._name_input = TextInput(0, 0, 280, 38, placeholder="Nome do personagem", max_len=48)
        self._dd_race = Dropdown(0, 0, 220, 36, _RACES, 0)
        self._dd_class = Dropdown(0, 0, 220, 36, _CLASSES, 0)
        self._dd_bg = Dropdown(0, 0, 240, 36, _BACKGROUNDS, 0)
        self._dd_he1 = Dropdown(0, 0, 88, 32, _HE_LABELS, 0)
        self._dd_he2 = Dropdown(0, 0, 88, 32, _HE_LABELS, 1)

        self._ability_method = "pointbuy"
        self._variante_feito = False
        self._roll_results: list[int] = []
        self._roll_assign_idx: dict[str, int | None] = {k: None for k in _ABILITY_KEYS}
        self._dd_roll_pick = {
            k: Dropdown(0, 0, 104, 30, list(_ROLL_DD_LABELS), 0)
            for k in _ABILITY_KEYS
        }

        self._scores = {k: point_buy.BASELINE for k in _ABILITY_KEYS}
        self._btn_minus = {k: Button(0, 0, 28, 28, "-") for k in _ABILITY_KEYS}
        self._btn_plus = {k: Button(0, 0, 28, 28, "+") for k in _ABILITY_KEYS}

        self._btn_mode_pb = Button(0, 0, 118, 30, "Point buy")
        self._btn_mode_roll = Button(0, 0, 100, 30, "Rolagem")
        self._btn_roll = Button(0, 0, 168, 30, "Rolar 6× (4d6)")
        self._btn_variante = Button(0, 0, VARIANTE_BTN_W, 36, "variante")

        self._btn_save = Button(0, 0, 160, 44, "Salvar", accent=True)
        self._btn_back = Button(0, 0, 130, 40, "← Voltar")

        self._stats_single_col = False
        self._race_snapshot = _RACES[0]

        self._build_layout()

    def _is_half_elf(self):
        return _RACES[self._dd_race.index] == "Meio-Elfo"

    def _half_elf_tuple(self):
        return (_HE_KEYS[self._dd_he1.index], _HE_KEYS[self._dd_he2.index])

    def _left_column_metrics(self, py):
        m = {"race_label_y": py + 66, "race_row_y": py + 88}
        y = py + 88 + 44
        if self._is_half_elf() and not self._variante_feito:
            m["he_label_y"] = py + 128
            m["he_dd_y"] = y
            y += 44
        m["class_dd_y"] = y
        m["class_label_y"] = y - 22
        m["bg_dd_y"] = y + 60
        m["bg_label_y"] = y + 38
        return m

    def _stats_header_h(self):
        h = 22 + 38
        if self._ability_method == "pointbuy":
            h += 56
        else:
            h += 38
            if len(self._roll_results) == 6:
                h += 46
            else:
                h += 40
        h += 10
        return h

    def _racial_dict(self):
        if self._variante_feito:
            return {k: 0 for k in _ABILITY_KEYS}
        race = _RACES[self._dd_race.index]
        he = self._half_elf_tuple() if race == "Meio-Elfo" else None
        return dnd1.racial_bonuses(race, he)

    def _base_scores(self) -> dict[str, int]:
        if self._ability_method == "pointbuy":
            return dict(self._scores)
        out = {}
        for k in _ABILITY_KEYS:
            i = self._roll_assign_idx.get(k)
            if i is not None and len(self._roll_results) == 6:
                out[k] = self._roll_results[i]
            else:
                out[k] = 0
        return out

    def _sync_roll_dropdowns_from_state(self):
        for k in _ABILITY_KEYS:
            i = self._roll_assign_idx[k]
            self._dd_roll_pick[k].index = 0 if i is None else i + 1

    def _apply_roll_pick(self, key: str, dd_index: int):
        if dd_index == 0:
            self._roll_assign_idx[key] = None
            return
        slot = dd_index - 1
        for ok in _ABILITY_KEYS:
            if ok != key and self._roll_assign_idx.get(ok) == slot:
                self._roll_assign_idx[ok] = None
        self._roll_assign_idx[key] = slot

    def _roll_assignment_valid(self) -> bool:
        if len(self._roll_results) != 6:
            return False
        vals = [self._roll_assign_idx[k] for k in _ABILITY_KEYS]
        if None in vals:
            return False
        return len(set(vals)) == 6

    def _build_layout(self):
        w, h = self.app.size
        half = self._is_half_elf()
        extra_rows = 44 if (half and not self._variante_feito) else 0
        pw = min(920, w - 48)
        ph = min(h - 56, 640 + min(extra_rows, 80))
        cx = w // 2
        self._panel = pygame.Rect(cx - pw // 2, 28, pw, ph)

        px, py = self._panel.x + 20, self._panel.y + 56
        col_gap = 24
        left_w = (pw - col_gap) // 2
        m = self._left_column_metrics(py)

        self._name_input.rect = pygame.Rect(px, py + 22, min(320, left_w - 8), 38)

        ry = m["race_row_y"]
        self._btn_variante.rect = pygame.Rect(px, ry, VARIANTE_BTN_W, 36)
        race_w = min(220, max(120, left_w - VARIANTE_BTN_W - VARIANTE_GAP - 8))
        self._dd_race.rect = pygame.Rect(px + VARIANTE_BTN_W + VARIANTE_GAP, ry, race_w, 36)

        if half and not self._variante_feito:
            self._dd_he1.rect = pygame.Rect(px, m["he_dd_y"], 92, 32)
            self._dd_he2.rect = pygame.Rect(px + 102, m["he_dd_y"], 92, 32)

        cdy = m["class_dd_y"]
        self._dd_class.rect = pygame.Rect(px, cdy, 220, 36)
        self._dd_bg.rect = pygame.Rect(px, m["bg_dd_y"], min(280, left_w - 8), 36)

        rx = px + left_w + col_gap
        hdr = self._stats_header_h()
        self._btn_mode_pb.rect = pygame.Rect(rx, py + 18, 118, 30)
        self._btn_mode_roll.rect = pygame.Rect(rx + 126, py + 18, 100, 30)
        self._btn_roll.rect = pygame.Rect(rx, py + 54, 168, 30)

        ry0 = py + hdr
        row_h = 42
        gap_y = 6

        stats_right = self._panel.right - 16
        stats_w = max(0, stats_right - rx)
        mid_gap = 10
        col_w = (stats_w - mid_gap) // 2 if stats_w > mid_gap else stats_w
        self._stats_single_col = col_w < 300

        order_left = ("str", "dex", "con")
        order_right = ("int", "wis", "cha")

        if self._stats_single_col:
            for row, key in enumerate(_ABILITY_KEYS):
                y = ry0 + row * (row_h + gap_y)
                self._place_stat_row(key, rx, y)
        else:
            rx2 = rx + col_w + mid_gap
            for row, key in enumerate(order_left):
                y = ry0 + row * (row_h + gap_y)
                self._place_stat_row(key, rx, y)
            for row, key in enumerate(order_right):
                y = ry0 + row * (row_h + gap_y)
                self._place_stat_row(key, rx2, y)

        self._btn_save.rect = pygame.Rect(cx - 80, self._panel.bottom - 52, 160, 44)
        self._btn_back.rect = pygame.Rect(self._panel.x + 12, self._panel.y + 12, 130, 40)

    def _place_stat_row(self, key, x, y):
        if self._ability_method == "pointbuy":
            self._btn_minus[key].rect = pygame.Rect(x + 34, y, 28, 28)
            self._btn_plus[key].rect = pygame.Rect(x + 104, y, 28, 28)
        else:
            self._dd_roll_pick[key].rect = pygame.Rect(x + 32, y, 104, 30)

    def on_resize(self, w, h):
        self.atm.resize(w, h)
        self._build_layout()

    def _handle_stat_clicks(self, event):
        if self._ability_method != "pointbuy":
            return
        for key in _ABILITY_KEYS:
            if self._btn_minus[key].handle_event(event):
                point_buy.try_delta(self._scores, key, -1)
            if self._btn_plus[key].handle_event(event):
                point_buy.try_delta(self._scores, key, 1)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.change_scene(SCENE_CHARACTERS)

        if self._btn_back.handle_event(event):
            self.app.change_scene(SCENE_CHARACTERS)

        if self._btn_save.handle_event(event):
            self._save()

        if self._btn_mode_pb.handle_event(event) and self._ability_method != "pointbuy":
            self._ability_method = "pointbuy"
            self._build_layout()

        if self._btn_mode_roll.handle_event(event) and self._ability_method != "roll":
            self._ability_method = "roll"
            self._roll_results = []
            self._roll_assign_idx = {k: None for k in _ABILITY_KEYS}
            self._sync_roll_dropdowns_from_state()
            self._build_layout()

        if self._ability_method == "roll" and self._btn_roll.handle_event(event):
            self._roll_results = ability_rolls.roll_six_ability_scores()
            self._roll_assign_idx = {k: None for k in _ABILITY_KEYS}
            self._sync_roll_dropdowns_from_state()
            self._build_layout()

        if self._btn_variante.handle_event(event):
            self._variante_feito = not self._variante_feito
            self._build_layout()

        self._handle_stat_clicks(event)

        self._name_input.handle_event(event)
        self._dd_race.handle_event(event)
        if self._is_half_elf() and not self._variante_feito:
            self._dd_he1.handle_event(event)
            self._dd_he2.handle_event(event)
        self._dd_class.handle_event(event)
        self._dd_bg.handle_event(event)

        if self._ability_method == "roll":
            for k in _ABILITY_KEYS:
                dd = self._dd_roll_pick[k]
                prev = dd.index
                dd.handle_event(event)
                if dd.index != prev:
                    self._apply_roll_pick(k, dd.index)
                    self._sync_roll_dropdowns_from_state()

    def _save(self):
        self._error = ""
        name = self._name_input.text.strip()
        if not name:
            self._error = "Nome é obrigatório."
            return

        race = _RACES[self._dd_race.index]
        if race == "Meio-Elfo" and not self._variante_feito:
            k1, k2 = self._half_elf_tuple()
            if k1 == k2:
                self._error = "Meio-elfo: dois atributos diferentes para cada +1."
                return

        if self._ability_method == "pointbuy":
            if not point_buy.is_valid_point_buy(self._scores):
                rem = point_buy.points_remaining(self._scores)
                tc = point_buy.total_cost(self._scores)
                self._error = (
                    "Point buy: custo da base deve ser 27 (atual %d/27, restante %d)."
                    % (tc, rem)
                )
                return
        else:
            if not self._roll_assignment_valid():
                self._error = "Rolagem: rode os seis dados e atribua cada Dado 1–6 a um atributo (sem repetir)."
                return

        rb = self._racial_dict()
        base = self._base_scores()
        if self._ability_method == "roll":
            for k in _ABILITY_KEYS:
                if base[k] < 3:
                    self._error = "Atributo base inválido."
                    return

        final = {k: base[k] + rb[k] for k in _ABILITY_KEYS}

        rec = {
            "name": name,
            "race": race,
            "class": _CLASSES[self._dd_class.index],
            "background": _BACKGROUNDS[self._dd_bg.index],
            "level": 1,
            "abilities": final,
            "racial_bonuses": rb,
            "ability_method": "point_buy" if self._ability_method == "pointbuy" else "rolled",
        }

        if self._ability_method == "pointbuy":
            rec["ability_point_buy"] = dict(self._scores)
        else:
            rec["rolled_raw"] = list(self._roll_results)
            rec["roll_slot_assignment"] = {k: self._roll_assign_idx[k] for k in _ABILITY_KEYS}

        if race == "Meio-Elfo" and not self._variante_feito:
            rec["half_elf_plus1"] = list(self._half_elf_tuple())

        if self._variante_feito:
            rec["feat_instead_of_racial_asi"] = True
            rec["feat_pending"] = True

        chars = _load_chars()
        chars.append(rec)
        _save_chars(chars)
        self.app._scenes.pop(SCENE_CHARACTERS, None)
        self.app.change_scene(SCENE_CHARACTERS)

    def update(self, dt):
        self._time += dt
        self.atm.update(dt)
        self._name_input.update(dt)
        r = _RACES[self._dd_race.index]
        if r != self._race_snapshot:
            self._race_snapshot = r
            if r != "Meio-Elfo":
                self._dd_he1.index = 0
                self._dd_he2.index = 1
            self._build_layout()

    def draw(self, surface):
        w, h = self.app.size
        self.atm.draw(surface)
        draw_panel(surface, self._panel, C_PANEL_DARK, C_BORDER, 1, radius=8, alpha=235)

        hfont = fonts.get("heading", 22)
        bfont = fonts.get("body", FONT_BODY)
        sfont = fonts.get("body", FONT_SMALL)
        xsfont = fonts.get("body", FONT_SMALL - 1)

        draw_text_centered(surface, "NOVO PERSONAGEM", hfont, C_GOLD,
                           w // 2, self._panel.y + 30)
        draw_ornament_line(surface, w // 2, self._panel.y + 50, 400)

        px = self._panel.x + 20
        py = self._panel.y + 56
        col_gap = 24
        left_w = (self._panel.width - col_gap) // 2
        rx = px + left_w + col_gap
        m = self._left_column_metrics(py)

        draw_text(surface, "Nome", bfont, C_TEXT_DIM, px, py)
        draw_text(surface, "Raça", bfont, C_TEXT_DIM, px, m["race_label_y"])
        if self._is_half_elf() and not self._variante_feito:
            draw_text(surface, "Meio-elfo +1 (2 atributos)", xsfont, C_TEXT_DIM, px, m["he_label_y"])

        draw_text(surface, "Classe", bfont, C_TEXT_DIM, px, m["class_label_y"])
        draw_text(surface, "Antecedente", bfont, C_TEXT_DIM, px, m["bg_label_y"])

        self._name_input.draw(surface, bfont)
        self._btn_variante.accent = self._variante_feito
        self._btn_variante.draw(surface, xsfont)
        self._dd_race.draw(surface, sfont)
        if self._is_half_elf() and not self._variante_feito:
            self._dd_he1.draw(surface, xsfont)
            self._dd_he2.draw(surface, xsfont)
        self._dd_class.draw(surface, sfont)
        self._dd_bg.draw(surface, sfont)

        self._btn_mode_pb.accent = self._ability_method == "pointbuy"
        self._btn_mode_roll.accent = self._ability_method == "roll"
        draw_text(surface, "Atributos", bfont, C_GOLD, rx, py - 2)
        self._btn_mode_pb.draw(surface, xsfont)
        self._btn_mode_roll.draw(surface, xsfont)

        if self._ability_method == "pointbuy":
            rem = point_buy.points_remaining(self._scores)
            tc = point_buy.total_cost(self._scores)
            pool_col = C_TEXT_ACCENT if rem != 0 else C_GOLD_BRIGHT
            draw_text(surface, "Point buy (base): custo %d/27 · restante %d" % (tc, rem),
                      bfont, C_TEXT, rx, py + 52)
            if self._variante_feito:
                draw_text(surface, "Variante: sem bônus racial de atributo; feito na próxima etapa.",
                          xsfont, C_TEXT_DIM, rx, py + 72)
            else:
                draw_text(surface, "Depois somam-se os bônus raciais do livro (PHB).",
                          xsfont, C_TEXT_DIM, rx, py + 72)
        else:
            self._btn_roll.draw(surface, xsfont)
            if len(self._roll_results) == 6:
                vals = "   ".join(str(v) for v in self._roll_results)
                draw_text(surface, "Resultados: %s" % vals, xsfont, C_GOLD_BRIGHT, rx, py + 88)
                draw_text(surface, "Atribua cada Dado 1–6 a um atributo (sem repetir).", xsfont, C_TEXT_DIM,
                          rx, py + 108)
            else:
                if self._variante_feito:
                    draw_text(surface, "Variante ativa: sem bônus racial de atributo após atribuir os dados.",
                              xsfont, C_TEXT_DIM, rx, py + 88)
                else:
                    draw_text(surface, "Atribua cada Dado 1–6 a um atributo (sem repetir).", xsfont, C_TEXT_DIM,
                              rx, py + 88)

        rb = self._racial_dict()
        hdr = self._stats_header_h()
        ry0 = py + hdr
        row_h = 42
        gap_y = 6
        stats_right = self._panel.right - 16
        stats_w = max(0, stats_right - rx)
        mid_gap = 10
        col_w = (stats_w - mid_gap) // 2 if stats_w > mid_gap else stats_w
        single = col_w < 300
        rx2 = rx + col_w + mid_gap if not single else rx

        order_left = ("str", "dex", "con")
        order_right = ("int", "wis", "cha")

        if single:
            for row, key in enumerate(_ABILITY_KEYS):
                self._draw_stat_row(surface, key, rx, ry0 + row * (row_h + gap_y), bfont, sfont, xsfont, rb)
        else:
            for row, key in enumerate(order_left):
                self._draw_stat_row(surface, key, rx, ry0 + row * (row_h + gap_y), bfont, sfont, xsfont, rb)
            for row, key in enumerate(order_right):
                self._draw_stat_row(surface, key, rx2, ry0 + row * (row_h + gap_y), bfont, sfont, xsfont, rb)

        if self._error:
            draw_text_centered(surface, self._error, bfont, C_TEXT_ACCENT,
                               w // 2, self._panel.bottom - 86)

        self._btn_save.draw(surface, bfont)
        self._btn_back.draw(surface, bfont)

    def _draw_stat_row(self, surface, key, x, y, bfont, sfont, xsfont, rb):
        lbl = _ABILITY_LABELS[key]
        if self._ability_method == "pointbuy":
            base = self._scores[key]
        else:
            i = self._roll_assign_idx.get(key)
            base = self._roll_results[i] if i is not None and len(self._roll_results) == 6 else 0
        r = rb[key]
        final = base + r if base > 0 else 0
        mod = point_buy.ability_modifier(final) if final > 0 else 0

        draw_text(surface, lbl, bfont, C_TEXT_BRIGHT, x, y + 8)

        if self._ability_method == "pointbuy":
            self._btn_minus[key].draw(surface, bfont)
            draw_text_centered(
                surface, str(base), fonts.get("heading", 17), C_TEXT_BRIGHT,
                x + 70, y + 15,
            )
            self._btn_plus[key].draw(surface, bfont)
            xb = x + 136
        else:
            self._dd_roll_pick[key].draw(surface, xsfont)
            txt = str(base) if base > 0 else "—"
            draw_text_centered(surface, txt, fonts.get("heading", 17), C_TEXT_BRIGHT, x + 148, y + 15)
            xb = x + 188

        draw_text(surface, _fmt_bonus(r), xsfont, C_GOLD if r else C_TEXT_DIM, xb, y + 10)
        tot_s = "%d (%s)" % (final, _mod_str(mod)) if final > 0 else "—"
        draw_text(surface, tot_s, sfont, C_TEXT_BRIGHT, xb + 34, y + 8)
