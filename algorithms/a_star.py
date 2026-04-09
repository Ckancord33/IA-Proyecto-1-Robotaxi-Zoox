import time
from algorithms import Algorithm
from utils.result import Result
from queue import PriorityQueue

class aStarSearch(Algorithm):

  def solve(self, config=1, progress_callback=None, progress_interval=1.0) -> Result:
    """
    Ejecuta A* y opcionalmente reporta progreso parcial.

    progress_callback(payload) se invoca como maximo cada `progress_interval`
    segundos con informacion parcial:
      - nodes_expanded
      - elapsed_time
      - frontier_size

    Si el callback devuelve False, se interpreta como cancelacion.
    """
    start_time = time.time()
    algorithm_name = "A* Search"
    nodes_expanded = 0
    heuristic = self.problem.heuristic
    if(config == 1):
      visited = set()

    pq = PriorityQueue()

    cont = 0
    root = self._make_root()
    if(config == 1):
      visited.add(root.state)
    pq.put((heuristic(root.state)+root.cost, cont, root))
    cont += 1

    emit_progress = self._make_progress_reporter(
      algorithm_name=algorithm_name,
      start_time=start_time,
      progress_callback=progress_callback,
      progress_interval=progress_interval,
    )

    while not pq.empty():
      if not emit_progress(nodes_expanded=nodes_expanded, frontier_size=pq.qsize(), force=False):
        return self._cancelled_result(start_time=start_time, nodes_expanded=nodes_expanded, algorithm_name=algorithm_name)

      node = pq.get()[2]
      if self.problem.goal_test(node.state):
        emit_progress(nodes_expanded=nodes_expanded, frontier_size=pq.qsize(), force=True)
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
        pq.put((heuristic(child.state)+child.cost, cont, child))
        cont += 1

      emit_progress(nodes_expanded=nodes_expanded, frontier_size=pq.qsize(), force=False)
    emit_progress(nodes_expanded=nodes_expanded, frontier_size=0, force=True)
    return Result(
            solution=None,
            nodes_expanded=nodes_expanded,
            depth=0,
            cost=0.0,
            time=time.time() - start_time,
            algorithm=algorithm_name,
        )