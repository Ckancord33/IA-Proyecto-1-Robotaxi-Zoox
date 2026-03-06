"""
Nodo del árbol de búsqueda.

Un nodo NO es lo mismo que un estado. La diferencia es:
  - State → la situación del vehículo (posición + pasajeros)
  - Node  → un estado + información de cómo llegamos ahí

Ejemplo:
  El vehículo puede llegar a (2,3) por dos caminos distintos.
  El State es el mismo: State(2, 3, ...).
  Pero son dos Nodos distintos porque tienen diferente padre,
  diferente acción y diferente costo acumulado.

Esa información extra es lo que los algoritmos necesitan para:
  - Reconstruir el camino cuando encuentran la solución (parent)
  - Decidir qué nodo explorar primero (cost, depth)
"""

from dataclasses import dataclass, field
from models.state import State


@dataclass
class Node:
    """
    Atributos
    ---------
    state  : estado del vehículo en este nodo
    parent : nodo del que venimos, None si es el nodo raíz
    action : acción que produjo este nodo ("UP", "DOWN", "LEFT", "RIGHT")
             None si es el nodo raíz
    cost   : costo acumulado desde el nodo raíz hasta este nodo
    depth  : profundidad en el árbol (raíz = 0)
    """
    state:  State
    parent: "Node | None"  = field(default=None, repr=False)
    action: str   | None   = None
    cost:   float          = 0.0
    depth:  int            = 0

    def get_path(self) -> list["Node"]:
        """
        Reconstruye la lista de nodos desde la raíz hasta este nodo.
        Se usa cuando un algoritmo encuentra la solución.

        Ejemplo:
          nodo_final.get_path() → [raíz, nodo1, nodo2, ..., nodo_final]
        """
        path = []
        current = self
        while current is not None:
            path.append(current)
            current = current.parent
        path.reverse()
        return path

    def get_actions(self) -> list[str]:
        """
        Devuelve solo la lista de acciones desde la raíz hasta este nodo.

        Ejemplo:
          nodo_final.get_actions() → ["RIGHT", "RIGHT", "DOWN", "UP", ...]
        """
        return [node.action for node in self.get_path() if node.action is not None]

    def __repr__(self) -> str:
        return (
            f"Node(state={self.state}, "
            f"action={self.action}, "
            f"cost={self.cost}, "
            f"depth={self.depth})"
        )