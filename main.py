from models.world import World
from models.problem import Problem
from utils.map_loader import load_world
from ui.renderer import launch

from algorithms.breadth_first_search import BFS
from algorithms.depth_first_search import DFS
from algorithms.cost_search import CostSearch

def main():
  """
    Muestra el flujo sin ui para llamar los algoritmos y resolver
    uno de los mapas en la carpeta /maps
  """

  world_grid = load_world('maps/map1.txt')
  world = World(world_grid)
  problem = Problem(world)

  print("----------------BFS--------------------------")
  bfs = BFS(problem)
  result = bfs.solve(3)
  print(result.__repr__())
  """
  print("\n---------------DFS-------------------------")
  dfs = DFS(problem)
  result_dfs = dfs.solve()
  print(result_dfs.__repr__())
  """
  
  print("\n---------------Cost search-------------------------")
  cs = CostSearch(problem)
  result_cs = cs.solve()
  print(result_cs.__repr__())
  

  
main()