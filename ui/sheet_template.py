import os
import re
from datetime import date, datetime
import pandas as pd
from PySide6 import QtCore, QtGui, QtWidgets

from back.data_manager import DataManager
from back.user.users import AdminSession
from ui.combo_box.mkb import SearchableComboBox, ListChoiceDelegate
from ui.functions.lock_policy import apply_row_lock_policy, is_record_locked
from ui.functions.paths import resource_path

from data import DEFAULT_MEDICATIONS, HOSPITALS


class AddressDelegate(QtWidgets.QStyledItemDelegate):
    """Делегат адресов в стиле MkbDelegate с исправленным автооткрытием."""

    def __init__(self, streets_list: list[str], parent=None):
        super().__init__(parent)
        self.streets_list = streets_list

    def createEditor(self, parent, option, index):
        editor = SearchableComboBox(
            self.streets_list, placeholder="Введите адрес...", parent=parent
        )
        editor.selected_text = None

        def on_selected(text):
            editor.selected_text = text
            self.commitData.emit(editor)
            self.closeEditor.emit(
                editor, QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache
            )

        editor.item_selected.connect(on_selected)
        
        # Автоматически раскрываем выпадающий список
        QtCore.QTimer.singleShot(0, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole) or ""
        editor.lineEdit().setText(value)
        editor.lineEdit().selectAll()

    def setModelData(self, editor, model, index):
        if getattr(editor, "selected_text", None) is not None:
            model.setData(index, editor.selected_text, QtCore.Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.lineEdit().text(), QtCore.Qt.ItemDataRole.EditRole)


class MkbComboBox(QtWidgets.QComboBox):
    
    mkb_selected = QtCore.Signal(str, str)

    def __init__(self, mkb_df: pd.DataFrame, parent=None, code_mode: bool = False):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        self._text_to_data = {}  # Словарь для поиска данных по тексту из комплитера

        if not mkb_df.empty:
            codes = mkb_df['MKB_CODE'].astype(str).str.strip()
            names = mkb_df['MKB_NAME'].astype(str).str.strip()
            for code, name in zip(codes, names):
                display_str = f"{code} - {name}"
                self.addItem(display_str, userData=(code, name))
                self._text_to_data[display_str] = (code, name)

        self.setCurrentIndex(-1)
        self.lineEdit().setPlaceholderText(
            "Введите код (например, I10)..." if code_mode else "Введите код или диагноз..."
        )

        completer = QtWidgets.QCompleter(self.model(), self)
        # Поиск по коду: строка вида «КОД - диагноз», поэтому ищем по началу строки
        completer.setFilterMode(
            QtCore.Qt.MatchFlag.MatchStartsWith if code_mode
            else QtCore.Qt.MatchFlag.MatchContains
        )
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        
        # Разделяем обработку сигналов
        completer.activated[str].connect(self._on_completer_activated)
        self.setCompleter(completer)
        self.activated.connect(self._on_activated)

    def _on_activated(self, index):
        if index >= 0:
            data = self.itemData(index)
            if data:
                code, name = data
                self.mkb_selected.emit(code, name)

    def _on_completer_activated(self, text: str):
        # Достаем данные по тексту из автодополнения
        data = self._text_to_data.get(text)
        if data:
            code, name = data
            self.mkb_selected.emit(code, name)

    def showPopup(self):
        # Блокируем сигналы комбобокса и комплитера на время открытия
        self.blockSignals(True)
        if self.completer():
            self.completer().blockSignals(True)

        super().showPopup()

        self.blockSignals(False)
        if self.completer():
            self.completer().blockSignals(False)


class MkbDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, mkb_df, parent=None, code_col_idx=None,
                 name_col_idx=None, code_mode=False):
        """code_mode=True — делегат стоит на колонке «Код МКБ» (поиск по коду);
        при выборе заполняется и код, и диагноз (колонка name_col_idx)."""
        super().__init__(parent)
        self.mkb_df = mkb_df
        self.code_col_idx = code_col_idx
        self.name_col_idx = name_col_idx
        self.code_mode = code_mode

    def createEditor(self, parent, option, index):
        editor = MkbComboBox(self.mkb_df, parent, code_mode=self.code_mode)
        editor.selected_code = None
        editor.selected_name = None

        def on_mkb_selected(code, name):
            editor.selected_code = code
            editor.selected_name = name
            
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache)

        editor.mkb_selected.connect(on_mkb_selected)
        
        # Автоматическое открытие списка
        QtCore.QTimer.singleShot(0, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole) or ""
        editor.lineEdit().setText(value)
        editor.lineEdit().selectAll()

    def setModelData(self, editor, model, index):
        if self.code_mode:
            if getattr(editor, 'selected_code', None) is not None:
                model.setData(index, editor.selected_code, QtCore.Qt.ItemDataRole.EditRole)
                if self.name_col_idx is not None:
                    name_index = model.index(index.row(), self.name_col_idx)
                    model.setData(name_index, editor.selected_name, QtCore.Qt.ItemDataRole.EditRole)
            else:
                model.setData(index, editor.lineEdit().text().strip(), QtCore.Qt.ItemDataRole.EditRole)
            return
        if getattr(editor, 'selected_name', None) is not None:
            model.setData(index, editor.selected_name, QtCore.Qt.ItemDataRole.EditRole)
            
            target_code_col = self.code_col_idx if self.code_col_idx is not None else (index.column() - 1)
            code_index = model.index(index.row(), target_code_col)
            model.setData(code_index, editor.selected_code, QtCore.Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.lineEdit().text(), QtCore.Qt.ItemDataRole.EditRole)


