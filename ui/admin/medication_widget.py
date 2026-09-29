from PySide6 import QtWidgets, QtCore
from back.data_manager import DataManager
from ui.sheet_template import DEFAULT_MEDICATIONS


class MedicationManagerWidget(QtWidgets.QWidget):
    """Виджет в дашборде админа для управления списком препаратов."""

    medications_updated = QtCore.Signal()  # Сигнал об изменении списка препаратов

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DataManager()

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("<b>Управление справочником препаратов:</b>")
        layout.addWidget(title)

        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        # Поле для добавления нового препарата
        input_layout = QtWidgets.QHBoxLayout()
        self.txt_input = QtWidgets.QLineEdit()
        self.txt_input.setPlaceholderText("Введите название препарата, дозировку и способ применения...")
        btn_add = QtWidgets.QPushButton("＋ Добавить")
        btn_add.clicked.connect(self.add_medication)

        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(btn_add)
        layout.addLayout(input_layout)

        # Кнопки действия
        btn_layout = QtWidgets.QHBoxLayout()
        btn_delete = QtWidgets.QPushButton("Удалить выбранное")
        btn_delete.clicked.connect(self.delete_medication)

        btn_reset = QtWidgets.QPushButton("Сбросить к стандартам")
        btn_reset.clicked.connect(self.reset_defaults)

        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_reset)
        layout.addLayout(btn_layout)

        self.load_medications()

    def load_medications(self):
        self.list_widget.clear()
        data = self.db.load_data()
        meds = data.get("medications", DEFAULT_MEDICATIONS)
        for med in meds:
            self.list_widget.addItem(med)

    def save_medications(self):
        data = self.db.load_data()
        meds = [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
        ]
        data["medications"] = meds
        self.db.save_data(data)
        self.medications_updated.emit()

    def add_medication(self):
        text = self.txt_input.text().strip()
        if text:
            self.list_widget.addItem(text)
            self.txt_input.clear()
            self.save_medications()

    def delete_medication(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.list_widget.takeItem(self.list_widget.row(item))
        self.save_medications()

    def reset_defaults(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение",
            "Вернуть базовый список препаратов?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.list_widget.clear()
            for med in DEFAULT_MEDICATIONS:
                self.list_widget.addItem(med)
            self.save_medications()