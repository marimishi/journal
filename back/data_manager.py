import os
import json
import base64
from datetime import datetime

from PySide6.QtCore import QSettings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DataManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            # Хранилище настроек приложения (реестр Windows / config в Linux/macOS)
            cls._instance.settings = QSettings("MedicalApp", "DataStorage")

            # Путь к файлу данных выбирается один раз и запоминается между запусками
            cls._instance.file_path = cls._instance.settings.value(
                "db_file_path", "", type=str
            )

            # Подписчики, которых нужно уведомить о смене файла (перезагрузить таблицы и т.п.)
            cls._instance._path_listeners = []

            # Инициализация ключа шифрования
            salt = b"medical_app_salt_2026"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(b"secret_key_med_app"))
            cls._instance.cipher = Fernet(key)
        return cls._instance

    # ------------------------------------------------------------------
    # Путь к файлу
    # ------------------------------------------------------------------
    def add_path_listener(self, callback):
        """callback() вызывается после каждой смены файла данных."""
        if callback not in self._path_listeners:
            self._path_listeners.append(callback)

    def set_file_path(self, path: str):
        """Запоминает выбранный путь (имя файла может быть любым) и сохраняет его в QSettings."""
        path = os.path.normpath(os.path.abspath(path)) if path else ""
        self.file_path = path
        self.settings.setValue("db_file_path", path)
        self.settings.sync()  # записываем сразу, не дожидаясь закрытия программы
        for callback in list(self._path_listeners):
            try:
                callback()
            except Exception as e:
                print(f"Ошибка при обновлении после смены файла данных: {e}")

    def has_valid_file_path(self) -> bool:
        """Проверяет, существует ли файл по сохранённому пути."""
        if not self.file_path:
            return False
        return os.path.isfile(self.file_path)

    def get_file_info(self) -> dict:
        """Сведения о текущем файле для отображения в настройках."""
        info = {"path": self.file_path, "exists": self.has_valid_file_path(),
                "size": 0, "modified": ""}
        if info["exists"]:
            stat = os.stat(self.file_path)
            info["size"] = stat.st_size
            info["modified"] = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%d.%m.%Y %H:%M"
            )
        return info

    def inspect_file(self, path: str) -> tuple[bool, str]:
        """Проверяет, что файл — база данных этой программы (расшифровывается и это JSON-словарь).

        Пустой файл считается допустимым (будет инициализирован при первой записи).
        """
        try:
            with open(path, "rb") as f:
                content = f.read()
        except OSError as e:
            return False, f"Не удалось прочитать файл:\n{e}"
        if not content:
            return True, ""
        try:
            data = json.loads(self._decrypt(content))
        except Exception:
            return False, (
                "Файл не удалось расшифровать. Это не база данных программы, "
                "либо она повреждена или создана с другим ключом."
            )
        if not isinstance(data, dict):
            return False, "Неверная структура файла данных."
        return True, ""

    def create_file(self, path: str):
        """Создаёт новый файл с пустой структурой и делает его текущим."""
        self.set_file_path(path)
        self.save_data(self._default_structure())

    # ------------------------------------------------------------------
    # Шифрование и чтение/запись
    # ------------------------------------------------------------------
    def _encrypt(self, text: str) -> bytes:
        return self.cipher.encrypt(text.encode("utf-8"))

    def _decrypt(self, data: bytes) -> str:
        return self.cipher.decrypt(data).decode("utf-8")

    def _default_structure(self) -> dict:
        return {"doctors": [], "ambulator": [], "ambulance": []}

    def load_data(self) -> dict:
        default_structure = self._default_structure()
        if not self.has_valid_file_path():
            return default_structure

        try:
            with open(self.file_path, "rb") as f:
                encrypted_content = f.read()
            if not encrypted_content:
                return default_structure
            data = json.loads(self._decrypt(encrypted_content))
            if not isinstance(data, dict):
                return default_structure
            # Файл мог быть создан раньше/другой версией — добавляем недостающие разделы
            for key, value in default_structure.items():
                data.setdefault(key, value)
            return data
        except Exception as e:
            print(f"Ошибка чтения/расшифровки файла: {e}")
            return default_structure

    def save_data(self, data: dict):
        if not self.file_path:
            return

        # Создаем директорию, если её нет
        folder = os.path.dirname(self.file_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        encrypted_data = self._encrypt(json_str)

        with open(self.file_path, "wb") as f:
            f.write(encrypted_data)