import sys
import pandas as pd
from datetime import date, datetime
from PySide6 import QtWidgets, QtCore, QtGui
from ui.combo_box.mkb import MkbDelegate
from ui.functions.copy import copy_row_by_headers


class AmbulatorSheet(QtWidgets.QWidget):
    def __init__(self, target_sheet=None, parent=None):
        """
        :param target_sheet: Ссылка на другой виджет (лист), куда будут копироваться данные.
        """
        super().__init__(parent)

        self.target_sheet = target_sheet
        self.mkb_df = self._load_mkb_data("MKB.csv")

        layout = QtWidgets.QVBoxLayout(self)

        self.btn_add = QtWidgets.QPushButton("＋ Добавить новую запись")
        self.btn_add.clicked.connect(self.add_row)
        layout.addWidget(self.btn_add)

        columns = [
            "Дата", "Время", "ФИО врача, вызвавшего БСМП", "ФИО пациента", 
            "Дата рождения", "Домашний адрес", "Код МКБ", "Диагноз", 
            "МО по месту прикрепления пациента", "Время прибытия БСМП",
            "Копировать"
        ]

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        # Колонка кнопки "Копировать" подгоняется по содержимому
        header.setSectionResizeMode(len(columns) - 1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        self.mkb_delegate = MkbDelegate(self.mkb_df, self.table)
        self.table.setItemDelegateForColumn(7, self.mkb_delegate)

        layout.addWidget(self.table)

    def _load_mkb_data(self, file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(file_path, sep=';', dtype=str, encoding='utf-8')
            df.columns = df.columns.str.strip()
            df = df.dropna(subset=['MKB_CODE', 'MKB_NAME'])
            return df
        except Exception as e:
            print(f"Ошибка загрузки МКБ-файла: {e}")
            return pd.DataFrame(columns=['MKB_CODE', 'MKB_NAME'])

    def add_row(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        # Создаем ячейки данных (пропуская последнюю колонку под кнопку)
        for col_idx in range(self.table.columnCount() - 1):
            item = QtWidgets.QTableWidgetItem("")
            if col_idx in (0, 1, 6):
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, col_idx, item)

        today_str = date.today().strftime("%d.%m.%Y")
        self.table.item(row_count, 0).setText(today_str)
        
        time_str = datetime.now().strftime("%H:%M")
        self.table.item(row_count, 1).setText(time_str)

        # Создание кнопки "Копировать"
        btn_copy = QtWidgets.QPushButton("Копировать")
        btn_copy.clicked.connect(lambda checked=False, r=row_count: self.on_copy_clicked(r))

        btn_container = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_container)
        btn_layout.addWidget(btn_copy)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        copy_col_idx = self.table.columnCount() - 1
        self.table.setCellWidget(row_count, copy_col_idx, btn_container)

        # Настраиваем фокус
        self.table.setCurrentCell(row_count, 2)
        self.table.editItem(self.table.item(row_count, 2))

    def on_copy_clicked(self, row_idx: int):
        """Обработчик нажатия на кнопку Копировать."""
        if not self.target_sheet or not hasattr(self.target_sheet, 'table'):
            QtWidgets.QMessageBox.warning(self, "Предупреждение", "Не задан целевой лист для копирования!")
            return

        new_row = copy_row_by_headers(self.table, row_idx, self.target_sheet.table)
        QtWidgets.QMessageBox.information(
            self, 
            "Успех", 
            f"Запись скопирована в целевую таблицу (строка {new_row + 1})."
        )


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Демонстрация взаимодействия двух листов
    target_sheet = AmbulatorSheet()
    main_sheet = AmbulatorSheet(target_sheet=target_sheet)

    tabs = QtWidgets.QTabWidget()
    tabs.addTab(main_sheet, "Исходный лист")
    tabs.addTab(target_sheet, "Приемник")
    tabs.resize(1300, 600)
    tabs.show()

    sys.exit(app.exec())