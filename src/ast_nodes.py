from dataclasses import dataclass
import sys
from typing import List, Optional
from lark import Transformer, ast_utils, v_args

@dataclass
class Node:
    pass

@dataclass
class Expr(Node):
    pass

@dataclass
class Stmt(Node):
    pass

@dataclass
class Number(Expr):
    value: float

@dataclass
class StringLiteral(Expr):
    value: str

@dataclass
class Variable(Expr):
    name: str

@dataclass
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr

@dataclass
class Assignment(Stmt):
    name: str
    value: Expr

@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]

@dataclass
class PrintStmt(Stmt):
    expression: Expr
    new_line: bool

@dataclass
class Body(Node):
    statements: List[Stmt]

@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_block: Body
    else_block: Optional[Body] = None

@dataclass
class ForLoop(Stmt):
    iterator: str
    start_val: Expr
    condition: Expr
    step: Expr
    body: Body

@dataclass
class Arg(Node):
    name: str
    type_name: str

@dataclass
class FunctionDef(Node):
    name: str
    args: List[Arg]
    ret_type: str
    body: Body

@dataclass
class Program(Node):
    functions: List[FunctionDef]


# --- Transformer ---

from lark import Transformer, v_args

class PikeTransformer(Transformer):
    def __init__(self):
        self.anon_counter = 0

    def start(self, items):
        functions = []
        for item in items:
            if isinstance(item, FunctionDef):
                functions.append(item)
            elif isinstance(item, Stmt):
                self.anon_counter += 1
                name = f"_anon{self.anon_counter}"
                # Change: Wrap item in Body
                func = FunctionDef(
                    name=name, 
                    args=[], 
                    ret_type="void", 
                    body=Body(statements=[item]) 
                )
                functions.append(func)
        return Program(functions=functions)

    def top_level_stmt(self, items):
        return items[0]

    def function_def(self, items):
        name = str(items[0])
        args = items[1] if items[1] is not None else []
        ret_type = str(items[2]) if items[2] is not None else "void"
        # Change: Wrap items[3] (list of stmts) in Body
        body = Body(statements=items[3]) 

        return FunctionDef(name, args, ret_type, body)

    def args(self, items):
        return items # returns list of Arg

    def arg(self, items):
        return Arg(name=str(items[0]), type_name=str(items[1]))

    def body(self, items):
        return items # returns list of Stmt (can be empty list)

    # --- Statements ---
    def assignment(self, items):
        return Assignment(name=str(items[0]), value=items[1])

    def return_stmt(self, items):
        return ReturnStmt(value=items[0])

    def print_nl(self, items):
        return PrintStmt(expression=items[0], new_line=True)

    def print_no_nl(self, items):
        return PrintStmt(expression=items[0], new_line=False)

    def if_stmt(self, items):
        cond = items[0]
        then_blk = Body(statements=items[1]) # Changed
        else_blk = Body(statements=items[2]) if items[2] is not None else None # Changed
        return IfStmt(cond, then_blk, else_blk)

    def for_stmt(self, items):
        # for (NAME, expr; expr; expr)
        # 0: iterator name
        # 1: start
        # 2: condition
        # 3: step
        # 4: body
        return ForLoop(
            iterator=str(items[0]),
            start_val=items[1],
            condition=items[2],
            step=items[3],
            body=Body(statements=items[4])
        )

    def expr_stmt(self, items):
        return items[0] 

    # --- Expressions & Binary Ops ---
    def add(self, items): return BinOp('+', items[0], items[1])
    def sub(self, items): return BinOp('-', items[0], items[1])
    def mul(self, items): return BinOp('*', items[0], items[1])
    def div(self, items): return BinOp('/', items[0], items[1])
    def lt(self, items): return BinOp('<', items[0], items[1])
    def gt(self, items): return BinOp('>', items[0], items[1])

    def number(self, items):
        return Number(float(items[0]))

    def string(self, items):
        # Remove quotes
        return StringLiteral(str(items[0])[1:-1])

    def var_load(self, items):
        return Variable(str(items[0]))