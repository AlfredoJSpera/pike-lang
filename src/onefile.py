import sys
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any

from lark import Lark, Transformer, v_args
from llvmlite import ir

# ==========================================
# 1. AST Definition
# ==========================================

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
class Arg:
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

# ==========================================
# 2. Lark Grammar
# ==========================================

grammar = r"""
    start: top_level*

    ?top_level: function_def
              | stmt                    -> top_level_stmt

    // Function Definition
    // items: 0=NAME, 1=args(opt), 2=ret(opt), 3=body
    function_def: "defunc" NAME "(" [args] ")" ["%" NAME] "{" body "}"
    
    args: arg ("," arg)*
    arg: NAME ":" NAME

    body: stmt*

    // Statements
    ?stmt: assignment ";"
         | return_stmt ";"
         | print_stmt ";"
         | if_stmt
         | for_stmt
         | expr ";"             -> expr_stmt

    assignment: NAME ":=" expr
    return_stmt: "ret" expr
    print_stmt: "!" "(" expr ")"   -> print_no_nl
              | "!!" "(" expr ")"  -> print_nl

    // If: items: 0=expr, 1=body, 2=else_body(opt)
    if_stmt: "if" "(" expr ")" "{" body "}" ["else" "{" body "}"]
    
    // For loop: for (x, 0; x < max_val; 1)
    for_stmt: "for" "(" NAME "," expr ";" expr ";" expr ")" "{" body "}"

    // Expressions with Precedence
    // Precedence: (<, >) -> (+, -) -> (*, /)
    
    ?expr: comparison

    ?comparison: sum
               | sum "<" sum  -> lt
               | sum ">" sum  -> gt

    ?sum: product
        | sum "+" product -> add
        | sum "-" product -> sub

    ?product: atom
            | product "*" atom -> mul
            | product "/" atom -> div

    ?atom: NUMBER           -> number
         | ESCAPED_STRING   -> string
         | NAME             -> var_load
         | "(" expr ")"

    // Terminals
    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /\d+(\.\d+)?/
    
    %import common.ESCAPED_STRING
    %import common.WS
    %import common.SH_COMMENT
    
    %ignore WS
    %ignore SH_COMMENT
"""

# ==========================================
# 3. Transformer (AST Builder)
# ==========================================

