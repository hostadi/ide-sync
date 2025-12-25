import sys
import pyperclip
from pathlib import Path
from typing import Optional
from project_serializer import ProjectSerializer
from git_manager import GitManager
from config import Config

class UIManager:
    """مدیریت رابط کاربری"""
    
    def __init__(self):
        self.serializer: Optional[ProjectSerializer] = None
        self.git_manager: Optional[GitManager] = None
        self.current_project_path: Optional[str] = None
        self.last_export: Optional[str] = None
    
    def run(self):
        """اجرای حلقه اصلی برنامه"""
        self.print_header()
        
        while True:
            self.print_menu()
            choice = input("\n👉 انتخاب شما: ").strip()
            
            if choice == '1':
                self.load_and_export_project()
            elif choice == '2':
                self.apply_ai_changes()
            elif choice == '3':
                self.view_last_export()
            elif choice == '4':
                self.view_git_status()
            elif choice == '5':
                self.show_instructions()
            elif choice == '6':
                self.exit_program()
                break
            else:
                print("❌ گزینه نامعتبر!")
    
    def print_header(self):
        """چاپ header برنامه"""
        print("\n" + "=" * 70)
        print("🤖  ابزار مدیریت پروژه با هوش مصنوعی (بدون API)")
        print("=" * 70)
        print("💡 این برنامه پروژه شما را آماده می‌کند تا با هر هوش مصنوعی کار کنید!")
        print("=" * 70)
    
    def print_menu(self):
        """چاپ منوی اصلی"""
        print("\n" + "-" * 70)
        print("📋 منوی اصلی:")
        print("-" * 70)
        print("1️⃣  بارگذاری پروژه و خروجی گرفتن (برای دادن به AI)")
        print("2️⃣  اعمال تغییرات AI (پس از دریافت پاسخ از AI)")
        print("3️⃣  مشاهده آخرین خروجی")
        print("4️⃣  وضعیت Git")
        print("5️⃣  راهنمای استفاده")
        print("6️⃣  خروج")
        print("-" * 70)
    
    def load_and_export_project(self):
        """بارگذاری پروژه و ایجاد خروجی برای AI"""
        project_path = input("\n📁 مسیر پروژه را وارد کنید: ").strip()
        
        if not project_path:
            print("❌ مسیر وارد نشد!")
            return
        
        try:
            print("\n⏳ در حال پردازش پروژه...")
            
            # ایجاد serializer و git manager
            self.serializer = ProjectSerializer(project_path)
            self.git_manager = GitManager(project_path)
            self.current_project_path = project_path
            
            # مقداردهی Git
            self.git_manager.init_or_load_repo()
            
            # سریال‌سازی پروژه
            json_output = self.serializer.serialize_project()
            self.last_export = json_output
            
            # نمایش آمار
            print(f"\n✅ پروژه آماده شد!")
            print(f"📏 اندازه خروجی: {len(json_output):,} کاراکتر")
            
            # ذخیره در فایل
            output_file = Path(project_path) / "ai_export.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"💾 خروجی ذخیره شد در: {output_file}")            
            # کپی به clipboard
            try:
                pyperclip.copy(json_output)
                print("📋 خروجی به clipboard کپی شد!")
            except:
                print("⚠️  نتوانستم به clipboard کپی کنم")
            
            # نمایش دستورالعمل
            print("\n" + "=" * 70)
            print("🎯 مراحل بعدی:")
            print("=" * 70)
            print(Config.SYSTEM_PROMPT)
            print("=" * 70)
            
            # نمایش بخشی از خروجی
            print("\n📄 پیش‌نمایش خروجی (500 کاراکتر اول):")
            print("-" * 70)
            print(json_output[:500] + "...")
            print("-" * 70)
            
            # پیشنهاد نمایش کامل
            show_full = input("\n❓ می‌خواهید کل خروجی را ببینید؟ (y/n): ").strip().lower()
            if show_full == 'y':
                print("\n" + "=" * 70)
                print(json_output)
                print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ خطا: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_ai_changes(self):
        """اعمال تغییرات دریافتی از AI"""
        if not self.serializer:
            print("\n❌ ابتدا یک پروژه بارگذاری کنید!")
            return
        
        print("\n" + "=" * 70)
        print("📥 دریافت پاسخ از هوش مصنوعی")
        print("=" * 70)
        print("💡 خروجی JSON دریافتی از هوش مصنوعی را paste کنید")
        print("⚠️  پس از paste، یک خط خالی وارد کنید و سپس 'END' تایپ کنید")
        print("-" * 70)
        
        lines = []
        print("شروع کنید:")
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        
        ai_output = "\n".join(lines)
        
        if not ai_output.strip():
            print("❌ ورودی خالی است!")
            return
        
        try:
            # نمایش خلاصه
            print("\n⏳ در حال پردازش پاسخ هوش مصنوعی...")
            
            # Parse کردن JSON
            project_data = self.serializer.deserialize_project(ai_output)
            
            print(f"✅ JSON معتبر است!")
            print(f"📊 تعداد فایل‌ها در پاسخ: {len(project_data.get('files', []))}")
            
            # درخواست توضیحات از کاربر
            description = input("\n📝 توضیح مختصری برای این تغییرات بنویسید: ").strip()
            if not description:
                description = "تغییرات هوش مصنوعی"
            
            # ایجاد branch جدید
            print("\n⏳ ایجاد branch جدید...")
            branch_name = self.git_manager.create_feature_branch(description)
            
            # اعمال تغییرات
            print("\n⏳ اعمال تغییرات به پروژه...")
            changes = self.serializer.apply_changes(project_data)
            
            # نمایش تغییرات
            print("\n" + "=" * 70)
            print("📝 تغییرات اعمال شده:")
            print("=" * 70)
            for change in changes:
                print(f"   {change}")
            print("=" * 70)
            
            # Stage و Commit
            print("\n⏳ ایجاد commit...")
            self.git_manager.stage_all_changes()
            commit_message = f"AI: {description}"
            self.git_manager.commit_changes(commit_message)
            
            # نمایش diff
            print("\n" + "=" * 70)
            print("🔍 مقایسه با نسخه قبلی (Git Diff):")
            print("=" * 70)
            diff = self.git_manager.get_diff()
            
            if diff:
                # نمایش محدود diff
                diff_lines = diff.split('\n')
                preview_lines = min(50, len(diff_lines))
                
                print('\n'.join(diff_lines[:preview_lines]))
                
                if len(diff_lines) > preview_lines:
                    print(f"\n... ({len(diff_lines) - preview_lines} خط دیگر)")
                    show_full_diff = input("\n❓ می‌خواهید کل diff را ببینید؟ (y/n): ").strip().lower()
                    if show_full_diff == 'y':
                        print("\n" + diff)
            else:
                print("ℹ️  تغییری شناسایی نشد")
            
            print("=" * 70)
            
            # درخواست تایید
            approve = input("\n✅ آیا این تغییرات را تایید می‌کنید؟ (y/n): ").strip().lower()
            
            if approve == 'y':
                # Merge به main
                print("\n⏳ ادغام تغییرات...")
                if self.git_manager.merge_to_base():
                    print("\n🎉 تغییرات با موفقیت اعمال و ادغام شدند!")
                    
                    # حذف feature branch
                    self.git_manager.checkout_branch(Config.DEFAULT_BASE_BRANCH)
                    self.git_manager.delete_branch(branch_name)
                else:
                    print("\n⚠️  مشکلی در ادغام پیش آمد. branch حفظ شد.")
            else:
                # بازگشت به main و حذف branch
                print("\n⏳ لغو تغییرات...")
                self.git_manager.checkout_branch(Config.DEFAULT_BASE_BRANCH)
                self.git_manager.delete_branch(branch_name)
                print("\n❌ تغییرات رد شدند و branch حذف شد.")
            
        except Exception as e:
            print(f"\n❌ خطا در پردازش: {e}")
            import traceback
            traceback.print_exc()
    
    def view_last_export(self):
        """نمایش آخرین خروجی ایجاد شده"""
        if not self.last_export:
            print("\n❌ هنوز خروجی ایجاد نشده است!")
            return
        
        print("\n" + "=" * 70)
        print("📄 آخرین خروجی:")
        print("=" * 70)
        print(self.last_export)
        print("=" * 70)
        
        # کپی به clipboard
        try:
            pyperclip.copy(self.last_export)
            print("\n📋 خروجی مجدداً به clipboard کپی شد!")
        except:
            pass
    
    def view_git_status(self):
        """نمایش وضعیت Git"""
        if not self.git_manager:
            print("\n❌ ابتدا یک پروژه بارگذاری کنید!")
            return
        
        print("\n" + "=" * 70)
        print("📊 وضعیت Git:")
        print("=" * 70)
        print(f"📁 مسیر: {self.current_project_path}")
        print(f"🌿 Branch فعلی: {self.git_manager.get_current_branch()}")
        print("-" * 70)
        print(self.git_manager.get_status())
        print("=" * 70)
    
    def show_instructions(self):
        """نمایش راهنمای کامل"""
        print("\n" + "=" * 70)
        print("📖 راهنمای کامل استفاده")
        print("=" * 70)
        print("""
🎯 مراحل کار با این ابزار:

1️⃣  بارگذاری پروژه:
   - گزینه 1 را انتخاب کنید
   - مسیر پروژه خود را وارد کنید
   - برنامه پروژه را پردازش کرده و یک JSON می‌سازد
   - JSON به clipboard و یک فایل کپی می‌شود

2️⃣  کار با هوش مصنوعی:
   - به هر چت AI بروید (ChatGPT, Claude, Gemini, ...)
   - دستورالعمل را به AI بدهید (برنامه نمایش می‌دهد)
   - JSON پروژه را paste کنید
   - درخواست‌های خود را بنویسید
   - AI یک JSON جدید با تغییرات برمی‌گرداند

3️⃣  اعمال تغییرات:
   - گزینه 2 را انتخاب کنید
   - JSON دریافتی از AI را paste کنید
   - توضیح مختصری بنویسید
   - تغییرات را بررسی کنید
   - تایید یا رد کنید

4️⃣  مدیریت Git:
   - برنامه خودکار branch می‌سازد
   - commit می‌کند
   - diff نمایش می‌دهد
   - در صورت تایید merge می‌کند

💡 نکات مهم:
   ✅ همیشه قبل از تایید، diff را بررسی کنید
   ✅ توضیحات واضح برای تغییرات بنویسید
   ✅ می‌توانید چندین بار تغییرات بگیرید
   ✅ تغییرات رد شده قابل بازیابی نیستند
   
🔒 امنیت:
   ✅ نیازی به API key نیست
   ✅ پروژه روی سیستم شما باقی می‌ماند
   ✅ کنترل کامل روی تغییرات دارید
        """)
        print("=" * 70)
    
    def exit_program(self):
        """خروج از برنامه"""
        print("\n" + "=" * 70)
        print("👋 از استفاده شما سپاسگزاریم!")
        print("💡 پروژه شما ذخیره شده و آماده استفاده مجدد است")
        print("=" * 70 + "\n")