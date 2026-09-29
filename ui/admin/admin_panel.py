from PySide6 import QtCore, QtWidgets
from back.user.users import AdminSession
from ui.admin.dashboard_widget import DashboardWidget
from ui.admin.login_widget import LoginWidget


class AdminPanel(QtWidgets.QWidget):
    # Сигнал для уведомления главных журналов об изменении справочников (препаратов, врачей)
    data_changed = QtCore.Signal()

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

        # Подключение сигналов
        self.login_widget.login_successful.connect(self.update_view)
        self.dashboard_widget.logout_requested.connect(self.update_view)

        # Если в dashboard_widget или medication_widget вызывается изменение данных — пробрасываем наверх
        if hasattr(self.dashboard_widget, "medications_updated"):
            self.dashboard_widget.medications_updated.connect(self.data_changed.emit)

        self.update_view()

    def update_view(self):
        """Обновляет отображаемый виджет в зависимости от статуса авторизации."""
        if self.session.is_authenticated():
            self.dashboard_widget.update_user_info()

            # Если в дашборде есть вкладка управления препаратами, обновляем её список
            if hasattr(self.dashboard_widget, "medication_widget"):
                self.dashboard_widget.medication_widget.load_medications()

            self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        else:
            self.stacked_widget.setCurrentWidget(self.login_widget)