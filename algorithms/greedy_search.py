import time
from algorithms import Algorithm
from utils.result import Result
from queue import PriorityQueue

class GreedySearch(Algorithm):

  def solve(self, config=1) -> Result:
    start_time = time.time()
    nodes_expanded = 0
    heuristic = self.problem.heuristic
    if(config == 1):
      visited = set()

    pq = PriorityQueue()

    cont = 0
    root = self._make_root()
    pq.put((heuristic(root.state), cont, root))
    cont += 1

    while not pq.empty():
      node = pq.get()[2]
      if self.problem.goal_test(node.state):
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
        pq.put((heuristic(child.state), cont, child))
        cont += 1
    return Result(
            solution=None,
            nodes_expanded=nodes_expanded,
            depth=0,
            cost=0.0,
            time=time.time() - start_time
        )