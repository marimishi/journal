import os
import sys
from PySide6 import QtCore, QtGui, QtWidgets

from back.style import get_style
from ui.admin.admin_panel import AdminPanel
from ui.ambulance import AmbulanceSheet
from ui.ambulator import AmbulatorSheet
from back.data_manager import DataManager

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainScreen(QtWidgets.QMainWindow):

    def __init__(self, backend_handler=None):
        super().__init__()
        self.db = DataManager()
        self.backend_handler = backend_handler

        self.setWindowTitle("Анализатор отчетов")
        self.setMinimumSize(900, 550)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_sidebar(main_layout)

        self.container = QtWidgets.QFrame()
        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(25, 25, 25, 25)

        self.stacked_widget = QtWidgets.QStackedWidget()
        container_layout.addWidget(self.stacked_widget)

        main_layout.addWidget(self.container, stretch=1)

        self.frames = {}
        for ScreenClass in [AmbulatorSheet, AmbulanceSheet, AdminPanel]:
            screen_name = ScreenClass.__name__
            frame = ScreenClass(parent=self.stacked_widget)
            self.frames[screen_name] = frame
            self.stacked_widget.addWidget(frame)
            
        self.frames["AmbulatorSheet"].target_sheet = self.frames["AmbulanceSheet"]

        # Проверка наличия и валидности файла базы данных при старте
        self._check_file_path()

    def _check_file_path(self):
        """Проверяет путь к файлу. Если путь не задан или файл перемещен — запрашивает выбор."""
        while not self.db.has_valid_file_path():
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg.setWindowTitle("Выбор базы данных")
            
            if self.db.file_path and not self.db.has_valid_file_path():
                msg.setText("Файл базы данных перемещён или удалён!")
                msg.setInformativeText(
                    f"Не удалось найти файл по пути:\n{self.db.file_path}\n\n"
                    "Пожалуйста, укажите новое местоположение или создайте новый файл."
                )
            else:
                msg.setText("Файл сохранения data.json не выбран!")
                msg.setInformativeText("Выберите путь к зашифрованной базе данных для продолжения работы.")
            
            btn_select = msg.addButton("Выбрать / Создать data.json", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            btn_exit = msg.addButton("Выход из программы", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            msg.exec()

            if msg.clickedButton() == btn_exit:
                sys.exit(0)

            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Выберите или создайте файл data.json",
                "data.json",
                "JSON Files (*.json)"
            )
            
            if file_path:
                self.db.set_file_path(file_path)
                # Если файла не существовало, инициализируем базовую структуру
                if not os.path.exists(file_path):
                    self.db.save_data({"doctors": [], "ambulator": [], "ambulance": []})
                
                # Загружаем данные в открытые таблицы
                self._reload_all_sheets()

    def _reload_all_sheets(self):
        """Перезагружает данные во всех дочерних таблицах после выбора файла."""
        for frame in self.frames.values():
            if hasattr(frame, 'load_data'):
                frame.load_data()

    def _create_sidebar(self, parent_layout):
        self.sidebar_frame = QtWidgets.QFrame()
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setStyleSheet(get_style("sidebar"))

        sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(15, 25, 15, 25)
        sidebar_layout.setSpacing(10)

        self.logo_label = QtWidgets.QLabel("Журнал")
        logo_font = QtGui.QFont("Arial", 16, QtGui.QFont.Weight.Bold)
        self.logo_label.setFont(logo_font)
        sidebar_layout.addWidget(self.logo_label)

        sidebar_layout.addSpacing(15)

        self.btn_ambulator = QtWidgets.QPushButton("Амбулаторное")
        self.btn_ambulator.setFixedHeight(40)
        self.btn_ambulator.clicked.connect(self.click_ambulator)
        sidebar_layout.addWidget(self.btn_ambulator)

        self.btn_ambulance = QtWidgets.QPushButton("Скорая помощь")
        self.btn_ambulance.setFixedHeight(40)
        self.btn_ambulance.clicked.connect(self.click_ambulance)
        sidebar_layout.addWidget(self.btn_ambulance)

        sidebar_layout.addStretch()

        self.btn_admin_panel = QtWidgets.QPushButton("Настройки")
        self.btn_admin_panel.setFixedHeight(40)
        self.btn_admin_panel.clicked.connect(self.click_admin_panel_nav)
        sidebar_layout.addWidget(self.btn_admin_panel)

        parent_layout.addWidget(self.sidebar_frame)

    def click_ambulator(self):
        self.show_screen("AmbulatorSheet")

    def click_ambulance(self):
        self.show_screen("AmbulanceSheet")

    def click_admin_panel_nav(self):
        self.show_screen("AdminPanel")

    def show_screen(self, screen_name: str):
        if screen_name in self.frames:
            frame = self.frames[screen_name]
            self.stacked_widget.setCurrentWidget(frame)
        else:
            print(
                f"Ошибка: Экран '{screen_name}' не найден в зарегистрированных фреймах."
            )