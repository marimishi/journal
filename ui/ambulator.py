import sys
from PySide6 import QtWidgets, QtCore

from ui.functions.copy import copy_row_by_headers
from ui.functions.print import print_conclusion
from ui.sheet_template import BaseSheet


class AmbulatorSheet(BaseSheet):

    DEFAULT_WIDTHS = {
        "Дата": 95,
        "Время": 70,
        "ФИО врача, вызвавшего БСМП": 200,
        "ФИО пациента": 200,
        "Дата рождения": 110,
        "Домашний адрес": 240,
        "Код МКБ": 90,
        "Диагноз": 240,
        "МО по месту прикрепления пациента": 260,
        "Время прибытия БСМП": 110,
        "АД": 80,
        "Температура": 100,
        "Пульс": 70,
        "Сатурация": 90,
        "Сахар крови": 100,
        "ЭКГ": 200,
        "Назначенное лечение": 300,
    }

    ACTION_COLUMNS = 2  # «Копировать» и «Печать»

    # Колонки прежней версии файла — по ним читаются старые записи
    LEGACY_COLUMNS = [
        "Дата", "Время", "ФИО врача, вызвавшего БСМП", "ФИО пациента", "Дата рождения",
        "Домашний адрес", "Код МКБ", "Диагноз", "МО по месту прикрепления пациента",
        "Время прибытия БСМП",
    ]

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
            "АД",
            "Температура",
            "Пульс",
            "Сатурация",
            "Сахар крови",
            "ЭКГ",
            "Назначенное лечение",
            "Копировать",
            "Печать",
        ]

        super().__init__(
            db_key="ambulator",
            columns=columns,
            mkb_col_idx=7,
            mkb_code_col_idx=None,
            doctor_col_idx=2,        # "ФИО врача, вызвавшего БСМП"
            address_col_idx=5,       # "Домашний адрес"
            mo_col_idx=8,            # "МО по месту прикрепления пациента"
            medication_col_idx=16,   # "Назначенное лечение"
            parent=parent,
        )

        self.load_data()

    def get_centered_columns(self) -> tuple:
        return (0, 1, 6, 10, 11, 12, 13, 14)

    def _make_button_cell(self, text: str, handler, col: int, row: int):
        btn = QtWidgets.QPushButton(text)
        btn.clicked.connect(lambda checked=False, r=row: handler(r))

        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.addWidget(btn)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, col, container)

    def _setup_action_button(self, row: int):
        count = self.table.columnCount()
        self._make_button_cell("Копировать", self.on_copy_clicked, count - 2, row)
        self._make_button_cell("Печать", self.on_print_clicked, count - 1, row)

    def on_print_clicked(self, row: int):
        """Собирает данные строки и открывает печать заключения."""
        data = {}
        for col in range(self.data_cols):
            header_item = self.table.horizontalHeaderItem(col)
            item = self.table.item(row, col)
            if header_item:
                data[header_item.text()] = item.text().strip() if item else ""
        # В форме врач и время называются как в журнале скорой помощи
        data["Врач, назначивший лечение"] = data.get("ФИО врача, вызвавшего БСМП", "")
        data["Время"] = data.get("Время прибытия БСМП") or data.get("Время", "")
        print_conclusion(data, parent=self)

    def on_copy_clicked(self, row_idx: int):
        if not self.target_sheet or not hasattr(self.target_sheet, "table"):
            QtWidgets.QMessageBox.warning(
                self, "Предупреждение", "Не задан целевой лист для копирования!"
            )
            return

        # «Время прибытия БСМП» из этого журнала становится «Временем» в журнале скорой помощи
        new_row = copy_row_by_headers(
            self.table,
            row_idx,
            self.target_sheet.table,
            aliases={"Время прибытия БСМП": "Время"},
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