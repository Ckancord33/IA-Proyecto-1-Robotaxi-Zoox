"""
Clase base de todos los algoritmos de búsqueda.

Define la interfaz común que debe cumplir cualquier algoritmo.
Los algoritmos solo interactúan con Problem — nunca con World directamente.
"""

from abc import ABC, abstractmethod
from models.problem import Problem
from models.node import Node
from models.state import State
from utils.result import Result


class Algorithm(ABC):

    def __init__(self, problem: Problem):
        self.problem = problem

    @abstractmethod
    def solve(self) -> Result:
        """
        Ejecuta la búsqueda y devuelve un SearchResult.
        Cada subclase implementa su propia estrategia.
        """
        ...

    # ------------------------------------------------------------------
    # Utilidades comunes para todos los algoritmos
    # ------------------------------------------------------------------

    def _make_root(self) -> Node:
        """Construye el nodo raíz a partir del estado inicial del problema."""
        return Node(
            state=self.problem.initial_state(),
            parent=None,
            action=None,
            cost=0.0,
            depth=0
        )

    def _expand(self, node: Node) -> list[Node]:
        """
        Expande un nodo generando todos sus hijos válidos.
        Este método es igual para todos los algoritmos — lo que cambia
        es el orden en que se agregan a la frontera.
        """
        children = []
        for action in self.problem.actions(node.state):
            new_state = self.problem.result(node.state, action)
            new_cost  = node.cost + self.problem.step_cost(node.state, action)
            new_depth = node.depth + 1
            child = Node(
                state=new_state,
                parent=node,
                action=action,
                cost=new_cost,
                depth=new_depth
            )
            children.append(child)
        return children