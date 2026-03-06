"""
Estado del agente en el problema Robotaxi.

Un estado es la combinación de:
  - Posición actual del vehículo (row, col)
  - Qué pasajeros ya fueron recogidos (tupla de booleanos)

Ejemplo con 3 pasajeros:
  picked_up = (False, False, False) → ninguno recogido
  picked_up = (True,  False, False) → solo recogí pasajero 0
  picked_up = (True,  False, True)  → recogí pasajero 0 y 2
  picked_up = (True,  True,  True)  → todos recogidos
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    """
    Atributos
    ---------
    row      : fila actual del vehículo
    col      : columna actual del vehículo
    picked_up: tupla de booleanos, uno por pasajero.
               picked_up[i] == True significa que el pasajero i ya fue recogido.
               El índice i corresponde al pasajero i en World.passengers.
    """
    row: int
    col: int
    picked_up: tuple = ()

    # ------------------------------------------------------------------
    # Consultas sobre pasajeros
    # ------------------------------------------------------------------

    def has_picked_up(self, passenger_idx: int) -> bool:
        """¿Ya fue recogido el pasajero con ese índice?"""
        return self.picked_up[passenger_idx]

    def pick_up(self, passenger_idx: int) -> "State":
        """
        Devuelve un NUEVO estado con el pasajero recogido.
        No modifica el estado actual.

        Ejemplo:
          state.picked_up = (False, False, True)
          state.pick_up(1).picked_up → (False, True, True)
        """
        new_picked = list(self.picked_up)
        new_picked[passenger_idx] = True
        return State(self.row, self.col, tuple(new_picked))

    def all_picked_up(self) -> bool:
        """¿Fueron recogidos todos los pasajeros?"""
        return all(self.picked_up)

    def move_to(self, row: int, col: int) -> "State":
        """
        Devuelve un NUEVO estado en (row, col),
        conservando los pasajeros ya recogidos.
        """
        return State(row, col, self.picked_up)

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"State(pos=({self.row},{self.col}), "
            f"picked_up={self.picked_up})"
        )