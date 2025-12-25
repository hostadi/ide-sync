import logging
import os
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

class AppLogger:
    """سیستم لاگ گیری برنامه"""
    
    def __init__(self, name="AIProjectManager", log_dir="logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # ایجاد logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # جلوگیری از تکرار handler
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """راه‌اندازی handlerهای مختلف"""
        
        # فرمت لاگ
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler 1: فایل اصلی (تمام لاگ‌ها)
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Handler 2: فایل خطاها (فقط ERROR و CRITICAL)
        error_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # Handler 3: Console (برای debug)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message):
        """لاگ debug"""
        self.logger.debug(message)
    
    def info(self, message):
        """لاگ اطلاعاتی"""
        self.logger.info(message)
    
    def warning(self, message):
        """لاگ هشدار"""
        self.logger.warning(message)
    
    def error(self, message, exc_info=False):
        """لاگ خطا"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message, exc_info=False):
        """لاگ خطای شدید"""
        self.logger.critical(message, exc_info=exc_info)
    
    def get_recent_logs(self, lines=100):
        """دریافت آخرین لاگ‌ها"""
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        if not log_file.exists():
            return "هنوز لاگی ثبت نشده است"
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"خطا در خواندن لاگ: {e}"
    
    def clear_old_logs(self, days=7):
        """حذف لاگ‌های قدیمی"""
        try:
            current_time = datetime.now()
            for log_file in self.log_dir.glob("*.log*"):
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if (current_time - file_time).days > days:
                    log_file.unlink()
                    self.info(f"لاگ قدیمی حذف شد: {log_file.name}")
        except Exception as e:
            self.error(f"خطا در حذف لاگ‌های قدیمی: {e}")

# نمونه global
app_logger = AppLogger()