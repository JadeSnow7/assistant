"""
文件和目录对象实现
"""

from typing import Any, List, Union
from pathlib import Path
from datetime import datetime
from . import ShellObject, ShellObjectError, ListObject


class FileObject(ShellObject):
    """文件对象"""
    
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path).resolve()
        self._cached_stat = None
        self._cache_time = None
    
    def _get_stat(self, force_refresh: bool = False):
        """获取文件状态（带缓存）"""
        now = datetime.now()
        
        if (force_refresh or 
            self._cached_stat is None or 
            self._cache_time is None or
            (now - self._cache_time).total_seconds() > 1.0):
            
            try:
                self._cached_stat = self.path.stat()
                self._cache_time = now
            except (OSError, IOError):
                self._cached_stat = None
        
        return self._cached_stat
    
    def get_property(self, name: str) -> Any:
        """获取文件属性"""
        if name == "name":
            return self.path.name
        elif name == "path":
            return str(self.path)
        elif name == "parent":
            return DirectoryObject(self.path.parent)
        elif name == "stem":
            return self.path.stem
        elif name == "suffix":
            return self.path.suffix
        elif name == "ext":
            return self.path.suffix.lstrip('.')
        elif name == "exists":
            return self.path.exists()
        elif name == "is_file":
            return self.path.is_file()
        elif name == "is_dir":
            return self.path.is_dir()
        elif name == "size":
            stat = self._get_stat()
            return stat.st_size if stat else 0
        elif name == "modified":
            stat = self._get_stat()
            return datetime.fromtimestamp(stat.st_mtime) if stat else None
        elif name == "created":
            stat = self._get_stat()
            return datetime.fromtimestamp(stat.st_ctime) if stat else None
        else:
            raise AttributeError(f"FileObject没有属性 '{name}'")
    
    def call_method(self, name: str, args: List[Any]) -> Any:
        """调用文件方法"""
        if name == "read":
            encoding = args[0] if args else 'utf-8'
            try:
                return self.path.read_text(encoding=encoding)
            except Exception as e:
                raise ShellObjectError(f"读取文件失败: {e}")
        
        elif name == "write":
            if not args:
                raise ShellObjectError("write方法需要至少一个参数")
            content = args[0]
            encoding = args[1] if len(args) > 1 else 'utf-8'
            try:
                self.path.write_text(content, encoding=encoding)
                return True
            except Exception as e:
                raise ShellObjectError(f"写入文件失败: {e}")
        
        elif name == "lines":
            encoding = args[0] if args else 'utf-8'
            try:
                content = self.path.read_text(encoding=encoding)
                return ListObject(content.splitlines())
            except Exception as e:
                raise ShellObjectError(f"读取文件行失败: {e}")
        
        elif name == "copy":
            if not args:
                raise ShellObjectError("copy方法需要一个目标路径参数")
            target = Path(args[0])
            try:
                import shutil
                shutil.copy2(self.path, target)
                return FileObject(target)
            except Exception as e:
                raise ShellObjectError(f"复制文件失败: {e}")
        
        elif name == "delete":
            try:
                self.path.unlink()
                return True
            except Exception as e:
                raise ShellObjectError(f"删除文件失败: {e}")
        
        elif name == "rename":
            if not args:
                raise ShellObjectError("rename方法需要一个新名称参数")
            new_name = args[0]
            new_path = self.path.parent / new_name
            try:
                self.path.rename(new_path)
                self.path = new_path
                return self
            except Exception as e:
                raise ShellObjectError(f"重命名文件失败: {e}")
        
        else:
            raise AttributeError(f"FileObject没有方法 '{name}'")
    
    def to_string(self) -> str:
        return str(self.path)


class DirectoryObject(ShellObject):
    """目录对象"""
    
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path).resolve()
    
    def get_property(self, name: str) -> Any:
        """获取目录属性"""
        if name == "name":
            return self.path.name
        elif name == "path":
            return str(self.path)
        elif name == "parent":
            return DirectoryObject(self.path.parent)
        elif name == "exists":
            return self.path.exists()
        elif name == "is_dir":
            return self.path.is_dir()
        elif name == "files":
            try:
                files = [FileObject(f) for f in self.path.iterdir() if f.is_file()]
                return ListObject(files)
            except Exception as e:
                raise ShellObjectError(f"获取文件列表失败: {e}")
        elif name == "subdirs":
            try:
                subdirs = [DirectoryObject(d) for d in self.path.iterdir() if d.is_dir()]
                return ListObject(subdirs)
            except Exception as e:
                raise ShellObjectError(f"获取子目录列表失败: {e}")
        else:
            raise AttributeError(f"DirectoryObject没有属性 '{name}'")
    
    def call_method(self, name: str, args: List[Any]) -> Any:
        """调用目录方法"""
        if name == "create":
            parents = args[0] if args else True
            try:
                self.path.mkdir(parents=parents, exist_ok=True)
                return True
            except Exception as e:
                raise ShellObjectError(f"创建目录失败: {e}")
        
        elif name == "delete":
            recursive = args[0] if args else False
            try:
                if recursive:
                    import shutil
                    shutil.rmtree(self.path)
                else:
                    self.path.rmdir()
                return True
            except Exception as e:
                raise ShellObjectError(f"删除目录失败: {e}")
        
        elif name == "find":
            if not args:
                raise ShellObjectError("find方法需要一个模式参数")
            pattern = args[0]
            recursive = args[1] if len(args) > 1 else True
            
            try:
                matches = []
                if recursive:
                    matches = list(self.path.rglob(pattern))
                else:
                    matches = list(self.path.glob(pattern))
                
                result = []
                for match in matches:
                    if match.is_file():
                        result.append(FileObject(match))
                    elif match.is_dir():
                        result.append(DirectoryObject(match))
                
                return ListObject(result)
            except Exception as e:
                raise ShellObjectError(f"查找文件失败: {e}")
        
        else:
            raise AttributeError(f"DirectoryObject没有方法 '{name}'")
    
    def to_string(self) -> str:
        return str(self.path)