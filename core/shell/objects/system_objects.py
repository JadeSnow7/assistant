"""
系统和进程对象实现
"""

import os
import psutil
import subprocess
from typing import Any, List, Union
from datetime import datetime
from . import ShellObject, ShellObjectError, ListObject


class ProcessObject(ShellObject):
    """进程对象"""
    
    def __init__(self, pid_or_command: Union[int, str]):
        if isinstance(pid_or_command, int):
            # 通过PID创建
            try:
                self.process = psutil.Process(pid_or_command)
                self.command = None
            except psutil.NoSuchProcess:
                raise ShellObjectError(f"进程 {pid_or_command} 不存在")
        else:
            # 通过命令创建（但不启动）
            self.process = None
            self.command = pid_or_command
    
    def get_property(self, name: str) -> Any:
        """获取进程属性"""
        if self.process is None:
            if name == "command":
                return self.command
            else:
                raise ShellObjectError("进程未启动，无法获取运行时属性")
        
        try:
            if name == "pid":
                return self.process.pid
            elif name == "name":
                return self.process.name()
            elif name == "status":
                return self.process.status()
            elif name == "cpu":
                return self.process.cpu_percent()
            elif name == "memory":
                return self.process.memory_percent()
            elif name == "is_running":
                return self.process.is_running()
            else:
                raise AttributeError(f"ProcessObject没有属性 '{name}'")
        except psutil.NoSuchProcess:
            raise ShellObjectError("进程已终止")
        except psutil.AccessDenied:
            raise ShellObjectError("访问进程信息被拒绝")
    
    def call_method(self, name: str, args: List[Any]) -> Any:
        """调用进程方法"""
        if name == "start":
            if self.process is not None:
                raise ShellObjectError("进程已启动")
            
            if self.command is None:
                raise ShellObjectError("没有指定启动命令")
            
            try:
                # 启动新进程
                if isinstance(self.command, str):
                    cmd_parts = self.command.split()
                else:
                    cmd_parts = self.command
                
                proc = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                self.process = psutil.Process(proc.pid)
                self._subprocess = proc
                return True
            except Exception as e:
                raise ShellObjectError(f"启动进程失败: {e}")
        
        elif name == "kill":
            if self.process is None:
                raise ShellObjectError("进程未启动")
            
            try:
                self.process.kill()
                return True
            except psutil.NoSuchProcess:
                return True  # 进程已经终止
            except Exception as e:
                raise ShellObjectError(f"终止进程失败: {e}")
        
        elif name == "output":
            if not hasattr(self, '_subprocess'):
                raise ShellObjectError("进程输出不可用")
            
            try:
                stdout, stderr = self._subprocess.communicate()
                return {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": self._subprocess.returncode
                }
            except Exception as e:
                raise ShellObjectError(f"获取进程输出失败: {e}")
        
        else:
            raise AttributeError(f"ProcessObject没有方法 '{name}'")
    
    def to_string(self) -> str:
        if self.process:
            try:
                return f"Process(pid={self.process.pid}, name='{self.process.name()}')"
            except:
                return f"Process(pid={self.process.pid})"
        else:
            return f"Process(command='{self.command}')"


class SystemObject(ShellObject):
    """系统对象 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_property(self, name: str) -> Any:
        """获取系统属性"""
        if name == "cpu":
            return {
                "usage": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count()
            }
        elif name == "memory":
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "usage": memory.percent
            }
        elif name == "disk":
            # 返回根目录磁盘使用情况
            try:
                usage = psutil.disk_usage('/')
                return {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "usage": (usage.used / usage.total) * 100
                }
            except:
                return {"error": "无法获取磁盘信息"}
        elif name == "platform":
            import platform
            return {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            }
        else:
            raise AttributeError(f"SystemObject没有属性 '{name}'")
    
    def call_method(self, name: str, args: List[Any]) -> Any:
        """调用系统方法"""
        if name == "processes":
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name']):
                    processes.append(ProcessObject(proc.info['pid']))
                return ListObject(processes)
            except Exception as e:
                raise ShellObjectError(f"获取进程列表失败: {e}")
        
        elif name == "disk_usage":
            path = args[0] if args else "/"
            try:
                usage = psutil.disk_usage(path)
                return {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "usage": (usage.used / usage.total) * 100
                }
            except Exception as e:
                raise ShellObjectError(f"获取磁盘使用情况失败: {e}")
        
        else:
            raise AttributeError(f"SystemObject没有方法 '{name}'")
    
    def to_string(self) -> str:
        return "System"


# 全局系统对象实例
System = SystemObject()


# 便利函数
def File(path: str):
    """创建文件对象"""
    from .file_objects import FileObject
    return FileObject(path)


def Dir(path: str):
    """创建目录对象"""
    from .file_objects import DirectoryObject
    return DirectoryObject(path)


def Files(pattern: str, base_dir: str = "."):
    """创建匹配模式的文件对象列表"""
    from .file_objects import DirectoryObject
    dir_obj = DirectoryObject(base_dir)
    return dir_obj.call_method("find", [pattern])


def Process(pid_or_command: Union[int, str]):
    """创建进程对象"""
    return ProcessObject(pid_or_command)


def Processes():
    """获取所有进程列表"""
    return System.call_method("processes", [])