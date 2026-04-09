"""UI/renderer.py  -  Backend Eel para la interfaz 3D con Three.js.

Mantiene una API simple para no complicar la comunicacion entre archivos:
- launch(maps_dir): punto de entrada desde main_ui.py
- get_app_state(): mapas y algoritmos disponibles
- load_map(map_name): datos serializados del mapa
- solve_map(map_name, algorithm_name): ejecuta busqueda y devuelve resultado
"""

from __future__ import annotations

import glob
import multiprocessing as mp
import os
from queue import Empty
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
_MAPS_DIR: str = "maps"
_ACTIVE_SOLVE_PROCESS: mp.Process | None = None
_ACTIVE_SOLVE_QUEUE: mp.Queue | None = None
_ACTIVE_SOLVE_ID: int | None = None
_ACTIVE_SOLVE_PROGRESS: dict[str, Any] | None = None
_SOLVE_COUNTER: int = 0
_ALGORITHMS = {
    "BFS": BFS,
    "DFS": DFS,
    "Cost Search" : CostSearch,
    "Greedy Search": GreedySearch,
    "A* Search": aStarSearch,
}

_ALGORITHM_CATEGORIES = {
    "No informado": ["BFS", "DFS", "Cost Search"],
    "Informado": ["Greedy Search", "A* Search"],
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


def _refresh_map_paths() -> None:
    """Actualiza el indice de mapas para reflejar cambios en disco en tiempo real."""
    global _MAP_PATHS
    _MAP_PATHS = _discover_maps(_MAPS_DIR)


def _load_world_for(map_name: str) -> World:
    _refresh_map_paths()
    if map_name not in _MAP_PATHS:
        raise ValueError(f"Mapa no valido: {map_name}")
    world_grid = load_world(_MAP_PATHS[map_name])
    return World(world_grid)


def _map_signature(map_name: str) -> str:
    """Firma de archivo para detectar cambios (mtime + tamano)."""
    path = _MAP_PATHS[map_name]
    stat = os.stat(path)
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _serialize_world(world: World, map_name: str) -> dict[str, Any]:
    return {
        "mapName": map_name,
        "sourceSignature": _map_signature(map_name),
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
            "algorithm": "Unknown",
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
            "algorithm": result.algorithm,
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
        "algorithm": result.algorithm,
        "found": True,
        "nodesExpanded": result.nodes_expanded,
        "depth": result.depth,
        "cost": result.cost,
        "time": result.time,
        "actions": result.get_actions(),
        "path": path,
    }


def _serialize_world_data(world: World, map_name: str, map_path: str) -> dict[str, Any]:
    stat = os.stat(map_path)
    return {
        "mapName": map_name,
        "sourceSignature": f"{stat.st_mtime_ns}:{stat.st_size}",
        "rows": world.rows,
        "cols": world.cols,
        "grid": [list(row) for row in world.grid],
        "start": [world.start[0], world.start[1]],
        "goal": [world.goal[0], world.goal[1]],
        "passengers": [[r, c] for r, c in world.passengers],
    }


def _solve_worker(map_name: str, map_path: str, algorithm_name: str, out_queue: mp.Queue):
    """Proceso aislado para poder cancelar con terminate()."""
    try:
        if algorithm_name not in _ALGORITHMS:
            raise ValueError(f"Algoritmo no valido: {algorithm_name}")

        world_grid = load_world(map_path)
        world = World(world_grid)
        problem = Problem(world)
        algorithm_cls = _ALGORITHMS[algorithm_name]
        solver = algorithm_cls(problem)

        def on_progress(payload: dict[str, Any]) -> bool:
            out_queue.put({"type": "progress", "payload": payload})
            return True

        result = solver.solve(progress_callback=on_progress, progress_interval=1.0)

        out_queue.put(
            {
                "type": "result",
                "ok": True,
                "payload": {
                    "world": _serialize_world_data(world, map_name, map_path),
                    "algorithm": algorithm_name,
                    "result": _serialize_result(result),
                },
            }
        )
    except Exception as exc:  # pragma: no cover - proceso aislado
        out_queue.put({"type": "result", "ok": False, "error": str(exc)})


def _cleanup_active_solve() -> None:
    global _ACTIVE_SOLVE_PROCESS, _ACTIVE_SOLVE_QUEUE, _ACTIVE_SOLVE_ID, _ACTIVE_SOLVE_PROGRESS
    _ACTIVE_SOLVE_PROCESS = None
    _ACTIVE_SOLVE_QUEUE = None
    _ACTIVE_SOLVE_ID = None
    _ACTIVE_SOLVE_PROGRESS = None


def _drain_solve_queue() -> dict[str, Any] | None:
    """Consume mensajes de progreso y devuelve el ultimo resultado final si existe."""
    global _ACTIVE_SOLVE_PROGRESS
    if _ACTIVE_SOLVE_QUEUE is None:
        return None

    final_msg: dict[str, Any] | None = None
    while True:
        try:
            msg = _ACTIVE_SOLVE_QUEUE.get_nowait()
        except Empty:
            break

        if msg.get("type") == "progress":
            _ACTIVE_SOLVE_PROGRESS = msg.get("payload") or {}
            continue

        if msg.get("type") == "result":
            final_msg = msg

    return final_msg


@eel.expose
def get_app_state() -> dict[str, Any]:
    """Devuelve listas para poblar la UI."""
    _refresh_map_paths()
    algorithms_sorted = sorted(_ALGORITHMS.keys())

    categorized = {
        category: [name for name in names if name in _ALGORITHMS]
        for category, names in _ALGORITHM_CATEGORIES.items()
    }

    # Si aparece un algoritmo nuevo no clasificado, cae en "No informado".
    categorized_names = {name for names in categorized.values() for name in names}
    uncategorized = [name for name in algorithms_sorted if name not in categorized_names]
    if uncategorized:
        categorized.setdefault("No informado", []).extend(uncategorized)

    return {
        "maps": sorted(_MAP_PATHS.keys()),
        "mapMeta": {name: _map_signature(name) for name in sorted(_MAP_PATHS.keys())},
        "algorithms": algorithms_sorted,
        "algorithmCategories": categorized,
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


@eel.expose
def start_solve(map_name: str, algorithm_name: str) -> dict[str, Any]:
    """Inicia un calculo en segundo plano y retorna un ID para hacer polling."""
    global _ACTIVE_SOLVE_PROCESS, _ACTIVE_SOLVE_QUEUE, _ACTIVE_SOLVE_ID, _ACTIVE_SOLVE_PROGRESS, _SOLVE_COUNTER
    try:
        if _ACTIVE_SOLVE_PROCESS and _ACTIVE_SOLVE_PROCESS.is_alive():
            return {
                "ok": False,
                "error": "Ya hay un calculo en curso. Cancela el actual antes de iniciar otro.",
            }

        _refresh_map_paths()
        if map_name not in _MAP_PATHS:
            raise ValueError(f"Mapa no valido: {map_name}")
        if algorithm_name not in _ALGORITHMS:
            raise ValueError(f"Algoritmo no valido: {algorithm_name}")

        _SOLVE_COUNTER += 1
        solve_id = _SOLVE_COUNTER

        queue_obj: mp.Queue = mp.Queue()
        process = mp.Process(
            target=_solve_worker,
            args=(map_name, _MAP_PATHS[map_name], algorithm_name, queue_obj),
            daemon=True,
        )
        process.start()

        _ACTIVE_SOLVE_ID = solve_id
        _ACTIVE_SOLVE_QUEUE = queue_obj
        _ACTIVE_SOLVE_PROCESS = process
        _ACTIVE_SOLVE_PROGRESS = {
            "algorithm": algorithm_name,
            "nodes_expanded": 0,
            "elapsed_time": 0.0,
            "frontier_size": 0,
        }

        return {"ok": True, "solveId": solve_id}
    except Exception as exc:  # pragma: no cover - proteccion de capa API
        _cleanup_active_solve()
        return {
            "ok": False,
            "error": str(exc),
        }


@eel.expose
def get_solve_status(solve_id: int) -> dict[str, Any]:
    """Consulta estado de un calculo activo: running/done/error/cancelled."""
    global _ACTIVE_SOLVE_PROCESS
    try:
        if _ACTIVE_SOLVE_ID is None:
            return {"ok": True, "state": "idle"}

        if solve_id != _ACTIVE_SOLVE_ID:
            return {"ok": True, "state": "stale"}

        final_msg = _drain_solve_queue()

        if final_msg is not None:
            if final_msg.get("ok"):
                _cleanup_active_solve()
                return {"ok": True, "state": "done", "payload": final_msg["payload"]}

            _cleanup_active_solve()
            return {"ok": True, "state": "error", "error": final_msg.get("error", "Error desconocido")}

        if _ACTIVE_SOLVE_PROCESS and _ACTIVE_SOLVE_PROCESS.is_alive():
            return {
                "ok": True,
                "state": "running",
                "progress": _ACTIVE_SOLVE_PROGRESS,
            }

        if _ACTIVE_SOLVE_QUEUE is not None:
            _cleanup_active_solve()
            return {
                "ok": True,
                "state": "error",
                "error": "El calculo termino sin devolver resultado final.",
            }

        _cleanup_active_solve()
        return {"ok": True, "state": "error", "error": "No hay cola de resultado activa."}
    except Exception as exc:  # pragma: no cover - proteccion de capa API
        _cleanup_active_solve()
        return {
            "ok": False,
            "error": str(exc),
        }


@eel.expose
def cancel_solve(solve_id: int) -> dict[str, Any]:
    """Cancela el calculo activo terminando el proceso de solve."""
    try:
        if _ACTIVE_SOLVE_ID is None:
            return {"ok": True, "state": "idle"}

        if solve_id != _ACTIVE_SOLVE_ID:
            return {"ok": True, "state": "stale"}

        if _ACTIVE_SOLVE_PROCESS and _ACTIVE_SOLVE_PROCESS.is_alive():
            _ACTIVE_SOLVE_PROCESS.terminate()
            _ACTIVE_SOLVE_PROCESS.join(timeout=0.5)

        _cleanup_active_solve()
        return {"ok": True, "state": "cancelled"}
    except Exception as exc:  # pragma: no cover - proteccion de capa API
        _cleanup_active_solve()
        return {
            "ok": False,
            "error": str(exc),
        }


def launch(maps_dir: str = "maps"):
    """Abre una ventana de escritorio con interfaz 3D (sin pestaña de localhost)."""
    global _MAP_PATHS, _MAPS_DIR

    _MAPS_DIR = maps_dir
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
