import sys
from PySide6 import QtWidgets, QtCore

from ui.functions.print import print_057
from ui.sheet_template import BaseSheet


class AmbulanceSheet(BaseSheet):

    DEFAULT_WIDTHS = {
        "Дата": 95,
        "Время": 70,
        "ФИО пациента": 200,
        "Пол": 90,
        "Дата рождения": 110,
        "Домашний адрес": 240,
        "Признаки/симптомы неотложного/экстренного состояния": 300,
        "Код МКБ": 90,
        "Диагноз": 240,
        "Назначенное лечение": 300,
        "Врач, назначивший лечение": 200,
        "Исход": 140,
        "Примечание": 240,
    }

    def __init__(self, parent=None):
        columns = [
            "Дата",
            "Время",
            "ФИО пациента",
            "Пол",
            "Дата рождения",
            "Домашний адрес",
            "Признаки/симптомы неотложного/экстренного состояния",
            "Код МКБ",
            "Диагноз",
            "Назначенное лечение",
            "Врач, назначивший лечение",
            "Исход",
            "Примечание",
            "Печать",
        ]

        super().__init__(
            db_key="ambulance",
            columns=columns,
            mkb_col_idx=8,
            mkb_code_col_idx=7,
            address_col_idx=5,
            gender_col_idx=3,        # "Пол"
            medication_col_idx=9,    # "Назначенное лечение"
            doctor_col_idx=10,       # "Врач, назначивший лечение"
            outcome_col_idx=11,      # "Исход"
            parent=parent,
        )

        self.load_data()

    def get_centered_columns(self) -> tuple:
        return (0, 1, 7)

    def _setup_action_button(self, row: int):
        btn_print = QtWidgets.QPushButton("Печать")
        btn_print.clicked.connect(
            lambda checked=False, r=row: self.on_print_clicked(r)
        )

        btn_container = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_container)
        btn_layout.addWidget(btn_print)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        print_col_idx = self.table.columnCount() - 1
        self.table.setCellWidget(row, print_col_idx, btn_container)


    def on_print_clicked(self, row: int):
        """Собирает данные строки {заголовок: текст} и открывает печать направления."""
        data = {}
        for col in range(self.table.columnCount() - 1):
            header_item = self.table.horizontalHeaderItem(col)
            item = self.table.item(row, col)
            if header_item:
                data[header_item.text()] = item.text().strip() if item else ""
        print_057(data, parent=self)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = AmbulanceSheet()
    window.resize(1400, 600)
    window.show()
    sys.exit(app.exec())