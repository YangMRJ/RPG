#!/usr/bin/env python3
"""GRID QUEST - mini RPG em pygame.  pip install pygame && python grid_quest.py"""
import math, random, json, heapq
from functools import lru_cache
from dataclasses import dataclass, asdict
import pygame as pg

TS, CH, SAVE = 48, 16, "ficha.json"   # tamanho do tile (px), tamanho do chunk, arquivo de save
SEED = 1
D8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
KINDS, ITYPES = ['melee', 'ranged', 'magic'], ['hp', 'mp', 'weapon', 'misc', 'coin']
GRASS, SAND, WATER, TREE, ROCK = range(5)


# ---------------------------------------------------------------- mundo infinito
def hsh(x, y, s=0):
    n = (x * 374761393 + y * 668265263 + (SEED + s) * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFFFF) / 0xFFFFFF


def vnoise(x, y, s=0):
    xi, yi = math.floor(x), math.floor(y)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = hsh(xi, yi, s), hsh(xi + 1, yi, s), hsh(xi, yi + 1, s), hsh(xi + 1, yi + 1, s)
    top, bot = a + (b - a) * fx, c + (d - c) * fx
    return top + (bot - top) * fy


@lru_cache(maxsize=300000)
def terrain(x, y):
    if abs(x) <= 2 and abs(y) <= 2:
        return GRASS
    n = vnoise(x / 12, y / 12)
    if n < 0.30: return WATER
    if n < 0.34: return SAND
    r = hsh(x, y, 3)
    if r < (0.22 if vnoise(x / 6, y / 6, 7) > 0.6 else 0.05): return TREE
    if r > 0.985: return ROCK
    return GRASS


def walkable(x, y):
    return terrain(x, y) in (GRASS, SAND)


def astar(start, goal, tgt, occ, maxn=1800):
    """A* 8 direcoes. Se nao achar o objetivo, vai ate o ponto mais proximo de tgt."""
    def hc(n):
        dx, dy = abs(n[0] - tgt[0]), abs(n[1] - tgt[1])
        return max(dx, dy) + 0.414 * min(dx, dy)
    openh, g, par, closed = [(hc(start), 0, start)], {start: 0}, {}, set()
    best, bh, cnt = start, hc(start), 0
    while openh and cnt < maxn:
        _, gc, n = heapq.heappop(openh)
        if n in closed: continue
        closed.add(n); cnt += 1
        if goal(n): best = n; break
        h = hc(n)
        if h < bh: bh, best = h, n
        for dx, dy in D8:
            m = (n[0] + dx, n[1] + dy)
            if m in closed or m in occ or not walkable(*m): continue
            if dx and dy and not (walkable(n[0] + dx, n[1]) and walkable(n[0], n[1] + dy)): continue
            ng = gc + (1.414 if dx and dy else 1)
            if ng < g.get(m, 1e9):
                g[m], par[m] = ng, n
                heapq.heappush(openh, (ng + hc(m), ng, m))
    path, n = [], best
    while n != start:
        path.append(n); n = par[n]
    return path[::-1]


# ---------------------------------------------------------------- dados
@dataclass
class Attack:
    name: str = "Ataque"
    kind: str = "melee"      # melee | ranged | magic
    dmg: int = 5
    reach: float = 1.6       # alcance em tiles
    cost: int = 0            # mana
    area: float = 0.0        # magia/ranged: raio da explosao; melee: >0 = golpe giratorio 360
    color: str = "#ffffff"


class Ent:
    def __init__(s, name, x, y, hp, color, team, atk=None, move=4):
        s.name, s.x, s.y, s.hp, s.max, s.color, s.team, s.atk, s.move = name, x + .5, y + .5, hp, hp, color, team, atk, move
        s.path, s.speed, s.face, s.dead, s.wander = [], 5.0, 0.0, False, random.random() * 3

    @property
    def tile(s): return (math.floor(s.x), math.floor(s.y))


class Player(Ent):
    def __init__(s):
        super().__init__("Herói", 0, 0, 40, (70, 140, 255), 'p', None, 5)
        s.mp = s.mpmax = 20; s.str = s.dex = s.intel = 4; s.gold = 0; s.cd = 0.0; s.sel = 0
        s.attacks = [Attack("Espada", "melee", 6, 1.6, 0, 0, "#e8eef8"),
                     Attack("Giro de Lâmina", "melee", 4, 1.8, 3, 1, "#ffd0d0"),
                     Attack("Arco", "ranged", 5, 7, 0, 0, "#ffd27a"),
                     Attack("Bola de Fogo", "magic", 9, 6, 4, 1.5, "#ff8c3a"),
                     Attack("Raio Arcano", "magic", 7, 8, 3, 0, "#4fd8ff")]
        s.inv = [dict(name="Poção de Vida", type="hp", qty=2, val=15),
                 dict(name="Poção de Mana", type="mp", qty=1, val=10),
                 dict(name="Espada Curta", type="weapon", qty=1, val=2, kind="melee", eq=True),
                 dict(name="Arco Curto", type="weapon", qty=1, val=2, kind="ranged", eq=True),
                 dict(name="Cajado Simples", type="weapon", qty=1, val=2, kind="magic", eq=True)]

    def power(s, a):
        b = a.dmg + {'melee': s.str, 'ranged': s.dex, 'magic': s.intel}.get(a.kind, 0) // 2
        return b + sum(i['val'] for i in s.inv if i['type'] == 'weapon' and i.get('eq') and i.get('kind') == a.kind)

    def data(s):
        d = {k: getattr(s, k) for k in ('name', 'max', 'hp', 'mp', 'mpmax', 'str', 'dex', 'intel', 'gold', 'move')}
        d['attacks'] = [asdict(a) for a in s.attacks]; d['inv'] = s.inv
        return d

    def load(s, d):
        for k in ('name', 'max', 'hp', 'mp', 'mpmax', 'str', 'dex', 'intel', 'gold', 'move'): setattr(s, k, d[k])
        s.attacks = [Attack(**a) for a in d['attacks']]; s.inv = d['inv']


TPL = [("Goblin", 22, Attack("Garras", "melee", 4, 1.5, 0, 0, "#ffffff"), (210, 70, 60)),
       ("Esqueleto", 30, Attack("Lâmina", "melee", 5, 1.5, 0, 0, "#dddddd"), (225, 225, 205)),
       ("Arqueiro", 16, Attack("Flecha", "ranged", 4, 6, 0, 0, "#ffd27a"), (220, 150, 50)),
       ("Mago Sombrio", 14, Attack("Orbe Sombrio", "magic", 6, 5, 0, 1.2, "#b46bff"), (150, 70, 210))]


