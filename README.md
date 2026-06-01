# IA-Proyecto-1-Robotaxi-Zoox

## 🚀 Cómo correr el proyecto

### Requisitos previos
- Python 3.10+
- Google Chrome instalado (la interfaz se abre como app de escritorio)

### Pasos

1. Clona el repositorio:
```bash
git clone https://github.com/Ckancord33/IA-Proyecto-1-Robotaxi-Zoox.git
cd IA-Proyecto-1-Robotaxi-Zoox
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecuta la aplicación:
```bash
python main_ui.py
```

> Se abrirá automáticamente una ventana de escritorio (modo `chrome-app`).  
> **No** se abre en una pestaña del navegador.

---

## ¿Qué es este proyecto?

Simulación de un robotaxi autónomo que navega por una ciudad representada 
como una cuadrícula de n×m. El vehículo debe recoger a todos los pasajeros 
dispersos en el mapa y llevarlos a un único destino, usando algoritmos de 
búsqueda de Inteligencia Artificial (BFS, DFS, Costo Uniforme, Greedy, A*).

## Arquitectura

La aplicación está dividida en dos capas:

- **Lógica (Python):** modelos del mundo, estado, y algoritmos de búsqueda.
- **Interfaz (Eel + Three.js):** visualización 3D interactiva que corre en 
  una ventana de escritorio sin tocar la lógica de búsqueda.

### Archivos principales

| Archivo / Carpeta | Rol |
|---|---|
| `main_ui.py` | Punto de entrada de la aplicación |
| `models/` | Representación del mundo, estado y problema |
| `algorithms/` | Implementación de los algoritmos de búsqueda |
| `UI/renderer.py` | Backend Python que comunica lógica e interfaz vía Eel |
| `UI/web/` | Frontend 3D (HTML, JS con Three.js, CSS) |
| `maps/` | Archivos de texto con los mapas de prueba |