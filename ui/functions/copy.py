# ui/functions/copy.py
from PySide6 import QtWidgets, QtCore

def copy_row_by_headers(
    source_table: QtWidgets.QTableWidget, 
    source_row: int, 
    target_table: QtWidgets.QTableWidget
) -> int:
    """
    Копирует данные из строки `source_row` таблицы `source_table` 
    в новую строку `target_table`, сопоставляя колонки по одинаковым названиям.
    
    :return: Индекс созданной строки в целевой таблице.
    """
    src_data = {}
    for col in range(source_table.columnCount()):
        header_item = source_table.horizontalHeaderItem(col)
        header_name = header_item.text() if header_item else ""
        
        # Исключаем служебные колонки с кнопками
        if header_name in ("Копировать", "Печать", ""):
            continue
            
        cell_item = source_table.item(source_row, col)
        val = cell_item.text() if cell_item else ""
        src_data[header_name] = (val, cell_item.textAlignment() if cell_item else None)

    target_row = target_table.rowCount()
    
    # Получаем родительский виджет целевой таблицы (AmbulanceSheet)
    target_widget = target_table.parentWidget()
    
    # Если у целевого листа есть встроенный метод add_row, вызываем его для генерации кнопок
    if hasattr(target_widget, 'add_row'):
        target_widget.add_row()
    else:
        # Иначе используем стандартную вставку (как было изначально)
        target_table.insertRow(target_row)
        for col in range(target_table.columnCount()):
            if target_table.horizontalHeaderItem(col).text() not in ("Копировать", "Печать"):
                target_table.setItem(target_row, col, QtWidgets.QTableWidgetItem(""))

    # Заполняем созданную строку скопированными данными
    for col in range(target_table.columnCount()):
        header_item = target_table.horizontalHeaderItem(col)
        header_name = header_item.text() if header_item else ""

        if header_name in src_data:
            val, alignment = src_data[header_name]
            
            item = target_table.item(target_row, col)
            if not item:
                item = QtWidgets.QTableWidgetItem()
                target_table.setItem(target_row, col, item)
            
            item.setText(val)
            if alignment is not None:
                item.setTextAlignment(alignment)

    return target_row