from dataclasses import dataclass
from typing import List, Optional
from lark import Transformer

# ===== Define base classes

class Node:
	pass

class TopLevel(Node):
	pass

class Statement(TopLevel):
	pass

class Expression(Statement):
	pass

# ===== Data holders

@dataclass
class Argument(Node):
	value: Expression

@dataclass
class Parameter(Node):
	name: str
	type_name: str

# ===== Expressions

@dataclass
class NumberValue(Expression):
	value: float

@dataclass
class StringValue(Expression):
	value: str

@dataclass
class Variable(Expression):
	name: str

@dataclass
class BinaryOperation(Expression):
	operator: str
	left: Expression
	right: Expression

@dataclass
class FunctionCall(Expression):
	called_name: str
	args: List[Argument]

# ===== Statements

@dataclass
class Assignment(Statement):
	name: str
	value: Expression

@dataclass
class Return(Statement):
	value: Optional[Expression]

@dataclass
class Print(Statement):
	expression: Expression
	new_line: bool

@dataclass
class Body(Node):
	statements: List[Statement]

@dataclass
class IfElse(Statement):
	condition: Expression
	then_block: Body
	else_block: Optional[Body] = None

@dataclass
class ForLoop(Statement):
	iterator: str
	start_val: Expression
	condition: Expression
	step: Expression
	body: Body

@dataclass
class Function(TopLevel):
	name: str
	parameters: List[Parameter]
	ret_type: str
	body: Body

@dataclass
class Program(Node):
	functions: List[Function]


# --- Transformer ---

class PikeTransformer(Transformer):
	def __init__(self):
		self.anon_counter = 0

	def start(self, items):
		functions = []

		for item in items:
			if isinstance(item, Function):
				functions.append(item)
			elif isinstance(item, Statement):
				self.anon_counter += 1
				name = f"_anon{self.anon_counter}"
				func = Function(
					name=name, 
					parameters=[], 
					ret_type="void", 
					body=Body(statements=[item]) 
				)
				functions.append(func)
		
		return Program(functions=functions)

	def top_level_stmt(self, items):
		return items[0]

	def function_def(self, items):
		name = str(items[0])
		parameters = items[1] if items[1] is not None else []
		ret_type = str(items[2]) if items[2] is not None else "void"
		body = Body(statements=items[3]) 

		return Function(name, parameters, ret_type, body)

	def function_call(self, items):
		name = str(items[0])
		args = items[1] if items[1] is not None else []

		return FunctionCall(name, args)

	def parameters(self, items):
		return items # returns list of Parameters

	def args(self, items):
		return items # returns list of Arguments

	def par(self, items):
		return Parameter(name=str(items[0]), type_name=str(items[1]))

	def body(self, items):
		return items # returns list of Stmt (can be empty list)

	# --- Statements ---
	def assignment(self, items):
		return Assignment(name=str(items[0]), value=items[1])

	def return_stmt(self, items):
		return Return(value=items[0])

	def print_nl(self, items):
		return Print(expression=items[0], new_line=True)

	def print_no_nl(self, items):
		return Print(expression=items[0], new_line=False)

	def if_stmt(self, items):
		cond = items[0]
		then_blk = Body(statements=items[1]) # Changed
		else_blk = Body(statements=items[2]) if items[2] is not None else None # Changed
		return IfElse(cond, then_blk, else_blk)

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
	def add(self, items): return BinaryOperation('+', items[0], items[1])
	def sub(self, items): return BinaryOperation('-', items[0], items[1])
	def mul(self, items): return BinaryOperation('*', items[0], items[1])
	def div(self, items): return BinaryOperation('/', items[0], items[1])
	def lt(self, items): return BinaryOperation('<', items[0], items[1])
	def gt(self, items): return BinaryOperation('>', items[0], items[1])

	def number(self, items):
		return NumberValue(float(items[0]))

	def string(self, items):
		# Remove quotes
		return StringValue(str(items[0])[1:-1])

	def var_load(self, items):
		return Variable(str(items[0]))