"""
现代Shell语法分析器 - 递归下降解析器
"""

from typing import List, Optional, Dict, Any
from .lexer import Token, TokenType, ASTNode, ParseError, Lexer


class Parser:
    """语法分析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current_token(self) -> Token:
        """获取当前token"""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # EOF token
        return self.tokens[self.pos]
    
    def peek_token(self, offset: int = 1) -> Token:
        """预览后续token"""
        peek_pos = self.pos + offset
        if peek_pos >= len(self.tokens):
            return self.tokens[-1]  # EOF token
        return self.tokens[peek_pos]
    
    def advance(self):
        """前进到下一个token"""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
    
    def expect(self, token_type: TokenType) -> Token:
        """期望特定类型的token"""
        token = self.current_token()
        if token.type != token_type:
            raise ParseError(
                f"期望 {token_type.value}，但得到 {token.type.value}",
                token.line, token.column
            )
        self.advance()
        return token
    
    def match(self, *token_types: TokenType) -> bool:
        """检查当前token是否匹配任一类型"""
        return self.current_token().type in token_types
    
    def skip_newlines(self):
        """跳过换行符"""
        while self.match(TokenType.NEWLINE):
            self.advance()
    
    def parse(self) -> ASTNode:
        """解析入口点"""
        self.skip_newlines()
        return self.parse_program()
    
    def parse_program(self) -> ASTNode:
        """解析程序"""
        statements = []
        
        while not self.match(TokenType.EOF):
            self.skip_newlines()
            if self.match(TokenType.EOF):
                break
            
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            
            self.skip_newlines()
        
        return ASTNode("program", children=statements)
    
    def parse_statement(self) -> Optional[ASTNode]:
        """解析语句"""
        if self.match(TokenType.LET):
            return self.parse_let_statement()
        elif self.match(TokenType.FN):
            return self.parse_function_definition()
        elif self.match(TokenType.RETURN):
            return self.parse_return_statement()
        elif self.match(TokenType.IF):
            return self.parse_if_statement()
        else:
            return self.parse_expression_statement()
    
    def parse_let_statement(self) -> ASTNode:
        """解析let变量声明"""
        let_token = self.expect(TokenType.LET)
        
        # 变量名
        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value
        
        # 可选类型注解
        type_annotation = None
        if self.match(TokenType.IDENTIFIER) and self.current_token().value == ":":
            self.advance()  # 跳过 ':'
            type_annotation = self.parse_type()
        
        # 赋值
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        
        return ASTNode(
            "let_statement",
            value={"name": name, "type": type_annotation},
            children=[value],
            line=let_token.line,
            column=let_token.column
        )
    
    def parse_function_definition(self) -> ASTNode:
        """解析函数定义"""
        fn_token = self.expect(TokenType.FN)
        
        # 函数名
        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value
        
        # 参数列表
        self.expect(TokenType.LPAREN)
        parameters = []
        
        while not self.match(TokenType.RPAREN):
            param_name = self.expect(TokenType.IDENTIFIER).value
            
            # 参数类型注解
            param_type = None
            if self.match(TokenType.IDENTIFIER) and self.current_token().value == ":":
                self.advance()  # 跳过 ':'
                param_type = self.parse_type()
            
            parameters.append({"name": param_name, "type": param_type})
            
            if self.match(TokenType.COMMA):
                self.advance()
            elif not self.match(TokenType.RPAREN):
                raise ParseError(
                    "期望 ',' 或 ')'",
                    self.current_token().line, self.current_token().column
                )
        
        self.expect(TokenType.RPAREN)
        
        # 返回类型注解
        return_type = None
        if self.match(TokenType.MINUS) and self.peek_token().type == TokenType.GT:
            self.advance()  # '-'
            self.advance()  # '>'
            return_type = self.parse_type()
        
        # 函数体
        self.expect(TokenType.LBRACE)
        body = []
        
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.RBRACE):
                break
            
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return ASTNode(
            "function_definition",
            value={
                "name": name,
                "parameters": parameters,
                "return_type": return_type
            },
            children=body,
            line=fn_token.line,
            column=fn_token.column
        )
    
    def parse_return_statement(self) -> ASTNode:
        """解析return语句"""
        return_token = self.expect(TokenType.RETURN)
        
        # 可选的返回值
        value = None
        if not self.match(TokenType.NEWLINE, TokenType.EOF, TokenType.RBRACE):
            value = self.parse_expression()
        
        return ASTNode(
            "return_statement", 
            children=[value] if value else [],
            line=return_token.line,
            column=return_token.column
        )
    
    def parse_if_statement(self) -> ASTNode:
        """解析if语句"""
        if_token = self.expect(TokenType.IF)
        
        # 条件表达式
        self.expect(TokenType.LPAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN)
        
        # then子句
        self.expect(TokenType.LBRACE)
        then_body = []
        
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.RBRACE):
                break
            
            stmt = self.parse_statement()
            if stmt:
                then_body.append(stmt)
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        # 可选的else子句
        else_body = []
        if self.match(TokenType.ELSE):
            self.advance()
            self.expect(TokenType.LBRACE)
            
            while not self.match(TokenType.RBRACE):
                self.skip_newlines()
                if self.match(TokenType.RBRACE):
                    break
                
                stmt = self.parse_statement()
                if stmt:
                    else_body.append(stmt)
                
                self.skip_newlines()
            
            self.expect(TokenType.RBRACE)
        
        return ASTNode(
            "if_statement",
            children=[condition] + then_body + else_body,
            value={"then_count": len(then_body), "else_count": len(else_body)},
            line=if_token.line,
            column=if_token.column
        )
    
    def parse_expression_statement(self) -> ASTNode:
        """解析表达式语句"""
        expr = self.parse_expression()
        return ASTNode("expression_statement", children=[expr])
    
    def parse_expression(self) -> ASTNode:
        """解析表达式"""
        return self.parse_pipeline()
    
    def parse_pipeline(self) -> ASTNode:
        """解析管道表达式"""
        left = self.parse_logical_or()
        
        while self.match(TokenType.PIPE):
            op_token = self.current_token()
            self.advance()
            right = self.parse_logical_or()
            
            left = ASTNode(
                "pipeline",
                value="|",
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_logical_or(self) -> ASTNode:
        """解析逻辑或表达式"""
        left = self.parse_logical_and()
        
        while self.match(TokenType.OR):
            op_token = self.current_token()
            self.advance()
            right = self.parse_logical_and()
            
            left = ASTNode(
                "binary_op",
                value="||",
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_logical_and(self) -> ASTNode:
        """解析逻辑与表达式"""
        left = self.parse_equality()
        
        while self.match(TokenType.AND):
            op_token = self.current_token()
            self.advance()
            right = self.parse_equality()
            
            left = ASTNode(
                "binary_op",
                value="&&",
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_equality(self) -> ASTNode:
        """解析相等比较表达式"""
        left = self.parse_comparison()
        
        while self.match(TokenType.EQ, TokenType.NE):
            op_token = self.current_token()
            self.advance()
            right = self.parse_comparison()
            
            left = ASTNode(
                "binary_op",
                value=op_token.value,
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_comparison(self) -> ASTNode:
        """解析比较表达式"""
        left = self.parse_addition()
        
        while self.match(TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op_token = self.current_token()
            self.advance()
            right = self.parse_addition()
            
            left = ASTNode(
                "binary_op",
                value=op_token.value,
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_addition(self) -> ASTNode:
        """解析加减表达式"""
        left = self.parse_multiplication()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.current_token()
            self.advance()
            right = self.parse_multiplication()
            
            left = ASTNode(
                "binary_op",
                value=op_token.value,
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_multiplication(self) -> ASTNode:
        """解析乘除表达式"""
        left = self.parse_unary()
        
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op_token = self.current_token()
            self.advance()
            right = self.parse_unary()
            
            left = ASTNode(
                "binary_op",
                value=op_token.value,
                children=[left, right],
                line=op_token.line,
                column=op_token.column
            )
        
        return left
    
    def parse_unary(self) -> ASTNode:
        """解析一元表达式"""
        if self.match(TokenType.NOT, TokenType.MINUS):
            op_token = self.current_token()
            self.advance()
            operand = self.parse_unary()
            
            return ASTNode(
                "unary_op",
                value=op_token.value,
                children=[operand],
                line=op_token.line,
                column=op_token.column
            )
        
        return self.parse_postfix()
    
    def parse_postfix(self) -> ASTNode:
        """解析后缀表达式"""
        expr = self.parse_primary()
        
        while True:
            if self.match(TokenType.DOT):
                # 属性访问
                self.advance()
                property_name = self.expect(TokenType.IDENTIFIER).value
                expr = ASTNode(
                    "property_access",
                    value=property_name,
                    children=[expr]
                )
            elif self.match(TokenType.LPAREN):
                # 函数调用
                self.advance()
                args = []
                
                while not self.match(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    
                    if self.match(TokenType.COMMA):
                        self.advance()
                    elif not self.match(TokenType.RPAREN):
                        raise ParseError(
                            "期望 ',' 或 ')'",
                            self.current_token().line, self.current_token().column
                        )
                
                self.expect(TokenType.RPAREN)
                
                expr = ASTNode(
                    "function_call",
                    children=[expr] + args
                )
            elif self.match(TokenType.LBRACKET):
                # 索引访问
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                
                expr = ASTNode(
                    "index_access",
                    children=[expr, index]
                )
            else:
                break
        
        return expr
    
    def parse_primary(self) -> ASTNode:
        """解析基本表达式"""
        token = self.current_token()
        
        if self.match(TokenType.IDENTIFIER):
            self.advance()
            return ASTNode("identifier", value=token.value, line=token.line, column=token.column)
        
        elif self.match(TokenType.STRING):
            self.advance()
            return ASTNode("string", value=token.value, line=token.line, column=token.column)
        
        elif self.match(TokenType.NUMBER):
            self.advance()
            return ASTNode("number", value=token.value, line=token.line, column=token.column)
        
        elif self.match(TokenType.BOOLEAN):
            self.advance()
            value = token.value == "true"
            return ASTNode("boolean", value=value, line=token.line, column=token.column)
        
        elif self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        elif self.match(TokenType.LBRACKET):
            # 数组字面量
            return self.parse_array_literal()
        
        elif self.match(TokenType.LBRACE):
            # 对象字面量
            return self.parse_object_literal()
        
        else:
            raise ParseError(
                f"意外的token {token.type.value}",
                token.line, token.column
            )
    
    def parse_array_literal(self) -> ASTNode:
        """解析数组字面量"""
        self.expect(TokenType.LBRACKET)
        elements = []
        
        while not self.match(TokenType.RBRACKET):
            elements.append(self.parse_expression())
            
            if self.match(TokenType.COMMA):
                self.advance()
            elif not self.match(TokenType.RBRACKET):
                raise ParseError(
                    "期望 ',' 或 ']'",
                    self.current_token().line, self.current_token().column
                )
        
        self.expect(TokenType.RBRACKET)
        
        return ASTNode("array", children=elements)
    
    def parse_object_literal(self) -> ASTNode:
        """解析对象字面量"""
        self.expect(TokenType.LBRACE)
        properties = []
        
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.RBRACE):
                break
            
            # 属性名
            if self.match(TokenType.IDENTIFIER):
                key = self.current_token().value
                self.advance()
            elif self.match(TokenType.STRING):
                key = self.current_token().value
                self.advance()
            else:
                raise ParseError(
                    "期望属性名",
                    self.current_token().line, self.current_token().column
                )
            
            # 检查冒号
            if not (self.match(TokenType.IDENTIFIER) and self.current_token().value == ":"):
                raise ParseError(
                    "期望 ':'",
                    self.current_token().line, self.current_token().column
                )
            self.advance()
            
            # 属性值
            value = self.parse_expression()
            
            properties.append(ASTNode("property", value=key, children=[value]))
            
            if self.match(TokenType.COMMA):
                self.advance()
            elif not self.match(TokenType.RBRACE):
                raise ParseError(
                    "期望 ',' 或 '}'",
                    self.current_token().line, self.current_token().column
                )
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return ASTNode("object", children=properties)
    
    def parse_type(self) -> Dict[str, Any]:
        """解析类型注解"""
        type_name = self.expect(TokenType.IDENTIFIER).value
        
        # 泛型类型
        if self.match(TokenType.LT):
            self.advance()
            generic_types = []
            
            while not self.match(TokenType.GT):
                generic_types.append(self.parse_type())
                
                if self.match(TokenType.COMMA):
                    self.advance()
                elif not self.match(TokenType.GT):
                    raise ParseError(
                        "期望 ',' 或 '>'",
                        self.current_token().line, self.current_token().column
                    )
            
            self.expect(TokenType.GT)
            
            return {"name": type_name, "generics": generic_types}
        
        return {"name": type_name, "generics": []}


class ModernShellParser:
    """现代Shell解析器主类"""
    
    def __init__(self):
        self.lexer = None
        self.parser = None
    
    def parse(self, text: str) -> ASTNode:
        """解析Shell命令文本"""
        try:
            # 词法分析
            self.lexer = Lexer(text)
            tokens = self.lexer.tokenize()
            
            # 语法分析
            self.parser = Parser(tokens)
            ast = self.parser.parse()
            
            return ast
            
        except ParseError as e:
            raise ParseError(f"解析错误: {e}", e.line, e.column)
        except Exception as e:
            raise ParseError(f"内部错误: {e}")
    
    def parse_expression(self, text: str) -> ASTNode:
        """解析单个表达式"""
        try:
            self.lexer = Lexer(text)
            tokens = self.lexer.tokenize()
            
            self.parser = Parser(tokens)
            return self.parser.parse_expression()
            
        except ParseError as e:
            raise ParseError(f"表达式解析错误: {e}", e.line, e.column)
        except Exception as e:
            raise ParseError(f"内部错误: {e}")