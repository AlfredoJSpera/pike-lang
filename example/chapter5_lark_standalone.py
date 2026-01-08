# Bundled from: ast_nodes, codegen, evaluator, grammar, utils, tests, main
# Auto-generated bundle

# --- External Imports ---
from ctypes import CFUNCTYPE, c_double
from lark import Lark
from lark import Transformer
import llvmlite.binding as llvm
import llvmlite.ir as ir
import re
import unittest

# --- Module: ast_nodes ---
class ASTNode(object):
    """A node that defines a structure with colorized, tightly-bound tree branches."""

    # Color Constants
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def dump(self, prefix="", is_last=True, is_root=True, label=""):
        attrs = []
        children = []

        # 1. Identify Attributes and Labeled Children
        for key, value in vars(self).items():
            if isinstance(value, list):
                if any(isinstance(item, ASTNode) for item in value):
                    for i, item in enumerate(value):
                        children.append((f"{key}[{i}]", item))
                else:
                    attrs.append(f"{self.CYAN}{key}={value}{self.RESET}")
            elif isinstance(value, ASTNode):
                children.append((key, value))
            else:
                attrs.append(f"{self.YELLOW}{value}{self.RESET}")

        # 2. Build the current line
        # Use standard tree connectors
        connector = "" if is_root else ("└── " if is_last else "├── ")
        
        # Format segments without extra padding/tabs
        label_part = f"{self.GREEN}{label}{self.RESET} => " if label else ""
        class_part = f"{self.BOLD}{self.BLUE}{self.__class__.__name__}{self.RESET}"
        attr_part = f"[{', '.join(attrs)}]"

        header = f"{prefix}{connector}{label_part}{class_part}{attr_part}"
        lines = [header]

        # 3. Handle recursion for children
        # The pipe connects siblings vertically
        pipe = "│   "
        space = "    "
        new_prefix = prefix if is_root else (prefix + (space if is_last else pipe))
        
        for i, (child_label, child_node) in enumerate(children):
            is_last_child = (i == len(children) - 1)
            lines.append(child_node.dump(new_prefix, is_last_child, False, child_label))

        return "\n".join(lines)

class ExprAST(ASTNode): 
	"""A node that defines logic that results in a value."""
	pass


class NumberExprAST(ExprAST):
	def __init__(self, value: float):
		"""
		An expression node that represents a number.
		
		Args:
			value (float): The number.
		
		Example:
			>>> # 1
			>>> node = NumberExprAST(1.0)
		"""
		self.value = value


class VariableExprAST(ExprAST):
	def __init__(self, name: str):
		"""
		An expression node that represents a variable (only its name).
		
		Args:
			name (str): The variable's name.
		
		Example:
			>>> # x
			>>> node = VariableExprAST("x")
		"""
		self.name = name


class BinaryExprAST(ExprAST):
	def __init__(self, operator: str, left_operand: ExprAST, right_operand: ExprAST):
		"""
		An expression node that represents a binary expression.
		
		Args:
			operator : The central operator.
			left_operand: The left operand of the expression.
			right_operand: The right operand of the expression.
		
		Example:
			>>> # x + 5
			>>> node = BinaryExprAST("+", VariableExprAST("a"), NumberExprAST(5.0))
		"""
		self.operator = operator
		self.left_operand = left_operand
		self.right_operand = right_operand


class IfExprAST(ExprAST):
	def __init__(self, cond_expr: ExprAST, then_expr: ExprAST, else_expr: ExprAST):
		"""
		An expression node that represents an if/then/else control flow.
		
		Args:
			condition_expr: The "condition" expression. If true, makes the flow continue to the "then" expression ("else" otherwise).
			then_expr: The "then" expression.
			else_expr: The "else" expression.
		
		Example:
			>>> # if x < 10 then 1 else 0
			>>> condition = BinaryExprAST("<", VariableExprAST("x"), NumberExprAST(10.0))
			>>> node = IfExprAST(condition, NumberExprAST(1.0), NumberExprAST(0.0))
		"""
		self.condition_expr = cond_expr
		self.then_expr = then_expr
		self.else_expr = else_expr


