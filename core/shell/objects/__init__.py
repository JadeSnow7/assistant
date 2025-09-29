"""
现代Shell对象系统 - 基础对象接口
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Any, List
from pathlib import Path
from datetime import datetime


class ShellObjectError(Exception):
    """Shell对象操作错误"""
    pass


class ShellObject(ABC):
    """Shell对象基类"""
    
    @abstractmethod
    def get_property(self, name: str) -> Any:
        """获取属性"""
        pass
    
    @abstractmethod
    def call_method(self, name: str, args: List[Any]) -> Any:
        """调用方法"""
        pass
    
    @abstractmethod
    def to_string(self) -> str:
        """转换为字符串"""
        pass
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_string()})"


class ListObject(ShellObject):
    """列表对象 - 支持函数式操作"""
    
    def __init__(self, items: List[Any]):
        self.items = list(items)
    
    def get_property(self, name: str) -> Any:
        """获取列表属性"""
        if name == "length" or name == "size":
            return len(self.items)
        elif name == "first":
            return self.items[0] if self.items else None
        elif name == "last":
            return self.items[-1] if self.items else None
        elif name == "empty":
            return len(self.items) == 0
        else:
            raise AttributeError(f"ListObject没有属性 '{name}'")
    
    def call_method(self, name: str, args: List[Any]) -> Any:
        """调用列表方法"""
        if name == "map":
            if not args:
                raise ShellObjectError("map方法需要一个函数参数")
            func = args[0]
            try:
                result = [func(item) for item in self.items]
                return ListObject(result)
            except Exception as e:
                raise ShellObjectError(f"map操作失败: {e}")
        
        elif name == "filter":
            if not args:
                raise ShellObjectError("filter方法需要一个谓词函数参数")
            predicate = args[0]
            try:
                result = [item for item in self.items if predicate(item)]
                return ListObject(result)
            except Exception as e:
                raise ShellObjectError(f"filter操作失败: {e}")
        
        elif name == "reduce":
            if not args:
                raise ShellObjectError("reduce方法需要一个函数参数")
            func = args[0]
            initial = args[1] if len(args) > 1 else None
            
            try:
                if initial is not None:
                    result = initial
                    items = self.items
                else:
                    if not self.items:
                        raise ShellObjectError("reduce操作需要非空列表或初始值")
                    result = self.items[0]
                    items = self.items[1:]
                
                for item in items:
                    result = func(result, item)
                
                return result
            except Exception as e:
                raise ShellObjectError(f"reduce操作失败: {e}")
        
        elif name == "count":
            predicate = args[0] if args else None
            try:
                if predicate:
                    return len([item for item in self.items if predicate(item)])
                else:
                    return len(self.items)
            except Exception as e:
                raise ShellObjectError(f"count操作失败: {e}")
        
        elif name == "sort":
            key_func = args[0] if args else None
            reverse = args[1] if len(args) > 1 else False
            try:
                if key_func:
                    result = sorted(self.items, key=key_func, reverse=reverse)
                else:
                    result = sorted(self.items, reverse=reverse)
                return ListObject(result)
            except Exception as e:
                raise ShellObjectError(f"sort操作失败: {e}")
        
        elif name == "join":
            separator = args[0] if args else ""
            try:
                str_items = [str(item) for item in self.items]
                return separator.join(str_items)
            except Exception as e:
                raise ShellObjectError(f"join操作失败: {e}")
        
        elif name == "sum":
            try:
                return sum(self.items)
            except Exception as e:
                raise ShellObjectError(f"sum操作失败: {e}")
        
        else:
            raise AttributeError(f"ListObject没有方法 '{name}'")
    
    def to_string(self) -> str:
        return f"[{', '.join(str(item) for item in self.items)}]"
    
    def __iter__(self):
        return iter(self.items)
    
    def __len__(self):
        return len(self.items)
    
    def __getitem__(self, index):
        return self.items[index]