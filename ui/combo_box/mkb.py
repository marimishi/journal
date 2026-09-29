import pandas as pd
from PySide6 import QtWidgets, QtCore, QtGui

class MkbComboBox(QtWidgets.QComboBox):
    
    mkb_selected = QtCore.Signal(str, str)

    def __init__(self, mkb_df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        self.model_data = []
        for _, row in mkb_df.iterrows():
            code = str(row['MKB_CODE']).strip()
            name = str(row['MKB_NAME']).strip()
            display_str = f"{code} - {name}"
            self.model_data.append((code, name, display_str))
            self.addItem(display_str, userData=(code, name))

        self.setCurrentIndex(-1)
        self.lineEdit().setPlaceholderText("Введите код или диагноз...")

        completer = QtWidgets.QCompleter(self.model(), self)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)

        self.activated.connect(self._on_activated)

    def _on_activated(self, index):
        data = self.itemData(index)
        if data:
            code, name = data
            self.mkb_selected.emit(code, name)


class MkbDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, mkb_df, parent=None, code_col_idx=None):
        super().__init__(parent)
        self.mkb_df = mkb_df
        # Если индекс колонки кода не задан, берем колонку слева от диагноза
        self.code_col_idx = code_col_idx

    def createEditor(self, parent, option, index):
        editor = MkbComboBox(self.mkb_df, parent)
        editor.selected_code = ""
        editor.selected_name = ""

        def on_mkb_selected(code, name):
            editor.selected_code = code
            editor.selected_name = name
            
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.EndEditHint.NoHint)

        editor.mkb_selected.connect(on_mkb_selected)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)
        if value:
            editor.lineEdit().setText(value)

    def setModelData(self, editor, model, index):
        if hasattr(editor, 'selected_name') and editor.selected_name:
            # Записываем наименование диагноза в текущую ячейку
            model.setData(index, editor.selected_name, QtCore.Qt.ItemDataRole.EditRole)
            
            # Определяем колонку для Кода МКБ
            target_code_col = self.code_col_idx if self.code_col_idx is not None else (index.column() - 1)
            code_index = model.index(index.row(), target_code_col)
            model.setData(code_index, editor.selected_code, QtCore.Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.lineEdit().text(), QtCore.Qt.ItemDataRole.EditRole)



class SearchableComboBox(QtWidgets.QComboBox):
    """Кастомный QComboBox с автодополнением, корректно работающий в таблицах."""

    item_selected = QtCore.Signal(str)

    def __init__(self, items_list: list[str], placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        self.addItems(items_list)
        self.setCurrentIndex(-1)
        self.lineEdit().setPlaceholderText(placeholder)

        completer = QtWidgets.QCompleter(self.model(), self)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        
        # Завершение редактирования при выборе из автодополнения
        completer.activated.connect(self._on_completer_activated)
        self.setCompleter(completer)

        # Выбор из стандартного выпадающего списка
        self.activated.connect(self._on_activated)

    def _on_activated(self, index):
        if index >= 0:
            text = self.itemText(index)
            self.item_selected.emit(text)

    def _on_completer_activated(self, text):
        self.item_selected.emit(text)

    def showPopup(self):
        """Автоматически разворачивает список при начале редактирования."""
        super().showPopup()


class ListChoiceDelegate(QtWidgets.QStyledItemDelegate):
    """Делегат выбора из списка для QTableWidget."""

    def __init__(self, items_list: list[str], placeholder: str = "Выберите...", parent=None):
        super().__init__(parent)
        self.items_list = items_list
        self.placeholder = placeholder

    def createEditor(self, parent, option, index):
        editor = SearchableComboBox(
            self.items_list, placeholder=self.placeholder, parent=parent
        )
        editor.selected_text = None

        def on_selected(text):
            editor.selected_text = text
            # Фиксируем данные и закрываем редактор только после клика/выбора
            self.commitData.emit(editor)
            self.closeEditor.emit(
                editor, QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache
            )

        editor.item_selected.connect(on_selected)
        
        # Автоматически раскрываем выпадающий список сразу при входе в ячейку
        QtCore.QTimer.singleShot(0, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole) or ""
        editor.lineEdit().setText(value)
        # Выделяем текст, чтобы пользователь мог сразу начать вводить новый
        editor.lineEdit().selectAll()

    def setModelData(self, editor, model, index):
        # Если элемент был выбран из списка — берем selected_text,
        # если пользователь просто ввел текст вручную и нажал Enter — берем из lineEdit
        if getattr(editor, "selected_text", None) is not None:
            model.setData(index, editor.selected_text, QtCore.Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.lineEdit().text(), QtCore.Qt.ItemDataRole.EditRole)