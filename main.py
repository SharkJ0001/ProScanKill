import sys
import os
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    from gui import ProScanKillMainWindow
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ProScanKillMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()