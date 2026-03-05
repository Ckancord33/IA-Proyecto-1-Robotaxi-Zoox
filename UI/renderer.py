"""UI/renderer.py  —  Interfaz grafica del Robotaxi (Zoox).

Muestra el mundo del problema con colores y simbolos para cada tipo
de celda, y permite navegar entre mapas con un selector lateral.
"""

import glob
import os
import sys

import pygame

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from models.world import (
    CELL_FREE, CELL_GOAL, CELL_HIGH, CELL_PASSENGER, CELL_START, CELL_WALL,
    World,
)
from utils.map_loader import load_world

# ── Layout ─────────────────────────────────────────────────────────────────────
WIN_W     = 980
WIN_H     = 720
HEADER_H  = 60
SIDEBAR_W = 230
PAD       = 14
MAX_CELL  = 70
MIN_CELL  = 20
FPS       = 60

# ── Palette (dark theme) ───────────────────────────────────────────────────────
C_BG          = ( 12,  14,  22)
C_PANEL       = ( 20,  23,  36)
C_BORDER      = ( 45,  50,  72)
C_ACCENT      = ( 64, 156, 255)
C_TEXT        = (215, 218, 230)
C_TEXT_DIM    = (110, 118, 140)
C_GRIDLINE    = ( 35,  38,  55)

# Road
C_ROAD        = ( 48,  52,  66)
C_ROAD_MARK   = ( 80,  88, 110)

# Wall
C_WALL_BG     = ( 22,  24,  34)
C_WALL_LINE   = ( 14,  16,  24)

# Start – robot taxi (green)
C_START_BG    = ( 20,  85,  30)
C_CAR_BODY    = ( 56, 172,  70)
C_CAR_ROOF    = ( 30, 115,  44)
C_CAR_WIN     = (172, 232, 240)
C_WHEEL       = ( 15,  15,  15)
C_HEADLIGHT   = (255, 230,  50)

# High traffic (orange)
C_HIGH_BG     = (145,  55,   5)
C_ARROW       = (255, 210,  60)

# Passenger (blue)
C_PASS_BG     = ( 10,  58, 148)
C_PASS_SKIN   = (255, 190, 140)
C_PASS_SHIRT  = ( 90, 170, 255)
C_PASS_PANTS  = ( 35,  75, 160)

# Goal (gold)
C_GOAL_BG     = (115,  78,   5)
C_GOAL_GOLD   = (210, 160,  20)
C_FLAG_R      = (210,  40,  40)
C_FLAG_W      = (245, 245, 245)
C_POLE        = (220, 220, 220)

# Sidebar buttons
C_BTN         = ( 28,  32,  52)
C_BTN_HOV     = ( 42,  50,  82)
C_BTN_ACT     = ( 18,  72, 148)
C_BTN_BORD    = ( 58,  68, 108)

LEGEND_DATA = [
    (CELL_FREE,      C_ROAD,     "Via libre",    "0"),
    (CELL_WALL,      C_WALL_BG,  "Muro",         "1"),
    (CELL_START,     C_START_BG, "Inicio",       "2"),
    (CELL_HIGH,      C_HIGH_BG,  "Alto trafico", "3"),
    (CELL_PASSENGER, C_PASS_BG,  "Pasajero",     "4"),
    (CELL_GOAL,      C_GOAL_BG,  "Destino",      "5"),
]


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _pill(surf, color, rect, r=5):
    pygame.draw.rect(surf, color, pygame.Rect(rect), border_radius=r)


# ── Cell renderers ─────────────────────────────────────────────────────────────

