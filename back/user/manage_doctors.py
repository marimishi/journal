from back.data_manager import DataManager

class DoctorsManager:
    def __init__(self):
        self.db = DataManager()

    def get_all_doctors(self) -> list:
        data = self.db.load_data()
        return data.get("doctors", [])

    def add_doctor(self, full_name: str) -> bool:
        full_name = full_name.strip()
        if not full_name:
            return False
            
        data = self.db.load_data()
        if full_name in data["doctors"]:
            return False
            
        data["doctors"].append(full_name)
        self.db.save_data(data)
        return True

    def delete_doctor(self, full_name: str) -> bool:
        data = self.db.load_data()
        if full_name in data["doctors"]:
            data["doctors"].remove(full_name)
            self.db.save_data(data)
            return True
        return False