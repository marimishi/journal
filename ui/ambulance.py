import sys
import pandas as pd
from datetime import date, datetime
from PySide6 import QtWidgets, QtCore, QtGui
from ui.functions.print import print_057
from ui.combo_box.mkb import MkbDelegate, MkbComboBox

class AmbulanceSheet(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. Загрузка данных МКБ
        self.mkb_df = self._load_mkb_data("MKB.csv")

        layout = QtWidgets.QVBoxLayout(self)

        self.btn_add = QtWidgets.QPushButton("＋ Добавить новую запись")
        self.btn_add.clicked.connect(self.add_row)
        layout.addWidget(self.btn_add)

        # 2. Добавлена колонка "Код МКБ" перед "Диагноз"
        columns = [
            "Дата", "Время", "ФИО пациента", "Пол", 
            "Дата рождения", "Домашний адрес", 
            "Признаки/симптомы неотложного/экстренного состояния", 
            "Код МКБ", "Диагноз", "Назначенное лечение", 
            "Врач, назначивший лечение", "Исход", "Примечание",
            "Печать"
        ]

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(len(columns) - 1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        # 3. Настройка делегата МКБ для колонки "Диагноз" (индекс 8)
        self.mkb_delegate = MkbDelegate(self.mkb_df, self.table, code_col_idx=7)
        self.table.setItemDelegateForColumn(8, self.mkb_delegate)

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

        for col_idx in range(self.table.columnCount() - 1):
            item = QtWidgets.QTableWidgetItem("")
            # Выравнивание по центру для даты (0), времени (1) и Кода МКБ (7)
            if col_idx in (0, 1, 7):
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, col_idx, item)

        today_str = date.today().strftime("%d.%m.%Y")
        self.table.item(row_count, 0).setText(today_str)
        
        time_str = datetime.now().strftime("%H:%M")
        self.table.item(row_count, 1).setText(time_str)

        btn_print = QtWidgets.QPushButton("Печать")
        btn_print.clicked.connect(lambda checked=False, r=row_count: print_057())
        
        btn_container = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(btn_container)
        btn_layout.addWidget(btn_print)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        print_col_idx = self.table.columnCount() - 1
        self.table.setCellWidget(row_count, print_col_idx, btn_container)

        self.table.setCurrentCell(row_count, 2)
        self.table.editItem(self.table.item(row_count, 2))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = AmbulanceSheet()
    window.resize(1400, 600)
    window.show()
    sys.exit(app.exec())