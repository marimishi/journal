import os
import json
import base64
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
            
            # Считываем ранее сохранённый путь из QSettings (по умолчанию "")
            cls._instance.file_path = cls._instance.settings.value("db_file_path", "", type=str)
            
            # Инициализация ключа шифрования
            salt = b'medical_app_salt_2026'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(b"secret_key_med_app"))
            cls._instance.cipher = Fernet(key)
        return cls._instance

    def set_file_path(self, path: str):
        """Запоминает выбранный путь и сохраняет его в QSettings."""
        self.file_path = path
        self.settings.setValue("db_file_path", path)

    def has_valid_file_path(self) -> bool:
        """
        Проверяет, существует ли файл по сохраненному пути.
        """
        if not self.file_path:
            return False
        return os.path.exists(self.file_path)

    def _encrypt(self, text: str) -> bytes:
        return self.cipher.encrypt(text.encode('utf-8'))

    def _decrypt(self, data: bytes) -> str:
        return self.cipher.decrypt(data).decode('utf-8')

    def load_data(self) -> dict:
        default_structure = {"doctors": [], "ambulator": [], "ambulance": []}
        if not self.has_valid_file_path():
            return default_structure

        try:
            with open(self.file_path, 'rb') as f:
                encrypted_content = f.read()
                if not encrypted_content:
                    return default_structure
                decrypted_json = self._decrypt(encrypted_content)
                return json.loads(decrypted_json)
        except Exception as e:
            print(f"Ошибка чтения/расшифровки файла: {e}")
            return default_structure

    def save_data(self, data: dict):
        if not self.file_path:
            return
        
        # Создаем директорию, если её нет
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        encrypted_data = self._encrypt(json_str)
        
        with open(self.file_path, 'wb') as f:
            f.write(encrypted_data)