import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFileDialog, QTabWidget,
    QSplitter, QGroupBox, QMessageBox, QProgressBar, QStatusBar,
    QAction, QMenuBar, QDialog, QScrollArea, QCheckBox, QLineEdit,
    QTextBrowser, QSpinBox  # اضافه شد
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QIcon, QColor, QPalette
import pyperclip

from project_serializer import ProjectSerializer
from git_manager import GitManager
from config import Config
from logger import app_logger

class WorkerThread(QThread):
    """Thread جداگانه برای عملیات سنگین"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            app_logger.error(f"خطا در WorkerThread: {e}", exc_info=True)
            self.error.emit(str(e))

class PromptDialog(QDialog):
    """پنجره نمایش و کپی پرامپت"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 دستورالعمل برای هوش مصنوعی")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "💡 این دستورالعمل را ابتدا به هوش مصنوعی بدهید، سپس JSON پروژه را ارسال کنید"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setFont(QFont("Courier New", 10))
        self.prompt_text.setPlainText(Config.SYSTEM_PROMPT)
        layout.addWidget(self.prompt_text)
        
        btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 کپی به Clipboard")
        copy_btn.clicked.connect(self.copy_prompt)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def copy_prompt(self):
        try:
            pyperclip.copy(Config.SYSTEM_PROMPT)
            QMessageBox.information(
                self,
                "موفق",
                "✅ دستورالعمل به clipboard کپی شد!\n\nحالا به چت هوش مصنوعی بروید و paste کنید."
            )
            app_logger.info("پرامپت به clipboard کپی شد")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در کپی:\n{e}")

