from PySide6.QtWidgets import QApplication

class ThemeManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.current = "dark"

    def apply(self, mode: str):
        mode = mode.lower()
        self.current = mode
        self.app.setStyleSheet(self._light() if mode in ("light", "system") else self._dark())

    @staticmethod
    def _dark():
        return '''
        QWidget { background:#111827; color:#E5E7EB; font-family:"Segoe UI"; font-size:10pt; }
        QMainWindow { background:#0B1220; }
        QFrame#Sidebar { background:#0B1220; border-right:1px solid #263244; }
        QFrame#Card { background:#172033; border:1px solid #263244; border-radius:12px; }
        QLabel#Brand { color:#F9FAFB; font-size:18pt; font-weight:700; }
        QLabel#PageTitle { color:#F9FAFB; font-size:20pt; font-weight:700; }
        QLabel#Muted { color:#94A3B8; }
        QLabel#Metric { color:#F9FAFB; font-size:17pt; font-weight:700; }
        QPushButton { background:#1F2937; border:1px solid #334155; border-radius:8px; padding:8px 12px; }
        QPushButton:hover { background:#273449; }
        QPushButton#NavButton { text-align:left; border:none; background:transparent; padding:10px 12px; }
        QPushButton#NavButton:hover { background:#172033; }
        QPushButton#NavButton[active="true"] { background:#24324A; color:#93C5FD; }
        QLineEdit, QComboBox { background:#0F172A; border:1px solid #334155; border-radius:8px; padding:8px; }
        QTableWidget { background:#0F172A; alternate-background-color:#131D2E; border:1px solid #263244; border-radius:8px; gridline-color:#263244; }
        QHeaderView::section { background:#172033; padding:8px; border:none; }
        '''

    @staticmethod
    def _light():
        return '''
        QWidget { background:#F5F7FA; color:#1F2937; font-family:"Segoe UI"; font-size:10pt; }
        QMainWindow { background:#F5F7FA; }
        QFrame#Sidebar { background:#FFFFFF; border-right:1px solid #D9E0E8; }
        QFrame#Card { background:#FFFFFF; border:1px solid #D9E0E8; border-radius:12px; }
        QLabel#Brand { color:#111827; font-size:18pt; font-weight:700; }
        QLabel#PageTitle { color:#111827; font-size:20pt; font-weight:700; }
        QLabel#Muted { color:#64748B; }
        QLabel#Metric { color:#111827; font-size:17pt; font-weight:700; }
        QPushButton { background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px 12px; }
        QPushButton:hover { background:#EEF2F7; }
        QPushButton#NavButton { text-align:left; border:none; background:transparent; padding:10px 12px; }
        QPushButton#NavButton:hover { background:#EEF2F7; }
        QPushButton#NavButton[active="true"] { background:#E0ECFF; color:#1D4ED8; }
        QLineEdit, QComboBox { background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; padding:8px; }
        QTableWidget { background:#FFFFFF; alternate-background-color:#F8FAFC; border:1px solid #D9E0E8; border-radius:8px; }
        QHeaderView::section { background:#EEF2F7; padding:8px; border:none; }
        '''
