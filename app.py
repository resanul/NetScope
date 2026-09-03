import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.theme import ThemeManager

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NetScope")
    app.setApplicationDisplayName("NetScope")
    app.setOrganizationName("NetScope")
    app.setStyle("Fusion")
    theme = ThemeManager(app)
    theme.apply("dark")
    window = MainWindow(theme)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