class ForExprAST(ExprAST):
	def __init__(self, counter_name: str, start_expr: ExprAST, end_expr: ExprAST, step_expr: ExprAST | None, body: ExprAST):
		"""
		An expression node that represents a for loop.
		
		Args:
			counter_name (str): The loop's counter variable name.
			start_expr (ExprAST): The expression that determines the initial value of the loop counter.
			end_expr (ExprAST): The expression that, if true, ends the loop.
			step_expr (ExprAST | None): The expression that is added to the counter.
			body (ExprAST): The expression to execute in the loop.
		
		Example:
			>>> # for i = 65, i < 79, 1.0 in i+1
			>>> id_n  = "i"
			>>> start = NumberExprAST(65.0)
			>>> end   = BinaryExprAST("<", "i", 79.0)
			>>> step  = NumberExprAST(1.0)
			>>> body  = BinaryExprAST("+", VariableExprAST("i"), NumberExprAST(1.0))
			>>> node  = ForExprAST(id_n, start, end, step, body)
		"""
		self.counter_name = counter_name
		self.start_expr = start_expr
		self.end_expr = end_expr
		self.step_expr = step_expr
		self.body = body


class CallExprAST(ExprAST):
	def __init__(self, called_function_name: str, args: list[ExprAST]):
		"""
		An expression node that represents a call to a function.
		
		Args:
			called_function_name (str): The name of the called function.
			args (list[ExprAst]): A list of arguments (expressions) passed in the call.
		
		Example:
			>>> # foo(a, 10)
			>>> callee = "foo"
			>>> args = [VariableExprAST("a"), NumberExprAST(1.0)]
			>>> node = CallExprAST(callee, args)
		"""
		self.called_function_name = called_function_name
		self.args = args


class PrototypeAST(ASTNode):
	def __init__(self, name: str, arg_names: list[str]):
		"""
		A node that represents a prototype of a function. 
		Is a part of the FunctionAST node.
		
		Args:
			name (str): The name of the function.
			arg_names (list[str]): A list of names of the arguments required.
		
		Example:
			>>> # def foo(x y)
			>>> node = PrototypeAST("foo", ["x", "y"])
		"""
		self.name = name
		self.arg_names = arg_names


class FunctionAST(ASTNode):
	def __init__(self, prototype: PrototypeAST, body: ExprAST):
		"""
		A node that represents a callable function.
		Can also create an anonymous function.
		
		Args:
			prototype (PrototypeAST): The prototype of the function.
			body (ExprAST): An expression for the body of the function.
		
		Example:
			>>> # def foo(x y) x + 1
			>>> proto = PrototypeAST("foo", ["x"])
			>>> body = BinaryExprAST("+", VariableExprAST("x"), NumberExprAST(1.0))
			>>> node = FunctionAST(proto, body)
		"""
		self.prototype = prototype
		self.body = body
	
	_anonymous_function_counter = 0

	@classmethod
	def create_anonymous(cls, expr):
		"""Wraps a top-level expression in a unique function without parameters for immediate JIT execution."""
		cls._anonymous_function_counter += 1
		anon_prototype = PrototypeAST(f"_anon{cls._anonymous_function_counter}", [])
		return cls(anon_prototype, expr)

	def is_anonymous(self):
		return self.prototype.name.startswith('_anon')

# --- Module: utils ---
import re

def visible_len(text: str) -> int:
    """Calculates the length of a string excluding ANSI escape sequences."""
    # This regex matches the ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return len(ansi_escape.sub('', text))

def print_boxed(label: str, text: str):
    """
    Print something inside a box with a label, handling ANSI colored text correctly.
    """
    lines = text.splitlines()

    # 1. Use visible_len for the width calculations
    content_width = max(visible_len(line) for line in lines) if lines else 0
    label_width = visible_len(label)
    
    # Total internal width needed
    width = max(content_width, label_width) + 2

    # 2. Draw the Top Border
    # We subtract 1 from the dash count because of the space after the label
    top_dashes = width - label_width - 1
    print(f"\n┌─ {label} {'─' * top_dashes}┐")

    # 3. Draw the Content Lines
    for line in lines:
        # Calculate how much padding is needed based on visible length
        padding = " " * (width - visible_len(line))
        print(f"│ {line}{padding} │")

    # 4. Draw the Bottom Border
    print(f"└{'─' * (width + 2)}┘")

# --- Module: codegen ---
import llvmlite.ir as ir

class CodegenError(Exception): 
	pass