def make_npc(r, x, y):
    n, hp, a, c = r.choice(TPL)
    return Ent(n, x, y, hp, c, 'n', Attack(**asdict(a)), 4)


def make_item(r):
    v = r.random()
    if v < .3: return dict(name="Poção de Vida", type="hp", qty=1, val=15)
    if v < .5: return dict(name="Poção de Mana", type="mp", qty=1, val=10)
    if v < .85: return dict(name="Ouro", type="coin", qty=r.randint(3, 12), val=0)
    n, b, k = r.choice([("Machado", 3, "melee"), ("Arco Longo", 3, "ranged"), ("Grimório", 3, "magic"), ("Adaga", 2, "melee")])
    return dict(name=n, type="weapon", qty=1, val=b, kind=k, eq=False)


ITEM_COL = {'hp': (220, 60, 60), 'mp': (70, 110, 240), 'coin': (250, 210, 60), 'weapon': (230, 230, 240), 'misc': (180, 140, 90)}


def hexc(h):
    try: return tuple(pg.Color(h))[:3]
    except Exception: return (255, 255, 255)


def gv(o, k): return o[k] if isinstance(o, dict) else getattr(o, k)
def sv(o, k, v):
    if isinstance(o, dict): o[k] = v
    else: setattr(o, k, v)


class Fx:
    def __init__(s, kind, x, y, **kw):
        s.kind, s.x, s.y, s.t = kind, x, y, 0.0
        s.__dict__.update(kw)


