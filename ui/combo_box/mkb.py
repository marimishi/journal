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
    """Универсальный комбобокс с защитой от ложных срабатываний при двойном клике."""
    item_selected = QtCore.Signal(str)

    def __init__(self, items: list[str], placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        
        # Время открытия выпадающего списка (для блокировки фантомных кликов)
        self._popup_time = QtCore.QTime()
        
        self.addItems(items)
        self.setCurrentIndex(-1)
        self.lineEdit().setPlaceholderText(placeholder)

        completer = QtWidgets.QCompleter(self.model(), self)
        completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        
        completer.activated[str].connect(self._on_completer_activated)
        self.setCompleter(completer)
        self.activated.connect(self._on_activated)

    def _on_activated(self, index: int):
        # Игнорируем события выбора, если с момента открытия списка прошло менее 200 мс
        if self._popup_time.isValid() and self._popup_time.msecsTo(QtCore.QTime.currentTime()) < 200:
            return
            
        if index >= 0:
            self.item_selected.emit(self.itemText(index))

    def _on_completer_activated(self, text: str):
        # Аналогичная защита для автодополнения
        if self._popup_time.isValid() and self._popup_time.msecsTo(QtCore.QTime.currentTime()) < 200:
            return
            
        self.item_selected.emit(text)

    def showPopup(self):
        self.blockSignals(True)
        if self.completer():
            self.completer().blockSignals(True)

        super().showPopup()

        self.blockSignals(False)
        if self.completer():
            self.completer().blockSignals(False)
            
        # Фиксируем точное время раскрытия списка
        self._popup_time = QtCore.QTime.currentTime()


class ListChoiceDelegate(QtWidgets.QStyledItemDelegate):
    """Универсальный делегат для выпадающих списков."""
    def __init__(self, items_list: list[str], placeholder: str = "Выберите...", parent=None):
        super().__init__(parent)
        self.items_list = items_list
        self.placeholder = placeholder

    def createEditor(self, parent, option, index):
        editor = SearchableComboBox(self.items_list, placeholder=self.placeholder, parent=parent)
        editor.selected_text = None

        def on_selected(text):
            editor.selected_text = text
            self.commitData.emit(editor)
            self.closeEditor.emit(
                editor, QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache
            )

        editor.item_selected.connect(on_selected)
        
        # Задержка в 100 мс гарантирует, что пользователь успеет отпустить 
        # кнопку мыши ДО того, как появится выпадающий список
        QtCore.QTimer.singleShot(100, editor.showPopup)
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