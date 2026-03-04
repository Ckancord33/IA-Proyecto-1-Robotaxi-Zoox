from models.world import World
from utils.map_loader import load_world

def main():
  #Carga el mapa
  world = load_world('maps/map1.txt')
  print(world.__repr__())
  
main()