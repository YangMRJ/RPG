"""
Constants and global configuration for Curse of Strahd VTT
"""

# ── Window ──────────────────────────────────────────────────────────────────
DEFAULT_WIDTH  = 1280
DEFAULT_HEIGHT = 720
MIN_WIDTH      = 800
MIN_HEIGHT     = 600
TITLE          = "Curse of Strahd — VTT"
TARGET_FPS     = 60

# ── Scenes ───────────────────────────────────────────────────────────────────
SCENE_MENU        = "menu"
SCENE_PLAY_SELECT = "play_select"
SCENE_LOBBY       = "lobby"
SCENE_CHARACTERS  = "characters"
SCENE_CHAR_CREATE = "char_create"
SCENE_COMPENDIUM  = "compendium"
SCENE_OPTIONS     = "options"

# ── Color Palette (gothic / Barovia) ────────────────────────────────────────
C_BG          = (10,  6,  14)       # near-black purple
C_BG2         = (18, 12, 24)        # slightly lighter
C_PANEL       = (22, 15, 30)        # panel bg
C_PANEL_DARK  = (14,  9, 20)        # darker panel
C_BORDER      = (80, 40, 60)        # muted crimson border
C_BORDER_HOV  = (160, 60, 80)       # hover border
C_BORDER_SEL  = (220, 80, 90)       # selected/active border

C_TEXT        = (210, 195, 175)     # parchment
C_TEXT_DIM    = (110, 95,  80)      # dimmed text
C_TEXT_BRIGHT = (240, 225, 200)     # bright parchment
C_TEXT_ACCENT = (200,  70,  70)     # blood-red accent

C_GOLD        = (180, 145,  60)     # aged gold
C_GOLD_BRIGHT = (220, 185,  90)
C_CRIMSON     = (160,  25,  35)
C_CRIMSON_HOV = (200,  40,  50)
C_SHADOW      = (  0,   0,   0, 180)

C_WHITE       = (255, 255, 255)
C_BLACK       = (  0,   0,   0)

# ── Typography sizes ─────────────────────────────────────────────────────────
FONT_TITLE    = 72
FONT_SUBTITLE = 28
FONT_MENU     = 32
FONT_BODY     = 18
FONT_SMALL    = 14

# ── Animations ───────────────────────────────────────────────────────────────
ANIM_SPEED    = 6.0    # general lerp speed
HOVER_GLOW    = 0.4    # seconds for glow pulse

# ── Network defaults ─────────────────────────────────────────────────────────
DEFAULT_PORT  = 5740
DEFAULT_HOST  = "0.0.0.0"

# ── Compendium categories ────────────────────────────────────────────────────
COMPENDIUM_SECTIONS = [
    ("A", "NPCs"),
    ("B", "Monstros"),
    ("C", "Itens"),
    ("D", "Magias"),
    ("E", "Raças"),
    ("F", "Classes"),
    ("G", "Antecedentes"),
    ("H", "Locais"),
    ("I", "Regras"),
]

# ── Resolutions ──────────────────────────────────────────────────────────────
RESOLUTIONS = [
    (800,  600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
]