class LLVMCodeGenerator(object):
	"""
	Uses the visitor pattern.
	"""
	def __init__(self):
		self.module = ir.Module()
		self.builder = None # initialized in _codegen_FunctionAST
		self.function_symbol_table = {}

	def generate_code(self, node):
		"""
		Generate the LLVM code as a string from the parsed AST 
		and store it in module.
		"""
		return self._codegen(node)

	def _codegen(self, node):
		"""Execute the correct codegen function."""
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)
	
	def _codegen_FunctionAST(self, node: FunctionAST):
		# Initialize the symbol table
		self.function_symbol_table = {}

		# Create or retrieve the function using its prototype
		function = self._codegen(node.prototype)
		entry_basic_block = function.append_basic_block("entry")
		
		# Initialize the builder with the entry at the top
		self.builder = ir.IRBuilder(entry_basic_block)
		
		# Generate the code of the body and return the final value
		#! Based on the content of the body (the function can be anonymous), 
		#! this is the main codegen caller
		retval = self._codegen(node.body)
		self.builder.ret(retval)
		
		return function

	def _codegen_PrototypeAST(self, node: PrototypeAST):
		# Get the function signature
		proto_func_name = node.name
		proto_func_types = ir.FunctionType(
			return_type=ir.DoubleType(), 
			args=[ir.DoubleType()] * len(node.arg_names) # A list of arguments of variable length
		)

		# Search if the function has already been declared
		if proto_func_name in self.module.globals:
			# The function already exists, get it
			existing_func = self.module.globals.get(proto_func_name)
			
			# Error checking
			if not isinstance(existing_func, ir.Function):
				raise CodegenError("Function/Global name collision", proto_func_name)
			if not existing_func.is_declaration:
				raise CodegenError(f"Re-definition of {proto_func_name}")
			
			# Args length check
			existing_func_args_number = len(existing_func.function_type.args)
			proto_func_args_number = len(proto_func_types.args)
			if existing_func_args_number != proto_func_args_number:
				raise CodegenError(f"Re-definition of {proto_func_name} with different number of arguments ({proto_func_args_number} instead of {existing_func_args_number})")
			
			# Get the function from globals
			function = self.module.globals[proto_func_name]
		else:
			# Create the new function
			function = ir.Function(
				module=self.module, 
				ftype=proto_func_types, 
				name=proto_func_name
			)

		for i, arg in enumerate(function.args):
			# Change the default indexed LLVM variable names
			# to the ones defined in the passed node
			# e.g. ".1" -> "my_arg"
			arg.name = node.arg_names[i]
			self.function_symbol_table[arg.name] = arg
		
		return function

	def _codegen_NumberExprAST(self, node: NumberExprAST):
		value = float(node.value)
		return ir.Constant(ir.DoubleType(), value)

	def _codegen_VariableExprAST(self, node: VariableExprAST):
		# Get the variable from the symbol table
		variable = self.function_symbol_table.get(node.name)
		
		# Error checking
		if variable is None:
			raise CodegenError("Using unknown variable", node.name)
		
		return variable

	def _codegen_BinaryExprAST(self, node: BinaryExprAST):
		# Recursion on the node's children
		left = self._codegen(node.left_operand)
		right = self._codegen(node.right_operand)

		if self.builder is None:
			raise CodegenError("Builder is not initialized")

		# Select and return the operation
		if node.operator == '+': 
			return self.builder.fadd(left, right, "addtmp")
		elif node.operator == '-': 
			return self.builder.fsub(left, right, "subtmp")
		elif node.operator == '*': 
			return self.builder.fmul(left, right, "multmp")
		elif node.operator == '/': 
			return self.builder.fdiv(left, right, "divtmp")
		elif node.operator == '<':
			cmp_func = self.builder.fcmp_unordered('<', left, right, "cmptmp")
			# Convert the integer (boolean) to a double
			return self.builder.uitofp(cmp_func, ir.DoubleType(), "booltmp")
		else:
			raise CodegenError("Unknown binary operator", node.operator)
	
	def _codegen_CallExprAST(self, node: CallExprAST):
		called_function_name = node.called_function_name
		
		# Get the function from the globals
		called_function = self.module.globals.get(called_function_name, None)
		
		# Error checking
		if called_function is None or not isinstance(called_function, ir.Function):
			raise CodegenError("Call to unknown function",called_function_name)
		
		# Args length checking
		called_function_args_length = len(called_function.args)
		args_passed_length = len(node.args)
		if called_function_args_length != args_passed_length:
			raise CodegenError(f"Call argument length mismatch for {called_function_name} (passed {args_passed_length} instead of {called_function_args_length})")
		
		# Generate the code for each argument
		args_passed = [self._codegen(arg) for arg in node.args]
		
		if self.builder is None:
			raise CodegenError("Builder is not initialized")
		
		# Call the function and return the reference to the call
		return self.builder.call(called_function, args_passed, "calltmp")

	def _codegen_IfExprAST(self, node: IfExprAST):
		# Generate the code for the condition
		condition_result = self._codegen(node.condition_expr)

		if self.builder is None: 
			raise CodegenError("Builder is not initialized")
		
		# Check if the condition is true
		# 1 != 0 => true
		# 0 != 0 => false
		zero_false = ir.Constant(ir.DoubleType(), 0.0)
		is_condition_true = self.builder.fcmp_ordered('!=', condition_result, zero_false)

		# Build the control flow basic blocks
		then_block = ir.Block(self.builder.function, "then")
		else_block = ir.Block(self.builder.function, "else")
		merge_block = ir.Block(self.builder.function, "ifcont")

		# Execute the branching
		self.builder.cbranch(is_condition_true, then_block, else_block)

		# THEN block
		self.builder.function.basic_blocks.append(then_block)
		self.builder.position_at_start(then_block) # Pointer for insertion
		then_value = self._codegen(node.then_expr)
		self.builder.branch(merge_block)
		then_block = self.builder.block

		# ELSE block
		self.builder.function.basic_blocks.append(else_block)
		self.builder.position_at_start(else_block) # Pointer for insertion
		else_value = self._codegen(node.else_expr)
		self.builder.branch(merge_block)
		else_block = self.builder.block

		# MERGE
		self.builder.function.basic_blocks.append(merge_block)
		self.builder.position_at_start(merge_block)
		
		# Decide the path taken with phi
		phi = self.builder.phi(ir.DoubleType(), "iftmp")
		phi.add_incoming(then_value, then_block)
		phi.add_incoming(else_value, else_block)
		
		return phi

	def _codegen_ForExprAST(self, node: ForExprAST):
		# Generate the code for the starting condition
		counter_start_value = self._codegen(node.start_expr)
		
		if self.builder is None:
			raise CodegenError("Builder is not initialized")

		# Keep track of the block we are currently in before entering the loop
		pre_header_block = self.builder.block

		# Explicitly jump from the current position into the loop
		loop_block = self.builder.function.append_basic_block("loop_header")
		self.builder.branch(loop_block)
		self.builder.position_at_start(loop_block)

		# Create a PHI node to track the loop counter
		# At this point it can be: 
		# - The init value from the parameter (entry, pre_header)
		# - The incremented counter
		counter_current_phi_value = self.builder.phi(ir.DoubleType(), node.counter_name)
		counter_current_phi_value.add_incoming(counter_start_value, pre_header_block)

		# Save any existing variable with the same name as the counter and hide it (shadowing)
		shadowed_value = self.function_symbol_table.get(node.counter_name)
		self.function_symbol_table[node.counter_name] = counter_current_phi_value

		# Generate code for the loop body
		self._codegen(node.body)

		# Calculate the step (default to 1.0 if not provided)
		if node.step_expr:
			step_value = self._codegen(node.step_expr)
		else:
			step_value = ir.Constant(ir.DoubleType(), 1.0)
		
		# Increment the current phi value with the step value
		counter_incremented_value = self.builder.fadd(counter_current_phi_value, step_value, "next_iterator_val")

		# Check if the end condition is true
		end_condition = self._codegen(node.end_expr)
		is_loop_active = self.builder.fcmp_ordered(
			'!=', 
			end_condition, 
			ir.Constant(ir.DoubleType(), 0.0), 
			"loop_active_bool"
		)

		# Record the block where the loop logic ends
		loop_end_block = self.builder.block

		# Create the block for the code following the loop
		after_loop_block = self.builder.function.append_basic_block("after_loop")

		# If active, jump back to the header, exit the loop otherwise
		self.builder.cbranch(is_loop_active, loop_block, after_loop_block)
		
		# If we loop back, the value is now the incremented counter
		counter_current_phi_value.add_incoming(counter_incremented_value, loop_end_block)

		# Move the builder to the block after the loop so codegen can continue
		self.builder.position_at_start(after_loop_block)

		# Restore the original variable to the symbol table (un-shadowing)
		if shadowed_value is None:
			# No variable was shadowed, delete the entry
			del self.function_symbol_table[node.counter_name]
		else:
			self.function_symbol_table[node.counter_name] = shadowed_value

		# For loops in this language traditionally return 0.0
		return ir.Constant(ir.DoubleType(), 0.0)

