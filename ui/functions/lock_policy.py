from datetime import datetime, timedelta
from PySide6 import QtCore, QtGui, QtWidgets

def is_record_locked(created_at_str: str) -> bool:
    if not created_at_str:
        return False
    try:
        record_time = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        return datetime.now() - record_time > timedelta(minutes=60)
    except ValueError:
        return False

def apply_row_lock_policy(table: QtWidgets.QTableWidget, row: int, created_at_str: str):
    locked = is_record_locked(created_at_str)
    
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            if locked:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                item.setBackground(QtGui.QColor("#e0e0e0"))
            else:
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)