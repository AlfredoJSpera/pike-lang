from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from lark import Token, Transformer

# ===== Define base classes

class NodeAst:
	"""
	Base class for all AST nodes in the Pike language.
	This class serves as a parent for specific AST node implementations.
	"""
	pass

class TopLevel(NodeAst):
	"""
	Represents a top-level node in the AST that 
	exist outside of any function definition.
	"""
	pass

class StatementAst(TopLevel):
	"""
	Represents a statement node in the AST. 
	These nodes do NOT return any value.
	"""
	pass

class ExpressionAst(StatementAst):
	"""
	Represents an expression node in the AST.
	These nodes RETURN a value.
	"""
	pass

# ===== Enums

class PikeType(Enum):
	"""
	The supported types in Pike's type system.
	Note: 'void' is not supported directly in the grammar.
	"""
	NUM = "num"
	STR = "str"
	VOID = "void"

	def __repr__(self) -> str:
		return self.value

# ===== Data holders

@dataclass
class ParameterAst(NodeAst):
	"""Represents a parameter in a function definition."""
	name: str
	type_name: PikeType

@dataclass
class BodyAst(NodeAst):
	"""A list of statements inside a block."""
	statements: List[StatementAst]

# ===== Functions

@dataclass
class FunctionAst(TopLevel):
	"""Represents a function definition. Can omit the return value."""
	name: str
	parameters: List[ParameterAst]
	ret_type: Optional[PikeType]
	body: BodyAst

@dataclass
class ProgramAst(NodeAst):
	"""
	Root node of the AST representing the entire Pike program.
	Contains all function definitions, including the implicit 'main' 
	for top-level statements.
	"""
	functions: List[FunctionAst]

# ===== Expressions

@dataclass
class NumberValueAst(ExpressionAst):
	"""An expression that holds a number value."""
	value: float

@dataclass
class StringValueAst(ExpressionAst):
	"""An expression that holds a string value."""
	value: str

@dataclass
class VariableAst(ExpressionAst):
	"""An expression that holds the name of a variable."""
	name: str

@dataclass
class BinaryOperationAst(ExpressionAst):
	"""
	An expression for a binary operation.
	The grammar keeps a left precedence:
	(<, >) <- (+, -) <- (*, /) <- value/variable
	"""
	operator: str
	left: ExpressionAst
	right: ExpressionAst

@dataclass
class FunctionCallAst(ExpressionAst):
	"""An expression that calls a function and returns the result (if it has one)."""
	called_name: str
	args: List[ExpressionAst]

# ===== Statements

@dataclass
class AssignmentAst(StatementAst):
	"""An assignment statement."""
	variable_name: str
	value: ExpressionAst

@dataclass
class ReturnAst(StatementAst):
	"""
	A return statement used in a function definition. 
	Can be used without the expression.
	"""
	expression: Optional[ExpressionAst]

@dataclass
class PrintAst(StatementAst):
	"""A print statement that prints an expression (num or str)."""
	expression: ExpressionAst
	new_line: bool

@dataclass
class IfElseAst(StatementAst):
	"""An if/else statement. The else block is optional."""
	condition: ExpressionAst
	then_block: BodyAst
	else_block: Optional[BodyAst] = None

@dataclass
class ForLoopAst(StatementAst):
	"""
	A for statement.
	Note 1: The the starting and step values are expressions,
		so they can also be comparisons that evaluate to 1 or 0.
	Note 2: An infinite loop can be created by having a true
		unchanging expression in the condition.
	"""
	iterator: str
	start_val: NumberValueAst
	condition: ExpressionAst
	step: NumberValueAst
	body: BodyAst


# ===== Transformer

class PikeTransformer(Transformer):
	def start(self, items: List[NodeAst]):
		"""
		Processes a list of AST items, separating function definitions from statements.
		Statements not part of a function are grouped into a 'main' function.
		"""
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

	def top_level_stmt(self, items: List[TopLevel]):
		"""
		Handles a top-level statement/expression.
		"""
		return items[0]

	def function_def(self, items):
		"""
		Creates a function AST node using a list
		composed of lark.Token and NodeAst.
		"""
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
		"""
		Creates a function call AST node using a list
		composed of lark.Token and a list of Argument.
		"""
		if items[1] is not None:
			args = items[1]
		else:
			args = []

		return FunctionCallAst(
			called_name=str(items[0]), 
			args=args
		)

	def parameters(self, items: List[ParameterAst]):
		return items

	def args(self, items: List[ExpressionAst]):
		return items

	def par(self, items: List[Token]):
		return ParameterAst(
			name=str(items[0]), 
			type_name=PikeType(str(items[1])),
		)

	def body(self, items: List[StatementAst]):
		return items 

	def assignment(self, items):
		"""
		Creates an assignment AST using a list
		composed of a lark.Token and an Expression.
		"""
		return AssignmentAst(
			variable_name=str(items[0]), 
			value=items[1],
		)

	def return_stmt(self, items: List[ExpressionAst]):
		return ReturnAst(expression=items[0])

	def print_nl(self, items: List[ExpressionAst]):
		return PrintAst(
			expression=items[0], 
			new_line=True
		)

	def print_no_nl(self, items: List[ExpressionAst]):
		return PrintAst(
			expression=items[0], 
			new_line=False
		)

	def if_stmt(self, items):
		"""
		Creates an if/else AST using a list
		composed of an expression AST and two lists of statements.
		"""
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
		"""
		Creates a for AST using a list composed of
		a lark.Token, three expressions, and a list of statements.
		"""
		return ForLoopAst(
			iterator=str(items[0]),
			start_val=items[1],
			condition=items[2],
			step=items[3],
			body=BodyAst(statements=items[4])
		)

	def expr_stmt(self, items: List[ExpressionAst]):
		return items[0]

	# The binary operations take a list 
	# composed of two expressions (that can be values).
	def add(self, items): return BinaryOperationAst('+', items[0], items[1])
	def sub(self, items): return BinaryOperationAst('-', items[0], items[1])
	def mul(self, items): return BinaryOperationAst('*', items[0], items[1])
	def div(self, items): return BinaryOperationAst('/', items[0], items[1])
	def lt(self, items): return BinaryOperationAst('<', items[0], items[1])
	def gt(self, items): return BinaryOperationAst('>', items[0], items[1])

	def number(self, items: List[Token]):
		"""
		Constructs a number value AST from a list:
		[Token('NUMBER')]
		"""
		return NumberValueAst(float(items[0]))

	def string(self, items: List[Token]):
		"""
		Constructs a string value AST (and removes quotation marks) 
		from a list: [Token('ESCAPED_STRING')]
		"""
		no_qm = str(items[0])[1:-1]
		return StringValueAst(no_qm)

	def var_load(self, items: List[Token]):
		"""
		Constructs a variable reference AST from a list: 
		[Token('NAME')]
		"""
		return VariableAst(str(items[0]))