# --- Module: grammar ---
from lark import Transformer

# Grammar in Lark format.
# Operator precedence with rule nesting (relation < add < term).
grammar = r"""
    ?start: toplevel

    ?toplevel: definition
             | external
             | expression_top

    // Definitions and externals
    definition: "def" prototype expression
    external: "extern" prototype
    prototype: NAME "(" [NAME (NAME)*] ")"

    // Expressions
    expression_top: expression 

    ?expression: relation

    // Precedence 10: <
    ?relation: add_expr (LESS add_expr)*

    // Precedence 20: "+, -"
    ?add_expr: term (( PLUS | MINUS ) term)*

    // Precedence 40: "*, /"
    ?term: factor (( STAR | SLASH ) factor)*

    ?factor: primary

    ?primary: number
            | call_expr
            | if_expr
            | for_expr
            | variable
            | "(" expression ")"

    // Specific constructs
    call_expr: NAME "(" [expression ("," expression)*] ")"
    
    if_expr: "if" expression "then" expression "else" expression

    for_expr: "for" NAME "=" expression "," expression ["," expression] "in" expression

    variable: NAME
    number: NUMBER

    // Terminals
    PLUS: "+"
    MINUS: "-"
    STAR: "*"
    SLASH: "/"
    LESS: "<"

    NAME: /[a-zA-Z][a-zA-Z0-9_]*/
    %import common.NUMBER
    %import common.WS
    %ignore WS
    %ignore /#.*/
"""

