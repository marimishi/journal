from PySide6 import QtWidgets, QtCore
from back.user.manage_doctors import DoctorsManager

class DoctorsTableWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = DoctorsManager()
        self._init_ui()
        self.load_doctors_to_table()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        input_layout = QtWidgets.QHBoxLayout()
        self.input_name = QtWidgets.QLineEdit()
        self.input_name.setPlaceholderText("Введите ФИО врача...")
        self.input_name.setFixedHeight(30)
        
        btn_add = QtWidgets.QPushButton("Добавить")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self.handle_add_doctor)

        input_layout.addWidget(self.input_name)
        input_layout.addWidget(btn_add)
        layout.addLayout(input_layout)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ФИО Врача", ""])
        
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)

    def load_doctors_to_table(self):
        doctors = self.manager.get_all_doctors()
        self.table.setRowCount(0)
        
        for row_idx, name in enumerate(doctors):
            self.table.insertRow(row_idx)
            
            item = QtWidgets.QTableWidgetItem(name)
            self.table.setItem(row_idx, 0, item)
            
            btn_delete = QtWidgets.QPushButton("X")
            btn_delete.setFixedSize(28, 24)
            btn_delete.setStyleSheet("border: none; background: transparent; font-size: 14px;")
            
            btn_delete.clicked.connect(lambda checked=False, n=name: self.handle_delete_doctor(n))
            
            container = QtWidgets.QWidget()
            btn_layout = QtWidgets.QHBoxLayout(container)
            btn_layout.addWidget(btn_delete)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            self.table.setCellWidget(row_idx, 1, container)

    def handle_add_doctor(self):
        name = self.input_name.text()
        if self.manager.add_doctor(name):
            self.load_doctors_to_table()
            self.input_name.clear()
        else:
            QtWidgets.QMessageBox.warning(
                self, 
                "Ошибка", 
                "Не удалось добавить врача (поле пустое или такой врач уже существует)."
            )

    def handle_delete_doctor(self, doctor_name: str):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить врача:\n{doctor_name}?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            if self.manager.delete_doctor(doctor_name):
                self.load_doctors_to_table()
            else:
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Ошибка", 
                    "Не удалось удалить врача из базы данных."
                )
