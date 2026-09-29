import sys
from PySide6 import QtWidgets

from ui.main_screen import MainScreen

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)


    main_window = MainScreen(backend_handler=None)
    main_window.show()
    main_window.showMaximized()
    sys.exit(app.exec())