class KaleidoscopeTransformer(Transformer):
	"""
	A transformer that converts the Lark tree (Parse Tree) directly into 
	the original AST classes (NumberExprAST, BinaryExprAST, etc.).

	The name of the methods of this class are equal to the nodes in the lark grammar specification.
	"""
	
	def number(self, items):
		value = float(items[0])
		return NumberExprAST(value)

	def variable(self, items):
		name = str(items[0])
		return VariableExprAST(name)

	def call_expr(self, items):
		called_function_name = str(items[0])
		called_function_args = items[1:]
		return CallExprAST(called_function_name, called_function_args)

	def if_expr(self, items):
		cond_expr=items[0]
		else_expr=items[1]
		then_expr=items[2]
		return IfExprAST(cond_expr, else_expr, then_expr)

	def for_expr(self, items):
		# items structure: [name, start, end, (step?), body]
		id_name = str(items[0])
		start_expr = items[1]
		end_expr = items[2]
		
		if len(items) == 5:
			# Step is present
			step_expr = items[3]
			body = items[4]
		else:
			# Step is missing (default None)
			step_expr = None
			body = items[3]
			
		return ForExprAST(id_name, start_expr, end_expr, step_expr, body)

	def _binary_op(self, items):
		"""Helper for managing binary operators (+, -, *, <) while maintaining left associativity."""
		lhs = items[0]
		# items is of [Expr, Token(PLUS), Expr, Token(MINUS), Expr...]
		for i in range(1, len(items), 2):
			op = items[i].value
			rhs = items[i+1]
			lhs = BinaryExprAST(op, lhs, rhs)
		return lhs

	def relation(self, items):
		# "<"
		# TODO: add a >
		return self._binary_op(items)

	def add_expr(self, items):
		# "+, -""
		return self._binary_op(items)
	
	def term(self, items):
		# "*, /"
		return self._binary_op(items)

	def prototype(self, items):
		name = str(items[0])
		arg_names = [str(x) for x in items[1:]]
		return PrototypeAST(name, arg_names)

	def definition(self, items):
		prototype = items[0]
		body = items[1]
		return FunctionAST(prototype, body)

	def external(self, items):
		# Returns PrototypeAST
		return items[0]

	def expression_top(self, items):
		# Code that is not inside a function is put inside an anonymous one
		return FunctionAST.create_anonymous(items[0])

# --- Module: evaluator ---
import llvmlite.binding as llvm
from lark import Lark
from ctypes import CFUNCTYPE, c_double
import llvmlite.ir as ir