def draw_free(surf, rect):
    """Asphalt tile with dashed centre lane mark."""
    x, y, w, h = rect
    pygame.draw.rect(surf, C_ROAD, rect)
    dw = max(2, w // 8)
    dh = max(4, h // 3)
    pygame.draw.rect(surf, C_ROAD_MARK,
                     (x + w // 2 - dw // 2, y + h // 2 - dh // 2, dw, dh))


def draw_wall(surf, rect):
    """Brick-patterned wall tile."""
    x, y, w, h = rect
    pygame.draw.rect(surf, C_WALL_BG, rect)
    bh = max(5, h // 4)
    for row in range(5):
        ry = y + row * bh
        pygame.draw.line(surf, C_WALL_LINE, (x, ry), (x + w, ry), 1)
        off = (row % 2) * (w // 3)
        mx  = x + off + w // 3
        if x < mx < x + w:
            pygame.draw.line(surf, C_WALL_LINE,
                             (mx, ry), (mx, min(ry + bh, y + h)), 1)


def draw_start(surf, rect):
    """Top-down robot taxi (zona de inicio)."""
    x, y, w, h = rect
    pygame.draw.rect(surf, C_START_BG, rect)

    p  = max(4, w // 8)
    bx = x + p
    by = y + p
    bw = w - 2 * p
    bh = h - 2 * p

    # Car body
    _pill(surf, C_CAR_BODY, (bx, by, bw, bh), r=5)

    # Wheels at four body corners
    wr = max(3, w // 13)
    for wx, wy in [
        (bx - wr + 1,        by + 1),
        (bx + bw - wr - 1,   by + 1),
        (bx - wr + 1,        by + bh - 2 * wr - 1),
        (bx + bw - wr - 1,   by + bh - 2 * wr - 1),
    ]:
        pygame.draw.ellipse(surf, C_WHEEL, (wx, wy, 2 * wr, 2 * wr))

    # Cab / roof
    cpx = bx + bw // 5
    cpy = by + bh // 5
    cpw = bw - 2 * (bw // 5)
    cph = bh - 2 * (bh // 5)
    _pill(surf, C_CAR_ROOF, (cpx, cpy, cpw, cph), r=4)

    # Windscreen (top of cab)
    if cpw > 8 and cph > 5:
        pygame.draw.rect(surf, C_CAR_WIN,
                         (cpx + 3, cpy + 3, max(3, cpw - 6), max(2, cph // 2 - 2)),
                         border_radius=2)

    # Front headlights (top edge of body)
    hl = max(2, w // 14)
    pygame.draw.circle(surf, C_HEADLIGHT, (bx + bw // 4,     by + hl + 2), hl)
    pygame.draw.circle(surf, C_HEADLIGHT, (bx + 3 * bw // 4, by + hl + 2), hl)


def draw_high(surf, rect):
    """High-traffic tile with 4-directional arrows."""
    x, y, w, h = rect
    pygame.draw.rect(surf, C_HIGH_BG, rect)
    cx = x + w // 2
    cy = y + h // 2
    ah = max(7, h // 3)
    aw = max(4, w // 7)

    # Vertical shaft (↑↓)
    pygame.draw.rect(surf, C_ARROW, (cx - 2, cy - ah, 4, 2 * ah))
    pygame.draw.polygon(surf, C_ARROW,
                        [(cx, cy - ah - 7), (cx - 6, cy - ah), (cx + 6, cy - ah)])
    pygame.draw.polygon(surf, C_ARROW,
                        [(cx, cy + ah + 7), (cx - 6, cy + ah), (cx + 6, cy + ah)])

    # Horizontal shaft (←→)
    pygame.draw.rect(surf, C_ARROW, (cx - aw, cy - 2, 2 * aw, 4))
    pygame.draw.polygon(surf, C_ARROW,
                        [(cx - aw - 7, cy), (cx - aw, cy - 5), (cx - aw, cy + 5)])
    pygame.draw.polygon(surf, C_ARROW,
                        [(cx + aw + 7, cy), (cx + aw, cy - 5), (cx + aw, cy + 5)])


def draw_passenger(surf, rect):
    """Waiting passenger with suitcase."""
    x, y, w, h = rect
    pygame.draw.rect(surf, C_PASS_BG, rect)

    # Figure slightly left so suitcase fits
    cx = x + w * 5 // 12

    # Head
    hr = max(4, w // 9)
    hy = y + h // 5
    pygame.draw.circle(surf, C_PASS_SKIN, (cx, hy + hr), hr)

    # Torso
    topy = hy + 2 * hr
    tw   = max(6, w // 4)
    th   = max(6, h // 5)
    _pill(surf, C_PASS_SHIRT, (cx - tw // 2, topy, tw, th), r=2)

    # Legs
    ly  = topy + th
    lh  = max(4, h // 6)
    gap = max(2, w // 14)
    pygame.draw.rect(surf, C_PASS_PANTS, (cx - gap - 2, ly, 3, lh))
    pygame.draw.rect(surf, C_PASS_PANTS, (cx + gap - 1, ly, 3, lh))

    # Suitcase (right side)
    sx2 = cx + tw // 2 + 3
    sy2 = topy + 2
    sw2 = max(5, w // 8)
    sh2 = max(6, h // 6)
    _pill(surf, C_PASS_PANTS, (sx2, sy2, sw2, sh2), r=2)
    pygame.draw.rect(surf, C_PASS_SHIRT,
                     (sx2, sy2, sw2, sh2), width=1, border_radius=2)
    # Handle
    hw = max(1, sw2 - 4)
    pygame.draw.rect(surf, C_PASS_SHIRT, (sx2 + 2, sy2 - 2, hw, 2))


def draw_goal(surf, rect):
    """Destination tile: checkered flag + location pin."""
    x, y, w, h = rect
    pygame.draw.rect(surf, C_GOAL_BG, rect)

    # Flagpole
    px  = x + w // 3
    pt  = y + h // 8
    pb  = y + h - h // 8
    pygame.draw.line(surf, C_POLE, (px, pt), (px, pb), 2)

    # Checkered flag (3 cols × 3 rows)
    sq = max(3, w // 9)
    for fr in range(3):
        for fc in range(3):
            clr = C_FLAG_R if (fr + fc) % 2 == 0 else C_FLAG_W
            pygame.draw.rect(surf, clr,
                             (px + 2 + fc * sq, pt + fr * sq, sq, sq))

    # Location pin (bottom-right quadrant)
    pcx = x + (w * 2) // 3
    pcy = y + (h * 2) // 3
    pr  = max(5, w // 9)
    pygame.draw.circle(surf, C_GOAL_GOLD, (pcx, pcy), pr)
    pygame.draw.circle(surf, C_GOAL_BG,   (pcx, pcy), max(2, pr - 3))


CELL_DRAWERS = {
    CELL_FREE:      draw_free,
    CELL_WALL:      draw_wall,
    CELL_START:     draw_start,
    CELL_HIGH:      draw_high,
    CELL_PASSENGER: draw_passenger,
    CELL_GOAL:      draw_goal,
}


# ── Grid renderer ──────────────────────────────────────────────────────────────

def draw_grid(surf, world: World, ox: int, oy: int, csz: int):
    for r in range(world.rows):
        for c in range(world.cols):
            drawer = CELL_DRAWERS.get(world.get_cell(r, c), draw_free)
            drawer(surf, (ox + c * csz, oy + r * csz, csz, csz))

    gw = world.cols * csz
    gh = world.rows * csz

    for c in range(world.cols + 1):
        pygame.draw.line(surf, C_GRIDLINE,
                         (ox + c * csz, oy), (ox + c * csz, oy + gh))
    for r in range(world.rows + 1):
        pygame.draw.line(surf, C_GRIDLINE,
                         (ox, oy + r * csz), (ox + gw, oy + r * csz))

    pygame.draw.rect(surf, C_BORDER, (ox, oy, gw, gh), 2)


# ── Button widget ──────────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect, label: str, tag=None):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.tag     = tag
        self.hovered = False
        self.active  = False

    def draw(self, surf, font):
        bg = C_BTN_ACT if self.active else (C_BTN_HOV if self.hovered else C_BTN)
        tc = C_TEXT    if self.active else (C_TEXT     if self.hovered else C_TEXT_DIM)
        pygame.draw.rect(surf, bg,       self.rect, border_radius=6)
        pygame.draw.rect(surf, C_BTN_BORD, self.rect, width=1, border_radius=6)
        lbl = font.render(self.label, True, tc)
        surf.blit(lbl, lbl.get_rect(center=self.rect.center))

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


# ── Main viewer ────────────────────────────────────────────────────────────────

class MapViewer:
    def __init__(self, maps_dir: str = "maps"):
        pygame.init()
        pygame.display.set_caption("Robotaxi Zoox  -  World Viewer")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock  = pygame.time.Clock()

        self.font_lg = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_md = pygame.font.SysFont("segoeui", 15)
        self.font_sm = pygame.font.SysFont("segoeui", 13)

        self.maps_dir = maps_dir
        self._discover_maps()
        self.selected = 0
        self._load(0)
        self._build_buttons()

    # ── Map management ─────────────────────────────────────────────────────────

    def _discover_maps(self):
        for base in (self.maps_dir, os.path.join(_BASE, self.maps_dir)):
            paths = sorted(glob.glob(os.path.join(base, "*.txt")))
            if paths:
                self.map_paths = paths
                self.map_names = [
                    os.path.splitext(os.path.basename(p))[0] for p in paths
                ]
                return
        raise FileNotFoundError(f"No maps found in '{self.maps_dir}'")

    def _load(self, idx: int):
        grid = load_world(self.map_paths[idx])
        self.world = World(grid)

    def _select(self, idx: int):
        self.selected = idx
        self._load(idx)
        for btn in self.buttons:
            btn.active = (btn.tag == idx)

    # ── Buttons ────────────────────────────────────────────────────────────────

    def _build_buttons(self):
        bx  = WIN_W - SIDEBAR_W + PAD
        bw  = SIDEBAR_W - PAD * 2
        by0 = HEADER_H + PAD + 30
        bh  = 36
        gap = 8
        self.buttons: list[Button] = []
        for i, name in enumerate(self.map_names):
            b = Button((bx, by0 + i * (bh + gap), bw, bh),
                       name.capitalize(), tag=i)
            b.active = (i == self.selected)
            self.buttons.append(b)

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _cell_metrics(self):
        avw = WIN_W - SIDEBAR_W - PAD * 2
        avh = WIN_H - HEADER_H  - PAD * 2
        csz = min(avw // self.world.cols, avh // self.world.rows, MAX_CELL)
        csz = max(csz, MIN_CELL)
        ox  = PAD + (avw - self.world.cols * csz) // 2
        oy  = HEADER_H + PAD + (avh - self.world.rows * csz) // 2
        return csz, ox, oy

    # ── Drawing ────────────────────────────────────────────────────────────────

    def _draw_header(self):
        pygame.draw.rect(self.screen, C_PANEL, (0, 0, WIN_W, HEADER_H))
        pygame.draw.line(self.screen, C_BORDER,
                         (0, HEADER_H), (WIN_W, HEADER_H), 1)

        title = self.font_lg.render("ROBOTAXI  -  ZOOX", True, C_TEXT)
        sub   = self.font_sm.render("World Viewer", True, C_TEXT_DIM)
        tot_h = title.get_height() + 2 + sub.get_height()
        base  = (HEADER_H - tot_h) // 2
        self.screen.blit(title, (20, base))
        self.screen.blit(sub,   (20, base + title.get_height() + 2))

        info = self.font_sm.render(
            f"{self.world.rows}x{self.world.cols}  |  "
            f"{len(self.world.passengers)} pasajero(s)",
            True, C_TEXT_DIM)
        self.screen.blit(info, info.get_rect(
            midright=(WIN_W - SIDEBAR_W - PAD, HEADER_H // 2)))

    def _draw_sidebar(self):
        sx = WIN_W - SIDEBAR_W
        pygame.draw.rect(self.screen, C_PANEL,  (sx, 0, SIDEBAR_W, WIN_H))
        pygame.draw.line(self.screen, C_BORDER, (sx, 0), (sx, WIN_H), 1)

        # Maps section
        lbl = self.font_md.render("MAPAS", True, C_ACCENT)
        self.screen.blit(lbl, (sx + PAD, HEADER_H + PAD))
        for btn in self.buttons:
            btn.draw(self.screen, self.font_md)

        # Separator
        n   = len(self.buttons)
        sep = HEADER_H + PAD + 30 + n * (36 + 8) + 12
        pygame.draw.line(self.screen, C_BORDER,
                         (sx + PAD, sep), (sx + SIDEBAR_W - PAD, sep), 1)

        # Legend section
        ly   = sep + 12
        lbl2 = self.font_md.render("LEYENDA", True, C_ACCENT)
        self.screen.blit(lbl2, (sx + PAD, ly))
        ly  += lbl2.get_height() + 8

        sq = 16
        for (_, color, name, code) in LEGEND_DATA:
            pygame.draw.rect(self.screen, color,
                             (sx + PAD, ly, sq, sq), border_radius=3)
            pygame.draw.rect(self.screen, C_BORDER,
                             (sx + PAD, ly, sq, sq), width=1, border_radius=3)
            midy = ly + sq // 2
            txt  = self.font_sm.render(name, True, C_TEXT)
            ctxt = self.font_sm.render(f"[{code}]", True, C_TEXT_DIM)
            self.screen.blit(txt,  txt.get_rect( midleft=(sx + PAD + sq + 5, midy)))
            self.screen.blit(ctxt, ctxt.get_rect(midright=(sx + SIDEBAR_W - PAD, midy)))
            ly += sq + 7

        # Keyboard hint
        hint = self.font_sm.render("<- / -> cambiar mapa", True, C_TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(
            midbottom=(sx + SIDEBAR_W // 2, WIN_H - 12)))

    # ── Main loop ──────────────────────────────────────────────────────────────

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                        self._select((self.selected + 1) % len(self.map_paths))
                    elif event.key in (pygame.K_LEFT, pygame.K_UP):
                        self._select((self.selected - 1) % len(self.map_paths))
                for btn in self.buttons:
                    if btn.handle_event(event):
                        self._select(btn.tag)

            self.screen.fill(C_BG)
            csz, ox, oy = self._cell_metrics()
            draw_grid(self.screen, self.world, ox, oy, csz)
            self._draw_sidebar()
            self._draw_header()
            pygame.display.flip()
            self.clock.tick(FPS)


# ── Entry point ────────────────────────────────────────────────────────────────

def launch(maps_dir: str = "maps"):
    """Abre la ventana del World Viewer. Llamar desde main.py."""
    MapViewer(maps_dir).run()
