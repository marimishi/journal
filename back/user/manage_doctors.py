import json
import os

class DoctorsManager:
    def __init__(self, file_path="doctors.json"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            self._save_to_file([])

    def _load_from_file(self) -> list:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_to_file(self, data: list):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_all_doctors(self) -> list:
        return self._load_from_file()

    def add_doctor(self, full_name: str) -> bool:
        full_name = full_name.strip()
        if not full_name:
            return False
            
        doctors = self._load_from_file()
        if full_name in doctors:
            return False
            
        doctors.append(full_name)
        self._save_to_file(doctors)
        return True
    
    def delete_doctor(self, full_name: str) -> bool:

        doctors = self._load_from_file()
        doctors.remove(full_name)
        self._save_to_file(doctors)
        return True