class KaleidoscopeEvaluator(object):
	"""Responsible for evaluating expressions and statements in the Kaleidoscope language."""

	def __init__(self):
		# Initialize llvmlite
		llvm.initialize()
		llvm.initialize_native_target()
		llvm.initialize_native_asmprinter()

		# Initialize the llvm code generation an evaluation
		self.llvm_code_generator = LLVMCodeGenerator()
		self._add_builtins(self.llvm_code_generator.module)
		self.target = llvm.Target.from_default_triple()

		# Initialize the Lark parser
		self.parser = Lark(grammar, parser="lalr", transformer=KaleidoscopeTransformer())

	def evaluate(self, 
			code_string: str, 
			optimize_llvm: bool = True, 
			print_ast_dump: bool = False,
			print_llvm_dump: bool = False,
		):
		"""
		Parse and evaluate the code.
		
		:param code_string: The code to evaluate.
		:type code_string: str
		
		:param optimize_llvm: Optimize the generated llvm code.
		:type optimize_llvm: bool

		:param print_ast_dump: AST debug flag.
		:type print_ast_dump: bool

		:param print_llvm_dump: LLVM debug flag.
		:type print_llvm_dump: bool
		"""
		
		# Parse the code string with Lark to return an AST
		try:
			parsed_ast = self.parser.parse(code_string)
		except Exception as e:
			print(f"Error parsing code: {e}")
			exit(1)
		
		if print_ast_dump:
			dump = parsed_ast.dump() # type: ignore
			print_boxed(f"AST Tree Dump: '{code_string}'", dump) 

		# Generate the llvm code
		try:
			self.llvm_code_generator.generate_code(parsed_ast)
		except Exception as e:
			print(f"Error generating llvm: {e}")
			exit(1)

		if print_llvm_dump:
			unoptimized = str(self.llvm_code_generator.module)
			print_boxed(f"Unoptimized LLVM IR: '{code_string}'", unoptimized) 

		# If the AST is a function definition (not anonymous), store it and do not execute it
		# Else, continue with the execution
		if not (isinstance(parsed_ast, FunctionAST) and parsed_ast.is_anonymous()):
			return None

		# Convert the LLVM IR string into a binary-like module and store it in a reference
		module_ref = llvm.parse_assembly(str(self.llvm_code_generator.module))

		# Optimize the LLVM IR
		if optimize_llvm:
			pm_builder = llvm.create_pass_manager_builder()
			pm_builder.opt_level = 2
			pm = llvm.create_module_pass_manager()
			pm_builder.populate(pm)
			pm.run(module_ref)

			if print_llvm_dump:
				optimized = str(module_ref)
				print_boxed(f"Optimized LLVM IR: '{code_string}'", optimized) 

		# Select the right set of machine code instructions
		target_machine = self.target.create_target_machine()

		# Compile the LLVM IR into machine code with a JIT compiler
		with llvm.create_mcjit_compiler(module_ref, target_machine) as jit_engine:
			# Resolve all memory addresses and "bake" the binary
			jit_engine.finalize_object()
			
			# Locate the compiled function's address in memory
			func_name = parsed_ast.prototype.name
			func_address = jit_engine.get_function_address(func_name)

			# Wrap the memory address as a Python-callable function (returning a double)
			native_func = CFUNCTYPE(c_double)(func_address)
			
			# Execute the function and return the result
			return native_func()

	def _add_builtins(self, module):
		"""Register external C functions and define helper functions in the LLVM module."""
		# int putchar(int)
		int32 = ir.IntType(32)
		putchar_signature = ir.FunctionType(int32, [int32])
		putchar = ir.Function(module, putchar_signature, 'putchar')

		# double putchard(double)
		double = ir.DoubleType()
		putchard_signature = ir.FunctionType(double, [double])
		putchard = ir.Function(module, putchard_signature, 'putchard')

		# Implement 'putchard' logic
		entry_block = putchard.append_basic_block('entry')
		builder = ir.IRBuilder(entry_block)
		
		# Convert input double to int32 so putchar can consume it
		char_value = builder.fptoui(putchard.args[0], int32, name='intcast')
		
		# Call the actual C putchar
		builder.call(putchar, [char_value])
		
		# Kaleidoscope functions must return a value; return 0.0 by default
		builder.ret(ir.Constant(double, 0.0))

# --- Module: tests ---
import unittest

