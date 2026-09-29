import sys
from PySide6 import QtWidgets, QtCore

from ui.functions.print import print_057
from ui.sheet_template import BaseSheet


class AmbulanceSheet(BaseSheet):

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
            parent=parent,
        )

        self.header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.header.setSectionResizeMode(
            len(self.columns) - 1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

        self.load_data()

    def get_centered_columns(self) -> tuple:
        return (0, 1, 7)

    def _setup_action_button(self, row: int):
        btn_print = QtWidgets.QPushButton("Печать")
        btn_print.clicked.connect(lambda checked=False, r=row: print_057())

        btn_container = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_container)
        btn_layout.addWidget(btn_print)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        print_col_idx = self.table.columnCount() - 1
        self.table.setCellWidget(row, print_col_idx, btn_container)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = AmbulanceSheet()
    window.resize(1400, 600)
    window.show()
    sys.exit(app.exec())