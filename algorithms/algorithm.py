"""
Clase base de todos los algoritmos de búsqueda.

Define la interfaz común que debe cumplir cualquier algoritmo.
Los algoritmos solo interactúan con Problem — nunca con World directamente.
"""

from abc import ABC, abstractmethod
import time
from typing import Callable
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

    def _make_progress_reporter(
        self,
        algorithm_name: str,
        start_time: float,
        progress_callback: Callable[[dict], bool] | None = None,
        progress_interval: float = 1.0,
    ):
        """
        Crea un emisor de progreso reutilizable para cualquier algoritmo.

        Uso:
          emit = self._make_progress_reporter(...)
          keep_running = emit(nodes_expanded, frontier_size, force=False)

        Si progress_callback devuelve False, se interpreta como cancelacion.
        """
        interval = max(progress_interval, 0.05)
        next_progress_at = start_time + interval

        def emit(nodes_expanded: int, frontier_size: int, force: bool = False) -> bool:
            nonlocal next_progress_at

            if progress_callback is None:
                return True

            now = time.time()
            if not force and now < next_progress_at:
                return True

            payload = {
                "algorithm": algorithm_name,
                "nodes_expanded": nodes_expanded,
                "elapsed_time": now - start_time,
                "frontier_size": frontier_size,
            }
            keep_running = progress_callback(payload)
            next_progress_at = now + interval
            return keep_running is not False

        return emit

    def _cancelled_result(self, start_time: float, nodes_expanded: int, algorithm_name: str) -> Result:
        """Resultado estandar para cancelacion cooperativa."""
        return Result(
            solution=None,
            nodes_expanded=nodes_expanded,
            depth=0,
            cost=0.0,
            time=time.time() - start_time,
            algorithm=algorithm_name,
        )