class TestEvaluator(unittest.TestCase):
	def setUp(self):
		"""
		Create a fresh evaluator for each test to ensure 
		a clean LLVM module and symbol table.
		"""
		self.evaluator = KaleidoscopeEvaluator()

	def test_arithmetic_basic(self):
		"""Test basic floating point arithmetic."""
		self.assertEqual(self.evaluator.evaluate('1 + 2'), 3.0)
		self.assertEqual(self.evaluator.evaluate('10 - 4'), 6.0)
		self.assertEqual(self.evaluator.evaluate('2 * 3'), 6.0)
		self.assertEqual(self.evaluator.evaluate('10 / 2'), 5.0)

	def test_arithmetic_precedence(self):
		"""
		Test that standard order of operations (PEMDAS) is respected.
		Precedence levels checked:
		1. Parentheses ()
		2. Multiplication (*) / Division (/) -> Left Associative
		3. Addition (+) / Subtraction (-) -> Left Associative
		4. Relation (<)
		"""
		# 1. Multiplication has higher precedence than Addition
		# 2 + (3 * 4) = 14
		self.assertEqual(self.evaluator.evaluate('2 + 3 * 4'), 14.0)
		# (3 * 4) + 2 = 14
		self.assertEqual(self.evaluator.evaluate('3 * 4 + 2'), 14.0)

		# 2. Division has higher precedence than Subtraction
		# 20 - (10 / 2) = 15
		self.assertEqual(self.evaluator.evaluate('20 - 10 / 2'), 15.0)

		# 3. Parentheses override standard precedence
		# (2 + 3) * 4 = 20
		self.assertEqual(self.evaluator.evaluate('(2 + 3) * 4'), 20.0)
		# 20 / (2 + 3) = 4
		self.assertEqual(self.evaluator.evaluate('20 / (2 + 3)'), 4.0)

		# 4. Left Associativity of Multiplication/Division
		# (12 / 2) * 3 = 18 ... NOT 12 / (2 * 3) = 2
		self.assertEqual(self.evaluator.evaluate('12 / 2 * 3'), 18.0)

		# 5. Left Associativity of Addition/Subtraction
		# (10 - 2) + 3 = 11 ... NOT 10 - (2 + 3) = 5
		self.assertEqual(self.evaluator.evaluate('10 - 2 + 3'), 11.0)

		# 6. Relational operator has lower precedence than arithmetic
		# (10 + 2) < (20 - 5) => 12 < 15 => 1.0 (True)
		self.assertEqual(self.evaluator.evaluate('10 + 2 < 20 - 5'), 1.0)
		
		# 7. Complex nested parentheses
		# (10 + (2 * 3)) / 2 => (10 + 6) / 2 => 8
		self.assertEqual(self.evaluator.evaluate('(10 + (2 * 3)) / 2'), 8.0)

	def test_function_definition_and_call(self):
		"""Test defining a simple function and calling it."""
		# Define function
		self.evaluator.evaluate('def square(x) x * x')
		
		# Call it
		result = self.evaluator.evaluate('square(5)')
		self.assertEqual(result, 25.0)
		
		# Call it with complex expression
		result_complex = self.evaluator.evaluate('square(2 + 2)')
		self.assertEqual(result_complex, 16.0)

	def test_multi_argument_functions(self):
		"""Test functions with multiple arguments."""
		self.evaluator.evaluate('def average(a b c) (a + b + c) / 3')
		self.assertEqual(self.evaluator.evaluate('average(10, 20, 30)'), 20.0)

	def test_recursion_factorial(self):
		"""Test recursive logic using a factorial function."""
		# Define factorial
		self.evaluator.evaluate('''
			def factorial(x) 
				if x < 1 then 
					1 
				else 
					x * factorial(x - 1)
		''')
		
		self.assertEqual(self.evaluator.evaluate('factorial(5)'), 120.0)
		self.assertEqual(self.evaluator.evaluate('factorial(0)'), 1.0)

	def test_recursion_fibonacci(self):
		"""Test deep recursion with Fibonacci sequence."""
		self.evaluator.evaluate('''
			def fib(x) 
				if x < 3 then 
					1 
				else 
					fib(x-1) + fib(x-2)
		''')
		
		# Fib sequence: 1, 1, 2, 3, 5, 8, 13
		self.assertEqual(self.evaluator.evaluate('fib(6)'), 8.0)
		self.assertEqual(self.evaluator.evaluate('fib(7)'), 13.0)

	def test_boolean_logic(self):
		"""
		Test logic gates implementation.
		In this language, 0.0 is false, anything else is true.
		The '<' operator returns 1.0 for true, 0.0 for false.
		"""
		# Define logical NOT
		self.evaluator.evaluate('def not(x) if x then 0 else 1')
		
		self.assertEqual(self.evaluator.evaluate('not(0)'), 1.0)
		self.assertEqual(self.evaluator.evaluate('not(1)'), 0.0)
		self.assertEqual(self.evaluator.evaluate('not(100)'), 0.0)

		# Define logical OR
		self.evaluator.evaluate('def or(x y) if x then 1 else (if y then 1 else 0)')
		
		self.assertEqual(self.evaluator.evaluate('or(0, 0)'), 0.0)
		self.assertEqual(self.evaluator.evaluate('or(1, 0)'), 1.0)
		self.assertEqual(self.evaluator.evaluate('or(0, 5)'), 1.0)

	def test_for_loop_return_value(self):
		"""
		Test that the for-loop construct compiles and runs.
		Note: In this implementation, 'for' loops always return 0.0.
		Testing side effects (like printing) is hard, so we test strict execution.
		"""
		# Loop from 1 to 5. Body is just a calculation that is discarded.
		loop_code = 'for i = 1, i < 5, 1.0 in i * i'
		result = self.evaluator.evaluate(loop_code)
		self.assertEqual(result, 0.0)

	def test_nested_nested_calls(self):
		"""Test calling functions within functions within conditionals."""
		self.evaluator.evaluate('def add(a b) a + b')
		self.evaluator.evaluate('def small(x) if x < 10 then 1 else 0')
		
		# if (10+10 < 10) then 100 else 10+10
		# if (20 < 10) -> False -> 20
		code = '''
			def complex(x) 
				if small(x) 
				then 100 
				else add(x, x)
		'''
		self.evaluator.evaluate(code)
		
		self.assertEqual(self.evaluator.evaluate('complex(5)'), 100.0)
		self.assertEqual(self.evaluator.evaluate('complex(10)'), 20.0)

	def test_shadowing_args(self):
		"""Test that function arguments shadow global functions or other names correctly."""
		# 'a' is a function argument, 'b' is a function argument
		self.evaluator.evaluate('def test(a b) a + b')
		
		# Here we ensure LLVM doesn't get confused if we use variable names 
		# that might look like hex code or existing globals.
		self.assertEqual(self.evaluator.evaluate('test(10, 20)'), 30.0)

	def test_extern_putchard(self):
		"""
		Test the external function call 'putchard'.
		We verify it returns 0.0 (as defined in _add_builtins) and runs without crashing.
		"""
		# Note: This will actually print to your console during tests.
		self.assertEqual(self.evaluator.evaluate('putchard(65)'), 0.0)
	
	def test_basic_if(self):
		e = KaleidoscopeEvaluator()
		e.evaluate('def foo(a b) a * if a < b then a + 1 else b + 1')
		self.assertEqual(e.evaluate('foo(3, 4)'), 12)
		self.assertEqual(e.evaluate('foo(5, 4)'), 25)

	def test_nested_if(self):
		e = KaleidoscopeEvaluator()
		e.evaluate('''
			def foo(a b c)
				if a < b
					then if a < c then a * 2 else c * 2
					else b * 2''')
		self.assertEqual(e.evaluate('foo(1, 20, 300)'), 2)
		self.assertEqual(e.evaluate('foo(10, 2, 300)'), 4)
		self.assertEqual(e.evaluate('foo(100, 2000, 30)'), 60)

	def test_for(self):
		e = KaleidoscopeEvaluator()
		e.evaluate('''
			def foo(a b c)
				if a < b
					then for x = 1.0, x < b, c in x+a+c*b
					else c * 2''')
		self.assertEqual(e.evaluate('foo(1, 2, 3)'), 0)
		self.assertEqual(e.evaluate('foo(3, 2, 30)'), 60)

# --- Module: main ---
# TODO: make the function have 0 args
# TODO: make assign
if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	kalei.evaluate('def foo(x) for i = x, i < 5, 1.0 in i+1', print_llvm_dump=True, print_ast_dump=True)
	kalei.evaluate('foo(1)')

