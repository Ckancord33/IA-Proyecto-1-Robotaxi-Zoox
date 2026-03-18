"""
Representa el mapa del problema Robotaxi.

Responsabilidad única: almacenar los datos del mapa y responder
consultas sobre él (costos, muros, límites). No sabe nada de
búsqueda, estados ni nodos.

Convención de celdas:
    0 → vía libre           (costo 1)
    1 → muro                (no transitable)
    2 → punto de partida    (costo 1)
    3 → flujo vehicular alto (costo 7)
    4 → pasajero            (costo 1)
    5 → destino             (costo 1)
"""

CELL_FREE      = 0
CELL_WALL      = 1
CELL_START     = 2
CELL_HIGH      = 3
CELL_PASSENGER = 4
CELL_GOAL      = 5

COST_NORMAL = 1
COST_HIGH   = 7


class World:
    """
    Mapa inmutable del problema. Se crea una sola vez y nunca
    se modifica durante la búsqueda.

    Atributos
    ---------
    grid       : tuple[tuple[int]]        — mapa original, inmutable
    rows       : int
    cols       : int
    start      : tuple[int, int]          — (row, col) del vehículo
    goal       : tuple[int, int]          — (row, col) del destino
    passengers : tuple[tuple[int, int]]   — posiciones fijas de pasajeros
                                            el índice aquí == índice en el bitmask
    """

    def __init__(self, grid: list[list[int]]):
        # Convertir a tupla de tuplas para garantizar inmutabilidad
        self.grid = tuple(tuple(row) for row in grid)
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows > 0 else 0

        self.start      = self._find_first(CELL_START)
        self.goal       = self._find_first(CELL_GOAL)
        self.passengers = self._find_all(CELL_PASSENGER)

        self._validate()

    # ------------------------------------------------------------------
    # Consultas públicas
    # ------------------------------------------------------------------

    def in_bounds(self, row: int, col: int) -> bool:
        """¿Está la posición dentro del mapa?"""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_wall(self, row: int, col: int) -> bool:
        return self.grid[row][col] == CELL_WALL

    def is_passable(self, row: int, col: int) -> bool:
        """¿Puede el vehículo entrar a esta celda?"""
        return self.in_bounds(row, col) and not self.is_wall(row, col)

    def get_cost(self, row: int, col: int) -> int:
        """Costo de moverse HACIA esta celda."""
        return COST_HIGH if self.grid[row][col] == CELL_HIGH else COST_NORMAL

    def get_cell(self, row: int, col: int) -> int:
        return self.grid[row][col]

    def passenger_index(self, row: int, col: int) -> int:
        """
        Índice del pasajero en self.passengers para (row, col).
        Devuelve -1 si no hay pasajero ahí.
        Este índice es el bit que se activa en el bitmask del State.
        """
        pos = (row, col)
        for i, p in enumerate(self.passengers):
            if p == pos:
                return i
        return -1
    
    def passenger_position(self, idx: int):
        return self.passengers[idx]
    
    def manhatan_passenger(self, row: int, col:int, passenger_index: int):
        passenger_row, passenger_col = self.passengers[passenger_index]
        return abs(passenger_row - row) + abs(passenger_col - col)
    
    def manhatan_goal(self, row: int, col:int):
        goal_row, goal_col = self.goal
        return abs(goal_row - row) + abs(goal_col - col)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        lines = [f"World({self.rows}x{self.cols})"]
        lines.append(f"  start     : {self.start}")
        lines.append(f"  goal      : {self.goal}")
        lines.append(f"  passengers: {self.passengers}")
        lines.append("  grid:")
        for row in self.grid:
            lines.append("    " + " ".join(str(c) for c in row))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _find_first(self, cell_type: int) -> tuple | None:
        for r, row in enumerate(self.grid):
            for c, val in enumerate(row):
                if val == cell_type:
                    return (r, c)
        return None

    def _find_all(self, cell_type: int) -> tuple:
        return tuple(
            (r, c)
            for r, row in enumerate(self.grid)
            for c, val in enumerate(row)
            if val == cell_type
        )

    def _validate(self):
        if self.start is None:
            raise ValueError("El mapa no tiene punto de partida (valor 2).")
        if self.goal is None:
            raise ValueError("El mapa no tiene destino (valor 5).")