import sys
from PySide6 import QtWidgets, QtCore

from ui.functions.copy import copy_row_by_headers
from ui.sheet_template import BaseSheet


class AmbulatorSheet(BaseSheet):

    def __init__(self, target_sheet=None, parent=None):
        self.target_sheet = target_sheet

        columns = [
            "Дата",
            "Время",
            "ФИО врача, вызвавшего БСМП",
            "ФИО пациента",
            "Дата рождения",
            "Домашний адрес",
            "Код МКБ",
            "Диагноз",
            "МО по месту прикрепления пациента",
            "Время прибытия БСМП",
            "Копировать",
        ]

        super().__init__(
            db_key="ambulator",
            columns=columns,
            mkb_col_idx=7,
            mkb_code_col_idx=None,
            parent=parent,
        )

        self.header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.header.setSectionResizeMode(
            len(self.columns) - 1,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )

        self.load_data()

    def get_centered_columns(self) -> tuple:
        return (0, 1, 6)

    def _setup_action_button(self, row: int):
        btn_copy = QtWidgets.QPushButton("Копировать")
        btn_copy.clicked.connect(
            lambda checked=False, r=row: self.on_copy_clicked(r)
        )

        btn_container = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_container)
        btn_layout.addWidget(btn_copy)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        copy_col_idx = self.table.columnCount() - 1
        self.table.setCellWidget(row, copy_col_idx, btn_container)

    def on_copy_clicked(self, row_idx: int):
        if not self.target_sheet or not hasattr(self.target_sheet, "table"):
            QtWidgets.QMessageBox.warning(
                self, "Предупреждение", "Не задан целевой лист для копирования!"
            )
            return

        new_row = copy_row_by_headers(
            self.table, row_idx, self.target_sheet.table
        )

        if hasattr(self.target_sheet, "save_data"):
            self.target_sheet.save_data()

        QtWidgets.QMessageBox.information(
            self,
            "Успех",
            f"Запись скопирована в целевую таблицу (строка {new_row + 1}).",
        )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    target_sheet = AmbulatorSheet()
    main_sheet = AmbulatorSheet(target_sheet=target_sheet)

    tabs = QtWidgets.QTabWidget()
    tabs.addTab(main_sheet, "Исходный лист")
    tabs.addTab(target_sheet, "Приемник")
    tabs.resize(1300, 600)
    tabs.show()

    sys.exit(app.exec())