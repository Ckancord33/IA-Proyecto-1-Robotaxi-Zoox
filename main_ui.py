"""
Robotaxi Zoox - Interfaz Gráfica con Solver y Animación

Este archivo lanza la interfaz gráfica que permite:
- Visualizar diferentes mapas del problema
- Calcular soluciones usando el algoritmo BFS
- Ver los resultados (nodos expandidos, costo, tiempo, etc.)
- Animar el recorrido del robotaxi recogiendo pasajeros
"""

from ui.renderer import launch

if __name__ == "__main__":
    launch("maps")
