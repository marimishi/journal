from PySide6 import QtCore, QtGui, QtWidgets

from back.style import get_style
from back.user.users import AdminSession

class LoginWidget(QtWidgets.QWidget):

    login_successful = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = AdminSession()
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        card = QtWidgets.QFrame()
        card.setFixedWidth(360)
        card.setStyleSheet(get_style("login_card"))

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        title = QtWidgets.QLabel("Введите пароль")
        title.setObjectName("title")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        self.input_password = QtWidgets.QLineEdit()
        self.input_password.setPlaceholderText("Пароль")
        self.input_password.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Password
        )
        self.input_password.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.input_password)

        self.btn_login = QtWidgets.QPushButton("Войти")
        self.btn_login.clicked.connect(self.handle_login)
        card_layout.addWidget(self.btn_login)

        self.lbl_error = QtWidgets.QLabel("")
        self.lbl_error.setStyleSheet(get_style("error_label"))
        self.lbl_error.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_error)

        layout.addWidget(card)

    def handle_login(self):
        password = self.input_password.text().strip()

        if self.session.login(password):
            self.lbl_error.setText("")
            self.input_password.clear()
            self.login_successful.emit()
        else:
            self.lbl_error.setText("Неверный пароль")