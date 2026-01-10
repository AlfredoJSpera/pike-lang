from dataclasses import dataclass
import sys
from typing import List
from lark import Transformer, ast_utils, v_args

# --- Base class ---

class _Ast(ast_utils.Ast):
	pass

# --- Abstract base classes ---

class _Instruction(_Ast):
	pass

class _Statement(_Instruction):
	pass

class _Expression(_Ast):
	pass

# --- Terminal wrappers ---

@dataclass
class Name(_Ast):
	value: str   # NAME token

@dataclass
class Number(_Expression):
	value: float # FLOAT_NUMBER token

@dataclass
class String(_Expression):
	value: str   # STRING token

# --- Components ---

@dataclass
class Variable(_Expression):
	name: Name

# --- Containers ---

@dataclass
class Program(_Ast, ast_utils.AsList):
	instructions: List[_Instruction]

@dataclass
class Body(_Ast, ast_utils.AsList):
	statements: List[_Statement]

# --- Functions ---

@dataclass
class Function(_Instruction):
	name: Name
	body: Body

# --- Statements ---

@dataclass
class Assignment(_Statement):
	variable: Variable
	expression: _Expression

@dataclass
class IfStatement(_Statement):
	condition: _Expression
	body: Body

@dataclass
class PrintNl(_Statement):
	expression: _Expression


# --- Transformer ---

class ToAst(Transformer):
	def NAME(self, token):
		return str(token)
	
	def STRING(self, token):
		# Remove quotation marks
		return str(token)[1:-1]
	
	def FLOAT_NUMBER(self, token):
		return float(token)
	
	@v_args(inline=True)
	def start(self, x):
		return x

PikeTransformer = ast_utils.create_transformer(
	sys.modules[__name__],
	ToAst()
)