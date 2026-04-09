"""
Búsqueda por Amplitud (BFS).

Estrategia: explorar primero los nodos más cercanos a la raíz.
Frontera  : cola FIFO — el primero en entrar es el primero en salir.

Garantías:
  - Completo  : siempre encuentra solución si existe
  - Óptimo    : solo si todos los costos son iguales (aquí NO es óptimo
                porque hay celdas con costo 1 y costo 7)
"""

import time
from collections import deque

from algorithms import Algorithm
from utils.result import Result


class BFS(Algorithm):

  def solve(self, config=1, progress_callback=None, progress_interval=1.0) -> Result:
    """
    Encuentra la solucion al problema por amplitud.

      - con config=1 el algoritmo usa una tabla hash donde almacena
        todos los estados visitados, asegurando que si cualquier rama
        ya visito un estado, otra no la repita.

      - con config != 1 el algoritmo solo revisa que el estado no se haya
        dado ya en su rama actual, recorriendola con is_in_branch.
    """
    start_time = time.time()
    algorithm_name = "BFS"
    nodes_expanded = 0

    if(config == 1):
      visited = set()
    queue = deque()

    root = self._make_root()
    if(config == 1):
      visited.add(root.state)
    queue.append(root)
    emit_progress = self._make_progress_reporter(
      algorithm_name=algorithm_name,
      start_time=start_time,
      progress_callback=progress_callback,
      progress_interval=progress_interval,
    )

    while queue:
      if not emit_progress(nodes_expanded=nodes_expanded, frontier_size=len(queue), force=False):
        return self._cancelled_result(start_time=start_time, nodes_expanded=nodes_expanded, algorithm_name=algorithm_name)

      node = queue.popleft()
      if(self.problem.goal_test(node.state)):
        emit_progress(nodes_expanded=nodes_expanded, frontier_size=len(queue), force=True)
        return Result(
          solution=node.get_path(),
          nodes_expanded=nodes_expanded,
          depth=node.depth,
          cost=node.cost,
          time=time.time() - start_time,
          algorithm=algorithm_name,
        )

      nodes_expanded += 1
      for child in self._expand(node):
        cond = False
        if(config == 1):
          cond = child.state in visited
        else:
          cond = self.problem.is_in_branch(child)
        if cond:
          continue
        if(config == 1):
          visited.add(child.state)
        queue.append(child)

      emit_progress(nodes_expanded=nodes_expanded, frontier_size=len(queue), force=False)

    emit_progress(nodes_expanded=nodes_expanded, frontier_size=0, force=True)
    
    return Result(
            solution=None,
            nodes_expanded=nodes_expanded,
            depth=0,
            cost=0.0,
            time=time.time() - start_time,
            algorithm=algorithm_name,
        )
        