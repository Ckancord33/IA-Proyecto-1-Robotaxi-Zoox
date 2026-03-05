"""
Lee un archivo .txt con el formato del enunciado y devuelve un World.

Formato esperado: números separados por espacios, una fila por línea.
Ejemplo:
    4 1 1 1 1 1 1 1 1 1
    0 1 1 0 0 0 3 0 0 0
    2 1 1 0 1 0 1 0 1 0
    ...
"""

from models.world import World


def load_world(filepath: str) -> World:
    """
    Lee el archivo en filepath y devuelve un World.

    Lanza
    -----
    FileNotFoundError  — si el archivo no existe
    ValueError         — si el formato es inválido o el mapa está incompleto
    """
    try:
        with open(filepath, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"No se encontró el archivo de mapa: '{filepath}'")

    if not lines:
        raise ValueError(f"El archivo '{filepath}' está vacío.")

    grid = []
    for i, line in enumerate(lines, start=1):
        try:
            row = [int(x) for x in line.split()]
        except ValueError:
            raise ValueError(
                f"Línea {i} contiene valores no enteros: '{line}'"
            )

        valid_values = {0, 1, 2, 3, 4, 5}
        invalid = set(row) - valid_values
        if invalid:
            raise ValueError(
                f"Línea {i} tiene valores no reconocidos: {invalid}. "
                f"Valores válidos: {valid_values}"
            )

        grid.append(row)

    return grid