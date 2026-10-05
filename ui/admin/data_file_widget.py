import os

from PySide6 import QtCore, QtGui, QtWidgets

from back.data_manager import DataManager
from back.user.users import AdminSession
from ui.functions.data_file import create_new_data_file, pick_existing_data_file


class DataFileWidget(QtWidgets.QGroupBox):
    """Показывает путь к файлу данных. Менять файл может только вошедший администратор."""

    def __init__(self, parent=None):
        super().__init__("Файл данных", parent)
        self.db = DataManager()
        self.session = AdminSession()

        layout = QtWidgets.QVBoxLayout(self)

        self.lbl_path = QtWidgets.QLabel()
        self.lbl_path.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.lbl_path.setWordWrap(True)
        layout.addWidget(self.lbl_path)

        self.lbl_info = QtWidgets.QLabel()
        layout.addWidget(self.lbl_info)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_change = QtWidgets.QPushButton("Выбрать другой файл…")
        self.btn_change.clicked.connect(lambda: pick_existing_data_file(self))
        self.btn_new = QtWidgets.QPushButton("Создать новый файл…")
        self.btn_new.clicked.connect(lambda: create_new_data_file(self))
        self.btn_folder = QtWidgets.QPushButton("Открыть папку")
        self.btn_folder.clicked.connect(self._open_folder)
        for btn in (self.btn_change, self.btn_new, self.btn_folder):
            buttons.addWidget(btn)
        buttons.addStretch()
        layout.addLayout(buttons)

        # При любой смене файла (из любого места программы) обновляем подпись
        self.db.add_path_listener(self.refresh)
        self.refresh()

    def refresh(self):
        info = self.db.get_file_info()
        self.lbl_path.setText(f"<b>Путь:</b> {info['path'] or 'не выбран'}")
        if info["exists"]:
            self.lbl_info.setText(
                f"Размер: {info['size'] / 1024:.1f} КБ · изменён: {info['modified']}"
            )
        else:
            self.lbl_info.setText("<span style='color:#c0392b'>Файл не найден</span>")

        is_admin = self.session.is_authenticated()
        self.btn_change.setEnabled(is_admin)
        self.btn_new.setEnabled(is_admin)
        self.btn_folder.setEnabled(info["exists"])
        tip = "" if is_admin else "Войдите как администратор, чтобы сменить файл"
        self.btn_change.setToolTip(tip)
        self.btn_new.setToolTip(tip)

    def _open_folder(self):
        folder = os.path.dirname(self.db.file_path)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))