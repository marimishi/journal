"""Печать «Направления в дежурный стационар по экстренным показаниям» (Приложение 11).

Форма рисуется через QPainter, поэтому никаких дополнительных библиотек не нужно —
хватает PySide6. Открывается окно предпросмотра, в нём кнопка принтера печатает
документ (или можно выбрать «Microsoft Print to PDF» и сохранить файл).
"""
from datetime import date, datetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog

# --- Реквизиты приказа (шапка формы) — при необходимости поменяйте здесь ---
ORDER_DAY = "28"
ORDER_MONTH = "февраля"
ORDER_YEAR = "2024"
ORDER_NUMBER = "036"

ORG_LINES = [
    "Государственное автономное учреждение здравоохранения",
    "Тюменской области «Многопрофильный консультативно-",
    "диагностический центр»",
    "625026, Тюменская обл, Тюмень г, Мельникайте ул, дом № 117",
    "тел.: +8(3452)561240",
]
FONT_NAME = "Arial"


def _years_word(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "лет"
    last = n % 10
    if last == 1:
        return "год"
    if 2 <= last <= 4:
        return "года"
    return "лет"


def _birth_with_age(text: str) -> str:
    """'15.03.1980' -> '15.03.1980 (46 лет)'. Если дату не распознали — вернём как есть."""
    text = (text or "").strip()
    if not text:
        return ""
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            born = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        today = date.today()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        if 0 <= age < 150:
            return f"{text} ({age} {_years_word(age)})"
        break
    return text


class _FormRenderer:
    PITCH = 8.0   # шаг между строками, мм
    LEFT = 5.0    # левая граница, мм

    def __init__(self, painter: QtGui.QPainter, printer: QPrinter, data: dict):
        self.p = painter
        self.data = data
        self.dpi = painter.device().logicalDpiX()
        self.M = self.dpi / 25.4  # пикселей в миллиметре
        page_w = printer.pageRect(QPrinter.Unit.Millimeter).width()
        self.RIGHT = page_w - 5.0
        self.y = 0.0
        self._font(10)

    # ---------- примитивы ----------
    def _font(self, size_pt: float, bold=False, underline=False):
        font = QtGui.QFont(FONT_NAME)
        font.setPixelSize(max(1, round(size_pt * self.dpi / 72)))
        font.setBold(bold)
        font.setUnderline(underline)
        self.p.setFont(font)

    def _w(self, text: str) -> float:
        """Ширина текста в мм."""
        return self.p.fontMetrics().horizontalAdvance(text) / self.M

    def _text(self, x: float, y: float, text: str):
        self.p.setPen(QtGui.QPen(QtGui.QColor("black")))
        self.p.drawText(QtCore.QPointF(x * self.M, y * self.M), text)

    def _line(self, x1: float, x2: float, y: float):
        pen = QtGui.QPen(QtGui.QColor("black"), max(1, round(0.25 * self.M)))
        self.p.setPen(pen)
        self.p.drawLine(
            QtCore.QPointF(x1 * self.M, y * self.M),
            QtCore.QPointF(x2 * self.M, y * self.M),
        )

    def _center(self, y: float, text: str):
        x = (self.LEFT + self.RIGHT) / 2 - self._w(text) / 2
        self._text(x, y, text)

    def _right(self, y: float, text: str):
        self._text(self.RIGHT - self._w(text), y, text)

    def _wrap(self, text: str, first_w: float, next_w: float) -> list[str]:
        words = " ".join((text or "").split()).split(" ")
        lines, cur, limit = [], "", first_w
        for word in words:
            if not word:
                continue
            trial = word if not cur else f"{cur} {word}"
            if self._w(trial) <= limit:
                cur = trial
                continue
            if cur:
                lines.append(cur)
                cur, limit = "", next_w
            while self._w(word) > limit:  # слишком длинное слово — режем по символам
                cut = len(word)
                while cut > 1 and self._w(word[:cut]) > limit:
                    cut -= 1
                lines.append(word[:cut])
                word, limit = word[cut:], next_w
            cur = word
        if cur or not lines:
            lines.append(cur)
        return lines

    def _ruled(self, text: str, y_first: float, n_min: int, x_first: float) -> float:
        """Пишет текст на линейках. Линеек минимум n_min, при длинном тексте добавляются."""
        lines = self._wrap(text, self.RIGHT - x_first, self.RIGHT - self.LEFT)
        count = max(n_min, len(lines))
        for i in range(count):
            ly = y_first + i * self.PITCH
            xs = x_first if i == 0 else self.LEFT
            self._line(xs, self.RIGHT, ly + 1.3)
            if i < len(lines):
                self._text(xs + 0.8, ly, lines[i])
        return y_first + (count - 1) * self.PITCH

    def _single_field(self, label: str, value: str):
        """Одна строка: подпись + значение на линейке. Длинное значение ужимается по шрифту."""
        self._font(10)
        self._text(self.LEFT, self.y, label)
        x = self.LEFT + self._w(label) + 1.5
        self._line(x, self.RIGHT, self.y + 1.3)
        max_w = self.RIGHT - x - 1
        size = 10.0
        while size > 6.5:
            self._font(size)
            if self._w(value) <= max_w:
                break
            size -= 0.5
        if self._w(value) > max_w:
            value = self.p.fontMetrics().elidedText(
                value, QtCore.Qt.TextElideMode.ElideRight, int(max_w * self.M)
            )
        self._text(x + 0.8, self.y, value)
        self._font(10)

    def _inline(self, x: float, prefix: str, suffix: str, line_w: float, value: str = ""):
        self._text(x, self.y, prefix)
        x1 = x + self._w(prefix) + 1
        self._line(x1, x1 + line_w, self.y + 1.3)
        if value:
            self._text(x1 + (line_w - self._w(value)) / 2, self.y, value)
        self._text(x1 + line_w + 1, self.y, suffix)

    # ---------- сама форма ----------
    def render(self):
        d = self.data
        P = self.PITCH
        get = lambda key: (d.get(key) or "").strip()

        # Шапка
        self.y = 5
        self._font(10)
        self._right(self.y, "Приложение 11")
        self.y += 5.5
        self._right(
            self.y,
            f"к приказу от «{ORDER_DAY}» {ORDER_MONTH} {ORDER_YEAR} г. № {ORDER_NUMBER}/24-ос",
        )

        self.y = 21
        self._font(11, bold=True)
        for line in ORG_LINES:
            self._center(self.y, line)
            self.y += 5

        self.y = 52
        self._font(11, underline=True)
        self._center(self.y, "Направление в дежурный стационар по экстренным показаниям")

        # Данные пациента
        self._font(10)
        self.y = 66
        self._single_field("ФИО пациента:", get("ФИО пациента"))
        self.y += P
        self._single_field("Дата рождения/возраст:", _birth_with_age(get("Дата рождения")))
        self.y += P
        self._single_field("Адрес проживания:", get("Домашний адрес"))
        self.y += P

        # Диагноз: подпись + 3 дополнительные линейки
        code, name = get("Код МКБ"), get("Диагноз")
        diagnosis = f"{code} - {name}" if code and name else (code or name)
        label = "Диагноз:"
        self._font(10)
        self._text(self.LEFT, self.y, label)
        x_first = self.LEFT + self._w(label) + 1.5
        self.y = self._ruled(diagnosis, self.y, 4, x_first)

        # Объективный осмотр
        self.y += P + 3
        self._font(10)
        self._text(self.LEFT + 1, self.y, "Данные объективного осмотра:")

        self.y += P
        self._inline(self.LEFT + 2, "АД -", "мм рт ст.", 16, get("АД"))
        self._inline(self.LEFT + 95, "Температура -", "°C", 12, get("Температура"))
        self.y += P
        self._inline(self.LEFT + 2, "Пульс -", "уд. в 1 мин.", 16, get("Пульс"))
        self._inline(self.LEFT + 95, "Сатурация -", "%", 12, get("Сатурация"))
        self.y += P
        self._inline(self.LEFT + 2, "Сахар крови -", "ммоль/л.", 14, get("Сахар крови"))

        # ЭКГ
        self.y += P + 3
        self._single_field("ЭКГ", get("ЭКГ"))

        # Лечение
        self.y += P
        self._font(10)
        self._text(self.LEFT + 1, self.y, "Проведено лечение:")
        self.y = self._ruled(get("Назначенное лечение"), self.y + P, 5, self.LEFT)

        # Врач, дата
        self.y += P + 4
        label = "Врач-специалист, должность, ФИО"
        self._font(10)
        self._text(self.LEFT + 1, self.y, label)
        x = self.LEFT + 1 + self._w(label) + 1.5
        self._line(x, self.RIGHT, self.y + 1.3)
        self._text(x + 0.8, self.y, get("Врач, назначивший лечение"))

        self.y += 7
        self._text(self.LEFT + 1, self.y, "Дата")
        x = self.LEFT + 1 + self._w("Дата") + 1
        self._line(x, x + 30, self.y + 1.3)
        self._text(x + 1, self.y, get("Дата"))

        # Время прибытия БСМП — рядом с датой
        x_time_label = x + 30 + 4
        self._text(x_time_label, self.y, "Время")
        x_time = x_time_label + self._w("Время") + 1
        self._line(x_time, x_time + 22, self.y + 1.3)
        self._text(x_time + 1, self.y, get("Время"))

        # Подписи
        self.y += 14
        self._text(self.LEFT + 1, self.y, "Врач:")
        x = self.LEFT + 1 + self._w("Врач:") + 1
        self._line(x, x + 45, self.y + 1.3)
        self._text(self.LEFT + 95, self.y, "Печать врача:")
        x = self.LEFT + 95 + self._w("Печать врача:") + 1
        self._line(x, x + 40, self.y + 1.3)


def _render(printer: QPrinter, data: dict):
    painter = QtGui.QPainter()
    if not painter.begin(printer):
        return
    try:
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        _FormRenderer(painter, printer, data).render()
    finally:
        painter.end()


def print_057(data: dict, parent=None):
    """Открывает предпросмотр направления, заполненного данными строки журнала.

    data — словарь {название колонки: текст ячейки}.
    """
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
    printer.setPageMargins(
        QtCore.QMarginsF(12, 12, 12, 12), QtGui.QPageLayout.Unit.Millimeter
    )

    dialog = QPrintPreviewDialog(printer, parent)
    dialog.setWindowTitle("Направление в дежурный стационар — предпросмотр")
    dialog.paintRequested.connect(lambda pr: _render(pr, data))
    dialog.resize(1000, 850)
    dialog.exec()