import os
from datetime import date, datetime
import pandas as pd
from PySide6 import QtCore, QtGui, QtWidgets

from back.data_manager import DataManager
from ui.combo_box.mkb import MkbDelegate
from ui.functions.lock_policy import apply_row_lock_policy, is_record_locked

DEFAULT_MEDICATIONS = [
    "Tab. Captoprili 25 mg - 1 таб., внутрь",
    "Tab. Moxonidini 0,2 mg - 1 таб., внутрь",
    "Tab. Moxonidini 0,4 mg - 1 таб., внутрь",
    "Solutio Glucosi 5% – 200 ml (в/в кап.) №1",
    "Solutio Glucosi 40% – 10 ml (в/в струйно) №1",
    "Solutio Natrii chloridi 0,9% – 200 ml (в/в кап.) №1",
    "Nitroglycerini spray - 1 доза, под язык",
    "Solutio Magnesii sulfatis 25% – 10 ml (в/в медленно) №1",
    "Solutio Furosemidi 1% (10 мг/мл) – 2 ml (в/в или в/м) №1",
    "Solutio Ketoprofeni 10% (100 мг/2 мл) – 2 ml (в/м или в/в) №1",
    "Solutio Chloropyramini 2% (20 мг/мл) – 1 ml (в/м или в/в) №1",
    "Solutio Platyphyllini hydrotartratis 0,2% – 1 ml (п/к или в/м) №1",
    "Solutio Prednisoloni 30 мг/мл – 1–3 ml (в/в или в/м) №1",
    "Solutio Dexamethasoni 4 мг/мл – 1 ml (в/в или в/м) №1",
    "Solutio Metoclopramidi 0,5% (10 мг/2 мл) – 2 ml (в/м или в/в) №1",
    "Solutio Ondansetroni (Latran) – 5 ml (в/в кап. или в/в струйно) №1",
    "Solutio Adrenalini 0,1% – 1 ml (в/м) №1",
    "Astmasoli aerosoli - 1–2 дозы, ингаляционно",
    "Tab. Nifedipini 10 mg - 1 таб., внутрь",
    "Tab. Anaprilini (Propranololum) 10 mg - 1 таб., внутрь",
    "Tab. Anaprilini (Propranololum) 40 mg - 1 таб., внутрь",
    "Tab. Metoprololi 25 mg - 1 таб., внутрь",
    "Tab. Metoprololi 50 mg - 1 таб., внутрь",
    "Tab. Acidi acetylsalicylici (Aspirinum) 150–300 mg - 1 таб., разжевать",
    "Corvaloli 20–30 капель (внутрь)",
]


class AddressDelegate(QtWidgets.QStyledItemDelegate):
    """Делегат с автодополнением улиц."""

    def __init__(self, streets_list: list[str], parent=None):
        super().__init__(parent)
        self.streets_list = streets_list

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        completer = QtWidgets.QCompleter(self.streets_list, editor)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        editor.setCompleter(completer)
        return editor


class ListChoiceDelegate(QtWidgets.QStyledItemDelegate):
    """Выпадающий список (QComboBox) с возможностью ручного ввода/поиска."""

    def __init__(self, items_list: list[str], parent=None):
        super().__init__(parent)
        self.items_list = items_list

    def createEditor(self, parent, option, index):
        combo = QtWidgets.QComboBox(parent)
        combo.setEditable(True)
        combo.addItems([""] + self.items_list)

        completer = combo.completer()
        if completer:
            completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        return combo

    def setEditorData(self, editor, index):
        text = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole) or ""
        editor.setCurrentText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), QtCore.Qt.ItemDataRole.EditRole)


