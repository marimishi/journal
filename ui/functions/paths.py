import os
import sys


def resource_path(relative_path: str) -> str:
    """Ищет файл ресурса (CSV и т.п.) в нескольких местах.

    В собранном exe: сначала рядом с Journal.exe (так файл можно подменить без
    пересборки), затем внутри самого exe (то, что добавлено через --add-data).
    При обычном запуске: корень проекта, затем текущая папка.
    """
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(os.path.dirname(sys.executable), relative_path),
            os.path.join(getattr(sys, "_MEIPASS", ""), relative_path),
        ]
    else:
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        candidates = [
            os.path.join(project_root, relative_path),
            os.path.abspath(relative_path),
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]
