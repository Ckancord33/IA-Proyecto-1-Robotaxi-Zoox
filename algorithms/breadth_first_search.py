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

  def solve(self, config=1) -> Result:
    """
    Encuentra la solucion al problema por amplitud.

      - con config=1 el algoritmo usa una tabla hash donde almacena
        todos los estados visitados, asegurando que si cualquier rama
        ya visito un estado, otra no la repita.

      - con config != 1 el algoritmo solo revisa que el estado no se haya
        dado ya en su rama actual, recorriendola con is_in_branch.
    """
    start_time = time.time()
    nodes_expanded = 0

    if(config == 1):
      visited = set()
    queue = deque()

    root = self._make_root()
    queue.append(root)
    while queue:
      node = queue.popleft()
      if(self.problem.goal_test(node.state)):
        return Result(
          solution=node.get_path(),
          nodes_expanded=nodes_expanded,
          depth=node.depth,
          cost=node.cost,
          time=time.time() - start_time
        )
      if(config == 1):
        visited.add(node.state)
      
      nodes_expanded += 1
      for child in self._expand(node):
        cond = False
        if(config == 1):
          cond = child.state in visited
        else:
          cond = self.problem.is_in_branch(child)
        if cond:
          continue
        queue.append(child)
    
    return Result(
            solution=None,
            nodes_expanded=nodes_expanded,
            depth=0,
            cost=0.0,
            time=time.time() - start_time
        )
        