import time
from algorithms import Algorithm
from utils.result import Result

class DFS(Algorithm):
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


    stack = []

    root = self._make_root()
    stack.append(root)
    while stack:
      node = stack.pop()
      if(self.problem.goal_test(node.state)):
        return Result(
          solution=node.get_path(),
          nodes_expanded=nodes_expanded,
          depth=node.depth,
          cost=node.cost,
          time=time.time() - start_time
        )
      
      nodes_expanded += 1
      for child in self._expand(node):
        if self.problem.is_in_branch(child):
          continue
        stack.append(child)
    
    return Result(
            solution=None,
            nodes_expanded=nodes_expanded,
            depth=0,
            cost=0.0,
            time=time.time() - start_time
        )