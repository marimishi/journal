from PySide6 import QtWidgets
from back.user.users import AdminSession
from ui.admin.login_widget import LoginWidget
from ui.admin.dashboard_widget import DashboardWidget

class AdminPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = AdminSession()

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.login_widget = LoginWidget()
        self.dashboard_widget = DashboardWidget()

        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.dashboard_widget)

        self.login_widget.login_successful.connect(self.update_view)
        self.dashboard_widget.logout_requested.connect(self.update_view)

        self.update_view()

    def update_view(self):
        if self.session.is_authenticated():
            self.dashboard_widget.update_user_info()
            self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        else:
            self.stacked_widget.setCurrentWidget(self.login_widget)