#!/usr/bin/env python3
"""
نقطه ورود رابط گرافیکی
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui_manager import MainWindow
from logger import app_logger

def main():
    """اجرای برنامه GUI"""
    try:
        app_logger.info("=" * 50)
        app_logger.info("شروع برنامه GUI")
        app_logger.info("=" * 50)
        
        app = QApplication(sys.argv)
        app.setApplicationName("AI Project Manager")
        app.setOrganizationName("AIProjectManager")
        
        # تنظیم فونت فارسی
        # app.setFont(QFont("Tahoma", 9))
        
        window = MainWindow()
        window.show()
        
        exit_code = app.exec_()
        
        app_logger.info("برنامه با موفقیت بسته شد")
        sys.exit(exit_code)
        
    except Exception as e:
        app_logger.critical(f"خطای کلی برنامه: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()