class ASTTransformer(Transformer):
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
        return ForLoop(
            iterator=str(items[0]),
            start_val=items[1],
            condition=items[2],
            step=items[3],
            body=Body(statements=items[4]) # Changed
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

# ==========================================
# 4. LLVM Code Generator (Skeleton)
# ==========================================

class LLVMCompiler:
    def __init__(self):
        self.module = ir.Module(name="main_module")
        self.builder = None
        self.func_symtab = {}
        
        # Define basic types
        self.double = ir.DoubleType()
        self.void = ir.VoidType()
        
        # Declare printf
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

    def compile(self, program: Program):
        for func_def in program.functions:
            self._compile_function(func_def)
        return str(self.module)

    def _compile_function(self, node: FunctionDef):
        # Map return type
        ret_type = self.double if node.ret_type == "num" else self.void
        
        # Map args
        arg_types = [self.double for _ in node.args] 
        
        func_type = ir.FunctionType(ret_type, arg_types)
        func = ir.Function(self.module, func_type, name=node.name)
        
        self.func_symtab[node.name] = func

        # Block setup
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        
        # Local variables
        self.locals = {}
        for i, arg in enumerate(node.args):
            ptr = self.builder.alloca(self.double, name=arg.name)
            self.builder.store(func.args[i], ptr)
            self.locals[arg.name] = ptr

        for stmt in node.body.statements:
            self._compile_stmt(stmt)
            
        # Ensure void return if not present
        if node.ret_type == "void" and not block.is_terminated:
            self.builder.ret_void()

    def _compile_stmt(self, stmt):
        if isinstance(stmt, Assignment):
            val = self._compile_expr(stmt.value)
            if stmt.name not in self.locals:
                ptr = self.builder.alloca(self.double, name=stmt.name)
                self.locals[stmt.name] = ptr
            self.builder.store(val, self.locals[stmt.name])

        elif isinstance(stmt, ReturnStmt):
            val = self._compile_expr(stmt.value)
            self.builder.ret(val)

        elif isinstance(stmt, PrintStmt):
            self._emit_print(stmt)
            
        elif isinstance(stmt, ForLoop):
            self._emit_for(stmt)
            
        elif isinstance(stmt, IfStmt):
            self._emit_if(stmt)

    def _compile_expr(self, expr):
        if isinstance(expr, Number):
            return ir.Constant(self.double, expr.value)
        elif isinstance(expr, Variable):
            if expr.name in self.locals:
                return self.builder.load(self.locals[expr.name])
            return ir.Constant(self.double, 0.0) # Fallback
        elif isinstance(expr, BinOp):
            lhs = self._compile_expr(expr.left)
            rhs = self._compile_expr(expr.right)
            if expr.op == '+': return self.builder.fadd(lhs, rhs)
            elif expr.op == '-': return self.builder.fsub(lhs, rhs)
            elif expr.op == '*': return self.builder.fmul(lhs, rhs)
            elif expr.op == '/': return self.builder.fdiv(lhs, rhs)
            elif expr.op == '<': return self.builder.fcmp_ordered('<', lhs, rhs)
            elif expr.op == '>': return self.builder.fcmp_ordered('>', lhs, rhs)
        return ir.Constant(self.double, 0.0)

    def _emit_print(self, stmt: PrintStmt):
        val = stmt.expression
        if isinstance(val, StringLiteral):
            # Very simplified string handling for demo
            s_bytes = bytearray(val.value.encode("utf8"))
            if stmt.new_line: s_bytes += b"\n"
            s_bytes += b"\0"
            
            c_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(s_bytes)), s_bytes)
            global_str = ir.GlobalVariable(self.module, c_str.type, name=f"str_{id(stmt)}")
            global_str.linkage = 'internal'
            global_str.global_constant = True
            global_str.initializer = c_str
            
            # Print strings via printf("%s") is standard, but here we just pass the string ptr to printf 
            # (assuming it doesn't have % in it for safety, or we define a "%s" fmt)
            # For strictness:
            fmt = "%s\0"
            c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
            global_fmt = ir.GlobalVariable(self.module, c_fmt.type, name=f"fmt_s_{id(stmt)}")
            global_fmt.initializer = c_fmt
            
            fmt_arg = self.builder.bitcast(global_fmt, ir.IntType(8).as_pointer())
            str_arg = self.builder.bitcast(global_str, ir.IntType(8).as_pointer())
            self.builder.call(self.printf, [fmt_arg, str_arg])
            
        else:
            value = self._compile_expr(val)
            fmt = "%.2f\n\0" if stmt.new_line else "%.2f\0"
            c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
            global_fmt = ir.GlobalVariable(self.module, c_fmt.type, name=f"fmt_n_{id(stmt)}")
            global_fmt.linkage = 'internal'
            global_fmt.global_constant = True
            global_fmt.initializer = c_fmt
            fmt_arg = self.builder.bitcast(global_fmt, ir.IntType(8).as_pointer())
            self.builder.call(self.printf, [fmt_arg, value])

    def _emit_if(self, stmt: IfStmt):
        cond_val = self._compile_expr(stmt.condition)
        bool_cond = self.builder.fcmp_ordered('!=', cond_val, ir.Constant(self.double, 0.0))
        
        with self.builder.if_else(bool_cond) as (then, otherwise):
            with then:
                # Change: access .statements
                for s in stmt.then_block.statements: self._compile_stmt(s)
            with otherwise:
                if stmt.else_block:
                    # Change: access .statements
                    for s in stmt.else_block.statements: self._compile_stmt(s)

    def _emit_for(self, stmt: ForLoop):
        init_val = self._compile_expr(stmt.start_val)
        ptr = self.builder.alloca(self.double, name=stmt.iterator)
        self.builder.store(init_val, ptr)
        self.locals[stmt.iterator] = ptr
        
        parent = self.builder.block.parent
        cond_block = parent.append_basic_block("loop_cond")
        body_block = parent.append_basic_block("loop_body")
        end_block = parent.append_basic_block("loop_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_expr = self._compile_expr(stmt.condition)
        bool_cond = self.builder.fcmp_ordered('!=', cond_expr, ir.Constant(self.double, 0.0))
        self.builder.cbranch(bool_cond, body_block, end_block)

        self.builder.position_at_end(body_block)
        for s in stmt.body.statements:
            self._compile_stmt(s)
        
        step_val = self._compile_expr(stmt.step)
        cur_val = self.builder.load(ptr)
        new_val = self.builder.fadd(cur_val, step_val)
        self.builder.store(new_val, ptr)
        self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

# ==========================================
# 5. Main Execution
# ==========================================

code = """
defunc greeter() {
    !!("Hello"); # Print with NL
}

# Assignment
max_val := 10;

# Function with typed arguments and return type
defunc add_numbers(a: num, b: num) %num {
    ret a + b;
}

# For loop for(x=0;x<max_val;x++)
for (x, 0; x < max_val; 1) {
	hello := "h";
    if (x < 5) {
        !("Small: "); # Print without NL
        !!(x);
    } else {
        !("Large: ");
        !!(x);
    }
}
"""

if __name__ == "__main__":
    print("--- 1. Parsing and AST Generation ---")
    parser = Lark(grammar, parser='lalr', transformer=ASTTransformer())
    try:
        ast_program = parser.parse(code)
        
        # Pretty print AST structure
        for func in ast_program.functions:
            print(f"Function: {func.name} (Ret: {func.ret_type})")
            if func.name.startswith("_anon"):
                print(f"  [Wrapper for top-level code] Body stmts: {len(func.body.statements)}")
            else:
                print(f"  Args: {func.args}")
                print(f"  Body stmts: {len(func.body.statements)}")

        print("\n--- 2. Generating LLVM IR ---")
        compiler = LLVMCompiler()
        llvm_ir = compiler.compile(ast_program)
        print(llvm_ir)
    except Exception as e:
        import traceback
        traceback.print_exc()