class MultilineTextDelegate(QtWidgets.QStyledItemDelegate):
    """Многострочный редактор для длинного текста.

    Enter — сохранить, Shift+Enter (или Ctrl+Enter) — перенос строки,
    Tab — сохранить и перейти дальше, Esc — отмена.
    """

    MIN_EDITOR_HEIGHT = 120

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QPlainTextEdit(parent)
        editor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        editor.setTabChangesFocus(True)
        option_text = editor.document().defaultTextOption()
        option_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        editor.document().setDefaultTextOption(option_text)
        editor.setPlaceholderText("Enter — сохранить, Shift+Enter — новая строка")
        editor.setStyleSheet(
            "QPlainTextEdit { background: #ffffff; color: #2b2b2b; "
            "border: 2px solid #1f538d; }"
        )
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole) or ""
        editor.setPlainText(text)
        editor.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText().strip(), QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        # Поле ввода выше самой ячейки, чтобы было удобно печатать много текста
        rect = QtCore.QRect(option.rect)
        rect.setHeight(max(rect.height(), self.MIN_EDITOR_HEIGHT))
        parent = editor.parentWidget()
        if parent is not None and rect.bottom() > parent.height():
            rect.moveBottom(parent.height() - 1)
            if rect.top() < 0:
                rect.moveTop(0)
        editor.setGeometry(rect)

    def eventFilter(self, editor, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                if (mods & QtCore.Qt.KeyboardModifier.ShiftModifier) or (
                    mods & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    editor.insertPlainText("\n")
                else:
                    self.commitData.emit(editor)
                    self.closeEditor.emit(
                        editor, QtWidgets.QAbstractItemDelegate.EndEditHint.NoHint
                    )
                return True
            if key == QtCore.Qt.Key.Key_Tab:
                self.commitData.emit(editor)
                self.closeEditor.emit(
                    editor, QtWidgets.QAbstractItemDelegate.EndEditHint.EditNextItem
                )
                return True
        return super().eventFilter(editor, event)


class MultiChoiceEditor(QtWidgets.QFrame):
    """Редактор с выбором нескольких значений из списка (чекбоксы + поиск).

    Итог записывается в ячейку через запятую. Enter в строке поиска — отметить
    первый найденный пункт (если ничего не найдено — добавить введённый текст как свой).
    """

    finished = QtCore.Signal()

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("MultiChoiceEditor")
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            "#MultiChoiceEditor { background: #ffffff; border: 2px solid #1f538d; }"
            "#MultiChoiceEditor QLabel { color: #555555; }"
            "#MultiChoiceEditor QLineEdit, #MultiChoiceEditor QListWidget "
            "{ background: #ffffff; color: #2b2b2b; }"
        )
        self.items = list(items)
        self.selected: list[str] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Поиск. Enter — отметить найденное")
        self.search.textChanged.connect(self._apply_filter)
        self.search.returnPressed.connect(self._on_enter)
        layout.addWidget(self.search)

        self.list = QtWidgets.QListWidget()
        self.list.itemClicked.connect(self._toggle_item)
        layout.addWidget(self.list, 1)

        # Свой вариант — для препаратов, которых нет в справочнике
        custom_row = QtWidgets.QHBoxLayout()
        self.custom = QtWidgets.QLineEdit()
        self.custom.setPlaceholderText("Свой вариант — впишите текст и нажмите «Добавить»")
        self.custom.returnPressed.connect(self._add_custom)
        btn_custom = QtWidgets.QPushButton("＋ Добавить")
        btn_custom.clicked.connect(self._add_custom)
        custom_row.addWidget(self.custom, 1)
        custom_row.addWidget(btn_custom)
        layout.addLayout(custom_row)

        bottom = QtWidgets.QHBoxLayout()
        self.hint = QtWidgets.QLabel("Можно выбрать несколько — запишутся через запятую")
        btn_done = QtWidgets.QPushButton("Готово")
        btn_done.clicked.connect(self.finished.emit)
        bottom.addWidget(self.hint, 1)
        bottom.addWidget(btn_done)
        layout.addLayout(bottom)

        self.setFocusProxy(self.search)

    # --- данные ---
    def set_text(self, text: str):
        """Разбирает текущее значение ячейки: известные пункты + прочий текст."""
        text = text or ""
        spans = []
        for med in self.items:
            start = text.find(med)
            if start >= 0:
                spans.append((start, start + len(med), med))
        spans.sort()
        selected, pos = [], 0
        for start, end, med in spans:
            if start < pos:  # пересечение с предыдущим — пропускаем
                continue
            selected += self._custom_pieces(text[pos:start])
            selected.append(med)
            pos = end
        selected += self._custom_pieces(text[pos:])
        self.selected = selected

        self.list.clear()
        for value in [v for v in selected if v not in self.items]:
            self._add_list_item(value)
        for value in self.items:
            self._add_list_item(value)

    @staticmethod
    def _custom_pieces(chunk: str) -> list[str]:
        chunk = chunk.strip(" ,;\n")
        return [chunk] if chunk else []

    def _add_list_item(self, value: str):
        item = QtWidgets.QListWidgetItem(value)
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
        item.setCheckState(
            QtCore.Qt.CheckState.Checked if value in self.selected
            else QtCore.Qt.CheckState.Unchecked
        )
        self.list.addItem(item)

    def text(self) -> str:
        return ", ".join(self.selected)

    # --- поведение ---
    def _toggle_item(self, item: QtWidgets.QListWidgetItem):
        value = item.text()
        if item.checkState() == QtCore.Qt.CheckState.Checked:
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            if value in self.selected:
                self.selected.remove(value)
        else:
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            if value not in self.selected:
                self.selected.append(value)

    def _add_custom(self):
        """Добавляет введённый вручную текст как отмеченный пункт."""
        value = self.custom.text().strip(" ,;")
        if not value:
            return
        if value not in self.selected:
            self.selected.append(value)
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.text() == value:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
                break
        else:
            item = QtWidgets.QListWidgetItem(value)
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            self.list.insertItem(0, item)
        self.custom.clear()
        self.custom.setFocus()

    def _apply_filter(self, text: str):
        needle = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_enter(self):
        needle = self.search.text().strip()
        if not needle:
            self.finished.emit()  # Enter в пустом поиске — завершить выбор
            return
        for i in range(self.list.count()):
            item = self.list.item(i)
            if not item.isHidden():
                if item.checkState() != QtCore.Qt.CheckState.Checked:
                    self._toggle_item(item)
                break
        else:  # ничего не найдено — добавляем введённый текст как свой пункт
            if needle not in self.selected:
                self.selected.append(needle)
                self._add_list_item(needle)
        self.search.clear()


class MultiChoiceDelegate(QtWidgets.QStyledItemDelegate):
    """Делегат: выбор нескольких значений из списка, запись через запятую."""

    EDITOR_SIZE = QtCore.QSize(540, 370)

    def __init__(self, items_list: list[str], parent=None):
        super().__init__(parent)
        self.items_list = items_list

    def createEditor(self, parent, option, index):
        editor = MultiChoiceEditor(self.items_list, parent)

        def finish():
            self.commitData.emit(editor)
            self.closeEditor.emit(
                editor, QtWidgets.QAbstractItemDelegate.EndEditHint.NoHint
            )

        editor.finished.connect(finish)
        return editor

    def setEditorData(self, editor, index):
        editor.set_text(index.model().data(index, QtCore.Qt.ItemDataRole.EditRole) or "")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        rect = QtCore.QRect(option.rect.topLeft(), self.EDITOR_SIZE)
        parent = editor.parentWidget()
        if parent is not None:
            if rect.right() > parent.width():
                rect.moveRight(parent.width() - 1)
            if rect.bottom() > parent.height():
                rect.moveBottom(parent.height() - 1)
            rect.moveLeft(max(0, rect.left()))
            rect.moveTop(max(0, rect.top()))
        editor.setGeometry(rect)


class BaseSheet(QtWidgets.QWidget):

    OUTCOME_OPTIONS = [
        "Выздоровление",
        "Улучшение",
        "Без перемен",
        "Ухудшение",
        "Летальный",
    ]

    GENDER_OPTIONS = [
        "Мужской",
        "Женский",
    ]

    DEFAULT_COLUMN_WIDTH = 150
    DEFAULT_WIDTHS: dict = {}  # {название колонки: ширина в px}, задаётся в наследниках
    ACTION_COLUMNS = 1         # сколько последних колонок — кнопки (не данные)
    # Колонки данных в прежней версии файла (для записей без списка заголовков)
    LEGACY_COLUMNS: list | None = None

    def __init__(
        self,
        db_key: str,
        columns: list[str],
        mkb_col_idx: int,
        address_col_idx: int = None,
        doctor_col_idx: int = None,
        medication_col_idx: int = None,
        mkb_code_col_idx: int = None,
        gender_col_idx: int = None,
        mo_col_idx: int = None,
        outcome_col_idx: int = None,
        parent=None,
    ):
        super().__init__(parent)

        self.db = DataManager()
        self.session = AdminSession()
        self.db_key = db_key
        self.columns = columns
        self.data_cols = len(columns) - self.ACTION_COLUMNS
        self.mkb_col_idx = mkb_col_idx
        self.address_col_idx = address_col_idx
        self.doctor_col_idx = doctor_col_idx
        self.medication_col_idx = medication_col_idx
        self.mkb_code_col_idx = mkb_code_col_idx
        self.gender_col_idx = gender_col_idx
        self.mo_col_idx = mo_col_idx
        self.outcome_col_idx = outcome_col_idx
        self.is_loading = False

        # Загрузка внешних справочников
        self.mkb_df = self._load_mkb_data(resource_path("MKB.csv"))
        self.streets_list = self._load_streets_data(resource_path("tyumen_streets.csv"))
        self.doctors_list = self._load_doctors_data()
        self.medications_list = self._load_medications_data()

        self.layout = QtWidgets.QVBoxLayout(self)

        # Кнопка добавления записи
        self.btn_add = QtWidgets.QPushButton("＋ Добавить новую запись")
        self.btn_add.clicked.connect(self.add_row)
        self.layout.addWidget(self.btn_add)

        # Кнопка удаления строк (видна только администратору)
        self.btn_delete = QtWidgets.QPushButton("Удалить выбранные строки")
        self.btn_delete.clicked.connect(self.delete_selected_rows)
        self.btn_delete.setVisible(False)
        self.layout.addWidget(self.btn_delete)

        # Таблица
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)

        for i, title in enumerate(self.columns):
            self.table.horizontalHeaderItem(i).setToolTip(title)  # полное название

        # Колонки: ширину можно менять мышкой (тянуть границу заголовка), она запоминается
        self.header = self.table.horizontalHeader()
        self.header.setStretchLastSection(False)
        self.header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.header.setMinimumSectionSize(50)
        self.header.setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Interactive
        )
        for col in range(self.data_cols, len(self.columns)):
            self.header.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )
        self.header.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._show_header_menu)

        # Длинный текст переносится по словам, высота строки подстраивается под содержимое
        self.table.setWordWrap(True)
        self.table.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.table.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setMinimumSectionSize(32)

        self.ui_settings = QtCore.QSettings("MedicalApp", "UiLayout")
        self._applying_widths = False
        self._row_fit_timer = QtCore.QTimer(self)
        self._row_fit_timer.setSingleShot(True)
        self._row_fit_timer.setInterval(40)
        self._row_fit_timer.timeout.connect(self.table.resizeRowsToContents)
        self._save_widths_timer = QtCore.QTimer(self)
        self._save_widths_timer.setSingleShot(True)
        self._save_widths_timer.setInterval(400)
        self._save_widths_timer.timeout.connect(self._save_column_widths)

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

        # 1а. Поиск по коду МКБ: делегат на колонке «Код МКБ» заполняет код и диагноз
        self._code_col = (
            self.mkb_code_col_idx if self.mkb_code_col_idx is not None
            else self.mkb_col_idx - 1
        )
        self.mkb_code_delegate = MkbDelegate(
            self.mkb_df, self.table, name_col_idx=self.mkb_col_idx, code_mode=True
        )
        self.table.setItemDelegateForColumn(self._code_col, self.mkb_code_delegate)

        # 2. Делегат адресов
        if self.address_col_idx is not None and self.streets_list:
            self.address_delegate = AddressDelegate(self.streets_list, self.table)
            self.table.setItemDelegateForColumn(
                self.address_col_idx, self.address_delegate
            )

        # 3. Делегат врачей
        if self.doctor_col_idx is not None:
            self.doctor_delegate = ListChoiceDelegate(
                self.doctors_list, placeholder="Выберите врача...", parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.doctor_col_idx, self.doctor_delegate
            )

        # 4. Делегат препаратов
        if self.medication_col_idx is not None:
            self.medication_delegate = MultiChoiceDelegate(
                self.medications_list, parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.medication_col_idx, self.medication_delegate
            )

        # 5. Делегат пола
        if self.gender_col_idx is not None:
            self.gender_delegate = ListChoiceDelegate(
                self.GENDER_OPTIONS, placeholder="Выберите пол...", parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.gender_col_idx, self.gender_delegate
            )

        # 6. Делегат МО по месту
        if self.mo_col_idx is not None:
            self.mo_delegate = ListChoiceDelegate(
                HOSPITALS, placeholder="Выберите МО...", parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.mo_col_idx, self.mo_delegate
            )

        # 7. Делегат исхода
        if self.outcome_col_idx is not None:
            self.outcome_delegate = ListChoiceDelegate(
                self.OUTCOME_OPTIONS, placeholder="Выберите исход...", parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.outcome_col_idx, self.outcome_delegate
            )

        # 8. Многострочный редактор для свободных текстовых колонок
        has_delegate = {
            self.mkb_col_idx,
            self._code_col,
            self.doctor_col_idx,
            self.medication_col_idx,
            self.gender_col_idx,
            self.mo_col_idx,
            self.outcome_col_idx,
        }
        if self.streets_list:
            has_delegate.add(self.address_col_idx)
        self.multiline_delegate = MultilineTextDelegate(self.table)
        for col in range(self.data_cols):
            title = self.columns[col]
            if (
                col in has_delegate
                or col in self.get_centered_columns()
                or title.startswith(("Дата", "Время"))
            ):
                continue
            self.table.setItemDelegateForColumn(col, self.multiline_delegate)

        # Контекстное меню (удаление строк для администратора)
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemChanged.connect(lambda *_: self._schedule_row_fit())
        self._restore_column_widths()
        self.header.sectionResized.connect(self._on_section_resized)
        self._start_lock_timer()
        self.refresh_admin_mode()

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
        """Обновляет список врачей и заново переназначает делегат для колонки."""
        self.doctors_list = self._load_doctors_data()
        if self.doctor_col_idx is not None:
            self.doctor_delegate = ListChoiceDelegate(
                self.doctors_list, placeholder="Выберите врача...", parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.doctor_col_idx, self.doctor_delegate
            )

    def refresh_medications_list(self):
        """Обновляет список препаратов и заново переназначает делегат для колонки."""
        self.medications_list = self._load_medications_data()
        if self.medication_col_idx is not None:
            self.medication_delegate = MultiChoiceDelegate(
                self.medications_list, parent=self.table
            )
            self.table.setItemDelegateForColumn(
                self.medication_col_idx, self.medication_delegate
            )

    def reload_from_file(self):
        """Полная перезагрузка после смены файла данных: справочники и записи журнала."""
        self.refresh_doctors_list()
        self.refresh_medications_list()
        self.load_data()

    # ------------------------------------------------------------------
    # Ширина колонок и высота строк
    # ------------------------------------------------------------------
    def _schedule_row_fit(self):
        """Пересчитать высоту строк под текст (с небольшой задержкой, чтобы не тормозить)."""
        self._row_fit_timer.start()

    def _default_width(self, col: int) -> int:
        return self.DEFAULT_WIDTHS.get(self.columns[col], self.DEFAULT_COLUMN_WIDTH)

    def _apply_widths(self, widths: list[int]):
        self._applying_widths = True
        try:
            for col, width in enumerate(widths):
                self.header.resizeSection(col, max(50, int(width)))
        finally:
            self._applying_widths = False
        self._schedule_row_fit()

    def _restore_column_widths(self):
        count = self.data_cols  # последняя колонка (кнопка) подгоняется сама
        widths = None
        saved = self.ui_settings.value(f"column_widths/{self.db_key}")
        if saved is not None:
            try:
                saved_list = saved if isinstance(saved, (list, tuple)) else [saved]
                candidate = [int(x) for x in saved_list]
                if len(candidate) == count:
                    widths = candidate
            except (TypeError, ValueError):
                widths = None
        if widths is None:
            widths = [self._default_width(c) for c in range(count)]
        self._apply_widths(widths)

    def _save_column_widths(self):
        widths = [self.header.sectionSize(c) for c in range(self.data_cols)]
        self.ui_settings.setValue(f"column_widths/{self.db_key}", widths)
        self.ui_settings.sync()

    def _on_section_resized(self, index, old_size, new_size):
        if self._applying_widths:
            return
        self._schedule_row_fit()
        self._save_widths_timer.start()

    def _show_header_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        act_reset = menu.addAction("Сбросить ширину колонок")
        act_fit = menu.addAction("Подогнать ширину под содержимое")
        chosen = menu.exec(self.header.mapToGlobal(pos))
        if chosen == act_reset:
            self._apply_widths(
                [self._default_width(c) for c in range(self.data_cols)]
            )
            self._save_column_widths()
        elif chosen == act_fit:
            for col in range(self.data_cols):
                self.table.resizeColumnToContents(col)
                self.header.resizeSection(col, min(self.header.sectionSize(col), 500))
            self._schedule_row_fit()
            self._save_column_widths()

    # ------------------------------------------------------------------
    # Режим администратора
    # ------------------------------------------------------------------
    def _is_admin(self) -> bool:
        return self.session.is_authenticated()

    def _apply_lock(self, row: int, created_at: str):
        """Админу строки всегда доступны для редактирования, остальным — политика 60 минут."""
        was_loading = self.is_loading
        self.is_loading = True  # setFlags/setBackground шлют itemChanged — не сохраняем
        try:
            if self._is_admin():
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                        item.setBackground(QtGui.QBrush())  # убираем серый фон
            else:
                apply_row_lock_policy(self.table, row, created_at)
        finally:
            self.is_loading = was_loading

    def refresh_admin_mode(self):
        """Вызывается при входе/выходе администратора."""
        self.btn_delete.setVisible(self._is_admin())
        self._check_row_locks()

    def _selected_rows(self) -> list[int]:
        return sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)

    def _show_context_menu(self, pos):
        if not self._is_admin():
            return
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        if index.row() not in self._selected_rows():
            self.table.selectRow(index.row())

        menu = QtWidgets.QMenu(self)
        act_delete = menu.addAction("Удалить строку")
        if menu.exec(self.table.viewport().mapToGlobal(pos)) == act_delete:
            self.delete_selected_rows()

    def delete_selected_rows(self):
        if not self._is_admin():
            return

        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(
                self, "Удаление", "Выделите строки (клик по номеру строки слева)."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить выбранные записи ({len(rows)} шт.)? Действие необратимо.",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self.is_loading = True
        for r in rows:  # rows отсортированы по убыванию — индексы не съезжают
            self.table.removeRow(r)
        self.is_loading = False

        # Кнопки «Печать»/«Копировать» захватили старый номер строки — пересоздаём
        for r in range(self.table.rowCount()):
            self._setup_action_button(r)

        self.save_data()
        self._schedule_row_fit()

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

            self._apply_lock(row, created_at)

    def get_centered_columns(self) -> tuple:
        # Весь текст в таблицах выравнивается по центру; эти колонки (дата, время, код)
        # дополнительно исключаются из многострочного редактора.
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
            row_values = self._align_values(record_data)

            for col_idx in range(self.data_cols):
                text = (
                    row_values[col_idx] if col_idx < len(row_values) else ""
                )
                item = QtWidgets.QTableWidgetItem(text)

                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                self.table.setItem(row_count, col_idx, item)

            if self.table.item(row_count, 0):
                self.table.item(row_count, 0).setData(
                    QtCore.Qt.ItemDataRole.UserRole, created_at
                )

            self._setup_action_button(row_count)
            self._apply_lock(row_count, created_at)

        self.is_loading = False
        self._schedule_row_fit()

    def _align_values(self, record: dict) -> list[str]:
        """Приводит значения записи к текущему набору колонок.

        Запись хранит названия колонок, с которыми была сохранена (старые записи —
        нет, для них берётся LEGACY_COLUMNS), поэтому новые колонки можно добавлять
        в любое место таблицы без потери данных.
        """
        values = record.get("values", [])
        current = self.columns[: self.data_cols]
        saved_cols = record.get("columns") or self.LEGACY_COLUMNS or current
        if list(saved_cols) == current:
            return values
        lookup = dict(zip(saved_cols, values))
        return [lookup.get(name, "") for name in current]

    def add_row(self):
        """Добавление новой записи в таблицу с предустановкой доктора по умолчанию."""
        self.is_loading = True  # Блокируем триггер itemChanged на время формирования строки

        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for col_idx in range(self.data_cols):
            item = QtWidgets.QTableWidgetItem("")
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
        self._apply_lock(row_count, now_str)

        self.is_loading = False  # Включаем отслеживание обратно
        self.save_data()         # Одиночное сохранение

        focus_col = 2
        if self.table.columnCount() > focus_col:
            self.table.setCurrentCell(row_count, focus_col)
            item_to_edit = self.table.item(row_count, focus_col)
            if item_to_edit:
                self.table.editItem(item_to_edit)

    def on_item_changed(self, item: QtWidgets.QTableWidgetItem):
        if self.is_loading:
            return

        # Администратор может редактировать любые записи, остальным — по политике блокировки
        if not self._is_admin():
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
            for col in range(self.data_cols):
                item = self.table.item(row, col)
                row_values.append(item.text() if item else "")

            records.append({
                "created_at": created_at,
                "columns": self.columns[: self.data_cols],
                "values": row_values,
            })

        full_db_data[self.db_key] = records
        self.db.save_data(full_db_data)