#!/usr/bin/env python3
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from driver_manager import DriverManager

class DriverManagerApp:
    def __init__(self):
        # Hapus/matikan set QT_QPA_PLATFORM agar Qt memilih platform otomatis

        # Check if running as root
        if os.geteuid() != 0:
            print("Error: This application requires root privileges.")
            print("Please run with sudo.")
            sys.exit(1)

        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Driver Manager")
        self.app.setApplicationVersion("1.0.0")

        # Gunakan icon dari tema KDE yang bukan gear, misal "computer"
        kde_icon = QIcon.fromTheme("computer")
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if not kde_icon.isNull():
            self.app.setWindowIcon(kde_icon)
        elif os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))

        self.window = DriverManager()
        if not kde_icon.isNull():
            self.window.setWindowIcon(kde_icon)
        elif os.path.exists(icon_path):
            self.window.setWindowIcon(QIcon(icon_path))


    def run(self):
        self.window.show()
        sys.exit(self.app.exec())

def main():
    app = DriverManagerApp()
    app.run()

if __name__ == "__main__":
    main()