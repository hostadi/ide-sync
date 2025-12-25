from git import Repo, GitCommandError
from pathlib import Path
from typing import Optional
from datetime import datetime
from config import Config

class GitManager:
    """مدیریت عملیات Git"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.repo: Optional[Repo] = None
        self.base_branch = None
        
    def init_or_load_repo(self) -> Repo:
        """مقداردهی اولیه یا بارگذاری repository"""
        try:
            self.repo = Repo(self.project_path)
            print(f"✅ Git repository موجود بارگذاری شد")
            
            # تشخیص base branch
            self.base_branch = self._detect_base_branch()
            print(f"📍 Base branch: {self.base_branch}")
            
        except:
            print(f"📦 Git repository جدید ایجاد می‌شود...")
            self.repo = Repo.init(self.project_path)
            
            # ایجاد .gitignore اگر وجود ندارد
            gitignore_path = self.project_path / '.gitignore'
            if not gitignore_path.exists():
                with open(gitignore_path, 'w') as f:
                    f.write('\n'.join(Config.IGNORE_PATTERNS))
            
            # ایجاد commit اولیه
            self.repo.index.add('*')
            try:
                self.repo.index.commit("Initial commit")
                print("✅ Commit اولیه ایجاد شد")
            except:
                pass
            
            # تشخیص base branch
            self.base_branch = self._detect_base_branch()
        
        return self.repo
    
    def _detect_base_branch(self) -> str:
        """تشخیص خودکار base branch"""
        try:
            # ابتدا سعی می‌کنیم branch فعلی را بگیریم
            current = self.repo.active_branch.name
            
            # لیست branch‌های موجود
            branches = [b.name for b in self.repo.heads]
            
            # اولویت‌ها
            preferred_branches = ['main', 'master', 'develop', 'dev']
            
            # اگر یکی از branch‌های ترجیحی وجود دارد
            for branch in preferred_branches:
                if branch in branches:
                    return branch
            
            # اگر هیچکدام نبود، از branch فعلی استفاده کن
            if current:
                return current
            
            # اگر branch‌ها وجود دارند، اولی را برگردان
            if branches:
                return branches[0]
            
            # در غیر این صورت، پیش‌فرض
            return Config.DEFAULT_BASE_BRANCH
            
        except:
            # اگر خطایی رخ داد، از تنظیمات استفاده کن
            return Config.DEFAULT_BASE_BRANCH
    
    def get_current_branch(self) -> str:
        """دریافت نام branch فعلی"""
        try:
            return self.repo.active_branch.name
        except:
            return "HEAD (detached)"
    
    def get_base_branch(self) -> str:
        """دریافت base branch"""
        if self.base_branch:
            return self.base_branch
        return self._detect_base_branch()
    
    def set_base_branch(self, branch_name: str):
        """تنظیم دستی base branch"""
        # بررسی وجود branch
        branches = [b.name for b in self.repo.heads]
        if branch_name in branches:
            self.base_branch = branch_name
            print(f"✅ Base branch تنظیم شد: {branch_name}")
            return True
        else:
            print(f"❌ Branch '{branch_name}' یافت نشد")
            return False
    
    def list_branches(self):
        """لیست تمام branch‌ها"""
        try:
            return [b.name for b in self.repo.heads]
        except:
            return []
    
    def create_feature_branch(self, request_summary: str = "ai-changes") -> str:
        """ایجاد branch جدید برای ویژگی"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_summary = "".join(c if c.isalnum() else "_" for c in request_summary[:30])
        branch_name = f"{Config.FEATURE_BRANCH_PREFIX}/{safe_summary}_{timestamp}"
        
        try:
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            print(f"🌿 Branch جدید ایجاد شد: {branch_name}")
            return branch_name
        except GitCommandError as e:
            print(f"❌ خطا در ایجاد branch: {e}")
            raise
    
    def stage_all_changes(self):
        """Stage کردن تمام تغییرات"""
        self.repo.git.add(A=True)
    
    def commit_changes(self, message: str) -> bool:
        """ایجاد commit"""
        try:
            if self.repo.index.diff("HEAD") or self.repo.untracked_files:
                self.repo.index.commit(message)
                print(f"✅ Commit ایجاد شد: {message}")
                return True
            else:
                print("ℹ️  تغییری برای commit وجود ندارد")
                return False
        except GitCommandError as e:
            print(f"❌ خطا در commit: {e}")
            raise
    
    def get_diff(self, base_branch: str = None) -> str:
        """دریافت diff بین branch‌ها"""
        if base_branch is None:
            base_branch = self.get_base_branch()
        
        try:
            # بررسی وجود base branch
            branches = [b.name for b in self.repo.heads]
            
            if base_branch not in branches:
                # اگر base branch وجود نداشت، diff با HEAD
                diff = self.repo.git.diff('HEAD')
                return diff
            
            diff = self.repo.git.diff(base_branch, self.get_current_branch())
            return diff
        except GitCommandError:
            # اگر خطایی رخ داد، diff ساده
            try:
                diff = self.repo.git.diff('HEAD')
                return diff
            except:
                return ""
    
    def get_status(self) -> str:
        """دریافت وضعیت فعلی repository"""
        try:
            status = self.repo.git.status()
            
            # اضافه کردن اطلاعات branch‌ها
            branches_info = f"\nBranches موجود:\n"
            for branch in self.repo.heads:
                marker = "→" if branch.name == self.get_current_branch() else " "
                branches_info += f"  {marker} {branch.name}\n"
            
            return status + "\n" + branches_info
        except:
            return "خطا در دریافت وضعیت"
    
    def merge_to_base(self, base_branch: str = None) -> bool:
        """ادغام branch فعلی به base branch"""
        if base_branch is None:
            base_branch = self.get_base_branch()
        
        current_branch = self.get_current_branch()
        
        # بررسی وجود base branch
        branches = [b.name for b in self.repo.heads]
        
        if base_branch not in branches:
            print(f"❌ Base branch '{base_branch}' یافت نشد")
            print(f"📋 Branch‌های موجود: {', '.join(branches)}")
            
            # اگر فقط یک branch وجود دارد، نیازی به merge نیست
            if len(branches) == 1:
                print(f"ℹ️  فقط یک branch وجود دارد. تغییرات در همین branch ذخیره می‌شوند.")
                return True
            
            # سوال از کاربر برای انتخاب base branch
            if branches:
                base_branch = branches[0]
                print(f"⚠️  از '{base_branch}' به عنوان base branch استفاده می‌شود")
            else:
                return False
        
        try:
            # تغییر به base branch
            self.repo.heads[base_branch].checkout()
            
            # ادغام
            self.repo.git.merge(current_branch)
            print(f"✅ Branch {current_branch} به {base_branch} ادغام شد")
            
            return True
        except GitCommandError as e:
            print(f"❌ خطا در merge: {e}")
            
            # برگشت به branch قبلی
            try:
                self.repo.heads[current_branch].checkout()
            except:
                pass
            
            return False
    
    def delete_branch(self, branch_name: str):
        """حذف یک branch"""
        try:
            self.repo.delete_head(branch_name, force=True)
            print(f"🗑️  Branch حذف شد: {branch_name}")
        except GitCommandError as e:
            print(f"❌ خطا در حذف branch: {e}")
    
    def checkout_branch(self, branch_name: str):
        """تغییر به یک branch"""
        try:
            # بررسی وجود branch
            branches = [b.name for b in self.repo.heads]
            
            if branch_name not in branches:
                print(f"❌ Branch '{branch_name}' یافت نشد")
                print(f"📋 Branch‌های موجود: {', '.join(branches)}")
                
                # اگر branch‌ها وجود دارند، به اولی برو
                if branches:
                    branch_name = branches[0]
                    print(f"⚠️  به جای آن به '{branch_name}' تغییر می‌کنیم")
                else:
                    return False
            
            self.repo.heads[branch_name].checkout()
            print(f"✅ تغییر به branch: {branch_name}")
            return True
            
        except GitCommandError as e:
            print(f"❌ خطا در checkout: {e}")
            raise