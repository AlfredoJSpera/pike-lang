from dataclasses import dataclass
from enum import Enum
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

# ===== Enums

class PikeType(Enum):
	NUM = "num"
	STR = "str"

# ===== Data holders

@dataclass
class Argument(Node):
	value: Expression

@dataclass
class Parameter(Node):
	name: str
	type_name: PikeType

@dataclass
class Body(Node):
	statements: List[Statement]

# ===== Functions

@dataclass
class Function(TopLevel):
	name: str
	parameters: List[Parameter]
	ret_type: Optional[PikeType]
	body: Body

	def is_anonymous(self):
		return self.name.startswith("_anon")

@dataclass
class Program(Node):
	"""Root node for anonymous functions."""
	functions: List[Function]

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
	variable_name: str
	value: Expression

@dataclass
class Return(Statement):
	expression: Optional[Expression]

@dataclass
class Print(Statement):
	expression: Expression
	new_line: bool

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


# ===== Transformer

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
					ret_type=None, 
					body=Body(statements=[item]) 
				)
				functions.append(func)
		
		return Program(functions)

	def top_level_stmt(self, items):
		return items[0]

	def function_def(self, items):
		if items[1] is not None:
			parameters = items[1]
		else:
			parameters = []
		
		if items[2] is not None:
			ret_type = PikeType(str(items[2]))
		else:
			ret_type = None
		
		return Function(
			name=str(items[0]), 
			parameters=parameters, 
			ret_type=ret_type, 
			body=Body(statements=items[3]),
		)

	def function_call(self, items):
		if items[1] is not None:
			args = items[1]
		else:
			args = []

		return FunctionCall(
			called_name=str(items[0]), 
			args=args
		)

	def parameters(self, items):
		# Returns list of Parameters
		return items

	def args(self, items):
		# Returns list of Arguments
		return items

	def par(self, items):
		return Parameter(
			name=str(items[0]), 
			type_name=PikeType(str(items[1])),
		)

	def body(self, items):
		# Returns list of Statements
		return items 

	def assignment(self, items):
		return Assignment(
			variable_name=str(items[0]), 
			value=items[1],
		)

	def return_stmt(self, items):
		return Return(expression=items[0])

	def print_nl(self, items):
		return Print(
			expression=items[0], 
			new_line=True
		)

	def print_no_nl(self, items):
		return Print(
			expression=items[0], 
			new_line=False
		)

	def if_stmt(self, items):
		if items[2] is not None:
			else_block = Body(statements=items[2])
		else:
			else_block = None

		return IfElse(
			condition=items[0],
			then_block=Body(statements=items[1]), 
			else_block=else_block,
		)

	def for_stmt(self, items):
		return ForLoop(
			iterator=str(items[0]),
			start_val=items[1],
			condition=items[2],
			step=items[3],
			body=Body(statements=items[4])
		)

	def expr_stmt(self, items):
		return items[0]

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