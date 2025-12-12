from ast_nodes import *
from lark import Transformer

# Grammar in EBNF format for Lark.
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
	Converts the Lark tree (ParseTree) directly into the original 
	AST classes (NumberExprAST, BinaryExprAST, etc.).
	"""
	
	def number(self, items):
		return NumberExprAST(float(items[0]))

	def variable(self, items):
		return VariableExprAST(str(items[0]))

	def call_expr(self, items):
		name = str(items[0])
		# items[1:] arguments (expressions)
		args = items[1:]
		return CallExprAST(name, args)

	def if_expr(self, items):
		return IfExprAST(items[0], items[1], items[2])

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
		return self._binary_op(items)

	def add_expr(self, items):
		return self._binary_op(items)
	
	def term(self, items):
		return self._binary_op(items)

	def prototype(self, items):
		name = str(items[0])
		argnames = [str(x) for x in items[1:]]
		return PrototypeAST(name, argnames)

	def definition(self, items):
		return FunctionAST(items[0], items[1])

	def external(self, items):
		return items[0] # Returns PrototypeAST

	def expression_top(self, items):
		return FunctionAST.create_anonymous(items[0])