class LogViewerDialog(QDialog):
    """پنجره نمایش لاگ‌ها"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 مشاهده لاگ‌ها")
        self.setGeometry(100, 100, 900, 600)
        
        layout = QVBoxLayout()
        
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.load_logs)
        toolbar.addWidget(refresh_btn)
        
        clear_btn = QPushButton("🗑️ پاک کردن لاگ‌های قدیمی")
        clear_btn.clicked.connect(self.clear_old_logs)
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        self.level_filter = QLineEdit()
        self.level_filter.setPlaceholderText("فیلتر سطح (INFO, ERROR, ...)")
        self.level_filter.textChanged.connect(self.filter_logs)
        toolbar.addWidget(QLabel("فیلتر:"))
        toolbar.addWidget(self.level_filter)
        
        layout.addLayout(toolbar)
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_viewer)
        
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.load_logs()
    
    def load_logs(self):
        try:
            logs = app_logger.get_recent_logs(500)
            self.all_logs = logs
            self.log_viewer.setPlainText(logs)
            
            cursor = self.log_viewer.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_viewer.setTextCursor(cursor)
            
            line_count = logs.count('\n')
            self.status_label.setText(f"تعداد خطوط: {line_count}")
            
            app_logger.info("لاگ‌ها بارگذاری شدند")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لاگ‌ها:\n{e}")
            app_logger.error(f"خطا در بارگذاری لاگ‌ها: {e}")
    
    def filter_logs(self):
        filter_text = self.level_filter.text().upper()
        
        if not filter_text:
            self.log_viewer.setPlainText(self.all_logs)
            return
        
        filtered_lines = [
            line for line in self.all_logs.split('\n')
            if filter_text in line.upper()
        ]
        
        self.log_viewer.setPlainText('\n'.join(filtered_lines))
        self.status_label.setText(f"نتایج فیلتر شده: {len(filtered_lines)} خط")
    
    def clear_old_logs(self):
        reply = QMessageBox.question(
            self,
            "تایید",
            "آیا مطمئن هستید که می‌خواهید لاگ‌های قدیمی‌تر از 7 روز را حذف کنید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            app_logger.clear_old_logs(7)
            QMessageBox.information(self, "انجام شد", "لاگ‌های قدیمی حذف شدند")
            self.load_logs()

class PartSelectorDialog(QDialog):
    """پنجره انتخاب تنظیمات تقسیم‌بندی"""
    
    def __init__(self, total_chars, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ تنظیمات تقسیم‌بندی")
        self.setGeometry(200, 200, 500, 400)
        
        self.total_chars = total_chars
        self.selected_max_chars = Config.DEFAULT_MAX_CHARS_PER_PART
        
        layout = QVBoxLayout()
        
        info = QLabel(f"📊 حجم کل پروژه: {total_chars:,} کاراکتر")
        info.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        chars_layout = QHBoxLayout()
        chars_layout.addWidget(QLabel("حداکثر کاراکتر هر بخش:"))
        
        self.chars_spinbox = QSpinBox()
        self.chars_spinbox.setRange(Config.MIN_CHARS_PER_PART, Config.MAX_CHARS_PER_PART)
        self.chars_spinbox.setValue(Config.DEFAULT_MAX_CHARS_PER_PART)
        self.chars_spinbox.setSuffix(" کاراکتر")
        self.chars_spinbox.valueChanged.connect(self.update_parts_count)
        chars_layout.addWidget(self.chars_spinbox)
        
        layout.addLayout(chars_layout)
        
        self.parts_label = QLabel()
        self.update_parts_count()
        layout.addWidget(self.parts_label)
        
        suggestions_group = QGroupBox("💡 پیشنهادات")
        suggestions_layout = QVBoxLayout()
        
        suggestions = [
            ("ChatGPT (GPT-4): 8,000 کاراکتر", 8000),
            ("Claude: 15,000 کاراکتر", 15000),
            ("Gemini: 20,000 کاراکتر", 20000),
        ]
        
        for text, value in suggestions:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, v=value: self.chars_spinbox.setValue(v))
            suggestions_layout.addWidget(btn)
        
        suggestions_group.setLayout(suggestions_layout)
        layout.addWidget(suggestions_group)
        
        btn_layout = QHBoxLayout()
        
        ok_btn = QPushButton("✅ تایید")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ لغو")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def update_parts_count(self):
        max_chars = self.chars_spinbox.value()
        estimated_parts = (self.total_chars // max_chars) + 1
        
        self.parts_label.setText(
            f"📦 تعداد بخش‌های تخمینی: {estimated_parts} بخش\n"
            f"⚠️ شما باید {estimated_parts} پیام جداگانه به AI بفرستید"
        )
        self.parts_label.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        self.selected_max_chars = max_chars
    
    def get_max_chars(self):
        return self.selected_max_chars

class FileSelectionDialog(QDialog):
    """پنجره انتخاب فایل‌ها"""
    
    def __init__(self, files_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📁 انتخاب فایل‌ها")
        self.setGeometry(200, 200, 600, 500)
        
        self.files_list = files_list
        self.selected_files = []
        
        layout = QVBoxLayout()
        
        info = QLabel(
            "💡 فایل‌هایی که می‌خواهید در خروجی باشند را انتخاب کنید.\n"
            "برای پروژه‌های بزرگ، فقط فایل‌های مرتبط با تغییرات را انتخاب کنید."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✅ انتخاب همه")
        select_all_btn.clicked.connect(self.select_all)
        btn_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("❌ لغو همه")
        deselect_all_btn.clicked.connect(self.deselect_all)
        btn_layout.addWidget(deselect_all_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        files_widget = QWidget()
        files_layout = QVBoxLayout()
        
        self.checkboxes = {}
        for path, size in files_list:
            size_kb = size / 1024
            checkbox = QCheckBox(f"{path} ({size_kb:.1f} KB)")
            checkbox.setChecked(True)
            self.checkboxes[path] = checkbox
            files_layout.addWidget(checkbox)
        
        files_widget.setLayout(files_layout)
        scroll.setWidget(files_widget)
        layout.addWidget(scroll)
        
        self.stats_label = QLabel()
        self.update_stats()
        layout.addWidget(self.stats_label)
        
        confirm_layout = QHBoxLayout()
        
        ok_btn = QPushButton("✅ تایید")
        ok_btn.clicked.connect(self.accept_selection)
        confirm_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("❌ لغو")
        cancel_btn.clicked.connect(self.reject)
        confirm_layout.addWidget(cancel_btn)
        
        layout.addLayout(confirm_layout)
        
        self.setLayout(layout)
        
        for checkbox in self.checkboxes.values():
            checkbox.stateChanged.connect(self.update_stats)
    
    def select_all(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
    
    def update_stats(self):
        selected_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        total_count = len(self.checkboxes)
        
        self.stats_label.setText(
            f"📊 {selected_count} از {total_count} فایل انتخاب شده"
        )
    
    def accept_selection(self):
        self.selected_files = [
            path for path, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]
        
        if not self.selected_files:
            QMessageBox.warning(self, "هشدار", "حداقل یک فایل را انتخاب کنید!")
            return
        
        self.accept()
    
    def get_selected_files(self):
        return self.selected_files

class PartsViewerDialog(QDialog):
    """پنجره نمایش و کپی بخش‌های جداگانه"""
    
    def __init__(self, parts, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📦 نمایش {len(parts)} بخش")
        self.setGeometry(100, 100, 900, 700)
        
        self.parts = parts
        
        layout = QVBoxLayout()
        
        guide = QLabel(
            f"💡 پروژه به {len(parts)} بخش تقسیم شده است.\n"
            f"هر بخش را به ترتیب در پیام‌های جداگانه به هوش مصنوعی بفرستید."
        )
        guide.setWordWrap(True)
        guide.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(guide)
        
        tabs = QTabWidget()
        
        for i, part in enumerate(parts, 1):
            part_widget = QWidget()
            part_layout = QVBoxLayout()
            
            copy_btn = QPushButton(f"📋 کپی بخش {i}")
            copy_btn.clicked.connect(lambda checked, p=part: self.copy_part(p))
            copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 10px;
                    font-weight: bold;
                }
            """)
            part_layout.addWidget(copy_btn)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Courier New", 9))
            text_edit.setPlainText(part)
            part_layout.addWidget(text_edit)
            
            stats = QLabel(f"📏 {len(part):,} کاراکتر | {part.count(chr(10)):,} خط")
            part_layout.addWidget(stats)
            
            part_widget.setLayout(part_layout)
            tabs.addTab(part_widget, f"بخش {i}/{len(parts)}")
        
        layout.addWidget(tabs)
        
        btn_layout = QHBoxLayout()
        
        copy_all_btn = QPushButton("📋 کپی همه بخش‌ها (با فاصله)")
        copy_all_btn.clicked.connect(self.copy_all_parts)
        btn_layout.addWidget(copy_all_btn)
        
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def copy_part(self, part):
        try:
            pyperclip.copy(part)
            QMessageBox.information(
                self,
                "موفق",
                "✅ بخش به clipboard کپی شد!\n\nحالا به چت AI بروید و paste کنید."
            )
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در کپی:\n{e}")
    
    def copy_all_parts(self):
        try:
            combined = "\n\n" + "="*80 + "\n\n".join(self.parts)
            pyperclip.copy(combined)
            QMessageBox.information(
                self,
                "موفق",
                f"✅ تمام {len(self.parts)} بخش به clipboard کپی شدند!\n\n"
                "توجه: این برای تست است. در عمل باید هر بخش را جداگانه بفرستید."
            )
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در کپی:\n{e}")

