"""UI/renderer.py  -  Backend Eel para la interfaz 3D con Three.js.

Mantiene una API simple para no complicar la comunicacion entre archivos:
- launch(maps_dir): punto de entrada desde main_ui.py
- get_app_state(): mapas y algoritmos disponibles
- load_map(map_name): datos serializados del mapa
- solve_map(map_name, algorithm_name): ejecuta busqueda y devuelve resultado
"""

from __future__ import annotations

import glob
import os
import socket
import sys
from pathlib import Path
from typing import Any

import eel

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from algorithms.breadth_first_search import BFS
from algorithms.depth_first_search import DFS
from algorithms.cost_search import CostSearch
from algorithms.greedy_search import GreedySearch
from algorithms.a_star import aStarSearch
from models.problem import Problem
from models.world import World
from utils.map_loader import load_world

_WEB_DIR = os.path.join(_HERE, "web")
_MAP_PATHS: dict[str, str] = {}
_ALGORITHMS = {
    "BFS": BFS,
    "DFS": DFS,
    "Cost Search" : CostSearch,
    "Greedy Search": GreedySearch,
    "A* Search": aStarSearch,
}


def _find_app_browser() -> str | None:
    """Retorna ruta de Edge/Chrome para abrir la UI en modo app."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]

    for candidate in candidates:
        if str(candidate) and candidate.exists():
            return str(candidate)
    return None


def _find_free_port() -> int:
    """Retorna un puerto TCP libre para levantar el servidor local de Eel."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _discover_maps(maps_dir: str) -> dict[str, str]:
    """Busca mapas en rutas relativas al proceso y al proyecto."""
    for base in (maps_dir, os.path.join(_BASE, maps_dir)):
        paths = sorted(glob.glob(os.path.join(base, "*.txt")))
        if paths:
            return {
                os.path.splitext(os.path.basename(path))[0]: path
                for path in paths
            }
    raise FileNotFoundError(f"No se encontraron mapas en '{maps_dir}'")


def _load_world_for(map_name: str) -> World:
    if map_name not in _MAP_PATHS:
        raise ValueError(f"Mapa no valido: {map_name}")
    world_grid = load_world(_MAP_PATHS[map_name])
    return World(world_grid)


def _serialize_world(world: World, map_name: str) -> dict[str, Any]:
    return {
        "mapName": map_name,
        "rows": world.rows,
        "cols": world.cols,
        "grid": [list(row) for row in world.grid],
        "start": [world.start[0], world.start[1]],
        "goal": [world.goal[0], world.goal[1]],
        "passengers": [[r, c] for r, c in world.passengers],
    }


def _serialize_result(result) -> dict[str, Any]:
    if result is None:
        return {
            "found": False,
            "nodesExpanded": 0,
            "depth": 0,
            "cost": 0,
            "time": 0,
            "actions": [],
            "path": [],
        }

    if not result.found():
        return {
            "found": False,
            "nodesExpanded": result.nodes_expanded,
            "depth": result.depth,
            "cost": result.cost,
            "time": result.time,
            "actions": [],
            "path": [],
        }

    path = []
    for node in result.solution:
        path.append(
            {
                "row": node.state.row,
                "col": node.state.col,
                "pickedUp": list(node.state.picked_up),
                "action": node.action,
                "cost": node.cost,
                "depth": node.depth,
            }
        )

    return {
        "found": True,
        "nodesExpanded": result.nodes_expanded,
        "depth": result.depth,
        "cost": result.cost,
        "time": result.time,
        "actions": result.get_actions(),
        "path": path,
    }


@eel.expose
def get_app_state() -> dict[str, Any]:
    """Devuelve listas para poblar la UI."""
    return {
        "maps": sorted(_MAP_PATHS.keys()),
        "algorithms": sorted(_ALGORITHMS.keys()),
    }


@eel.expose
def load_map(map_name: str) -> dict[str, Any]:
    """Carga un mapa y devuelve su modelo serializado."""
    try:
        world = _load_world_for(map_name)
        return {
            "ok": True,
            "payload": {
                "world": _serialize_world(world, map_name),
            },
        }
    except Exception as exc:  # pragma: no cover - proteccion de capa API
        return {
            "ok": False,
            "error": str(exc),
        }


@eel.expose
def solve_map(map_name: str, algorithm_name: str) -> dict[str, Any]:
    """Ejecuta el algoritmo seleccionado y devuelve mundo + resultado."""
    try:
        if algorithm_name not in _ALGORITHMS:
            raise ValueError(f"Algoritmo no valido: {algorithm_name}")

        world = _load_world_for(map_name)
        problem = Problem(world)
        algorithm_cls = _ALGORITHMS[algorithm_name]
        solver = algorithm_cls(problem)
        result = solver.solve()

        return {
            "ok": True,
            "payload": {
                "world": _serialize_world(world, map_name),
                "algorithm": algorithm_name,
                "result": _serialize_result(result),
            },
        }
    except Exception as exc:  # pragma: no cover - proteccion de capa API
        return {
            "ok": False,
            "error": str(exc),
        }


def launch(maps_dir: str = "maps"):
    """Abre una ventana de escritorio con interfaz 3D (sin pestaña de localhost)."""
    global _MAP_PATHS

    _MAP_PATHS = _discover_maps(maps_dir)

    if not os.path.isdir(_WEB_DIR):
        raise FileNotFoundError(f"No existe carpeta web: {_WEB_DIR}")

    eel.init(_WEB_DIR)

    browser_exe = _find_app_browser()
    port = _find_free_port()
    start_kwargs = {
        "size": (1320, 860),
        "position": (40, 40),
        "host": "127.0.0.1",
        "port": port,
        "disable_cache": True,
        "block": True,
    }

    if browser_exe:
        app_url = f"http://127.0.0.1:{port}/index.html"
        eel.start(
            "index.html",
            mode="custom",
            cmdline_args=[
                browser_exe,
                "--new-window",
                f"--app={app_url}",
            ],
            **start_kwargs,
        )
        return

    # Fallback: si no se detecta Edge/Chrome, usar navegador por defecto.
    eel.start("index.html", mode="default", **start_kwargs)
