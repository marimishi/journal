from PySide6 import QtWidgets, QtCore, QtGui
from back.user.users import AdminSession
from ui.admin.doctors_widget import DoctorsTableWidget

class DashboardWidget(QtWidgets.QWidget):
    logout_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = AdminSession()
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        header_layout = QtWidgets.QHBoxLayout()
        self.welcome_label = QtWidgets.QLabel("Панель администратора")
        self.welcome_label.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Weight.Bold))
        
        btn_logout = QtWidgets.QPushButton("Выйти из аккаунта")
        btn_logout.setFixedHeight(35)
        btn_logout.clicked.connect(self.handle_logout)

        header_layout.addWidget(self.welcome_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_logout)

        layout.addLayout(header_layout)

        tab_widget = QtWidgets.QTabWidget()
        self.doctors_tab = DoctorsTableWidget()
        tab_widget.addTab(self.doctors_tab, "Врачи")

        layout.addWidget(tab_widget)

    def update_user_info(self):
        self.welcome_label.setText(f"Администратор")

    def handle_logout(self):
        self.session.logout()
        self.logout_requested.emit()