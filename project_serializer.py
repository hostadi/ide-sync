import os
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
import fnmatch
from config import Config

class ProjectSerializer:
    """تبدیل پروژه به فرمت قابل ارسال به LLM و برعکس"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.last_snapshot = {}  # برای ردیابی تغییرات
        
    def should_ignore(self, path: Path) -> bool:
        """بررسی اینکه آیا فایل یا پوشه باید نادیده گرفته شود"""
        path_str = str(path)
        
        for pattern in Config.IGNORE_PATTERNS:
            if fnmatch.fnmatch(path_str, f'*{pattern}*'):
                return True
        
        if path.is_file():
            try:
                if path.stat().st_size > Config.MAX_FILE_SIZE:
                    print(f"⚠️  فایل {path.name} بیش از حد بزرگ است")
                    return True
            except:
                pass
                
        return False
    
    def is_binary_file(self, file_path: Path) -> bool:
        """بررسی اینکه فایل binary است یا text"""
        try:
            with open(file_path, 'tr', encoding='utf-8') as f:
                f.read(1024)
            return False
        except:
            return True
    
    def load_project_files(self) -> List[Dict[str, Any]]:
        """بارگذاری فایل‌های پروژه"""
        if not self.project_path.exists():
            raise FileNotFoundError(f"مسیر پروژه یافت نشد: {self.project_path}")
        
        files = []
        ignored_count = 0
        binary_count = 0
        
        for root, dirs, filenames in os.walk(self.project_path):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            
            for filename in filenames:
                file_path = root_path / filename
                
                if self.should_ignore(file_path):
                    ignored_count += 1
                    continue
                
                if self.is_binary_file(file_path):
                    binary_count += 1
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    relative_path = file_path.relative_to(self.project_path)
                    
                    files.append({
                        "path": str(relative_path).replace('\\', '/'),
                        "content": content
                    })
                    
                except Exception as e:
                    print(f"⚠️  خطا در خواندن {file_path.name}: {e}")
                    continue
        
        print(f"\n📊 آمار:")
        print(f"   ✅ فایل‌ها: {len(files)}")
        print(f"   ⏭️  نادیده گرفته: {ignored_count}")
        print(f"   🔒 Binary: {binary_count}")
        
        # ذخیره snapshot
        self.last_snapshot = {f["path"]: f["content"] for f in files}
        
        return files
    
    def serialize_project(self, selected_files: List[str] = None) -> str:
        """تبدیل پروژه به JSON"""
        files = self.load_project_files()
        
        # فیلتر کردن فایل‌های انتخابی
        if selected_files:
            files = [f for f in files if f["path"] in selected_files]
        
        project_data = {
            "project_name": self.project_path.name,
            "base_path": str(self.project_path),
            "total_files": len(files),
            "files": files
        }
        
        json_output = json.dumps(project_data, ensure_ascii=False, indent=2)
        return json_output
    
    def serialize_changes_only(self, current_files: List[Dict[str, Any]]) -> str:
        """خروجی فقط تغییرات (بهینه‌تر)"""
        changes = []
        current_paths = {f["path"]: f["content"] for f in current_files}
        
        # فایل‌های تغییر یافته یا جدید
        for path, content in current_paths.items():
            if path not in self.last_snapshot:
                # فایل جدید
                changes.append({
                    "path": path,
                    "content": content,
                    "action": "added"
                })
            elif self.last_snapshot[path] != content:
                # فایل تغییر یافته
                changes.append({
                    "path": path,
                    "content": content,
                    "action": "modified"
                })
        
        # فایل‌های حذف شده
        for path in self.last_snapshot.keys():
            if path not in current_paths:
                changes.append({
                    "path": path,
                    "action": "deleted"
                })
        
        if not changes:
            # هیچ تغییری وجود ندارد
            return json.dumps({
                "project_name": self.project_path.name,
                "changes_only": True,
                "message": "هیچ تغییری شناسایی نشد",
                "files": []
            }, ensure_ascii=False, indent=2)
        
        project_data = {
            "project_name": self.project_path.name,
            "changes_only": True,
            "total_changes": len(changes),
            "files": changes
        }
        
        return json.dumps(project_data, ensure_ascii=False, indent=2)
    
    def split_into_parts(self, json_str: str, max_chars: int) -> List[str]:
        """تقسیم JSON به بخش‌های کوچکتر"""
        if len(json_str) <= max_chars:
            return [json_str]
        
        try:
            data = json.loads(json_str)
        except:
            # اگر parse نشد، تقسیم ساده
            return self._simple_split(json_str, max_chars)
        
        # تقسیم هوشمند بر اساس فایل‌ها
        files = data.get("files", [])
        if not files:
            return [json_str]
        
        parts = []
        header = {
            "project_name": data.get("project_name"),
            "base_path": data.get("base_path"),
            "changes_only": data.get("changes_only", False),
            "total_files": data.get("total_files", len(files))
        }
        
        current_part_files = []
        current_size = len(json.dumps(header, ensure_ascii=False))
        
        for file_obj in files:
            file_json = json.dumps(file_obj, ensure_ascii=False)
            file_size = len(file_json)
            
            # اگر یک فایل خیلی بزرگ است
            if file_size > max_chars:
                # اگر فایل‌های قبلی وجود دارد، آن‌ها را ذخیره کن
                if current_part_files:
                    part_data = header.copy()
                    part_data["files"] = current_part_files
                    parts.append(json.dumps(part_data, ensure_ascii=False, indent=2))
                    current_part_files = []
                    current_size = len(json.dumps(header, ensure_ascii=False))
                
                # فایل بزرگ را به تنهایی به عنوان یک بخش اضافه کن
                part_data = header.copy()
                part_data["files"] = [file_obj]
                part_data["warning"] = f"فایل {file_obj['path']} بسیار بزرگ است"
                parts.append(json.dumps(part_data, ensure_ascii=False, indent=2))
                continue
            
            # بررسی اگر اضافه کردن این فایل از حد بگذرد
            if current_size + file_size + 100 > max_chars:  # 100 برای کاماها و آرایه
                # ذخیره بخش فعلی
                part_data = header.copy()
                part_data["files"] = current_part_files
                parts.append(json.dumps(part_data, ensure_ascii=False, indent=2))
                
                # شروع بخش جدید
                current_part_files = [file_obj]
                current_size = len(json.dumps(header, ensure_ascii=False)) + file_size
            else:
                current_part_files.append(file_obj)
                current_size += file_size
        
        # اضافه کردن آخرین بخش
        if current_part_files:
            part_data = header.copy()
            part_data["files"] = current_part_files
            parts.append(json.dumps(part_data, ensure_ascii=False, indent=2))
        
        # اضافه کردن تگ‌های PART
        total_parts = len(parts)
        tagged_parts = []
        for i, part in enumerate(parts, 1):
            tagged = f"---START PART {i}/{total_parts}---\n{part}\n---END PART {i}/{total_parts}---"
            tagged_parts.append(tagged)
        
        return tagged_parts
    
    def _simple_split(self, text: str, max_chars: int) -> List[str]:
        """تقسیم ساده متن"""
        parts = []
        for i in range(0, len(text), max_chars):
            parts.append(text[i:i+max_chars])
        
        total = len(parts)
        return [f"---START PART {i+1}/{total}---\n{p}\n---END PART {i+1}/{total}---" 
                for i, p in enumerate(parts)]
    
    def deserialize_project(self, json_str: str) -> Dict[str, Any]:
        """تبدیل JSON به ساختار پروژه"""
        try:
            # پاکسازی ورودی
            json_str = json_str.strip()
            
            # حذف markdown code blocks
            if json_str.startswith('```'):
                lines = json_str.split('\n')
                json_str = '\n'.join(lines[1:-1]) if len(lines) > 2 else json_str
            
            # حذف تگ‌های PART اگر وجود دارد
            if '---START PART' in json_str:
                json_str = self._extract_from_parts(json_str)
            
            project_data = json.loads(json_str)
            
            if "files" not in project_data:
                raise ValueError("فرمت JSON نادرست است. کلید 'files' یافت نشد.")
            
            return project_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"خطا در parse کردن JSON: {e}")
    
    def _extract_from_parts(self, text: str) -> str:
        """استخراج JSON از بخش‌های چندگانه"""
        import re
        
        # پیدا کردن تمام بخش‌ها
        pattern = r'---START PART \d+/\d+---\n(.*?)\n---END PART \d+/\d+---'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if not matches:
            return text
        
        # ترکیب بخش‌ها
        combined_files = []
        base_info = None
        
        for match in matches:
            try:
                part_data = json.loads(match)
                
                if base_info is None:
                    base_info = {
                        "project_name": part_data.get("project_name"),
                        "base_path": part_data.get("base_path"),
                        "changes_only": part_data.get("changes_only", False)
                    }
                
                if "files" in part_data:
                    combined_files.extend(part_data["files"])
                    
            except json.JSONDecodeError:
                continue
        
        result = base_info or {}
        result["files"] = combined_files
        result["total_files"] = len(combined_files)
        
        return json.dumps(result, ensure_ascii=False)
    
    def apply_changes(self, project_data: Dict[str, Any]) -> List[str]:
        """اعمال تغییرات به پروژه واقعی"""
        applied_changes = []
        
        # بررسی حالت changes_only
        changes_only = project_data.get("changes_only", False)
        
        if changes_only:
            # حالت فقط تغییرات
            return self._apply_changes_only(project_data)
        else:
            # حالت کل پروژه
            return self._apply_full_project(project_data)
    
    def _apply_changes_only(self, project_data: Dict[str, Any]) -> List[str]:
        """اعمال فقط تغییرات"""
        applied_changes = []
        
        for file_obj in project_data.get("files", []):
            path = file_obj["path"]
            action = file_obj.get("action", "modified")
            file_path = self.project_path / path
            
            if action == "deleted":
                # حذف فایل
                if file_path.exists():
                    file_path.unlink()
                    applied_changes.append(f"➖ حذف: {path}")
                    
            elif action == "added":
                # اضافه کردن فایل جدید
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_obj["content"])
                applied_changes.append(f"➕ جدید: {path}")
                
            elif action == "modified":
                # تغییر فایل موجود
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_obj["content"])
                applied_changes.append(f"✏️  تغییر: {path}")
        
        return applied_changes
    
    def _apply_full_project(self, project_data: Dict[str, Any]) -> List[str]:
        """اعمال کل پروژه"""
        applied_changes = []
        
        # دریافت فایل‌های موجود
        existing_files = set()
        for root, dirs, filenames in os.walk(self.project_path):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            
            for filename in filenames:
                file_path = root_path / filename
                if not self.should_ignore(file_path):
                    relative_path = file_path.relative_to(self.project_path)
                    existing_files.add(str(relative_path).replace('\\', '/'))
        
        new_files = {f["path"] for f in project_data.get("files", [])}
        
        # اعمال فایل‌های جدید/تغییر یافته
        for file_obj in project_data.get("files", []):
            file_path = self.project_path / file_obj["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_obj["content"])
            
            if file_obj["path"] in existing_files:
                applied_changes.append(f"✏️  تغییر: {file_obj['path']}")
            else:
                applied_changes.append(f"➕ جدید: {file_obj['path']}")
        
        # حذف فایل‌های حذف شده
        deleted_files = existing_files - new_files
        for file_path_str in deleted_files:
            file_path = self.project_path / file_path_str
            if file_path.exists():
                file_path.unlink()
                applied_changes.append(f"➖ حذف: {file_path_str}")
        
        return applied_changes
    
    def get_file_list(self) -> List[Tuple[str, int]]:
        """دریافت لیست فایل‌ها با اندازه"""
        files = self.load_project_files()
        return [(f["path"], len(f["content"])) for f in files]