# IA-Proyecto-1-Robotaxi-Zoox
El proyecto consiste en desarrollar una aplicación que simule un vehículo autónomo (robotaxi) navegando por una ciudad representada como una cuadrícula de 10×10. El vehículo debe recoger a todos los pasajeros dispersos en el mapa y llevarlos a un único destino común, usando algoritmos de búsqueda de Inteligencia Artificial.

## UI 3D de escritorio (Eel + Three.js)

La interfaz fue migrada de Pygame a una UI 3D construida con Three.js, manteniendo Python como backend con Eel para que la comunicacion siga siendo simple.

- Backend Python: [UI/renderer.py](UI/renderer.py)
- Frontend 3D: [UI/web/index.html](UI/web/index.html), [UI/web/app.js](UI/web/app.js), [UI/web/style.css](UI/web/style.css)
- Punto de entrada: [main_ui.py](main_ui.py)

### Ejecutar en modo escritorio

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecuta la interfaz:

```bash
python main_ui.py
```

Se abrira en una ventana de aplicacion (`chrome-app`) y no en una pestaña de navegador tradicional.
