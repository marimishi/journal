
# 1. Единая палитра цветов приложения
COLORS = {
    "primary": "#1f538d",
    "primary_hover": "#14375e",
    "sidebar_bg": "#2b2b2b",
    "card_bg": "#ffffff",
    "border": "#e0e0e0",
    "input_border": "#cccccc",
    "text_dark": "#2b2b2b",
    "text_light": "#ffffff",
    "error": "#d9534f",
}

# 2. Шаблоны стилей (QSS)
STYLES = {
    "sidebar": f"""
        QFrame {{
            background-color: {COLORS['sidebar_bg']};
        }}
        QPushButton {{
            background-color: {COLORS['primary']};
            color: {COLORS['text_light']};
            border-radius: 8px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['primary_hover']};
        }}
        QLabel {{
            color: {COLORS['text_light']};
        }}
    """,
    
    "login_card": f"""
        QFrame {{
            background-color: {COLORS['card_bg']};
            border-radius: 12px;
            border: 1px solid {COLORS['border']};
        }}
        QLineEdit {{
            padding: 10px;
            border: 1px solid {COLORS['input_border']};
            border-radius: 6px;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 1px solid {COLORS['primary']};
        }}
        QPushButton {{
            background-color: {COLORS['primary']};
            color: {COLORS['text_light']};
            padding: 10px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['primary_hover']};
        }}
        QLabel#title {{
            font-size: 20px;
            font-weight: bold;
            color: {COLORS['text_dark']};
            border-radius: 0px;
            border: none;
        }}
    """,
    
    "error_label": f"color: {COLORS['error']}; border-radius: 0px; border: none;"
}


def get_style(name: str) -> str:
    return STYLES.get(name, "")