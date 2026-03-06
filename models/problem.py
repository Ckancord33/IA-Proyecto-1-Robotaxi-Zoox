# models/problem.py
"""
Reglas del problema Robotaxi.

Esta clase es el puente entre el mapa (World) y los algoritmos.
Los algoritmos NUNCA tocan World directamente — solo llaman métodos
de Problem.

Responsabilidades:
  - Construir el estado inicial
  - Decir qué acciones son válidas en cada estado
  - Producir el nuevo estado resultado de una acción
  - Evaluar si un estado es el goal
  - Calcular el costo de un movimiento
  - Estimar el costo restante (heurística)
"""

from models.world import World
from models.state import State
from models.node import Node


# Movimientos posibles y su efecto en (row, col)
ACTIONS = {
    "UP":    (-1,  0),
    "DOWN":  ( 1,  0),
    "LEFT":  ( 0, -1),
    "RIGHT": ( 0,  1),
}


class Problem:

    def __init__(self, world: World):
        self.world = world

    # ------------------------------------------------------------------
    # Interfaz que usan los algoritmos
    # ------------------------------------------------------------------

    def initial_state(self) -> State:
        """
        Estado inicial: vehículo en el punto de partida,
        ningún pasajero recogido.
        """
        return State(
            row=self.world.start[0],
            col=self.world.start[1],
            picked_up=tuple(False for _ in self.world.passengers)
        )

    def actions(self, state: State) -> list[str]:
        """
        Devuelve las acciones válidas desde este estado.
        Una acción es válida si la celda destino existe y no es muro.
        """
        valid = []
        for action, (dr, dc) in ACTIONS.items():
            new_row = state.row + dr
            new_col = state.col + dc
            if self.world.is_passable(new_row, new_col):
                valid.append(action)
        return valid

    def result(self, state: State, action: str) -> State:
        """
        Aplica una acción a un estado y devuelve el nuevo estado.

        Si en la celda destino hay un pasajero que aún no fue recogido,
        automáticamente se sube al vehículo.
        """
        dr, dc = ACTIONS[action]
        new_row = state.row + dr
        new_col = state.col + dc

        # Mover el vehículo conservando pasajeros recogidos
        new_state = state.move_to(new_row, new_col)

        # Si hay un pasajero en esa celda y no fue recogido aún, recogerlo
        passenger_idx = self.world.passenger_index(new_row, new_col)
        if passenger_idx != -1 and not new_state.has_picked_up(passenger_idx):
            new_state = new_state.pick_up(passenger_idx)

        return new_state

    def goal_test(self, state: State) -> bool:
        """
        El goal se cumple cuando:
          1. Todos los pasajeros fueron recogidos
          2. El vehículo está en el destino
        """
        at_goal = (state.row, state.col) == self.world.goal
        return at_goal and state.all_picked_up()

    def step_cost(self, state: State, action: str) -> int:
        """
        Costo de ejecutar una acción desde un estado.
        Depende de la celda a la que se llega, no de la que se sale.
        """
        dr, dc = ACTIONS[action]
        new_row = state.row + dr
        new_col = state.col + dc
        return self.world.get_cost(new_row, new_col)