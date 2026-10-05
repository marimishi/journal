from PySide6 import QtCore, QtWidgets
from back.user.users import AdminSession
from ui.admin.dashboard_widget import DashboardWidget
from ui.admin.data_file_widget import DataFileWidget
from ui.admin.login_widget import LoginWidget


class AdminPanel(QtWidgets.QWidget):
    # Сигнал для уведомления главных журналов об изменении справочников (препаратов, врачей)
    data_changed = QtCore.Signal()
    # Админ вошёл / вышел — журналы включают или отключают режим администратора
    admin_state_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = AdminSession()

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget, stretch=1)

        self.login_widget = LoginWidget()
        self.dashboard_widget = DashboardWidget()

        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.dashboard_widget)

        # Путь к файлу данных виден всегда, менять его можно только после входа
        self.data_file_widget = DataFileWidget()
        self.main_layout.addWidget(self.data_file_widget)

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
            self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        else:
            self.stacked_widget.setCurrentWidget(self.login_widget)

        self.data_file_widget.refresh()
        self.admin_state_changed.emit()

    def reload_data(self):
        """Перечитывает врачей и препараты после смены файла данных."""
        self.dashboard_widget.doctors_tab.load_doctors_to_table()
        self.dashboard_widget.medication_tab.load_medications()
        self.data_file_widget.refresh()