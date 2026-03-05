from models.world import World
from utils.map_loader import load_world

def main():
  #Carga el mapa
  world_grid = load_world('maps/map1.txt')
  world = World(world_grid)
  print(world.__repr__())
  
main()