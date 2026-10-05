"""Диалоги выбора файла данных. Имя и расширение файла могут быть любыми."""
import os

from PySide6 import QtWidgets

from back.data_manager import DataManager

FILE_FILTER = "Все файлы (*);;JSON (*.json)"


def _start_dir() -> str:
    db = DataManager()
    folder = os.path.dirname(db.file_path) if db.file_path else ""
    return folder if folder and os.path.isdir(folder) else os.path.expanduser("~")


def pick_existing_data_file(parent=None) -> bool:
    """Выбор уже существующего файла с данными. True — путь изменён."""
    db = DataManager()
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        parent, "Выберите файл базы данных", _start_dir(), FILE_FILTER
    )
    if not path:
        return False

    ok, error = db.inspect_file(path)
    if not ok:
        QtWidgets.QMessageBox.critical(parent, "Неверный файл", error)
        return False

    db.set_file_path(path)
    return True


def create_new_data_file(parent=None) -> bool:
    """Создание нового файла данных (или выбор существующего в окне сохранения)."""
    db = DataManager()
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        "Создать файл базы данных",
        os.path.join(_start_dir(), "data.json"),
        FILE_FILTER,
        options=QtWidgets.QFileDialog.Option.DontConfirmOverwrite,
    )
    if not path:
        return False

    if os.path.exists(path):
        # Существующий файл никогда не перезаписываем — просто используем его как базу
        ok, error = db.inspect_file(path)
        if not ok:
            QtWidgets.QMessageBox.critical(parent, "Неверный файл", error)
            return False
        db.set_file_path(path)
        return True

    try:
        db.create_file(path)
    except OSError as e:
        QtWidgets.QMessageBox.critical(
            parent, "Ошибка", f"Не удалось создать файл:\n{e}"
        )
        return False
    return True