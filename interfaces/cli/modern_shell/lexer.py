"""
现代Shell语法解析器 - 基础词法分析和AST定义
"""

import re
from typing import Any, List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Token类型枚举"""
    # 字面量
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER" 
    BOOLEAN = "BOOLEAN"
    
    # 操作符
    ASSIGN = "="
    ARROW = "=>"
    PIPE = "|"
    DOT = "."
    COMMA = ","
    
    # 比较操作符
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="
    
    # 逻辑操作符
    AND = "&&"
    OR = "||"
    NOT = "!"
    
    # 算术操作符
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"
    
    # 括号
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    
    # 关键字
    LET = "let"
    FN = "fn"
    RETURN = "return"
    IF = "if"
    ELSE = "else"
    FOR = "for"
    WHILE = "while"
    TRY = "try"
    CATCH = "catch"
    CLASS = "class"
    EXTENDS = "extends"
    
    # 特殊
    NEWLINE = "NEWLINE"
    EOF = "EOF"


@dataclass
class Token:
    """Token数据结构"""
    type: TokenType
    value: str
    line: int
    column: int


@dataclass 
class ASTNode:
    """抽象语法树节点"""
    type: str
    value: Any = None
    children: List['ASTNode'] = None
    line: int = 0
    column: int = 0
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class ParseError(Exception):
    """解析错误"""
    
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(message)
        self.line = line
        self.column = column


class Lexer:
    """词法分析器"""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        
        # 关键字映射
        self.keywords = {
            'let': TokenType.LET,
            'fn': TokenType.FN,
            'return': TokenType.RETURN,
            'if': TokenType.IF,
            'else': TokenType.ELSE,
            'for': TokenType.FOR,
            'while': TokenType.WHILE,
            'try': TokenType.TRY,
            'catch': TokenType.CATCH,
            'class': TokenType.CLASS,
            'extends': TokenType.EXTENDS,
            'true': TokenType.BOOLEAN,
            'false': TokenType.BOOLEAN,
        }
        
        # 操作符映射
        self.operators = {
            '=': TokenType.ASSIGN,
            '=>': TokenType.ARROW,
            '|': TokenType.PIPE,
            '.': TokenType.DOT,
            ',': TokenType.COMMA,
            '==': TokenType.EQ,
            '!=': TokenType.NE,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '<=': TokenType.LE,
            '>=': TokenType.GE,
            '&&': TokenType.AND,
            '||': TokenType.OR,
            '!': TokenType.NOT,
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.MULTIPLY,
            '/': TokenType.DIVIDE,
            '%': TokenType.MODULO,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
        }
    
    def current_char(self) -> Optional[str]:
        """获取当前字符"""
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        """预览后续字符"""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]
    
    def advance(self):
        """前进一个字符"""
        if self.pos < len(self.text):
            if self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def skip_whitespace(self):
        """跳过空白字符（除了换行符）"""
        while self.current_char() and self.current_char() in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        """跳过注释"""
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()
    
    def read_string(self) -> str:
        """读取字符串字面量"""
        quote_char = self.current_char()  # ' 或 "
        self.advance()  # 跳过开始引号
        
        value = ""
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\':
                self.advance()
                # 处理转义字符
                escape_char = self.current_char()
                if escape_char == 'n':
                    value += '\n'
                elif escape_char == 't':
                    value += '\t'
                elif escape_char == 'r':
                    value += '\r'
                elif escape_char == '\\':
                    value += '\\'
                elif escape_char == quote_char:
                    value += quote_char
                else:
                    value += escape_char
            else:
                value += self.current_char()
            self.advance()
        
        if self.current_char() == quote_char:
            self.advance()  # 跳过结束引号
        else:
            raise ParseError(f"未闭合的字符串在行 {self.line}")
        
        return value
    
    def read_number(self) -> Union[int, float]:
        """读取数字字面量"""
        value = ""
        has_dot = False
        
        while (self.current_char() and 
               (self.current_char().isdigit() or self.current_char() == '.')):
            if self.current_char() == '.':
                if has_dot:
                    break
                has_dot = True
            value += self.current_char()
            self.advance()
        
        return float(value) if has_dot else int(value)
    
    def read_identifier(self) -> str:
        """读取标识符"""
        value = ""
        while (self.current_char() and 
               (self.current_char().isalnum() or self.current_char() in '_')):
            value += self.current_char()
            self.advance()
        return value
    
    def read_operator(self) -> str:
        """读取操作符"""
        # 检查双字符操作符
        if self.pos + 1 < len(self.text):
            two_char = self.text[self.pos:self.pos + 2]
            if two_char in self.operators:
                self.advance()
                self.advance()
                return two_char
        
        # 单字符操作符
        char = self.current_char()
        if char in self.operators:
            self.advance()
            return char
        
        raise ParseError(f"未知的操作符 '{char}' 在行 {self.line}")
    
    def tokenize(self) -> List[Token]:
        """将输入文本标记化"""
        tokens = []
        
        while self.current_char():
            # 跳过空白字符
            if self.current_char() in ' \t\r':
                self.skip_whitespace()
                continue
            
            # 处理换行符
            if self.current_char() == '\n':
                tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.column))
                self.advance()
                continue
            
            # 跳过注释
            if self.current_char() == '#':
                self.skip_comment()
                continue
            
            # 字符串字面量
            if self.current_char() in '"\'':
                value = self.read_string()
                tokens.append(Token(TokenType.STRING, value, self.line, self.column))
                continue
            
            # 数字字面量
            if self.current_char().isdigit():
                value = self.read_number()
                tokens.append(Token(TokenType.NUMBER, value, self.line, self.column))
                continue
            
            # 标识符和关键字
            if self.current_char().isalpha() or self.current_char() == '_':
                value = self.read_identifier()
                token_type = self.keywords.get(value, TokenType.IDENTIFIER)
                tokens.append(Token(token_type, value, self.line, self.column))
                continue
            
            # 操作符
            if self.current_char() in '=!<>&|+-*/%(){}[].,':
                try:
                    op = self.read_operator()
                    token_type = self.operators[op]
                    tokens.append(Token(token_type, op, self.line, self.column))
                    continue
                except ParseError:
                    pass
            
            # 未知字符
            raise ParseError(f"未知字符 '{self.current_char()}' 在行 {self.line}")
        
        tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return tokens