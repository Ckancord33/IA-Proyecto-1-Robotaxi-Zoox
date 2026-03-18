# README de arquitectura

Este documento explica como funciona actualmente nuestro proyecto y donde podemos ir para cambiar UI 3D, reglas, mapas o algoritmos.

## 1) Vista general

El sistema tiene 3 capas principales:

1. Frontend 3D (Three.js): dibuja el mundo, botones, metricas y animacion.
2. Backend UI (Python + Eel): expone funciones para cargar mapa y resolver.
3. Nucleo de IA (modelos(la carpeta de models) + algoritmos(lo mismo)): representa el problema y ejecuta BFS/DFS.

Flujo completo:

1. Se ejecuta `main_ui.py`.
2. `UI/renderer.py` inicia Eel, descubre mapas y abre `UI/web/index.html`.
3. `UI/web/app.js` llama al backend con Eel (`get_app_state`, `load_map`, `solve_map`).
4. El backend crea `World` + `Problem`, ejecuta algoritmo, serializa resultado.
5. Frontend renderiza tablero y anima la ruta solucion.

## 2) Entrypoints

- `main_ui.py`: punto de entrada de la app visual 3D (el recomendado para uso normal).
- `main.py`: ejecucion por consola para probar algoritmos sin UI.

## 3) Estructura por carpetas

### `UI/`

- `renderer.py`
  - Puente entre frontend y logica Python.
  - Detecta mapas (`_discover_maps`) y algoritmos disponibles (`_ALGORITHMS`).
  - API expuesta a JS con Eel:
    - `get_app_state()`
    - `load_map(map_name)`
    - `solve_map(map_name, algorithm_name)`

### `UI/web/`

- `index.html`: layout base (panel de control, botones, canvas).
- `style.css`: estilo visual de paneles, tipografias, colores, responsive.
- `app.js`: escena 3D y comportamiento de UI.
  - Render de celdas, taxi, pasajeros, destino.
  - Control de camara (OrbitControls y modo manual fallback).
  - Animacion de ruta y logs.

### `models/`

- `world.py`: mapa inmutable y reglas del terreno.
  - Tipos de celda (0..5), costos (`COST_NORMAL`, `COST_HIGH`).
- `state.py`: estado del agente (fila, columna, pasajeros recogidos).
- `node.py`: nodo del arbol de busqueda (estado + padre + accion + costo + profundidad).
- `problem.py`: reglas del problema usadas por algoritmos.
  - Acciones validas, transicion de estado, costo de paso, goal test.

### `algorithms/`

- `algorithm.py`: clase base abstracta (`solve`, `_make_root`, `_expand`).
- `breadth_first_search.py`: BFS.
- `depth_first_search.py`: DFS.
- `cost_search.py`: placeholder de busqueda por costo (sin implementar).

### `utils/`

- `map_loader.py`: lee archivos de mapa `.txt` y valida valores.
- `result.py`: estructura estandar del resultado de busqueda.

### `maps/`

- `map1.txt` ... `map5.txt`: mapas en cuadricula (numeros separados por espacios).

## 4) Donde cambiar cada cosa (guia rapida)

## A. Cambiar disenos 3D (taxi, pasajeros, terreno, ruta)

Archivo principal: `UI/web/app.js`

- Color de cada tipo de celda:
  - funcion `cellColor(cellType)`
- Geometria del taxi:
  - funcion `createTaxi(position)`
- Geometria de pasajeros:
  - bloque dentro de `renderWorld(world)` cuando `type === CELL_PASSENGER`
- Marcador del destino:
  - bloque dentro de `renderWorld(world)` cuando `type === CELL_GOAL`
- Tamano/escala del tablero:
  - constante `tileSize`
- Linea de la ruta solucion:
  - funcion `createRouteLine(path)`

Nota: actualmente no se cargan modelos .glb/.obj; todo se dibuja con primitivas Three.js (Box, Cone, Capsule/Sphere). Si quieres modelos 3D reales, ese cambio se hace en este mismo archivo incorporando loaders de Three.js.

## B. Cambiar estilo visual del panel (no 3D)

- `UI/web/style.css`: colores, fuentes, espaciados, responsive.
- `UI/web/index.html`: estructura de controles (botones, selectores, panel de logs/metricas).

## C. Cambiar camara y navegacion

Archivo: `UI/web/app.js`

- Posicion inicial de camara:
  - configuracion de `camera.position` y ajuste dentro de `renderWorld`
- OrbitControls:
  - bloque donde se instancia `new THREE.OrbitControls(...)`
- Modo manual de camara:
  - estructura `manualOrbit` y funcion `setupManualOrbitEvents()`

## D. Cambiar algoritmos disponibles en UI

Archivo: `UI/renderer.py`

- Registro de algoritmos visibles para la interfaz:
  - diccionario `_ALGORITHMS = { "BFS": BFS, "DFS": DFS }`

Para agregar uno nuevo:

1. Implementar clase en `algorithms/` heredando `Algorithm`.
2. Importarla en `UI/renderer.py`.
3. Agregarla al diccionario `_ALGORITHMS`.

## E. Cambiar reglas del problema

- Acciones permitidas (UP/DOWN/LEFT/RIGHT): `models/problem.py` en `ACTIONS`.
- Condicion de exito (goal): `models/problem.py` en `goal_test`.
- Regla de recoger pasajeros: `models/problem.py` en `result`.

## F. Cambiar costos del mapa

Archivo: `models/world.py`

- Costos base:
  - `COST_NORMAL`
  - `COST_HIGH`
- Regla de costo por celda:
  - `get_cost(row, col)`

## G. Cambiar mapa o crear uno nuevo

- Carpeta: `maps/`
- Formato: matriz de enteros separados por espacios.
- Convencion:
  - 0: via libre
  - 1: muro
  - 2: inicio
  - 3: trafico alto
  - 4: pasajero
  - 5: destino

Validacion de formato:

- `utils/map_loader.py`

## 5) Flujo de datos entre frontend y backend

Frontend (`app.js`) llama por Eel a Python:

1. `get_app_state()` -> listas de mapas y algoritmos.
2. `load_map(map_name)` -> mundo serializado para renderizar.
3. `solve_map(map_name, algorithm_name)` -> mundo + resultado del solver.

Backend (`renderer.py`) responde con objetos serializados:

- `world`: grid, rows, cols, start, goal, passengers.
- `result`: found, nodesExpanded, depth, cost, time, actions, path.

`path` es la base para animar el taxi paso a paso.

## 6) Ejecucion

- UI 3D:
  - `python main_ui.py`
- Consola (sin UI):
  - `python main.py`

## 7) Observaciones tecnicas actuales
- `utils/map_loader.py` documenta que retorna `World`, pero en la practica retorna la grilla y luego `World` se construye en `main.py`/`renderer.py`.

