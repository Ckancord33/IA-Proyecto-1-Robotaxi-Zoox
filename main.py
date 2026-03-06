from models.world import World
from models.problem import Problem
from utils.map_loader import load_world
from ui.renderer import launch
from algorithms.breadth_first_search import BFS

def main():
  world_grid = load_world('maps/map1.txt')
  world = World(world_grid)
  problem = Problem(world)
  bfs = BFS(problem)
  result = bfs.solve()
  print(result.__repr__())
  
main()