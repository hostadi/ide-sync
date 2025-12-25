#!/usr/bin/env python3
"""
ابزار مدیریت پروژه با هوش مصنوعی (بدون API)
"""

import sys
from ui_manager import UIManager

def main():
    """نقطه ورود اصلی برنامه"""
    try:
        # اجرای رابط کاربری
        ui = UIManager()
        ui.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 برنامه متوقف شد.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()