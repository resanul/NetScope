from PySide6.QtWidgets import QApplication


class ThemeManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.current = "dark"

    def apply(self, mode: str):
        mode = mode.lower()
        self.current = mode
        self.app.setStyleSheet(self._light() if mode == "light" else self._dark())

    @staticmethod
    def _dark():
        return """
        * { font-family: "Segoe UI"; }
        QWidget { background:#0A0F18; color:#E7EDF5; font-size:10pt; }
        QMainWindow { background:#080D15; }
        QFrame#Sidebar { background:#0D131E; border-right:1px solid #202B3A; }
        QFrame#SidebarBottom { border-top:1px solid #202B3A; }
        QFrame#Card, QFrame#ToolHero { background:#111A27; border:1px solid #223044; border-radius:12px; }
        QLabel#Brand { color:#F8FAFC; font-size:18pt; font-weight:800; }
        QLabel#BrandBadge { color:#7DD3FC; background:#10283A; border:1px solid #1D4B67; border-radius:5px; padding:3px 6px; font-size:8pt; font-weight:700; }
        QLabel#PageTitle { color:#F8FAFC; font-size:20pt; font-weight:700; }
        QLabel#Muted { color:#8190A5; }
        QLabel#Metric { color:#F8FAFC; font-size:17pt; font-weight:700; }
        QLabel#HeroIcon { color:#67E8F9; background:#102B35; border:1px solid #1A5664; border-radius:10px; min-width:46px; min-height:46px; font-size:22pt; }
        QLabel#NavGroup { color:#5F7087; font-size:8pt; font-weight:700; padding:10px 10px 4px; }
        QLabel#StatusPill { color:#86EFAC; background:#102A20; border:1px solid #1C5A3D; border-radius:10px; padding:5px 10px; font-weight:700; }
        QLabel#AccentText { color:#67E8F9; font-weight:650; }
        QPushButton { background:#141F2D; color:#DCE6F2; border:1px solid #2A394D; border-radius:8px; padding:9px 14px; }
        QPushButton:hover { background:#1A293B; border-color:#3A526C; }
        QPushButton#PrimaryButton { background:#123C4B; color:#9BE8F3; border:1px solid #1F6B7D; font-weight:700; }
        QPushButton#PrimaryButton:hover { background:#165064; }
        QPushButton#NavButton { text-align:left; border:1px solid transparent; background:transparent; padding:8px 10px; border-radius:7px; }
        QPushButton#NavButton:hover { background:#151F2C; }
        QPushButton#NavButton[active="true"] { background:#102D3A; color:#7DE3F0; border:1px solid #1A5362; }
        QLineEdit, QComboBox { background:#0C141F; color:#E7EDF5; border:1px solid #2A394D; border-radius:8px; padding:9px 10px; }
        QLineEdit:focus, QComboBox:focus { border:1px solid #3C8192; }
        QTableWidget { background:#0C141F; alternate-background-color:#101B29; color:#DDE7F2; border:1px solid #223044; border-radius:9px; gridline-color:#1B2737; }
        QTableWidget::item { padding:6px; }
        QTableWidget::item:selected { background:#153C49; color:#F1FEFF; }
        QHeaderView::section { background:#141F2D; color:#8EA0B5; padding:8px; border:none; font-weight:700; }
        QScrollArea#NavScroll { border:none; background:transparent; }
        QScrollBar:vertical { background:#0D131E; width:8px; margin:0; }
        QScrollBar::handle:vertical { background:#263548; border-radius:4px; min-height:24px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """

    @staticmethod
    def _light():
        return """
        * { font-family: "Segoe UI"; }
        QWidget { background:#F5F7FA; color:#1E293B; font-size:10pt; }
        QMainWindow { background:#F5F7FA; }
        QFrame#Sidebar { background:#FFFFFF; border-right:1px solid #D9E1EA; }
        QFrame#SidebarBottom { border-top:1px solid #D9E1EA; }
        QFrame#Card, QFrame#ToolHero { background:#FFFFFF; border:1px solid #D9E1EA; border-radius:12px; }
        QLabel#Brand { color:#0F172A; font-size:18pt; font-weight:800; }
        QLabel#BrandBadge { color:#0369A1; background:#E0F2FE; border:1px solid #BAE6FD; border-radius:5px; padding:3px 6px; font-size:8pt; font-weight:700; }
        QLabel#PageTitle { color:#0F172A; font-size:20pt; font-weight:700; }
        QLabel#Muted { color:#64748B; }
        QLabel#Metric { color:#0F172A; font-size:17pt; font-weight:700; }
        QLabel#HeroIcon { color:#0E7490; background:#ECFEFF; border:1px solid #A5F3FC; border-radius:10px; min-width:46px; min-height:46px; font-size:22pt; }
        QLabel#NavGroup { color:#64748B; font-size:8pt; font-weight:700; padding:10px 10px 4px; }
        QLabel#StatusPill { color:#166534; background:#DCFCE7; border:1px solid #BBF7D0; border-radius:10px; padding:5px 10px; font-weight:700; }
        QLabel#AccentText { color:#0369A1; font-weight:650; }
        QPushButton { background:#FFFFFF; color:#334155; border:1px solid #CBD5E1; border-radius:8px; padding:9px 14px; }
        QPushButton:hover { background:#F1F5F9; }
        QPushButton#PrimaryButton { background:#E0F7FA; color:#0E7490; border:1px solid #A5F3FC; font-weight:700; }
        QPushButton#NavButton { text-align:left; border:1px solid transparent; background:transparent; padding:8px 10px; border-radius:7px; }
        QPushButton#NavButton:hover { background:#F1F5F9; }
        QPushButton#NavButton[active="true"] { background:#E0F7FA; color:#0E7490; border:1px solid #BAE6FD; }
        QLineEdit, QComboBox { background:#FFFFFF; color:#1E293B; border:1px solid #CBD5E1; border-radius:8px; padding:9px 10px; }
        QTableWidget { background:#FFFFFF; alternate-background-color:#F8FAFC; color:#334155; border:1px solid #D9E1EA; border-radius:9px; gridline-color:#E2E8F0; }
        QTableWidget::item { padding:6px; }
        QTableWidget::item:selected { background:#E0F7FA; color:#0F172A; }
        QHeaderView::section { background:#F1F5F9; color:#64748B; padding:8px; border:none; font-weight:700; }
        QScrollArea#NavScroll { border:none; background:transparent; }
        """
