"""
Resultado de una búsqueda.
Es lo que todos los algoritmos devuelven al terminar.
"""

from dataclasses import dataclass
from models.node import Node


@dataclass
class Result:
    """
    Atributos
    ---------
    solution        : lista de nodos desde raíz hasta el goal,
                      None si no se encontró solución
    nodes_expanded  : cantidad de nodos expandidos durante la búsqueda
    depth           : profundidad del nodo solución
    cost            : costo acumulado de la solución
    time            : tiempo de cómputo en segundos
    """
    solution:       list[Node] | None
    nodes_expanded: int
    depth:          int
    cost:           float
    time:           float

    def found(self) -> bool:
        return self.solution is not None

    def get_actions(self) -> list[str]:
        """Lista de acciones de la solución. Útil para la animación."""
        if not self.found():
            return []
        return [node.action for node in self.solution if node.action is not None]

    def __repr__(self) -> str:
        if not self.found():
            return "SearchResult(sin solución)"
        return (
            f"SearchResult(\n"
            f"  acciones      : {self.get_actions()}\n"
            f"  nodos expandidos: {self.nodes_expanded}\n"
            f"  profundidad   : {self.depth}\n"
            f"  costo         : {self.cost}\n"
            f"  tiempo        : {self.time:.4f}s\n"
            f")"
        )