class MainWindow(QMainWindow):
    """پنجره اصلی برنامه"""
    
    def __init__(self):
        super().__init__()
        
        app_logger.info("برنامه شروع شد")
        
        self.serializer = None
        self.git_manager = None
        self.current_project_path = None
        self.last_export = None
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """ایجاد رابط کاربری"""
        self.setWindowTitle("🤖 ابزار مدیریت پروژه با هوش مصنوعی")
        self.setGeometry(100, 100, 1400, 900)
        
        self.create_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        header = self.create_header()
        main_layout.addWidget(header)
        
        tabs = QTabWidget()
        
        export_tab = self.create_export_tab()
        tabs.addTab(export_tab, "📤 خروجی پروژه")
        
        import_tab = self.create_import_tab()
        tabs.addTab(import_tab, "📥 اعمال تغییرات")
        
        git_tab = self.create_git_tab()
        tabs.addTab(git_tab, "🌿 وضعیت Git")
        
        help_tab = self.create_help_tab()
        tabs.addTab(help_tab, "📖 راهنما")
        
        main_layout.addWidget(tabs)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("آماده")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        central_widget.setLayout(main_layout)
        
        app_logger.info("رابط کاربری ایجاد شد")
    
    def create_menu_bar(self):
        """ایجاد منوبار"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("📁 فایل")
        
        open_action = QAction("باز کردن پروژه", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("خروج", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        tools_menu = menubar.addMenu("🔧 ابزارها")
        
        prompt_action = QAction("📋 مشاهده دستورالعمل AI", self)
        prompt_action.setShortcut("Ctrl+P")
        prompt_action.triggered.connect(self.show_prompt_dialog)
        tools_menu.addAction(prompt_action)
        
        tools_menu.addSeparator()
        
        logs_action = QAction("مشاهده لاگ‌ها", self)
        logs_action.setShortcut("Ctrl+L")
        logs_action.triggered.connect(self.show_logs)
        tools_menu.addAction(logs_action)
        
        settings_action = QAction("تنظیمات", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        help_menu = menubar.addMenu("❓ راهنما")
        
        about_action = QAction("درباره", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_header(self):
        """ایجاد header"""
        header = QGroupBox()
        layout = QVBoxLayout()
        
        title = QLabel("🤖 ابزار مدیریت پروژه با هوش مصنوعی")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("بدون نیاز به API - با همه هوش مصنوعی‌ها کار می‌کند")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        self.project_info_label = QLabel("هیچ پروژه‌ای بارگذاری نشده")
        self.project_info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.project_info_label)
        
        header.setLayout(layout)
        return header
    
    def create_export_tab(self):
        """ایجاد تب خروجی"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        btn_layout_1 = QHBoxLayout()
        
        self.select_project_btn = QPushButton("📁 انتخاب پروژه")
        self.select_project_btn.clicked.connect(self.select_project)
        btn_layout_1.addWidget(self.select_project_btn)
        
        self.full_export_radio = QCheckBox("کل پروژه")
        self.full_export_radio.setChecked(True)
        btn_layout_1.addWidget(self.full_export_radio)
        
        self.selected_files_radio = QCheckBox("فایل‌های انتخابی")
        btn_layout_1.addWidget(self.selected_files_radio)
        
        self.changes_only_radio = QCheckBox("فقط تغییرات")
        btn_layout_1.addWidget(self.changes_only_radio)
        
        btn_layout_1.addStretch()
        
        layout.addLayout(btn_layout_1)
        
        btn_layout_2 = QHBoxLayout()
        
        self.export_btn = QPushButton("📤 خروجی گرفتن")
        self.export_btn.clicked.connect(self.export_project_with_options)
        self.export_btn.setEnabled(False)
        btn_layout_2.addWidget(self.export_btn)
        
        self.split_btn = QPushButton("✂️ تقسیم به بخش‌ها")
        self.split_btn.clicked.connect(self.split_into_parts)
        self.split_btn.setEnabled(False)
        btn_layout_2.addWidget(self.split_btn)
        
        btn_layout_2.addStretch()
        
        layout.addLayout(btn_layout_2)
        
        btn_layout_3 = QHBoxLayout()
        
        self.copy_prompt_btn = QPushButton("📋 کپی دستورالعمل (مرحله 1)")
        self.copy_prompt_btn.clicked.connect(self.copy_prompt_quick)
        self.copy_prompt_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        btn_layout_3.addWidget(self.copy_prompt_btn)
        
        self.copy_json_btn = QPushButton("📋 کپی JSON (مرحله 2)")
        self.copy_json_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_json_btn.setEnabled(False)
        self.copy_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        btn_layout_3.addWidget(self.copy_json_btn)
        
        self.save_file_btn = QPushButton("💾 ذخیره")
        self.save_file_btn.clicked.connect(self.save_to_file)
        self.save_file_btn.setEnabled(False)
        btn_layout_3.addWidget(self.save_file_btn)
        
        layout.addLayout(btn_layout_3)
        
        quick_guide = QLabel(
            "📌 <b>راهنما:</b> "
            "1️⃣ دستورالعمل (نارنجی) → "
            "2️⃣ JSON یا بخش‌ها (آبی) → "
            "3️⃣ اگر بزرگ بود از دکمه 'تقسیم' استفاده کنید"
        )
        quick_guide.setWordWrap(True)
        quick_guide.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(quick_guide)
        
        output_group = QGroupBox("خروجی JSON")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 10))
        output_layout.addWidget(self.output_text)
        
        self.stats_label = QLabel()
        output_layout.addWidget(self.stats_label)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_import_tab(self):
        """ایجاد تب اعمال تغییرات"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        guide = QLabel(
            "💡 JSON دریافتی از هوش مصنوعی را در کادر زیر paste کنید و روی دکمه 'اعمال تغییرات' کلیک کنید"
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)
        
        input_group = QGroupBox("JSON دریافتی از هوش مصنوعی")
        input_layout = QVBoxLayout()
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("JSON را اینجا paste کنید...")
        self.input_text.setFont(QFont("Courier New", 10))
        input_layout.addWidget(self.input_text)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("توضیحات:"))
        
        self.change_description = QLineEdit()
        self.change_description.setPlaceholderText("توضیح مختصری درباره تغییرات...")
        desc_layout.addWidget(self.change_description)
        
        layout.addLayout(desc_layout)
        
        btn_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("✅ اعمال تغییرات")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.apply_btn.setEnabled(False)
        btn_layout.addWidget(self.apply_btn)
        
        self.preview_btn = QPushButton("👁️ پیش‌نمایش تغییرات")
        self.preview_btn.clicked.connect(self.preview_changes)
        btn_layout.addWidget(self.preview_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        diff_group = QGroupBox("تغییرات (Git Diff)")
        diff_layout = QVBoxLayout()
        
        self.diff_text = QTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setFont(QFont("Courier New", 9))
        diff_layout.addWidget(self.diff_text)
        
        diff_group.setLayout(diff_layout)
        layout.addWidget(diff_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_git_tab(self):
        """ایجاد تب Git"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.clicked.connect(self.refresh_git_status)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        status_group = QGroupBox("وضعیت Repository")
        status_layout = QVBoxLayout()
        
        self.git_status_text = QTextEdit()
        self.git_status_text.setReadOnly(True)
        self.git_status_text.setFont(QFont("Courier New", 10))
        status_layout.addWidget(self.git_status_text)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_help_tab(self):
        """ایجاد تب راهنما"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        copy_prompt_btn = QPushButton("📋 کپی دستورالعمل AI")
        copy_prompt_btn.clicked.connect(self.copy_prompt_quick)
        copy_prompt_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(copy_prompt_btn)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        help_widget = QWidget()
        help_layout = QVBoxLayout()
        
        prompt_display = QTextEdit()
        prompt_display.setReadOnly(True)
        prompt_display.setFont(QFont("Courier New", 10))
        prompt_display.setPlainText(Config.SYSTEM_PROMPT)
        help_layout.addWidget(prompt_display)
        
        help_widget.setLayout(help_layout)
        scroll.setWidget(help_widget)
        
        layout.addWidget(scroll)
        widget.setLayout(layout)
        
        return widget
    
    def apply_theme(self):
        """اعمال تم رنگی"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QGroupBox {
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
            }
        """)
    
    def select_project(self):
        """انتخاب پروژه"""
        app_logger.info("انتخاب پروژه...")
        
        project_path = QFileDialog.getExistingDirectory(
            self,
            "انتخاب پوشه پروژه",
            str(Path.home())
        )
        
        if not project_path:
            return
        
        try:
            app_logger.info(f"پروژه انتخاب شد: {project_path}")
            
            self.current_project_path = project_path
            self.serializer = ProjectSerializer(project_path)
            self.git_manager = GitManager(project_path)
            
            self.git_manager.init_or_load_repo()
            
            base_branch = self.git_manager.get_base_branch()
            self.project_info_label.setText(
                f"📁 پروژه: {Path(project_path).name} | "
                f"🌿 Base: {base_branch}"
            )
            self.export_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
            self.split_btn.setEnabled(True)
            
            self.status_bar.showMessage(f"پروژه بارگذاری شد: {project_path}")
            
            self.refresh_git_status()
            
            branches = self.git_manager.list_branches()
            branch_info = f"📋 Branch‌های موجود: {', '.join(branches)}\n" if branches else ""
            
            QMessageBox.information(
                self,
                "موفق",
                f"پروژه '{Path(project_path).name}' با موفقیت بارگذاری شد!\n\n"
                f"🌿 Base branch: {base_branch}\n"
                f"{branch_info}"
            )
            
        except Exception as e:
            app_logger.error(f"خطا در بارگذاری پروژه: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری پروژه:\n{e}")
    
    def export_project_with_options(self):
        """خروجی با گزینه‌های مختلف"""
        if not self.serializer:
            QMessageBox.warning(self, "هشدار", "ابتدا یک پروژه انتخاب کنید!")
            return
        
        app_logger.info("شروع خروجی‌گیری...")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("در حال پردازش...")
        
        try:
            if self.changes_only_radio.isChecked():
                files = self.serializer.load_project_files()
                json_output = self.serializer.serialize_changes_only(files)
                
            elif self.selected_files_radio.isChecked():
                files_list = self.serializer.get_file_list()
                
                dialog = FileSelectionDialog(files_list, self)
                if dialog.exec_() == QDialog.Accepted:
                    selected = dialog.get_selected_files()
                    json_output = self.serializer.serialize_project(selected)
                else:
                    self.progress_bar.setVisible(False)
                    return
            else:
                json_output = self.serializer.serialize_project()
            
            self.on_export_finished(json_output)
            
        except Exception as e:
            self.on_worker_error(str(e))
    
    def split_into_parts(self):
        """تقسیم خروجی به بخش‌ها"""
        if not self.last_export:
            QMessageBox.warning(self, "هشدار", "ابتدا خروجی بگیرید!")
            return
        
        dialog = PartSelectorDialog(len(self.last_export), self)
        if dialog.exec_() != QDialog.Accepted:
            return
        
        max_chars = dialog.get_max_chars()
        
        app_logger.info(f"تقسیم به بخش‌ها با حداکثر {max_chars} کاراکتر")
        
        try:
            parts = self.serializer.split_into_parts(self.last_export, max_chars)
            
            app_logger.info(f"تقسیم به {len(parts)} بخش انجام شد")
            
            parts_dialog = PartsViewerDialog(parts, self)
            parts_dialog.exec_()
            
        except Exception as e:
            app_logger.error(f"خطا در تقسیم: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در تقسیم:\n{e}")
    
    def on_export_finished(self, json_output):
        """پس از اتمام خروجی‌گیری"""
        self.progress_bar.setVisible(False)
        
        self.last_export = json_output
        self.output_text.setPlainText(json_output)
        
        char_count = len(json_output)
        line_count = json_output.count('\n')
        self.stats_label.setText(
            f"📊 آمار: {char_count:,} کاراکتر | {line_count:,} خط"
        )
        
        self.copy_json_btn.setEnabled(True)
        self.save_file_btn.setEnabled(True)
        self.split_btn.setEnabled(True)
        
        self.status_bar.showMessage("✅ خروجی آماده شد")
        
        QMessageBox.information(
            self,
            "موفق",
            "✅ خروجی آماده شد!\n\n"
            "مراحل بعدی:\n"
            "1️⃣ دکمه نارنجی 'کپی دستورالعمل' را بزنید\n"
            "2️⃣ به چت AI بروید و دستورالعمل را paste کنید\n"
            "3️⃣ سپس دکمه آبی 'کپی JSON' را بزنید\n"
            "4️⃣ JSON را در چت AI paste کنید"
        )
        
        app_logger.info(f"خروجی با موفقیت ایجاد شد ({char_count} کاراکتر)")
    
    def copy_prompt_quick(self):
        """کپی سریع پرامپت"""
        try:
            pyperclip.copy(Config.SYSTEM_PROMPT)
            self.status_bar.showMessage("📋 دستورالعمل به clipboard کپی شد", 3000)
            
            QMessageBox.information(
                self,
                "موفق",
                "✅ دستورالعمل به clipboard کپی شد!\n\n"
                "حالا:\n"
                "1️⃣ به چت هوش مصنوعی بروید\n"
                "2️⃣ Paste کنید (Ctrl+V)\n"
                "3️⃣ منتظر تایید AI بمانید\n"
                "4️⃣ سپس JSON پروژه را ارسال کنید"
            )
            
            app_logger.info("پرامپت به clipboard کپی شد")
        except Exception as e:
            app_logger.error(f"خطا در کپی پرامپت: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در کپی:\n{e}")
    
    def copy_to_clipboard(self):
        """کپی JSON به clipboard"""
        if not self.last_export:
            QMessageBox.warning(self, "هشدار", "ابتدا خروجی بگیرید!")
            return
        
        try:
            pyperclip.copy(self.last_export)
            self.status_bar.showMessage("📋 JSON به clipboard کپی شد", 3000)
            
            QMessageBox.information(
                self,
                "موفق",
                "✅ JSON پروژه به clipboard کپی شد!\n\nحالا به چت هوش مصنوعی بروید و paste کنید"
            )
            
            app_logger.info("JSON به clipboard کپی شد")
        except Exception as e:
            app_logger.error(f"خطا در کپی: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در کپی:\n{e}")
    
    def save_to_file(self):
        """ذخیره در فایل"""
        if not self.last_export:
            QMessageBox.warning(self, "هشدار", "ابتدا خروجی بگیرید!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره خروجی",
            str(Path(self.current_project_path) / "ai_export.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.last_export)
                
                self.status_bar.showMessage(f"💾 ذخیره شد: {file_path}", 5000)
                app_logger.info(f"خروجی در فایل ذخیره شد: {file_path}")
                
                QMessageBox.information(self, "موفق", f"فایل ذخیره شد:\n{file_path}")
                
            except Exception as e:
                app_logger.error(f"خطا در ذخیره فایل: {e}")
                QMessageBox.critical(self, "خطا", f"خطا در ذخیره:\n{e}")
    
    def show_prompt_dialog(self):
        """نمایش پنجره پرامپت"""
        dialog = PromptDialog(self)
        dialog.exec_()
    
    def preview_changes(self):
        """پیش‌نمایش تغییرات"""
        ai_output = self.input_text.toPlainText().strip()
        
        if not ai_output:
            QMessageBox.warning(self, "هشدار", "ابتدا JSON را paste کنید!")
            return
        
        try:
            project_data = self.serializer.deserialize_project(ai_output)
            
            file_count = len(project_data.get('files', []))
            
            QMessageBox.information(
                self,
                "پیش‌نمایش",
                f"✅ JSON معتبر است\n\n"
                f"📊 تعداد فایل‌ها: {file_count}\n\n"
                f"برای اعمال تغییرات، دکمه 'اعمال تغییرات' را بزنید."
            )
            
            app_logger.info(f"پیش‌نمایش موفق: {file_count} فایل")
            
        except Exception as e:
            app_logger.error(f"خطا در پیش‌نمایش: {e}")
            QMessageBox.critical(
                self,
                "خطا",
                f"JSON نامعتبر است:\n\n{e}\n\n"
                "لطفاً مطمئن شوید که کل JSON را کپی کرده‌اید."
            )
    
    def apply_changes(self):
        """اعمال تغییرات هوش مصنوعی"""
        if not self.serializer or not self.git_manager:
            QMessageBox.warning(self, "هشدار", "ابتدا یک پروژه انتخاب کنید!")
            return
        
        ai_output = self.input_text.toPlainText().strip()
        
        if not ai_output:
            QMessageBox.warning(self, "هشدار", "JSON را paste کنید!")
            return
        
        description = self.change_description.text().strip()
        if not description:
            description = "تغییرات هوش مصنوعی"
        
        try:
            app_logger.info(f"شروع اعمال تغییرات: {description}")
            
            self.status_bar.showMessage("در حال پردازش JSON...")
            project_data = self.serializer.deserialize_project(ai_output)
            
            self.status_bar.showMessage("ایجاد branch جدید...")
            branch_name = self.git_manager.create_feature_branch(description)
            
            self.status_bar.showMessage("اعمال تغییرات...")
            changes = self.serializer.apply_changes(project_data)
            
            self.git_manager.stage_all_changes()
            commit_message = f"AI: {description}"
            self.git_manager.commit_changes(commit_message)
            
            diff = self.git_manager.get_diff()
            self.diff_text.setPlainText(diff if diff else "تغییری شناسایی نشد")
            
            changes_text = '\n'.join(changes[:20])
            if len(changes) > 20:
                changes_text += f"\n... و {len(changes) - 20} تغییر دیگر"
            
            reply = QMessageBox.question(
                self,
                "تایید تغییرات",
                f"تغییرات زیر اعمال شد:\n\n{changes_text}\n\n"
                f"آیا این تغییرات را تایید می‌کنید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.git_manager.merge_to_base():
                    base_branch = self.git_manager.get_base_branch()
                    self.git_manager.checkout_branch(base_branch)
                    self.git_manager.delete_branch(branch_name)
                    
                    QMessageBox.information(
                        self,
                        "موفق",
                        "🎉 تغییرات با موفقیت اعمال و ادغام شدند!"
                    )
                    
                    self.status_bar.showMessage("✅ تغییرات اعمال شدند")
                    app_logger.info("تغییرات با موفقیت اعمال شدند")
                    
                    self.input_text.clear()
                    self.change_description.clear()
                    
                    self.refresh_git_status()
                    
            else:
                base_branch = self.git_manager.get_base_branch()
                self.git_manager.checkout_branch(base_branch)
                self.git_manager.delete_branch(branch_name)
                
                QMessageBox.information(self, "لغو شد", "تغییرات رد شدند")
                self.status_bar.showMessage("❌ تغییرات رد شدند")
                app_logger.info("تغییرات توسط کاربر رد شدند")
                
        except Exception as e:
            app_logger.error(f"خطا در اعمال تغییرات: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در اعمال تغییرات:\n{e}")
            self.status_bar.showMessage("❌ خطا در اعمال تغییرات")
    
    def refresh_git_status(self):
        """بروزرسانی وضعیت Git"""
        if not self.git_manager:
            self.git_status_text.setPlainText("هیچ پروژه‌ای بارگذاری نشده")
            return
        
        try:
            status = self.git_manager.get_status()
            branch = self.git_manager.get_current_branch()
            
            status_text = f"🌿 Branch: {branch}\n\n{status}"
            self.git_status_text.setPlainText(status_text)
            
            app_logger.debug("وضعیت Git بروز شد")
            
        except Exception as e:
            app_logger.error(f"خطا در دریافت وضعیت Git: {e}")
            self.git_status_text.setPlainText(f"خطا: {e}")
    
    def show_logs(self):
        """نمایش پنجره لاگ‌ها"""
        app_logger.info("باز کردن پنجره لاگ‌ها")
        log_dialog = LogViewerDialog(self)
        log_dialog.exec_()
    
    def show_settings(self):
        """نمایش تنظیمات"""
        QMessageBox.information(
            self,
            "تنظیمات",
            "تنظیمات را می‌توانید در فایل config.py تغییر دهید"
        )
    
    def show_about(self):
        """نمایش درباره"""
        QMessageBox.about(
            self,
            "درباره",
            "🤖 ابزار مدیریت پروژه با هوش مصنوعی\n\n"
            "نسخه: 1.0.0\n\n"
            "این ابزار به شما کمک می‌کند از هر هوش مصنوعی برای مدیریت "
            "پروژه‌های نرم‌افزاری خود استفاده کنید، بدون نیاز به API key.\n\n"
            "توسعه: ابزار مدیریت پروژه AI"
        )
    
    def on_worker_error(self, error_msg):
        """مدیریت خطاهای worker thread"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("❌ خطا")
        
        QMessageBox.critical(self, "خطا", f"خطا در پردازش:\n{error_msg}")
        app_logger.error(f"خطای worker: {error_msg}")
    
    def closeEvent(self, event):
        """هنگام بستن برنامه"""
        reply = QMessageBox.question(
            self,
            "خروج",
            "آیا مطمئن هستید که می‌خواهید خارج شوید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            app_logger.info("برنامه بسته شد")
            event.accept()
        else:
            event.ignore()