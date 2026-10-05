# Пароль администратора зашит в программу — впишите свой вместо значения ниже
ADMIN_PASSWORD = "112"


class AdminSession:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AdminSession, cls).__new__(cls)
            cls._instance._is_authenticated = False
            cls._instance._current_user = None
        return cls._instance

    def is_authenticated(self) -> bool:
        return self._is_authenticated

    def login(self, password: str, username: str = "admin") -> bool:
        if password == ADMIN_PASSWORD:
            self._is_authenticated = True
            self._current_user = username
            return True
        return False

    def logout(self):
        self._is_authenticated = False
        self._current_user = None

    def get_current_user(self):
        return self._current_user