
## 2. فایل `project_manager.py` - مدیریت پروژه

```python
import os
import json
from pathlib import Path
from typing import Dict, List, Any
import fnmatch
from config import Config

class ProjectManager:
    """مدیریت بارگذاری و سریال‌سازی پروژه"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.project_data = {}
        
    def should_ignore(self, path: Path) -> bool:
        """بررسی اینکه آیا فایل یا پوشه باید نادیده گرفته شود"""
        path_str = str(path)
        for pattern in Config.IGNORE_PATTERNS:
            if fnmatch.fnmatch(path_str, f'*{pattern}*'):
                return True
        return False
    
    def load_project(self) -> Dict[str, Any]:
        """بارگذاری کل پروژه و تبدیل به ساختار JSON"""
        if not self.project_path.exists():
            raise FileNotFoundError(f"مسیر پروژه یافت نشد: {self.project_path}")
        
        files = []
        
        # پیمایش تمام فایل‌های پروژه
        for root, dirs, filenames in os.walk(self.project_path):
            root_path = Path(root)
            
            # فیلتر کردن پوشه‌های نادیده گرفته شده
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            
            for filename in filenames:
                file_path = root_path / filename
                
                if self.should_ignore(file_path):
                    continue
                
                try:
                    # خواندن محتوای فایل
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # مسیر نسبی از ریشه پروژه
                    relative_path = file_path.relative_to(self.project_path)
                    
                    files.append({
                        "path": str(relative_path).replace('\\', '/'),
                        "content": content,
                        "status": "unchanged"
                    })
                    
                except (UnicodeDecodeError, PermissionError) as e:
                    print(f"خطا در خواندن {file_path}: {e}")
                    continue
        
        # ساخت داده پروژه
        self.project_data = {
            "project_name": self.project_path.name,
            "version": "1.0",
            "files": files,
            "metadata": {
                "base_path": str(self.project_path),
                "total_files": len(files)
            }
        }
        
        return self.project_data
    
    def serialize_to_parts(self, data: Dict[str, Any]) -> List[str]:
        """تبدیل JSON به بخش‌های کوچکتر"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        total_chars = len(json_str)
        
        if total_chars <= Config.MAX_CHARS_PER_PART:
            return [f"---START PART 1/1---\n{json_str}\n---END PART 1/1---"]
        
        # تقسیم به بخش‌ها
        parts = []
        current_part = ""
        part_num = 1
        
        # تقسیم بر اساس فایل‌ها
        files = data.get("files", [])
        header = {
            "project_name": data.get("project_name"),
            "version": data.get("version"),
            "metadata": data.get("metadata")
        }
        
        temp_data = header.copy()
        temp_data["files"] = []
        
        for file_obj in files:
            temp_data["files"].append(file_obj)
            temp_json = json.dumps(temp_data, ensure_ascii=False, indent=2)
            
            if len(temp_json) > Config.MAX_CHARS_PER_PART and len(temp_data["files"]) > 1:
                # ذخیره بخش قبلی
                temp_data["files"].pop()
                part_json = json.dumps(temp_data, ensure_ascii=False, indent=2)
                parts.append(part_json)
                
                # شروع بخش جدید
                temp_data = header.copy()
                temp_data["files"] = [file_obj]
        
        # اضافه کردن آخرین بخش
        if temp_data["files"]:
            parts.append(json.dumps(temp_data, ensure_ascii=False, indent=2))
        
        # اضافه کردن تگ‌ها
        total_parts = len(parts)
        tagged_parts = []
        for i, part in enumerate(parts, 1):
            tagged_part = f"---START PART {i}/{total_parts}---\n{part}\n---END PART {i}/{total_parts}---"
            tagged_parts.append(tagged_part)
        
        return tagged_parts
    
    def parse_from_parts(self, parts: List[str]) -> Dict[str, Any]:
        """بازسازی JSON از بخش‌های چندگانه"""
        all_files = []
        project_info = None
        
        for part in parts:
            # حذف تگ‌ها
            content = part
            if '---START PART' in content:
                start_idx = content.find('---\n') + 4
                end_idx = content.rfind('\n---END PART')
                content = content[start_idx:end_idx]
            
            try:
                part_data = json.loads(content)
                
                if project_info is None:
                    project_info = {
                        "project_name": part_data.get("project_name"),
                        "version": part_data.get("version"),
                        "metadata": part_data.get("metadata")
                    }
                
                # ترکیب فایل‌ها
                if "files" in part_data:
                    all_files.extend(part_data["files"])
                    
            except json.JSONDecodeError as e:
                print(f"خطا در parse کردن بخش: {e}")
                continue
        
        result = project_info or {}
        result["files"] = all_files
        
        return result
    
    def apply_changes(self, updated_data: Dict[str, Any]):
        """اعمال تغییرات LLM به فایل‌های واقعی"""
        updated_files = {f["path"]: f for f in updated_data.get("files", [])}
        current_files = {f["path"]: f for f in self.project_data.get("files", [])}
        
        # فایل‌های جدید یا تغییر یافته
        for path, file_obj in updated_files.items():
            file_path = self.project_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_obj["content"])
            
            print(f"به‌روز شد: {path}")
        
        # فایل‌های حذف شده
        for path in current_files.keys():
            if path not in updated_files:
                file_path = self.project_path / path
                if file_path.exists():
                    file_path.unlink()
                    print(f"حذف شد: {path}")