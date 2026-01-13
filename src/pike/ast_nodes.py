from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from lark import Transformer

# ===== Define base classes

class NodeAst:
	pass

class TopLevel(NodeAst):
	pass

class StatementAst(TopLevel):
	pass

class ExpressionAst(StatementAst):
	pass

# ===== Enums

class PikeType(Enum):
	NUM = "num"
	STR = "str"
	VOID = "void"

# ===== Data holders

@dataclass
class ArgumentAst(NodeAst):
	value: ExpressionAst

@dataclass
class ParameterAst(NodeAst):
	name: str
	type_name: PikeType

@dataclass
class BodyAst(NodeAst):
	statements: List[StatementAst]

# ===== Functions

@dataclass
class FunctionAst(TopLevel):
	name: str
	parameters: List[ParameterAst]
	ret_type: Optional[PikeType]
	body: BodyAst

	def is_anonymous(self):
		return self.name.startswith("_anon")

@dataclass
class ProgramAst(NodeAst):
	"""Root node of the AST containing a list of anonymous functions."""
	functions: List[FunctionAst]

# ===== Expressions

@dataclass
class NumberValueAst(ExpressionAst):
	value: float

@dataclass
class StringValueAst(ExpressionAst):
	value: str

@dataclass
class VariableAst(ExpressionAst):
	name: str

@dataclass
class BinaryOperationAst(ExpressionAst):
	operator: str
	left: ExpressionAst
	right: ExpressionAst

@dataclass
class FunctionCallAst(ExpressionAst):
	called_name: str
	args: List[ArgumentAst]

# ===== Statements

@dataclass
class AssignmentAst(StatementAst):
	variable_name: str
	value: ExpressionAst

@dataclass
class ReturnAst(StatementAst):
	expression: Optional[ExpressionAst]

@dataclass
class PrintAst(StatementAst):
	expression: ExpressionAst
	new_line: bool

@dataclass
class IfElseAst(StatementAst):
	condition: ExpressionAst
	then_block: BodyAst
	else_block: Optional[BodyAst] = None

@dataclass
class ForLoopAst(StatementAst):
	iterator: str
	start_val: ExpressionAst
	condition: ExpressionAst
	step: ExpressionAst
	body: BodyAst


# ===== Transformer

class PikeTransformer(Transformer):
	def __init__(self):
		self.anon_counter = 0

	def start(self, items):
		functions = []
		main_statements = []

		for item in items:
			if isinstance(item, FunctionAst):
				functions.append(item)
			elif isinstance(item, StatementAst):
				main_statements.append(item)
		
		if main_statements:
			functions.append(FunctionAst(
				name="main", 
				parameters=[], 
				ret_type=None, 
				body=BodyAst(statements=main_statements) 
			))
		
		return ProgramAst(functions)

	def top_level_stmt(self, items):
		return items[0]

	def function_def(self, items):
		if items[1] is not None:
			parameters = items[1]
		else:
			parameters = []
		
		if items[2] is not None:
			ret_type = PikeType.NUM
		else:
			ret_type = PikeType.VOID
		
		return FunctionAst(
			name=str(items[0]), 
			parameters=parameters, 
			ret_type=ret_type, 
			body=BodyAst(statements=items[3]),
		)

	def function_call(self, items):
		if items[1] is not None:
			args = items[1]
		else:
			args = []

		return FunctionCallAst(
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
		return ParameterAst(
			name=str(items[0]), 
			type_name=PikeType(str(items[1])),
		)

	def body(self, items):
		# Returns list of Statements
		return items 

	def assignment(self, items):
		return AssignmentAst(
			variable_name=str(items[0]), 
			value=items[1],
		)

	def return_stmt(self, items):
		return ReturnAst(expression=items[0])

	def print_nl(self, items):
		return PrintAst(
			expression=items[0], 
			new_line=True
		)

	def print_no_nl(self, items):
		return PrintAst(
			expression=items[0], 
			new_line=False
		)

	def if_stmt(self, items):
		if items[2] is not None:
			else_block = BodyAst(statements=items[2])
		else:
			else_block = None

		return IfElseAst(
			condition=items[0],
			then_block=BodyAst(statements=items[1]), 
			else_block=else_block,
		)

	def for_stmt(self, items):
		return ForLoopAst(
			iterator=str(items[0]),
			start_val=items[1],
			condition=items[2],
			step=items[3],
			body=BodyAst(statements=items[4])
		)

	def expr_stmt(self, items):
		return items[0]

	def add(self, items): return BinaryOperationAst('+', items[0], items[1])
	def sub(self, items): return BinaryOperationAst('-', items[0], items[1])
	def mul(self, items): return BinaryOperationAst('*', items[0], items[1])
	def div(self, items): return BinaryOperationAst('/', items[0], items[1])
	def lt(self, items): return BinaryOperationAst('<', items[0], items[1])
	def gt(self, items): return BinaryOperationAst('>', items[0], items[1])

	def number(self, items):
		return NumberValueAst(float(items[0]))

	def string(self, items):
		# Remove quotes
		return StringValueAst(str(items[0])[1:-1])

	def var_load(self, items):
		return VariableAst(str(items[0]))