# ---------------------------------------------------------------- jogo
class Game:
    def __init__(s, scr):
        s.scr, s.fonts, s.quit, s.t = scr, {}, False, 0.0
        s.mode, s.started, s.hits, s.tip = 'menu', False, [], None
        s.W, s.H = scr.get_size(); s.layer = None
        s.toast, s.toast_t, s.ed, s.buf, s.drag = "", 0, None, "", False
        s.panel, s.tab, s.scroll = False, 0, 0

    # ---------- util
    def font(s, sz):
        if sz not in s.fonts: s.fonts[sz] = pg.font.Font(None, sz)
        return s.fonts[sz]

    def txt(s, t, x, y, sz=18, col=(235, 235, 240), center=False, right=False, out=False):
        f = s.font(sz); im = f.render(str(t), True, col); r = im.get_rect()
        if center: r.center = (x, y)
        elif right: r.topright = (x, y)
        else: r.topleft = (x, y)
        if out:
            sh = f.render(str(t), True, (0, 0, 0))
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)): s.scr.blit(sh, r.move(dx, dy))
        s.scr.blit(im, r)

    def msg(s, t): s.toast, s.toast_t = t, 2.6

    def w2s(s, x, y):
        z = TS * s.zoom; return ((x - s.cx) * z + s.W / 2, (y - s.cy) * z + s.H / 2)

    def s2w(s, px, py):
        z = TS * s.zoom; return ((px - s.W / 2) / z + s.cx, (py - s.H / 2) / z + s.cy)

    def ents(s):
        p = s.player
        return [p] + [n for n in s.npcs if not n.dead and abs(n.x - p.x) < 60 and abs(n.y - p.y) < 60]

    def cur(s):
        c = s.combat; return c['order'][c['i']] if c else None

    def busy(s): return any(f.kind in ('slash', 'proj') for f in s.fx)

    # ---------- novo jogo
    def new_game(s):
        global SEED
        SEED = random.randint(1, 10 ** 6); terrain.cache_clear()
        s.player = Player(); s.npcs, s.items, s.chunks, s.fx = [], {}, set(), []
        s.combat, s.pending, s.regen = None, None, 0.0
        s.cx, s.cy, s.zoom, s.follow = .5, .5, 1.0, True
        s.mode, s.started, s.panel = 'play', True, False
        s.msg("Bem-vindo! Clique para andar, botão direito ataca. Veja Controles no menu.")

    def gen(s, cx, cy):
        r = random.Random(f"{SEED}:{cx}:{cy}")

        def spot():
            for _ in range(20):
                x, y = cx * CH + r.randrange(CH), cy * CH + r.randrange(CH)
                if walkable(x, y) and abs(x) + abs(y) > 6 and (x, y) not in s.items: return x, y
        n = 2 if (cx, cy) in ((0, 0), (-1, -1), (-1, 0), (0, -1)) else r.choice([0, 1, 1, 2])
        for _ in range(n):
            pt = spot()
            if pt: s.npcs.append(make_npc(r, *pt))
        for _ in range(r.randint(2, 4)):
            pt = spot()
            if pt: s.items[pt] = make_item(r)

    def ensure_chunks(s):
        for (x, y), rad in (((s.player.x, s.player.y), 2), ((s.cx, s.cy), 3)):
            px, py = math.floor(x / CH), math.floor(y / CH)
            for dx in range(-rad, rad + 1):
                for dy in range(-rad, rad + 1):
                    if (px + dx, py + dy) not in s.chunks:
                        s.chunks.add((px + dx, py + dy)); s.gen(px + dx, py + dy)

    # ---------- movimento / pathfinding
    def go(s, e, goal, tgt, budget=None):
        occ = {n.tile for n in s.ents() if n is not e}
        path = astar(e.tile, goal, tgt, occ)
        c = s.combat
        if e is s.player and c:
            path = path[:c['move']]; c['move'] -= len(path)
            if not path: s.msg("Sem movimento restante")
        elif budget is not None:
            path = path[:budget]
        e.path = path

    def move_ent(s, e, dt):
        if not e.path: return
        tx, ty = e.path[0][0] + .5, e.path[0][1] + .5
        dx, dy = tx - e.x, ty - e.y; d = math.hypot(dx, dy); st = e.speed * dt
        if d <= st: e.x, e.y = tx, ty; e.path.pop(0)
        else: e.x += dx / d * st; e.y += dy / d * st; e.face = math.atan2(dy, dx)

    def pickup(s):
        p = s.player; it = s.items.pop(p.tile, None)
        if not it: return
        if it['type'] == 'coin': p.gold += it['qty']
        else:
            for o in p.inv:
                if o['type'] == it['type'] and o['name'] == it['name'] and it['type'] != 'weapon': o['qty'] += it['qty']; break
            else: p.inv.append(it)
        s.msg(f"Pegou: {it['name']}" + (f" x{it['qty']}" if it['qty'] > 1 else ""))

    # ---------- combate
    def deal(s, t, dmg):
        if t.dead: return
        t.hp -= dmg
        s.fx.append(Fx('text', t.x, t.y - .6, txt=str(dmg), col=(255, 90, 90) if t.team == 'p' else (255, 230, 120), dur=1.0))
        if t.hp <= 0:
            t.hp, t.dead = 0, True
            if t.team == 'n':
                if random.random() < .4 and t.tile not in s.items: s.items[t.tile] = make_item(random)
            else:
                s.combat = None; s.msg("Você foi derrotado! Pressione R para reviver.")

    def perform(s, src, a, tx, ty, dmg):
        ang = math.atan2(ty - src.y, tx - src.x); src.face = ang; col = hexc(a.color)
        if a.kind == 'melee':
            def cb():
                for e in s.ents():
                    if e.team == src.team or e.dead: continue
                    dx, dy = e.x - src.x, e.y - src.y; d = math.hypot(dx, dy)
                    if d > a.reach + .4: continue
                    diff = abs((math.atan2(dy, dx) - ang + math.pi) % math.tau - math.pi)
                    if a.area <= 0 and diff > 1.0 and d > .9: continue
                    s.deal(e, dmg)
            s.fx.append(Fx('slash', src.x, src.y, ang=ang, reach=a.reach, dur=.28, col=col, hit=False, cb=cb,
                           cone=math.tau if a.area > 0 else 2.0))
        else:
            d = max(.5, min(math.hypot(tx - src.x, ty - src.y), a.reach))
            s.fx.append(Fx('proj', src.x, src.y, tx=src.x + math.cos(ang) * d, ty=src.y + math.sin(ang) * d,
                           sp=16 if a.kind == 'ranged' else 9, team=src.team, atk=a, dmg=dmg, col=col, trail=[], ang=ang))

    def impact(s, f, px, py, tgt):
        a = f.atk
        if a.area > 0:
            for e in s.ents():
                if e.team != f.team and math.hypot(e.x - px, e.y - py) <= a.area + .3: s.deal(e, f.dmg)
        elif tgt: s.deal(tgt, f.dmg)
        if a.kind == 'magic' or a.area > 0: s.fx.append(Fx('burst', px, py, r=max(.5, a.area), dur=.35, col=f.col))
        elif tgt: s.fx.append(Fx('burst', px, py, r=.3, dur=.2, col=f.col))

    def update_fx(s, dt):
        for f in s.fx[:]:
            f.t += dt
            if f.kind == 'slash':
                if not f.hit and f.t >= .08: f.hit = True; f.cb()
                if f.t >= f.dur: s.fx.remove(f)
            elif f.kind == 'proj':
                f.trail = (f.trail + [(f.x, f.y)])[-10:]
                d = math.hypot(f.tx - f.x, f.ty - f.y); st = f.sp * dt
                hit = next((e for e in s.ents() if e.team != f.team and not e.dead and math.hypot(e.x - f.x, e.y - f.y) < .45), None)
                if hit or d <= st:
                    s.fx.remove(f); s.impact(f, hit.x if hit else f.tx, hit.y if hit else f.ty, hit)
                else: f.x += (f.tx - f.x) / d * st; f.y += (f.ty - f.y) / d * st
            elif f.t >= f.dur: s.fx.remove(f)

    def player_attack(s, tx, ty):
        p, c = s.player, s.combat
        if p.dead or not p.attacks: return False
        a = p.attacks[min(p.sel, len(p.attacks) - 1)]
        if c and (s.cur() is not p or c['acted'] or s.busy()): s.msg("Sem ação disponível neste turno"); return False
        if not c and p.cd > 0: return False
        if p.mp < a.cost: s.msg("Mana insuficiente"); return False
        p.mp -= a.cost
        b = p.power(a); s.perform(p, a, tx, ty, random.randint(max(1, int(b * .85)), max(1, int(b * 1.15))))
        p.cd = .55
        if c: c['acted'] = True
        return True

    def start_combat(s):
        p = s.player
        foes = sorted([n for n in s.npcs if not n.dead and math.hypot(n.x - p.x, n.y - p.y) <= 14],
                      key=lambda n: math.hypot(n.x - p.x, n.y - p.y))[:6]
        if not foes: s.msg("Nenhum NPC por perto para lutar"); return
        s.combat = dict(order=[p] + foes, i=0, move=p.move, acted=False, wait=0.0, ph='think')
        p.path, s.pending = [], None
        s.msg("Combate iniciado! Enter = fim do turno")

    def toggle_combat(s):
        if s.combat: s.combat = None; s.msg("Combate encerrado")
        elif not s.player.dead: s.start_combat()

    def next_turn(s):
        c, p = s.combat, s.player
        order, idx = c['order'], c['i']; n = len(order); nxt = None
        for k in range(1, n + 1):
            e = order[(idx + k) % n]
            if not e.dead: nxt = e; break
        alive = [e for e in order if not e.dead]
        if len([e for e in alive if e is not p]) == 0: s.combat = None; s.msg("Vitória! Combate encerrado."); return
        c['order'] = alive; c['i'] = alive.index(nxt); c['acted'] = False; c['ph'] = 'think'; c['wait'] = .4
        if nxt is p:
            c['move'] = p.move; p.mp = min(p.mpmax, p.mp + 2); s.msg("Seu turno!")

    def update_combat(s, dt):
        c = s.combat; e = s.cur(); p = s.player
        if e is p or s.busy() or e.path: return
        c['wait'] -= dt
        if c['wait'] > 0: return
        a = e.atk; d = math.hypot(p.x - e.x, p.y - e.y)
        if c['ph'] == 'think':
            if d > a.reach:
                s.go(e, lambda n: math.hypot(n[0] + .5 - p.x, n[1] + .5 - p.y) <= a.reach * .95, p.tile, e.move)
            c['ph'] = 'moved'; c['wait'] = .15; return
        if c['ph'] == 'moved':
            c['ph'] = 'done'
            if d <= a.reach + .05:
                s.perform(e, a, p.x, p.y, random.randint(max(1, int(a.dmg * .8)), int(a.dmg * 1.2) + 1)); c['wait'] = .5
            return
        s.next_turn()

    # ---------- ações do jogador
    def click_world(s, pos):
        p = s.player
        if p.dead or (s.combat and s.cur() is not p) or s.busy() and s.combat: return
        wx, wy = s.s2w(*pos)
        foe = next((n for n in s.ents() if n.team == 'n' and math.hypot(n.x - wx, n.y - wy) < .6), None)
        if foe and p.attacks:
            a = p.attacks[min(p.sel, len(p.attacks) - 1)]
            if math.hypot(foe.x - p.x, foe.y - p.y) <= a.reach + .3: p.path = []; s.player_attack(foe.x, foe.y)
            else:
                s.go(p, lambda n: math.hypot(n[0] + .5 - foe.x, n[1] + .5 - foe.y) <= a.reach, foe.tile); s.pending = foe
        else:
            t = (math.floor(wx), math.floor(wy)); s.pending = None
            s.go(p, lambda n: n == t, t)

    def use_item(s, it):
        p = s.player
        if it['type'] in ('hp', 'mp'):
            if it['type'] == 'hp': p.hp = min(p.max, p.hp + it['val'])
            else: p.mp = min(p.mpmax, p.mp + it['val'])
            it['qty'] -= 1
        elif it['type'] == 'weapon':
            on = not it.get('eq')
            for o in p.inv:
                if o['type'] == 'weapon' and o.get('kind') == it.get('kind'): o['eq'] = False
            it['eq'] = on
        elif it['type'] == 'coin': p.gold += it['qty']; it['qty'] = 0
        s.clamp()

    def quick(s, typ):
        it = next((i for i in s.player.inv if i['type'] == typ), None)
        if it: s.use_item(it)
        else: s.msg("Sem poção disponível")

    def clamp(s):
        p = s.player
        p.max = max(1, p.max); p.hp = max(1, min(p.hp, p.max)); p.mpmax = max(0, p.mpmax); p.mp = max(0, min(p.mp, p.mpmax))
        p.move, p.gold = max(0, p.move), max(0, p.gold)
        for a in p.attacks: a.reach, a.cost, a.area, a.dmg = max(.5, a.reach), max(0, a.cost), max(0, a.area), max(0, a.dmg)
        for i in p.inv: i.setdefault('kind', 'melee'); i.setdefault('eq', False); i['qty'] = max(0, i['qty']); i['val'] = max(0, i['val'])
        p.inv = [i for i in p.inv if i['qty'] > 0]
        p.sel = min(p.sel, max(0, len(p.attacks) - 1))

    # ---------- edição de campos
    def begin(s, o, k, kind):
        s.ed = (o, k, kind); s.buf = f"{gv(o, k):g}" if kind == 'float' else str(gv(o, k))

    def commit(s):
        if not s.ed: return
        o, k, kind = s.ed; b = s.buf.strip(); s.ed = None
        try:
            if kind == 'int': v = int(float(b))
            elif kind == 'float': v = float(b)
            elif kind == 'color': pg.Color(b); v = b
            else: v = b
        except Exception: s.msg("Valor inválido"); return
        sv(o, k, v); s.clamp()

    def cycle(s, o, k, opts):
        sv(o, k, opts[(opts.index(gv(o, k)) + 1) % len(opts)]); s.clamp()

    def set_tab(s, i): s.commit(); s.tab, s.scroll = i, 0

    def open_tab(s, i):
        s.commit()
        if s.panel and s.tab == i: s.panel = False
        else: s.panel, s.tab, s.scroll = True, i, 0

    def save(s):
        json.dump(dict(seed=SEED, player=s.player.data()), open(SAVE, "w"), indent=1, ensure_ascii=False); s.msg(f"Ficha salva em {SAVE}")

    def load(s):
        try: s.player.load(json.load(open(SAVE))['player']); s.clamp(); s.msg("Ficha carregada")
        except Exception: s.msg("Não consegui carregar a ficha")

    # ---------- eventos
    def handle(s, e):
        if e.type == pg.QUIT: s.quit = True
        elif e.type == pg.KEYDOWN: s.key(e)
        elif e.type == pg.MOUSEBUTTONDOWN: s.click(e)
        elif e.type == pg.MOUSEBUTTONUP and e.button == 2: s.drag = False
        elif e.type == pg.MOUSEMOTION and s.drag and s.mode == 'play':
            z = TS * s.zoom; s.cx -= e.rel[0] / z; s.cy -= e.rel[1] / z; s.follow = False
        elif e.type == pg.MOUSEWHEEL and s.mode == 'play': s.wheel(e.y)

    def wheel(s, d):
        if s.panel and s.hits and s.tab > 0:
            s.scroll = max(0, s.scroll - d); return
        mx, my = pg.mouse.get_pos(); before = s.s2w(mx, my)
        s.zoom = max(.3, min(3.0, s.zoom * 1.12 ** d))
        if not s.follow:
            after = s.s2w(mx, my); s.cx += before[0] - after[0]; s.cy += before[1] - after[1]

    def click(s, e):
        if e.button > 3: return
        s.commit()
        for r, fn in reversed(s.hits):
            if r.collidepoint(e.pos):
                if e.button == 1: fn()
                return
        if s.mode != 'play': return
        if e.button == 1: s.click_world(e.pos)
        elif e.button == 3:
            if not (s.combat and s.cur() is not s.player): s.player_attack(*s.s2w(*e.pos))
        elif e.button == 2: s.drag = True

    def key(s, e):
        k = e.key
        if s.ed:
            if k in (pg.K_RETURN, pg.K_KP_ENTER): s.commit()
            elif k == pg.K_ESCAPE: s.ed = None
            elif k == pg.K_BACKSPACE: s.buf = s.buf[:-1]
            elif e.unicode and e.unicode.isprintable(): s.buf += e.unicode
            return
        if s.mode == 'help': 
            if k == pg.K_ESCAPE: s.mode = 'menu'
            return
        if s.mode != 'play': return
        p = s.player
        if k == pg.K_ESCAPE:
            if s.panel: s.panel = False
            else: s.mode = 'menu'
        elif k == pg.K_c: s.open_tab(0)
        elif k == pg.K_a: s.open_tab(1)
        elif k == pg.K_i: s.open_tab(2)
        elif pg.K_1 <= k <= pg.K_8:
            if k - pg.K_1 < len(p.attacks): p.sel = k - pg.K_1
        elif k == pg.K_t: s.toggle_combat()
        elif k in (pg.K_RETURN, pg.K_KP_ENTER):
            if s.combat and s.cur() is p and not s.busy(): s.next_turn()
        elif k == pg.K_SPACE: s.follow = True
        elif k == pg.K_q: s.quick('hp')
        elif k == pg.K_e: s.quick('mp')
        elif k == pg.K_F5: s.save()
        elif k == pg.K_F9: s.load()
        elif k == pg.K_r and p.dead:
            p.dead, p.hp, p.path = False, max(1, p.max // 2), []; s.msg("Você se levantou.")

    # ---------- update
    def update(s, dt):
        s.t += dt
        s.toast_t -= dt
        if s.mode != 'play': return
        p = s.player; s.ensure_chunks(); s.update_fx(dt)
        if not p.dead:
            p.cd = max(0, p.cd - dt); s.move_ent(p, dt); s.pickup()
            if s.pending and not p.path:
                f, s.pending = s.pending, None; a = p.attacks[min(p.sel, len(p.attacks) - 1)]
                if not f.dead and math.hypot(f.x - p.x, f.y - p.y) <= a.reach + .3: s.player_attack(f.x, f.y)
            if not s.combat:
                s.regen += dt * .5
                if s.regen >= 1: s.regen -= 1; p.mp = min(p.mpmax, p.mp + 1)
        for n in s.npcs:
            if n.dead: continue
            n.speed = 5.0 if s.combat else 2.5; s.move_ent(n, dt)
            n.wander -= dt
            if not s.combat and n.wander <= 0 and not n.path:
                n.wander = random.uniform(2, 6)
                if abs(n.x - p.x) < 40 and abs(n.y - p.y) < 40:
                    dx, dy = random.choice(D8[:4]); t = (n.tile[0] + dx, n.tile[1] + dy)
                    if walkable(*t) and t not in {e.tile for e in s.ents()}: n.path = [t]
        s.npcs = [n for n in s.npcs if not n.dead]
        if s.combat: s.update_combat(dt)
        k = pg.key.get_pressed()
        if not s.ed:
            dx, dy = k[pg.K_RIGHT] - k[pg.K_LEFT], k[pg.K_DOWN] - k[pg.K_UP]
            if dx or dy: s.follow = False; s.cx += dx * 12 * dt / s.zoom ** .5; s.cy += dy * 12 * dt / s.zoom ** .5
        if s.follow: s.cx += (p.x - s.cx) * min(1, dt * 6); s.cy += (p.y - s.cy) * min(1, dt * 6)

    # ---------- desenho: UI base
    def bar(s, x, y, w, h, f, col, label=None):
        pg.draw.rect(s.scr, (20, 20, 24), (x, y, w, h), border_radius=4)
        pg.draw.rect(s.scr, col, (x + 1, y + 1, max(0, (w - 2) * max(0, min(1, f))), h - 2), border_radius=4)
        pg.draw.rect(s.scr, (200, 200, 210), (x, y, w, h), 1, border_radius=4)
        if label: s.txt(label, x + w / 2, y + h / 2, 15 if h < 20 else 18, center=True, out=True)

    def btn(s, r, text, fn, active=False):
        hov = r.collidepoint(pg.mouse.get_pos())
        pg.draw.rect(s.scr, (80, 90, 150) if active else (62, 68, 100) if hov else (42, 46, 70), r, border_radius=6)
        pg.draw.rect(s.scr, (140, 150, 200), r, 1, border_radius=6)
        s.txt(text, r.centerx, r.centery, 19, center=True); s.hits.append((r, fn))

    def field(s, x, y, w, o, k, kind, opts=None):
        r = pg.Rect(x, y, w, 26); ed = s.ed and s.ed[0] is o and s.ed[1] == k
        pg.draw.rect(s.scr, (50, 52, 96) if ed else (18, 20, 28), r, border_radius=4)
        pg.draw.rect(s.scr, (110, 115, 160), r, 1, border_radius=4)
        v = gv(o, k); tx = s.buf + "|" if ed else (f"{v:g}" if kind == 'float' else str(v))
        if kind == 'color':
            pg.draw.rect(s.scr, hexc(str(v)), (r.x + 4, r.y + 4, 18, 18)); s.txt(tx, r.x + 28, r.y + 6, 18)
        else: s.txt(tx, r.x + 6, r.y + 6, 18)
        s.hits.append((r, (lambda: s.cycle(o, k, opts)) if kind == 'cycle' else (lambda: s.begin(o, k, kind))))

    def icon(s, kind, r, col):
        sc, c = s.scr, r.center
        if kind == 'melee':
            pg.draw.line(sc, col, (r.left + 13, r.bottom - 13), (r.right - 13, r.top + 13), 5)
            pg.draw.line(sc, (170, 120, 70), (c[0] - 9, c[1] + 3), (c[0] - 3, c[1] + 9), 4)
        elif kind == 'ranged':
            pg.draw.line(sc, col, (r.left + 10, c[1]), (r.right - 10, c[1]), 3)
            pg.draw.polygon(sc, col, [(r.right - 8, c[1]), (r.right - 18, c[1] - 7), (r.right - 18, c[1] + 7)])
        else:
            pg.draw.circle(sc, col, c, 9)
            for a in range(0, 360, 60):
                pg.draw.line(sc, col, c, (c[0] + math.cos(math.radians(a)) * 17, c[1] + math.sin(math.radians(a)) * 17), 2)

    # ---------- desenho: menu / help
    def draw_menu(s):
        W, H = s.W, s.H; s.scr.fill((18, 20, 30)); off = (s.t * 20) % 48
        for i in range(-1, W // 48 + 2): pg.draw.line(s.scr, (30, 34, 52), (i * 48 + off, 0), (i * 48 + off, H))
        for i in range(-1, H // 48 + 2): pg.draw.line(s.scr, (30, 34, 52), (0, i * 48 + off), (W, i * 48 + off))
        s.txt("GRID QUEST", W // 2, H // 2 - 170, 110, (255, 220, 120), center=True, out=True)
        s.txt("mini RPG em mapa infinito", W // 2, H // 2 - 110, 28, (170, 180, 220), center=True)
        items = [("Novo Jogo", s.new_game)]
        if s.started: items.append(("Continuar", lambda: setattr(s, 'mode', 'play')))
        items += [("Controles", lambda: setattr(s, 'mode', 'help')), ("Sair", lambda: setattr(s, 'quit', True))]
        for i, (t, fn) in enumerate(items): s.btn(pg.Rect(W // 2 - 130, H // 2 - 50 + i * 58, 260, 46), t, fn)

    def draw_help(s):
        s.draw_menu(); W, H = s.W, s.H
        r = pg.Rect(W // 2 - 380, H // 2 - 230, 760, 460)
        pg.draw.rect(s.scr, (28, 30, 42), r, border_radius=10); pg.draw.rect(s.scr, (110, 115, 150), r, 2, border_radius=10)
        s.hits.append((r, lambda: None))
        L = ["Botão esquerdo: andar (A*) / atacar o inimigo clicado com o ataque selecionado",
             "Botão direito: dispara o ataque selecionado na direção do cursor",
             "1-8: escolhe o ataque da hotbar      Q / E: poção de vida / mana",
             "Roda do mouse: zoom      Botão do meio ou setas: mover câmera",
             "Espaço: câmera volta a seguir o personagem",
             "C: ficha   A: editar ataques   I: inventário e itens",
             "   (clique em um campo, digite e Enter; campos de tipo alternam ao clicar)",
             "T: inicia/encerra combate por turnos com NPCs a até 14 tiles",
             "Enter: fim do turno   (cada turno: movimento limitado + 1 ação)",
             "F5 / F9: salvar / carregar ficha      Esc: menu"]
        for i, l in enumerate(L): s.txt(l, r.x + 24, r.y + 28 + i * 34, 21)
        s.btn(pg.Rect(r.centerx - 70, r.bottom - 58, 140, 40), "Voltar", lambda: setattr(s, 'mode', 'menu'))

    # ---------- desenho: mundo
    def draw_world(s):
        sc, W, H = s.scr, s.W, s.H; z = TS * s.zoom
        x0, y0 = map(math.floor, s.s2w(0, 0)); x1, y1 = map(math.floor, s.s2w(W, H)); sz = math.ceil(z) + 1
        for ty in range(y0, y1 + 1):
            py = (ty - s.cy) * z + H / 2
            for tx in range(x0, x1 + 1):
                px = (tx - s.cx) * z + W / 2; t = terrain(tx, ty); v = hsh(tx, ty, 9)
                if t == SAND: c = (196 + int(v * 10), 180 + int(v * 10), 120)
                elif t == WATER: k = int(12 * math.sin(s.t * 2 + tx * .7 + ty * .5)); c = (40 + k, 88 + k, 168 + k)
                else: c = (50 + int(v * 14), 110 + int(v * 22), 56)
                pg.draw.rect(sc, c, (int(px), int(py), sz, sz))
                if t == TREE:
                    pg.draw.rect(sc, (90, 60, 35), (px + z * .43, py + z * .55, z * .14, z * .35))
                    pg.draw.circle(sc, (28, 78, 36), (px + z / 2, py + z * .42), z * .34)
                    pg.draw.circle(sc, (42, 104, 48), (px + z * .42, py + z * .36), z * .2)
                elif t == ROCK:
                    pg.draw.circle(sc, (110, 112, 122), (px + z / 2, py + z * .55), z * .3)
                    pg.draw.circle(sc, (150, 152, 162), (px + z * .43, py + z * .47), z * .13)
        if z >= 24:
            for tx in range(x0, x1 + 2):
                X = (tx - s.cx) * z + W / 2; pg.draw.line(sc, (30, 62, 40), (X, 0), (X, H))
            for ty in range(y0, y1 + 2):
                Y = (ty - s.cy) * z + H / 2; pg.draw.line(sc, (30, 62, 40), (0, Y), (W, Y))
        mx, my = pg.mouse.get_pos(); wx, wy = s.s2w(mx, my)
        hx, hy = s.w2s(math.floor(wx), math.floor(wy)); pg.draw.rect(sc, (255, 255, 255), (hx, hy, z, z), 2)
        for (ix, iy), it in s.items.items():
            if not (x0 <= ix <= x1 and y0 <= iy <= y1): continue
            px, py = s.w2s(ix + .5, iy + .5 + math.sin(s.t * 3 + ix) * .04); c = ITEM_COL.get(it['type'], (200, 200, 200))
            pg.draw.circle(sc, (0, 0, 0), (px, py + z * .12), z * .2); pg.draw.circle(sc, c, (px, py), z * .17)
            pg.draw.circle(sc, (255, 255, 255), (px, py), z * .17, 2)
            if (ix, iy) == (math.floor(wx), math.floor(wy)): s.tip = [it['name'] + (f" x{it['qty']}" if it['qty'] > 1 else "")]
        p = s.player
        for pt in p.path:
            ax, ay = s.w2s(pt[0] + .5, pt[1] + .5); pg.draw.circle(sc, (255, 255, 255), (ax, ay), max(2, z * .06))
        if p.attacks and not p.dead:
            a = p.attacks[min(p.sel, len(p.attacks) - 1)]; ax, ay = s.w2s(p.x, p.y); pg.draw.circle(sc, hexc(a.color), (ax, ay), a.reach * z, 1)
        cu = s.cur()
        for e in sorted(s.ents(), key=lambda e: e.y):
            px, py = s.w2s(e.x, e.y)
            if not (-60 < px < W + 60 and -60 < py < H + 60): continue
            r = z * .32
            pg.draw.ellipse(sc, (25, 50, 30), (px - r, py + r * .4, r * 2, r))
            if e is cu: pg.draw.circle(sc, (255, 230, 80), (px, py), r + 5, 3)
            pg.draw.circle(sc, e.color, (px, py), r); pg.draw.circle(sc, (15, 15, 20), (px, py), r, 2)
            pg.draw.line(sc, (255, 255, 255), (px, py), (px + math.cos(e.face) * r * 1.3, py + math.sin(e.face) * r * 1.3), max(2, int(z * .06)))
            if e.team == 'n' and math.hypot(e.x - wx, e.y - wy) < .6: pg.draw.circle(sc, (255, 60, 60), (px, py), r + 4, 2)
            bw = z * .8; s.bar(px - bw / 2, py - r - z * .28, bw, max(5, z * .1), e.hp / e.max, (200, 50, 50) if e.team == 'n' else (70, 200, 90))
            if e.team == 'n' and z >= 40: s.txt(e.name, px, py - r - z * .4, 15, center=True, out=True)

    def draw_fx(s):
        if not s.fx: return
        if s.layer is None or s.layer.get_size() != (s.W, s.H): s.layer = pg.Surface((s.W, s.H), pg.SRCALPHA)
        L = s.layer; L.fill((0, 0, 0, 0)); z = TS * s.zoom
        for f in s.fx:
            px, py = s.w2s(f.x, f.y)
            if f.kind == 'slash':
                u = f.t / f.dur; R = f.reach * z; st = f.ang - f.cone / 2; en = st + f.cone * min(1, u * 1.5); n = 14
                po, pi = [], []
                for i in range(n + 1):
                    a = st + (en - st) * i / n; k = i / n; ri = R * (1 - .4 * k)
                    po.append((px + math.cos(a) * R, py + math.sin(a) * R)); pi.append((px + math.cos(a) * ri, py + math.sin(a) * ri))
                pg.draw.polygon(L, (*f.col, int(255 * (1 - u) ** .7)), po + pi[::-1])
            elif f.kind == 'proj':
                magic = f.atk.kind == 'magic'; n = len(f.trail)
                for i, (tx, ty) in enumerate(f.trail):
                    qx, qy = s.w2s(tx, ty); k = (i + 1) / (n + 1)
                    pg.draw.circle(L, (*f.col, int(150 * k)), (qx, qy), max(1, z * (.2 if magic else .06) * k))
                if magic:
                    pg.draw.circle(L, (*f.col, 70), (px, py), z * .32); pg.draw.circle(L, (*f.col, 150), (px, py), z * .21)
                    pg.draw.circle(L, (255, 255, 255, 235), (px, py), z * .1)
                else:
                    dx, dy = math.cos(f.ang), math.sin(f.ang)
                    pg.draw.line(L, (*f.col, 255), (px - dx * z * .45, py - dy * z * .45), (px, py), 3)
                    pg.draw.polygon(L, (255, 255, 255, 255), [(px + dx * z * .1, py + dy * z * .1), (px - dx * z * .08 - dy * z * .07, py - dy * z * .08 + dx * z * .07),
                                                              (px - dx * z * .08 + dy * z * .07, py - dy * z * .08 - dx * z * .07)])
            elif f.kind == 'burst':
                u = f.t / f.dur; r = f.r * z * (.3 + .7 * u)
                pg.draw.circle(L, (*f.col, int(140 * (1 - u))), (px, py), r); pg.draw.circle(L, (255, 255, 255, int(220 * (1 - u))), (px, py), r, 3)
        s.scr.blit(L, (0, 0))
        for f in s.fx:
            if f.kind == 'text':
                u = f.t / f.dur; px, py = s.w2s(f.x, f.y - u * .8); s.txt(f.txt, px, py, 28, f.col, center=True, out=True)

    # ---------- desenho: HUD
    def draw_hud(s):
        p, W, H, c = s.player, s.W, s.H, s.combat
        s.bar(20, H - 66, 270, 22, p.hp / p.max, (190, 40, 40), f"HP {p.hp}/{p.max}")
        s.bar(20, H - 38, 270, 18, p.mp / max(1, p.mpmax), (50, 90, 210), f"MP {int(p.mp)}/{p.mpmax}")
        s.txt(f"{p.name}   Ouro: {p.gold}", 20, H - 90, 20, (255, 225, 140), out=True)
        sw, gap = 56, 6; x0 = (W - (8 * sw + 7 * gap)) // 2; y = H - sw - 14
        for i in range(8):
            r = pg.Rect(x0 + i * (sw + gap), y, sw, sw); a = p.attacks[i] if i < len(p.attacks) else None
            pg.draw.rect(s.scr, (24, 26, 38), r, border_radius=6)
            if a:
                col = hexc(a.color); s.icon(a.kind, r, col)
                if not c and p.cd > 0 and i == p.sel: pg.draw.rect(s.scr, (0, 0, 0), (r.x, r.y, sw, sw * p.cd / .55), border_radius=6)
                if p.mp < a.cost: pg.draw.rect(s.scr, (30, 30, 120), r.inflate(-8, -8), 2)
                if r.collidepoint(pg.mouse.get_pos()):
                    s.tip = [a.name, f"{a.kind}  dano {p.power(a)}  alcance {a.reach:g}  mana {a.cost}" + (f"  área {a.area:g}" if a.area else "")]
                s.hits.append((r, (lambda i=i: setattr(p, 'sel', i))))
            pg.draw.rect(s.scr, (255, 220, 90) if i == p.sel else (90, 95, 120), r, 3 if i == p.sel else 1, border_radius=6)
            s.txt(str(i + 1), r.x + 5, r.y + 3, 17, (200, 200, 210))
        for i, (t, fn, act) in enumerate([("Ficha (C)", lambda: s.open_tab(0), s.panel and s.tab == 0), ("Ataques (A)", lambda: s.open_tab(1), s.panel and s.tab == 1),
                                          ("Inventário (I)", lambda: s.open_tab(2), s.panel and s.tab == 2),
                                          ("Encerrar combate (T)" if c else "Iniciar combate (T)", s.toggle_combat, bool(c))]):
            w = 200 if i == 3 else 130
            s.btn(pg.Rect(W - 12 - w, 12 + i * 38, w, 32), t, fn, act)
        s.txt(f"Tile {p.tile[0]},{p.tile[1]}   Zoom {s.zoom:.2f}x", 12, 10, 20, (255, 255, 255), out=True)
        s.txt("Esq: mover/atacar  Dir: disparar  Roda: zoom  Meio/setas: câmera  Esp: seguir", 12, 32, 17, (220, 220, 230), out=True)
        if c:
            cu = s.cur()
            s.txt("COMBATE POR TURNOS", W // 2, 20, 34, (255, 120, 100), center=True, out=True)
            s.txt(f"Turno: {cu.name}", W // 2, 48, 24, (255, 230, 120), center=True, out=True)
            for i, e in enumerate(c['order']):
                s.txt(("► " if e is cu else "   ") + f"{e.name}  {e.hp}/{e.max}", 12, 70 + i * 22, 19, (255, 230, 120) if e is cu else (230, 230, 235), out=True)
            if cu is p:
                s.txt(f"Movimento: {c['move']}   Ação: {'usada' if c['acted'] else 'disponível'}", W - 12, H - 120, 22, (255, 255, 255), right=True, out=True)
                s.btn(pg.Rect(W - 212, H - 90, 200, 40), "Fim do turno (Enter)", lambda: s.next_turn() if s.cur() is p and not s.busy() else None)

    def draw_panel(s):
        p, sc, W, H = s.player, s.scr, s.W, s.H
        pw, ph = min(1000, W - 30), min(600, H - 30); R = pg.Rect((W - pw) // 2, (H - ph) // 2, pw, ph)
        pg.draw.rect(sc, (28, 30, 42), R, border_radius=10); pg.draw.rect(sc, (110, 115, 150), R, 2, border_radius=10)
        s.hits.append((R, lambda: None))
        for i, t in enumerate(["Ficha", "Ataques", "Inventário"]): s.btn(pg.Rect(R.x + 16 + i * 130, R.y + 12, 120, 32), t, (lambda i=i: s.set_tab(i)), s.tab == i)
        s.btn(pg.Rect(R.right - 46, R.y + 12, 32, 32), "X", lambda: setattr(s, 'panel', False))
        x, y = R.x + 24, R.y + 66; vr = max(1, (ph - 66 - 30 - 64) // 34)
        if s.tab == 0:
            rows = [("Nome", 'name', 'str'), ("HP", 'hp', 'int'), ("HP máx.", 'max', 'int'), ("MP", 'mp', 'int'), ("MP máx.", 'mpmax', 'int'), ("Força", 'str', 'int'),
                    ("Destreza", 'dex', 'int'), ("Inteligência", 'intel', 'int'), ("Movimento/turno", 'move', 'int'), ("Ouro", 'gold', 'int')]
            for i, (lab, k, kd) in enumerate(rows): s.txt(lab, x, y + i * 38 + 5, 21); s.field(x + 190, y + i * 38, 170, p, k, kd)
            s.txt("Dano efetivo (base + atributo/2 + arma equipada)", x + 420, y, 21, (255, 225, 140))
            for i, a in enumerate(p.attacks[:12]):
                s.txt(f"{i + 1}. {a.name} [{a.kind}] → {p.power(a)}   alc. {a.reach:g}   mana {a.cost}", x + 420, y + 30 + i * 26, 19, hexc(a.color))
            s.txt("Clique num campo, digite e Enter. F5/F9 salva/carrega a ficha.", x, R.bottom - 34, 18, (160, 165, 190))
        elif s.tab == 1:
            s.scroll = max(0, min(s.scroll, max(0, len(p.attacks) - vr)))
            for lab, ox in (("#", 0), ("Nome", 30), ("Tipo", 210), ("Dano", 310), ("Alcance", 380), ("Mana", 460), ("Área", 530), ("Cor", 610)): s.txt(lab, x + ox, y, 18, (160, 170, 210))
            for row, i in enumerate(range(s.scroll, min(len(p.attacks), s.scroll + vr))):
                a, yy = p.attacks[i], y + 26 + row * 34
                s.txt(str(i + 1), x, yy + 5, 20, (255, 220, 90) if i < 8 else (120, 120, 130))
                s.field(x + 30, yy, 170, a, 'name', 'str'); s.field(x + 210, yy, 90, a, 'kind', 'cycle', KINDS)
                s.field(x + 310, yy, 60, a, 'dmg', 'int'); s.field(x + 380, yy, 70, a, 'reach', 'float'); s.field(x + 460, yy, 60, a, 'cost', 'int')
                s.field(x + 530, yy, 70, a, 'area', 'float'); s.field(x + 610, yy, 110, a, 'color', 'color')
                s.btn(pg.Rect(x + 730, yy, 30, 26), "X", (lambda i=i: (p.attacks.pop(i), s.clamp())))
            s.btn(pg.Rect(x, R.bottom - 56, 170, 34), "+ Novo ataque", lambda: p.attacks.append(Attack("Novo ataque")))
            s.txt("Os 8 primeiros vão para a hotbar. Melee com Área>0 = giro 360°. Magia/ranged com Área>0 explodem.", x + 190, R.bottom - 46, 18, (160, 165, 190))
        else:
            s.scroll = max(0, min(s.scroll, max(0, len(p.inv) - vr)))
            for lab, ox in (("Item", 0), ("Tipo", 230), ("Qtd", 320), ("Valor", 390), ("Arma p/", 460)): s.txt(lab, x + ox, y, 18, (160, 170, 210))
            for row, i in enumerate(range(s.scroll, min(len(p.inv), s.scroll + vr))):
                it, yy = p.inv[i], y + 26 + row * 34
                s.field(x, yy, 220, it, 'name', 'str'); s.field(x + 230, yy, 80, it, 'type', 'cycle', ITYPES)
                s.field(x + 320, yy, 60, it, 'qty', 'int'); s.field(x + 390, yy, 60, it, 'val', 'int')
                if it['type'] == 'weapon': s.field(x + 460, yy, 90, it, 'kind', 'cycle', KINDS)
                lab = {'hp': "Usar", 'mp': "Usar", 'coin': "Pegar ouro", 'weapon': "Desequipar" if it.get('eq') else "Equipar"}.get(it['type'])
                if lab: s.btn(pg.Rect(x + 560, yy, 110, 26), lab, (lambda it=it: s.use_item(it)))
                s.btn(pg.Rect(x + 680, yy, 30, 26), "X", (lambda it=it: (p.inv.remove(it), s.clamp())))
            s.btn(pg.Rect(x, R.bottom - 56, 120, 34), "+ Item", lambda: p.inv.append(dict(name="Novo item", type="misc", qty=1, val=0, kind="melee", eq=False)))
            s.txt("Valor = cura (poções) ou bônus de dano (armas equipadas somam ao tipo correspondente).", x + 140, R.bottom - 46, 18, (160, 165, 190))
            s.txt(f"Ouro: {p.gold}", R.right - 120, R.bottom - 46, 22, (255, 225, 140))

    def draw(s):
        s.W, s.H = s.scr.get_size(); s.hits, s.tip = [], None
        if s.mode == 'menu': s.draw_menu()
        elif s.mode == 'help': s.draw_help()
        else:
            s.draw_world(); s.draw_fx(); s.draw_hud()
            if s.panel: s.draw_panel()
            if s.player.dead:
                s.txt("VOCÊ CAIU", s.W // 2, s.H // 2 - 20, 80, (230, 60, 60), center=True, out=True)
                s.txt("Pressione R para reviver", s.W // 2, s.H // 2 + 30, 30, center=True, out=True)
        if s.toast_t > 0 and s.mode == 'play': s.txt(s.toast, s.W // 2, s.H - 130 if not s.combat else 90, 26, (255, 255, 255), center=True, out=True)
        if s.tip:
            mx, my = pg.mouse.get_pos(); w = max(s.font(19).size(t)[0] for t in s.tip) + 16; r = pg.Rect(mx + 14, my - 14 - 24 * len(s.tip), w, 8 + 24 * len(s.tip))
            r.clamp_ip(s.scr.get_rect()); pg.draw.rect(s.scr, (12, 12, 20), r, border_radius=5); pg.draw.rect(s.scr, (150, 150, 190), r, 1, border_radius=5)
            for i, t in enumerate(s.tip): s.txt(t, r.x + 8, r.y + 6 + i * 24, 19)


def main():
    pg.init(); scr = pg.display.set_mode((1280, 720), pg.RESIZABLE); pg.display.set_caption("Grid Quest")
    g, clock = Game(scr), pg.time.Clock()
    while not g.quit:
        dt = min(clock.tick(60) / 1000, .05)
        for e in pg.event.get(): g.handle(e)
        g.update(dt); g.draw(); pg.display.flip()
    pg.quit()


if __name__ == "__main__":
    main()
