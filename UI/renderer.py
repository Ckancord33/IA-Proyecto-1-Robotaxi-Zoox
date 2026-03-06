"""UI/renderer.py  —  Interfaz grafica del Robotaxi (Zoox).

Muestra el mundo del problema con colores y simbolos para cada tipo
de celda, y permite navegar entre mapas con un selector lateral.
Incluye solver y animación del recorrido.
"""

import glob
import os
import sys
import time

import pygame

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from models.world import (
    CELL_FREE, CELL_GOAL, CELL_HIGH, CELL_PASSENGER, CELL_START, CELL_WALL,
    World,
)
from models.problem import Problem
from utils.map_loader import load_world
from utils.result import Result
from algorithms.breadth_first_search import BFS
# Importar otros algoritmos aquí en el futuro

# ── Layout ─────────────────────────────────────────────────────────────────────
WIN_W     = 1200
WIN_H     = 720
HEADER_H  = 60
SIDEBAR_W = 300
PAD       = 14
MAX_CELL  = 60
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
    _draw_car(surf, rect)


def _draw_car(surf, rect, highlight=False):
    """Dibuja el carro del robotaxi. Puede usarse para animación."""
    x, y, w, h = rect
    p  = max(4, w // 8)
    bx = x + p
    by = y + p
    bw = w - 2 * p
    bh = h - 2 * p

    # Car body (con highlight opcional para animación)
    car_color = (100, 220, 110) if highlight else C_CAR_BODY
    _pill(surf, car_color, (bx, by, bw, bh), r=5)

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

def draw_grid(surf, world: World, ox: int, oy: int, csz: int, 
              car_pos=None, picked_passengers=None, highlight_cell=None):
    """
    Dibuja el grid del mundo.
    
    car_pos: (row_float, col_float) posición del carro con interpolación
    picked_passengers: set de índices de pasajeros ya recogidos
    highlight_cell: (row, col) celda a resaltar durante animación
    """
    if picked_passengers is None:
        picked_passengers = set()
    
    for r in range(world.rows):
        for c in range(world.cols):
            cell_type = world.get_cell(r, c)
            
            # Si es pasajero y ya fue recogido, dibujar como celda libre
            if cell_type == CELL_PASSENGER:
                passenger_idx = world.passenger_index(r, c)
                if passenger_idx in picked_passengers:
                    cell_type = CELL_FREE
            
            drawer = CELL_DRAWERS.get(cell_type, draw_free)
            cell_rect = (ox + c * csz, oy + r * csz, csz, csz)
            drawer(surf, cell_rect)
            
            # Resaltar celda actual durante animación
            if highlight_cell and highlight_cell == (r, c):
                pygame.draw.rect(surf, (255, 255, 100), cell_rect, 3)
    
    # Dibujar el carro en su posición actual (si está animando)
    if car_pos:
        row_float, col_float = car_pos
        # Posición interpolada en píxeles
        car_x = ox + col_float * csz
        car_y = oy + row_float * csz
        car_rect = (car_x, car_y, csz, csz)
        
        # Dibujar fondo de la celda donde está el carro actualmente
        r_int, c_int = int(row_float), int(col_float)
        if 0 <= r_int < world.rows and 0 <= c_int < world.cols:
            cell_type = world.get_cell(r_int, c_int)
            if cell_type == CELL_HIGH:
                pygame.draw.rect(surf, C_HIGH_BG, car_rect)
            elif cell_type == CELL_GOAL:
                pygame.draw.rect(surf, C_GOAL_BG, car_rect)
            else:
                pygame.draw.rect(surf, C_ROAD, car_rect)
        
        # Luego dibujar el carro sobre la celda
        _draw_car(surf, car_rect, highlight=True)

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
        global WIN_W, WIN_H
        pygame.init()
        pygame.display.set_caption("Robotaxi Zoox  -  Solver & Animation")
        display_info = pygame.display.Info()
        # Permitir crecer hasta el tamano total de la pantalla (sin fullscreen).
        self.max_win_w = max(1000, display_info.current_w)
        self.max_win_h = max(620, display_info.current_h)
        self.min_win_w = 1000
        self.min_win_h = 620

        WIN_W = min(WIN_W, self.max_win_w)
        WIN_H = min(WIN_H, self.max_win_h)
        WIN_W = max(WIN_W, self.min_win_w)
        WIN_H = max(WIN_H, self.min_win_h)

        # Ventana redimensionable (sin fullscreen).
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
        self.clock  = pygame.time.Clock()

        self.font_lg = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_md = pygame.font.SysFont("segoeui", 15)
        self.font_sm = pygame.font.SysFont("segoeui", 13)
        self.font_xs = pygame.font.SysFont("consolas", 11)

        # Estado del solver, animación y log tipo terminal
        self.result: Result | None = None
        self.is_solving = False
        self.is_animating = False
        self.animation_step = 0
        self.animation_path = []
        self.animation_picked = set()
        self.animation_delay = 0  # Para simular tráfico alto
        
        # Variables para interpolación suave
        self.animation_progress = 0.0  # Progreso entre 0.0 y 1.0 de celda a celda
        self.animation_from_pos = None  # (row, col) origen
        self.animation_to_pos = None    # (row, col) destino
        self.animation_speed = 1.0      # Multiplicador de velocidad (0.5, 1.0, 1.5, 2.0)
        self.speed_options = [0.5, 1.0, 1.5, 2.0]
        self.speed_index = 1  # Índice actual (default 1.0x)
        
        self.log_messages = []
        self.log_scroll_offset = 0
        self.log_auto_follow = True
        
        # Estado de secciones desplegables
        self.maps_collapsed = False
        self.algorithms_collapsed = False
        self.log_collapsed = False
        self.maps_scroll_offset = 0
        self.algorithms_scroll_offset = 0
        
        # Áreas de scroll para detectar mouse
        self.maps_scroll_area = None
        self.algorithms_scroll_area = None
        self.log_scroll_area = None

        self.maps_dir = maps_dir
        self._discover_maps()
        self._discover_algorithms()
        self.selected = 0
        self.selected_algorithm = 0
        self._load(0)
        self._build_buttons()

        self._append_log("=== UI INICIADA ===", f"Mapa cargado: {self.map_names[self.selected]}")
        self._append_log(f"Algoritmo: {self.algorithm_names[self.selected_algorithm]}")
        self._append_log(
            f"Ventana redimensionable activa: min {self.min_win_w}x{self.min_win_h} | "
            f"max {self.max_win_w}x{self.max_win_h}"
        )
        self._append_log("Sidebar anclado a la derecha activado")

    def _apply_window_size(self, width: int, height: int):
        """Aplica tamaño con límites seguros y recalcula layout."""
        global WIN_W, WIN_H
        new_w = max(self.min_win_w, min(width, self.max_win_w))
        new_h = max(self.min_win_h, min(height, self.max_win_h))
        if new_w == WIN_W and new_h == WIN_H:
            return

        WIN_W, WIN_H = new_w, new_h
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
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
    
    def _discover_algorithms(self):
        """Descubre los algoritmos disponibles."""
        # Lista de algoritmos disponibles (nombre, clase)
        # En el futuro se pueden agregar más aquí
        self.algorithms = [
            ("BFS", BFS),
            # ("DFS", DFS),
            # ("UCS", UCS),
            # ("A*", AStar),
        ]
        self.algorithm_names = [name for name, _ in self.algorithms]
        self.algorithm_classes = [cls for _, cls in self.algorithms]

    def _load(self, idx: int):
        grid = load_world(self.map_paths[idx])
        self.world = World(grid)
        self.problem = Problem(self.world)
        # Resetear estado cuando se cambia de mapa
        self.result = None
        self.is_animating = False
        self.animation_step = 0
        self.animation_path = []
        self.animation_picked = set()

    def _select(self, idx: int):
        self.selected = idx
        self._load(idx)
        for btn in self.map_buttons:
            btn.active = (btn.tag == idx)
        self._append_log("", f"=== MAPA: {self.map_names[idx]} ===")
    
    def _select_algorithm(self, idx: int):
        """Selecciona un algoritmo."""
        self.selected_algorithm = idx
        self._append_log(f"Algoritmo seleccionado: {self.algorithm_names[idx]}")

    def _append_log(self, *lines: str):
        """Agrega líneas al historial del log (modo terminal)."""
        for line in lines:
            self.log_messages.append(str(line))

        # Si el usuario no está revisando historial, mantener vista al final.
        if self.log_auto_follow:
            self.log_scroll_offset = len(self.log_messages)
    
    # ── Solver y Animación ─────────────────────────────────────────────────────
    
    def _solve(self):
        """Ejecuta el algoritmo seleccionado y guarda el resultado."""
        algo_name = self.algorithm_names[self.selected_algorithm]
        self._append_log("", f"Calculando solución con {algo_name}...")
        self.is_solving = True
        
        try:
            algo_class = self.algorithm_classes[self.selected_algorithm]
            algorithm = algo_class(self.problem)
            self.result = algorithm.solve()
            
            if self.result.found():
                self._append_log(
                    "=== SOLUCIÓN ENCONTRADA ===",
                    f"Nodos expandidos: {self.result.nodes_expanded}",
                    f"Profundidad: {self.result.depth}",
                    f"Costo total: {self.result.cost}",
                    f"Tiempo: {self.result.time:.4f}s",
                    f"Acciones: {len(self.result.get_actions())}",
                    "",
                    "Presiona 'Animar' para ver el recorrido"
                )
            else:
                self._append_log(
                    "=== NO SE ENCONTRÓ SOLUCIÓN ===",
                    f"Nodos expandidos: {self.result.nodes_expanded}",
                    f"Tiempo: {self.result.time:.4f}s"
                )
        except Exception as e:
            self._append_log(
                "ERROR al calcular:",
                str(e)
            )
            self.result = None
        
        self.is_solving = False
    
    def _start_animation(self):
        """Inicia la animación del recorrido."""
        if not self.result or not self.result.found():
            self._append_log("Primero debes calcular una solución válida")
            return
        
        self.is_animating = True
        self.animation_step = 0
        self.animation_path = self.result.solution
        self.animation_picked = set()
        self.animation_delay = 0
        self.animation_progress = 0.0
        
        # Inicializar primera transición si hay al menos 2 nodos
        if len(self.animation_path) >= 2:
            state0 = self.animation_path[0].state
            state1 = self.animation_path[1].state
            self.animation_from_pos = (state0.row, state0.col)
            self.animation_to_pos = (state1.row, state1.col)
        elif len(self.animation_path) == 1:
            state0 = self.animation_path[0].state
            self.animation_from_pos = (state0.row, state0.col)
            self.animation_to_pos = (state0.row, state0.col)
        
        self._append_log(
            "=== ANIMANDO RECORRIDO ===",
            f"Velocidad: {self.animation_speed}x",
            "",
            "El carro está siguiendo el camino...",
        )
    
    def _update_animation(self):
        """Actualiza un paso de la animación con interpolación suave."""
        if not self.is_animating or not self.animation_path:
            return
        
        # Si hay delay (tráfico alto), esperar
        if self.animation_delay > 0:
            self.animation_delay -= 1
            return
        
        # Verificar si ya terminamos
        if self.animation_step >= len(self.animation_path) - 1:
            # Asegurar que llegamos a la posición final
            if self.animation_progress < 1.0:
                self.animation_progress = min(1.0, self.animation_progress + 0.03 * self.animation_speed)
            else:
                self.is_animating = False
                self.log_messages.append("")
                self.log_messages.append("¡Animación completada!")
                self.log_messages.append(f"Llegó a la meta con costo {self.result.cost}")
            return
        
        # Incrementar progreso de interpolación (más rápido según la velocidad)
        base_speed = 0.03  # Velocidad base de interpolación
        self.animation_progress += base_speed * self.animation_speed
        
        # Si llegamos al destino, avanzar al siguiente segmento
        if self.animation_progress >= 1.0:
            self.animation_progress = 0.0
            self.animation_step += 1
            
            if self.animation_step < len(self.animation_path):
                # Eventos al llegar a una nueva celda
                node = self.animation_path[self.animation_step]
                state = node.state
                pos = (state.row, state.col)
                
                # Verificar si recogemos un pasajero
                passenger_idx = self.world.passenger_index(state.row, state.col)
                if passenger_idx != -1 and passenger_idx not in self.animation_picked:
                    self.animation_picked.add(passenger_idx)
                    self.log_messages.append(f"✓ Pasajero {passenger_idx + 1} recogido!")
                
                # Verificar si estamos en tráfico alto (delay mayor)
                cell_type = self.world.get_cell(state.row, state.col)
                if cell_type == CELL_HIGH:
                    # Delay más corto, ajustado por velocidad
                    self.animation_delay = int(15 / self.animation_speed)
                    self.log_messages.append(f"⚠ Tráfico alto en ({state.row}, {state.col})")
                
                # Verificar si llegamos a la meta
                if pos == self.world.goal:
                    self.log_messages.append(f"★ ¡Llegó a la meta!")
                
                # Configurar siguiente transición
                if self.animation_step + 1 < len(self.animation_path):
                    state_from = self.animation_path[self.animation_step].state
                    state_to = self.animation_path[self.animation_step + 1].state
                    self.animation_from_pos = (state_from.row, state_from.col)
                    self.animation_to_pos = (state_to.row, state_to.col)
    
    def _get_interpolated_car_pos(self):
        """Retorna la posición interpolada del carro para dibujo suave."""
        if not self.is_animating or not self.animation_from_pos or not self.animation_to_pos:
            return None
        
        from_r, from_c = self.animation_from_pos
        to_r, to_c = self.animation_to_pos
        
        # Interpolación lineal
        t = self.animation_progress
        row_float = from_r + (to_r - from_r) * t
        col_float = from_c + (to_c - from_c) * t
        
        return (row_float, col_float)
    
    def _cycle_animation_speed(self):
        """Cambia la velocidad de animación al siguiente valor."""
        self.speed_index = (self.speed_index + 1) % len(self.speed_options)
        self.animation_speed = self.speed_options[self.speed_index]
        self._append_log(f"Velocidad de animación: {self.animation_speed}x")

    # ── Buttons ────────────────────────────────────────────────────────────────

    def _build_buttons(self):
        # Botones de mapas (más pequeños para el scroll)
        bx  = WIN_W - SIDEBAR_W + PAD
        bw  = SIDEBAR_W - PAD * 2 - 10  # Espacio para scrollbar visual
        bh  = 26  # Más pequeños
        gap = 4
        
        # Los botones se crearán dinámicamente en _draw_sidebar según el scroll
        self.map_buttons: list[Button] = []
        self.algorithm_buttons: list[Button] = []
        self.map_button_height = bh
        self.map_button_gap = gap
        self.map_button_x = bx
        self.map_button_width = bw
        
        # Botones de control (Calcular y Animar) - tamaño normal
        self.btn_solve = None
        self.btn_animate = None
        self.btn_speed = None
        self.btn_clear_log = None
        self.control_buttons = []

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _cell_metrics(self):
        avw = WIN_W - SIDEBAR_W - PAD * 2
        avh = WIN_H - HEADER_H - PAD * 2
        csz = min(avw // self.world.cols, avh // self.world.rows, MAX_CELL)
        csz = max(csz, MIN_CELL)
        ox  = PAD + (avw - self.world.cols * csz) // 2
        oy  = HEADER_H + PAD + (avh - self.world.rows * csz) // 2
        return csz, ox, oy

    # ── Drawing ────────────────────────────────────────────────────────────────

    def _draw_header(self):
        surf = self.screen
        pygame.draw.rect(surf, C_PANEL, (0, 0, WIN_W, HEADER_H))
        pygame.draw.line(surf, C_BORDER,
                         (0, HEADER_H), (WIN_W, HEADER_H), 1)

        title = self.font_lg.render("ROBOTAXI  -  ZOOX", True, C_TEXT)
        sub   = self.font_sm.render("World Viewer", True, C_TEXT_DIM)
        tot_h = title.get_height() + 2 + sub.get_height()
        base  = (HEADER_H - tot_h) // 2
        surf.blit(title, (20, base))
        surf.blit(sub,   (20, base + title.get_height() + 2))

        info = self.font_sm.render(
            f"{self.world.rows}x{self.world.cols}  |  "
            f"{len(self.world.passengers)} pasajero(s)",
            True, C_TEXT_DIM)
        surf.blit(info, info.get_rect(
            midright=(WIN_W - SIDEBAR_W - PAD, HEADER_H // 2)))

    def _draw_collapsible_header(self, surf, sx, y, title, collapsed, show_clear_button=False):
        """Dibuja un header desplegable y retorna el rect del área clickeable."""
        header_h = 28
        header_rect = pygame.Rect(sx + PAD, y, SIDEBAR_W - PAD * 2, header_h)
        
        # Fondo del header
        pygame.draw.rect(surf, C_BTN, header_rect, border_radius=4)
        pygame.draw.rect(surf, C_BORDER, header_rect, width=1, border_radius=4)
        
        # Icono de expandir/colapsar
        icon = "▼" if not collapsed else "▶"
        icon_surf = self.font_sm.render(icon, True, C_ACCENT)
        surf.blit(icon_surf, (sx + PAD + 6, y + 7))
        
        # Título
        lbl = self.font_md.render(title, True, C_ACCENT)
        surf.blit(lbl, (sx + PAD + 22, y + 5))
        
        # Botón de limpiar (solo para log)
        clear_btn_rect = None
        if show_clear_button:
            btn_w = 50
            btn_h = 20
            btn_x = sx + SIDEBAR_W - PAD - btn_w - 2
            btn_y = y + 4
            clear_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            
            # Detectar hover
            mx, my = pygame.mouse.get_pos()
            is_hovered = clear_btn_rect.collidepoint(mx, my)
            btn_color = C_BTN_HOV if is_hovered else (35, 38, 50)
            
            pygame.draw.rect(surf, btn_color, clear_btn_rect, border_radius=3)
            pygame.draw.rect(surf, C_BORDER, clear_btn_rect, width=1, border_radius=3)
            
            clear_text = self.font_xs.render("Limpiar", True, C_TEXT_DIM)
            text_rect = clear_text.get_rect(center=clear_btn_rect.center)
            surf.blit(clear_text, text_rect)
            
            self.btn_clear_log = clear_btn_rect
        
        return header_rect
    
    def _draw_sidebar(self):
        surf = self.screen
        sx = WIN_W - SIDEBAR_W
        pygame.draw.rect(surf, C_PANEL,  (sx, 0, SIDEBAR_W, WIN_H))
        pygame.draw.line(surf, C_BORDER, (sx, 0), (sx, WIN_H), 1)
        
        current_y = HEADER_H + PAD
        
        # ═══ SECCIÓN MAPAS (desplegable con scroll) ═══
        self.maps_header_rect = self._draw_collapsible_header(
            surf, sx, current_y, "MAPAS", self.maps_collapsed
        )
        current_y += 32
        
        if not self.maps_collapsed:
            # Área disponible para mapas (límite fijo)
            maps_area_height = 160
            maps_area_rect = pygame.Rect(sx + PAD, current_y, SIDEBAR_W - PAD * 2, maps_area_height)
            self.maps_scroll_area = maps_area_rect
            
            # Crear superficie de recorte para scroll
            clip_rect = surf.get_clip()
            surf.set_clip(maps_area_rect)
            
            # Calcular scroll
            bh = self.map_button_height
            gap = self.map_button_gap
            total_maps_height = len(self.map_names) * (bh + gap)
            max_scroll = max(0, total_maps_height - maps_area_height)
            self.maps_scroll_offset = max(0, min(self.maps_scroll_offset, max_scroll))
            
            # Dibujar botones de mapas
            self.map_buttons.clear()
            for i, name in enumerate(self.map_names):
                by = current_y + i * (bh + gap) - self.maps_scroll_offset
                # Solo dibujar si está visible
                if by + bh >= current_y and by < current_y + maps_area_height:
                    b = Button(
                        (self.map_button_x, by, self.map_button_width, bh),
                        name.capitalize(), tag=i
                    )
                    b.active = (i == self.selected)
                    b.draw(surf, self.font_sm)
                    self.map_buttons.append(b)
            
            # Restaurar clip
            surf.set_clip(clip_rect)
            
            # Dibujar scrollbar si es necesario
            if total_maps_height > maps_area_height:
                scrollbar_h = max(20, (maps_area_height / total_maps_height) * maps_area_height)
                scrollbar_y = current_y + (self.maps_scroll_offset / max_scroll) * (maps_area_height - scrollbar_h)
                pygame.draw.rect(surf, C_BORDER,
                               (sx + SIDEBAR_W - PAD - 6, scrollbar_y, 4, scrollbar_h),
                               border_radius=2)
            
            current_y += maps_area_height + 8
        else:
            # Si está colapsado, limpiar botones y área de scroll
            self.map_buttons.clear()
            self.maps_scroll_area = None
        
        # Separador
        pygame.draw.line(surf, C_BORDER,
                        (sx + PAD, current_y), (sx + SIDEBAR_W - PAD, current_y), 1)
        current_y += 12
        
        # ═══ SECCIÓN ALGORITMOS (desplegable con scroll) ═══
        self.algorithms_header_rect = self._draw_collapsible_header(
            surf, sx, current_y, "ALGORITMOS", self.algorithms_collapsed
        )
        current_y += 32
        
        if not self.algorithms_collapsed:
            # Área disponible para algoritmos (límite fijo)
            algorithms_area_height = 120
            algorithms_area_rect = pygame.Rect(sx + PAD, current_y, SIDEBAR_W - PAD * 2, algorithms_area_height)
            self.algorithms_scroll_area = algorithms_area_rect
            
            # Crear superficie de recorte para scroll
            clip_rect = surf.get_clip()
            surf.set_clip(algorithms_area_rect)
            
            # Calcular scroll
            bh = self.map_button_height
            gap = self.map_button_gap
            total_algorithms_height = len(self.algorithm_names) * (bh + gap)
            max_scroll = max(0, total_algorithms_height - algorithms_area_height)
            self.algorithms_scroll_offset = max(0, min(self.algorithms_scroll_offset, max_scroll))
            
            # Dibujar botones de algoritmos
            self.algorithm_buttons.clear()
            for i, name in enumerate(self.algorithm_names):
                by = current_y + i * (bh + gap) - self.algorithms_scroll_offset
                # Solo dibujar si está visible
                if by + bh >= current_y and by < current_y + algorithms_area_height:
                    b = Button(
                        (self.map_button_x, by, self.map_button_width, bh),
                        name, tag=i
                    )
                    b.active = (i == self.selected_algorithm)
                    b.draw(surf, self.font_sm)
                    self.algorithm_buttons.append(b)
            
            # Restaurar clip
            surf.set_clip(clip_rect)
            
            # Dibujar scrollbar si es necesario
            if total_algorithms_height > algorithms_area_height:
                scrollbar_h = max(20, (algorithms_area_height / total_algorithms_height) * algorithms_area_height)
                scrollbar_y = current_y + (self.algorithms_scroll_offset / max_scroll) * (algorithms_area_height - scrollbar_h)
                pygame.draw.rect(surf, C_BORDER,
                               (sx + SIDEBAR_W - PAD - 6, scrollbar_y, 4, scrollbar_h),
                               border_radius=2)
            
            current_y += algorithms_area_height + 8
        else:
            # Si está colapsado, limpiar botones y área de scroll
            self.algorithm_buttons.clear()
            self.algorithms_scroll_area = None
        
        # Separador
        pygame.draw.line(surf, C_BORDER,
                        (sx + PAD, current_y), (sx + SIDEBAR_W - PAD, current_y), 1)
        current_y += 12
        
        # ═══ SECCIÓN CONTROLES (siempre visible) ═══
        lbl_ctrl = self.font_md.render("CONTROLES", True, C_ACCENT)
        surf.blit(lbl_ctrl, (sx + PAD, current_y))
        current_y += lbl_ctrl.get_height() + 8
        
        # Botones de control
        bx = sx + PAD
        bw = SIDEBAR_W - PAD * 2
        bh = 32
        gap = 6
        
        self.btn_solve = Button(
            (bx, current_y, bw, bh),
            "Calcular Solución",
            tag="solve"
        )
        self.btn_solve.draw(surf, self.font_sm)
        current_y += bh + gap
        
        self.btn_animate = Button(
            (bx, current_y, bw, bh),
            "Animar",
            tag="animate"
        )
        self.btn_animate.draw(surf, self.font_sm)
        current_y += bh + gap
        
        # Botón de velocidad
        speed_label = f"Velocidad: {self.animation_speed}x"
        self.btn_speed = Button(
            (bx, current_y, bw, bh),
            speed_label,
            tag="speed"
        )
        self.btn_speed.draw(surf, self.font_sm)
        current_y += bh + 12
        
        self.control_buttons = [self.btn_solve, self.btn_animate, self.btn_speed]
        
        # Separador
        pygame.draw.line(surf, C_BORDER,
                        (sx + PAD, current_y), (sx + SIDEBAR_W - PAD, current_y), 1)
        current_y += 12
        
        # ═══ SECCIÓN LOG (desplegable con scroll) ═══
        self.log_header_rect = self._draw_collapsible_header(
            surf, sx, current_y, "LOG / RESULTADO", self.log_collapsed, show_clear_button=True
        )
        current_y += 32
        
        if not self.log_collapsed:
            # Área disponible para log (hasta el final menos hint)
            log_area_height = WIN_H - current_y - 30
            log_area_rect = pygame.Rect(sx + PAD, current_y, SIDEBAR_W - PAD * 2, log_area_height)
            self.log_scroll_area = log_area_rect
            
            # Crear superficie de recorte
            clip_rect = surf.get_clip()
            surf.set_clip(log_area_rect)
            
            line_height = 13
            max_visible_lines = int(log_area_height / line_height)
            
            # Calcular scroll
            total_lines = len(self.log_messages)
            max_start_idx = max(0, total_lines - max_visible_lines)
            if self.log_auto_follow:
                self.log_scroll_offset = max_start_idx
            else:
                self.log_scroll_offset = max(0, min(self.log_scroll_offset, max_start_idx))
                if self.log_scroll_offset >= max_start_idx:
                    self.log_auto_follow = True
            
            start_idx = self.log_scroll_offset
            end_idx = min(start_idx + max_visible_lines, total_lines)
            
            # Dibujar mensajes
            for i, msg in enumerate(self.log_messages[start_idx:end_idx]):
                msg_surf = self.font_xs.render(msg, True, C_TEXT)
                surf.blit(msg_surf, (sx + PAD + 3, current_y + i * line_height))
            
            # Restaurar clip
            surf.set_clip(clip_rect)
            
            # Dibujar scrollbar si es necesario
            if total_lines > max_visible_lines:
                scrollbar_h = max(20, (max_visible_lines / total_lines) * log_area_height)
                scrollbar_y = current_y + (self.log_scroll_offset / max_start_idx) * (log_area_height - scrollbar_h) if max_start_idx > 0 else current_y
                pygame.draw.rect(surf, C_BORDER,
                               (sx + SIDEBAR_W - PAD - 6, scrollbar_y, 4, scrollbar_h),
                               border_radius=2)
        else:
            # Si está colapsado, limpiar área de scroll
            self.log_scroll_area = None
        
        # Keyboard hint
        hint = self.font_sm.render("<- / -> cambiar mapa", True, C_TEXT_DIM)
        surf.blit(hint, hint.get_rect(
            midbottom=(sx + SIDEBAR_W // 2, WIN_H - 12)))

    def _clear_log(self):
        """Limpia todos los mensajes del log."""
        self.log_messages.clear()
        self.log_scroll_offset = 0
        self.log_auto_follow = True
        self._append_log("=== Log limpiado ===")
    
    def _handle_scroll(self, event):
        """Maneja el scroll en las áreas del sidebar (mapas, algoritmos y log)."""
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            
            # Scroll en área de mapas
            if self.maps_scroll_area and self.maps_scroll_area.collidepoint(mx, my):
                self.maps_scroll_offset -= event.y * 15  # Scroll más rápido
                return
            
            # Scroll en área de algoritmos
            if self.algorithms_scroll_area and self.algorithms_scroll_area.collidepoint(mx, my):
                self.algorithms_scroll_offset -= event.y * 15
                return
            
            # Scroll en área de log
            if self.log_scroll_area and self.log_scroll_area.collidepoint(mx, my):
                self.log_scroll_offset -= event.y * 3
                self.log_scroll_offset = max(0, min(self.log_scroll_offset, len(self.log_messages)))
                if event.y > 0:
                    self.log_auto_follow = False
                return
    
    def _handle_collapsible_click(self, event):
        """Maneja clicks en los headers desplegables."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Primero verificar si el click fue en el botón de limpiar log
            if self.btn_clear_log and self.btn_clear_log.collidepoint(event.pos):
                return False  # No procesar como click en header
            
            if hasattr(self, 'maps_header_rect') and self.maps_header_rect.collidepoint(event.pos):
                self.maps_collapsed = not self.maps_collapsed
                return True
            if hasattr(self, 'algorithms_header_rect') and self.algorithms_header_rect.collidepoint(event.pos):
                self.algorithms_collapsed = not self.algorithms_collapsed
                return True
            if hasattr(self, 'log_header_rect') and self.log_header_rect.collidepoint(event.pos):
                self.log_collapsed = not self.log_collapsed
                return True
        return False

    # ── Main loop ──────────────────────────────────────────────────────────────

    def run(self):
        while True:
            # Limpiar botones de secciones colapsadas ANTES de procesar eventos
            if self.maps_collapsed:
                self.map_buttons.clear()
                self.maps_scroll_area = None
            if self.algorithms_collapsed:
                self.algorithm_buttons.clear()
                self.algorithms_scroll_area = None
            if self.log_collapsed:
                self.log_scroll_area = None
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    self._apply_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                        self._select((self.selected + 1) % len(self.map_paths))
                    elif event.key in (pygame.K_LEFT, pygame.K_UP):
                        self._select((self.selected - 1) % len(self.map_paths))
                
                # Manejar click en botón de limpiar log (ANTES de headers para evitar conflicto)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_clear_log and self.btn_clear_log.collidepoint(event.pos):
                        self._clear_log()
                        continue  # No procesar más este evento
                
                # Manejar clicks en headers desplegables
                if self._handle_collapsible_click(event):
                    continue
                
                # Manejar clicks en botones de mapas (solo si no está colapsado)
                if not self.maps_collapsed:
                    for btn in self.map_buttons:
                        if btn.handle_event(event):
                            self._select(btn.tag)
                
                # Manejar clicks en botones de algoritmos (solo si no está colapsado)
                if not self.algorithms_collapsed:
                    for btn in self.algorithm_buttons:
                        if btn.handle_event(event):
                            self._select_algorithm(btn.tag)
                
                # Manejar clicks en botones de control
                if self.btn_solve and self.btn_solve.handle_event(event):
                    if not self.is_solving and not self.is_animating:
                        self._solve()
                
                if self.btn_animate and self.btn_animate.handle_event(event):
                    if not self.is_animating and not self.is_solving:
                        self._start_animation()
                
                if self.btn_speed and self.btn_speed.handle_event(event):
                    self._cycle_animation_speed()
                
                # Manejar scroll en sidebar
                self._handle_scroll(event)

            # Actualizar animación si está activa
            if self.is_animating:
                self._update_animation()

            # Dibujar todo
            self.screen.fill(C_BG)
            
            csz, ox, oy = self._cell_metrics()
            
            # Obtener posición interpolada del carro
            car_pos = self._get_interpolated_car_pos()
            
            draw_grid(self.screen, self.world, ox, oy, csz,
                     car_pos=car_pos, 
                     picked_passengers=self.animation_picked)
            
            self._draw_sidebar()
            self._draw_header()
            
            pygame.display.flip()
            self.clock.tick(FPS)


# ── Entry point ────────────────────────────────────────────────────────────────

def launch(maps_dir: str = "maps"):
    """Abre la ventana del World Viewer. Llamar desde main.py."""
    MapViewer(maps_dir).run()