class BaseSheet(QtWidgets.QWidget):

    def __init__(
        self,
        db_key: str,
        columns: list[str],
        mkb_col_idx: int,
        address_col_idx: int = None,
        doctor_col_idx: int = None,
        medication_col_idx: int = None,
        mkb_code_col_idx: int = None,
        parent=None,
    ):
        super().__init__(parent)

        self.db = DataManager()
        self.db_key = db_key
        self.columns = columns
        self.mkb_col_idx = mkb_col_idx
        self.address_col_idx = address_col_idx
        self.doctor_col_idx = doctor_col_idx
        self.medication_col_idx = medication_col_idx
        self.mkb_code_col_idx = mkb_code_col_idx
        self.is_loading = False

        # Загрузка внешних справочников
        self.mkb_df = self._load_mkb_data("MKB.csv")
        self.streets_list = self._load_streets_data("tyumen_streets.csv")
        self.doctors_list = self._load_doctors_data()
        self.medications_list = self._load_medications_data()

        self.layout = QtWidgets.QVBoxLayout(self)

        # Кнопка добавления записи
        self.btn_add = QtWidgets.QPushButton("＋ Добавить новую запись")
        self.btn_add.clicked.connect(self.add_row)
        self.layout.addWidget(self.btn_add)

        # Таблица
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)

        self.header = self.table.horizontalHeader()
        self.header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Interactive
        )
        self.header.setSectionResizeMode(
            len(self.columns) - 1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

        # 1. Делегат МКБ
        if self.mkb_code_col_idx is not None:
            self.mkb_delegate = MkbDelegate(
                self.mkb_df, self.table, code_col_idx=self.mkb_code_col_idx
            )
        else:
            self.mkb_delegate = MkbDelegate(self.mkb_df, self.table)

        self.table.setItemDelegateForColumn(
            self.mkb_col_idx, self.mkb_delegate
        )

        # 2. Делегат адресов
        if self.address_col_idx is not None and self.streets_list:
            self.address_delegate = AddressDelegate(self.streets_list, self.table)
            self.table.setItemDelegateForColumn(
                self.address_col_idx, self.address_delegate
            )

        # 3. Делегат врачей
        if self.doctor_col_idx is not None:
            self.doctor_delegate = ListChoiceDelegate(self.doctors_list, self.table)
            self.table.setItemDelegateForColumn(
                self.doctor_col_idx, self.doctor_delegate
            )

        # 4. Делегат препаратов
        if self.medication_col_idx is not None:
            self.medication_delegate = ListChoiceDelegate(self.medications_list, self.table)
            self.table.setItemDelegateForColumn(
                self.medication_col_idx, self.medication_delegate
            )

        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self._start_lock_timer()

    def _load_mkb_data(self, file_path: str) -> pd.DataFrame:
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path, sep=";", dtype=str, encoding="utf-8")
                df.columns = df.columns.str.strip()
                return df.dropna(subset=["MKB_CODE", "MKB_NAME"])
        except Exception as e:
            print(f"Ошибка загрузки МКБ-файла: {e}")
        return pd.DataFrame(columns=["MKB_CODE", "MKB_NAME"])

    def _load_streets_data(self, file_path: str) -> list[str]:
        """Универсальная загрузка файла улиц (CSV/TSV)."""
        try:
            if os.path.exists(file_path):
                for sep in ["\t", ";", ","]:
                    df = pd.read_csv(file_path, sep=sep, dtype=str, encoding="utf-8")
                    if len(df.columns) >= 1:
                        col_name = df.columns[0]
                        streets = df[col_name].dropna().str.strip().tolist()
                        return [s for s in streets if s and s.lower() != "улица"]
        except Exception as e:
            print(f"Ошибка загрузки улиц: {e}")
        return []

    def _load_doctors_data(self) -> list[str]:
        """Загрузка списка докторов из общего файла данных DataManager."""
        try:
            if self.db.has_valid_file_path():
                data = self.db.load_data()
                doctors = data.get("doctors", [])
                if isinstance(doctors, list):
                    return doctors
        except Exception as e:
            print(f"Ошибка загрузки врачей: {e}")
        return []

    def _load_medications_data(self) -> list[str]:
        """Загрузка препаратов из data.json или использование дефолтных."""
        try:
            if self.db.has_valid_file_path():
                data = self.db.load_data()
                meds = data.get("medications")
                if isinstance(meds, list) and len(meds) > 0:
                    return meds
                else:
                    data["medications"] = DEFAULT_MEDICATIONS
                    self.db.save_data(data)
                    return DEFAULT_MEDICATIONS
        except Exception as e:
            print(f"Ошибка загрузки препаратов: {e}")
        return DEFAULT_MEDICATIONS

    def refresh_doctors_list(self):
        """Обновляет список врачей из базы данных при изменении настроек кабинета."""
        self.doctors_list = self._load_doctors_data()

    def _start_lock_timer(self):
        """Запускает таймер, обновляющий состояние блокировки строк каждую минуту."""
        self.lock_timer = QtCore.QTimer(self)
        self.lock_timer.setInterval(60000)
        self.lock_timer.timeout.connect(self._check_row_locks)
        self.lock_timer.start()

    def _check_row_locks(self):
        """Проверяет все строки таблицы и блокирует те, у которых истек тайм-аут."""
        if self.is_loading or self.table.rowCount() == 0:
            return

        for row in range(self.table.rowCount()):
            created_at_item = self.table.item(row, 0)
            if not created_at_item:
                continue

            created_at = created_at_item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not created_at:
                continue

            apply_row_lock_policy(self.table, row, created_at)

    def get_centered_columns(self) -> tuple:
        return (0, 1, 6)

    def _setup_action_button(self, row: int):
        pass

    def load_data(self):
        """Загрузка данных журнала из зашифрованного data.json."""
        if not self.db.has_valid_file_path():
            return

        self.is_loading = True
        self.table.setRowCount(0)

        data = self.db.load_data()
        records = data.get(self.db_key, [])

        for record_data in records:
            row_count = self.table.rowCount()
            self.table.insertRow(row_count)

            created_at = record_data.get("created_at", "")
            row_values = record_data.get("values", [])

            for col_idx in range(self.table.columnCount() - 1):
                text = (
                    row_values[col_idx] if col_idx < len(row_values) else ""
                )
                item = QtWidgets.QTableWidgetItem(text)

                if col_idx in self.get_centered_columns():
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row_count, col_idx, item)

            if self.table.item(row_count, 0):
                self.table.item(row_count, 0).setData(
                    QtCore.Qt.ItemDataRole.UserRole, created_at
                )

            self._setup_action_button(row_count)
            apply_row_lock_policy(self.table, row_count, created_at)

        self.is_loading = False

    def add_row(self):
        """Добавление новой записи в таблицу с предустановкой доктора по умолчанию."""
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for col_idx in range(self.table.columnCount() - 1):
            item = QtWidgets.QTableWidgetItem("")
            if col_idx in self.get_centered_columns():
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_count, col_idx, item)

        self.table.item(row_count, 0).setData(
            QtCore.Qt.ItemDataRole.UserRole, now_str
        )

        today_str = date.today().strftime("%d.%m.%Y")
        time_str = datetime.now().strftime("%H:%M")

        self.table.item(row_count, 0).setText(today_str)
        self.table.item(row_count, 1).setText(time_str)

        if self.doctor_col_idx is not None and self.doctors_list:
            default_doctor = self.doctors_list[0] if len(self.doctors_list) > 0 else ""
            self.table.item(row_count, self.doctor_col_idx).setText(default_doctor)

        self._setup_action_button(row_count)
        apply_row_lock_policy(self.table, row_count, now_str)

        self.save_data()

        focus_col = 2
        self.table.setCurrentCell(row_count, focus_col)
        item_to_edit = self.table.item(row_count, focus_col)
        if item_to_edit:
            self.table.editItem(item_to_edit)

    def on_item_changed(self, item: QtWidgets.QTableWidgetItem):
        if self.is_loading:
            return

        row = item.row()
        created_at_item = self.table.item(row, 0)
        if created_at_item:
            created_at = created_at_item.data(QtCore.Qt.ItemDataRole.UserRole)
            if is_record_locked(created_at):
                return

        self.save_data()

    def save_data(self):
        if not self.db.has_valid_file_path() or self.is_loading:
            return

        full_db_data = self.db.load_data()
        records = []

        for row in range(self.table.rowCount()):
            created_at_item = self.table.item(row, 0)
            created_at = (
                created_at_item.data(QtCore.Qt.ItemDataRole.UserRole)
                if created_at_item
                else ""
            )

            row_values = []
            for col in range(self.table.columnCount() - 1):
                item = self.table.item(row, col)
                row_values.append(item.text() if item else "")

            records.append({"created_at": created_at, "values": row_values})

        full_db_data[self.db_key] = records
        self.db.save_data(full_db_data)