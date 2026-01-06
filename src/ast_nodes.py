class ASTNode(object):
	def dump(self, indent=0):
		raise NotImplementedError

class ExprAST(ASTNode): pass

class NumberExprAST(ExprAST):
	"""
	Represents a number.
	
	:example: 1.0
	>>> node = NumberExprAST(1.0)
	"""
	def __init__(self, val):
		"""
		:param val: The number.
		"""
		self.val = val
	
	def dump(self, indent=0):
		return f"{' ' * indent}{self.__class__.__name__}[{self.val}]"

class VariableExprAST(ExprAST):
	"""
	Represents a variable (only its name).

	:example: x
	>>> node = VariableExprAST("x")
	"""
	
	def __init__(self, name: str):
		"""
		:param name: The variable's name.
		:type name: str
		"""
		self.name = name
	
	def dump(self, indent=0):
		return f"{' ' * indent}{self.__class__.__name__}[{self.name}]"

class BinaryExprAST(ExprAST):
	"""
	Represents a binary expression.

	:example: x + 5
	>>> node = BinaryExprAST("+", VariableExprAST("a"), NumberExprAST(1.0))
	"""

	def __init__(self, op: str, lhs, rhs):
		"""
		:param op: The central operator.
		:param lhs: The left operand of the expression.
		:param rhs: The right operand of the expression.
		"""
		self.op = op
		self.lhs = lhs
		self.rhs = rhs
	
	def dump(self, indent=0):
		s = f"{' ' * indent}{self.__class__.__name__}[{self.op}]\n"
		s += self.lhs.dump(indent + 2) + '\n'
		s += self.rhs.dump(indent + 2)
		return s

class IfExprAST(ExprAST):
	"""
	Represents an if/then/else control flow.

	:example: if x < 10 then 1 else 0
	>>> condition = BinaryExprAST("<", VariableExprAST("x"), NumberExprAST(10.0))
	>>> node = IfExprAST(condition, NumberExprAST(1.0), NumberExprAST(0.0))
	"""

	def __init__(self, cond_expr, then_expr, else_expr):
		"""
		:param cond_expr: The "condition" expression that, if true, makes the flow continue to the "then" expression ("else" otherwise).
		:param then_expr: The "then" expression.
		:param else_expr: The "else" expression.
		"""
		self.cond_expr = cond_expr
		self.then_expr = then_expr
		self.else_expr = else_expr
	
	def dump(self, indent=0):
		prefix = ' ' * indent
		s = f"{prefix}{self.__class__.__name__}\n"
		s += f"{prefix} Condition:\n{self.cond_expr.dump(indent + 2)}\n"
		s += f"{prefix} Then:\n{self.then_expr.dump(indent + 2)}\n"
		s += f"{prefix} Else:\n{self.else_expr.dump(indent + 2)}"
		return s

class ForExprAST(ExprAST):
	"""
	Represents a for loop.

	:example: for i = 65, i < 79, 1.0 in i+1

	>>> id_n  = "i"
	>>> start = NumberExprAST(65.0)
	>>> end   = BinaryExprAST("<", "i", 79.0)
	>>> step  = NumberExprAST(1.0)
	>>> body  = BinaryExprAST("+", VariableExprAST("i"), NumberExprAST(1.0))
	>>> node  = ForExprAST(id_n, start, end, step, body)
	"""

	def __init__(self, id_name, start_expr, end_expr, step_expr, body):
		"""
		:param id_name: The loop's counter variable name.
		:param start_expr: The expression that determines the initial value of the loop counter.
		:param end_expr: The expression that, if true, ends the loop.
		:param step_expr: The expression that is added to the counter.
		:param body: The expression to execute in the loop.
		"""
		self.id_name = id_name
		self.start_expr = start_expr
		self.end_expr = end_expr
		self.step_expr = step_expr
		self.body = body
	
	def dump(self, indent=0):
		prefix = ' ' * indent
		s = f"{prefix}{self.__class__.__name__}[{self.id_name}]\n"
		s += f"{prefix} Start:\n{self.start_expr.dump(indent + 2)}\n"
		s += f"{prefix} End:\n{self.end_expr.dump(indent + 2)}\n"
		s += f"{prefix} Step:\n{self.step_expr.dump(indent + 2)}\n"
		s += f"{prefix} Body:\n{self.body.dump(indent + 2)}\n"
		return s

class CallExprAST(ExprAST):
	"""
	Represents the call to a function.

	:example: foo(a, 10.0)

	>>> callee = "foo"
	>>> args = [VariableExprAST("a"), NumberExprAST(1.0)]
	>>> node = CallExprAST(callee, args)
	"""

	def __init__(self, callee, args):
		"""
		:param callee: The name of the function to call.
		:param args: A list of arguments to pass to the function.
		"""
		self.callee = callee
		self.args = args
	
	def dump(self, indent=0):
		s = f"{' ' * indent}{self.__class__.__name__}[{self.callee}])\n"
		for arg in self.args:
			s += arg.dump(indent + 2) + '\n'
		return s[:-1]

class PrototypeAST(ASTNode):
	"""
	Represents a prototype of a function. Is a part of the FunctionAST.

	:example: def foo(x y)

	>>> node = PrototypeAST("foo", ["x", "y"])
	"""
	def __init__(self, name, argnames):
		"""
		:param name: The name of the function.
		:param argnames: A list of names of the arguments required.
		"""
		self.name = name
		self.argnames = argnames
	
	def dump(self, indent=0):
		return f"{' ' * indent}{self.__class__.__name__}[{', '.join(self.argnames)}]"

class FunctionAST(ASTNode):
	"""
	Represents a callable function.

	:example: def foo(x y) x + 1

	>>> proto = PrototypeAST("foo", ["x"])
    >>> body = BinaryExprAST("+", VariableExprAST("x"), NumberExprAST(1.0))
    >>> node = FunctionAST(proto, body)
	"""

	def __init__(self, proto, body):
		"""
		:param proto: The prototype (PrototypeAST) of the function.
		:param body: An expression for the body of the function.
		"""
		self.proto = proto
		"""e"""
		self.body = body
	
	_anonymous_function_counter = 0

	@classmethod
	def create_anonymous(cls, expr):
		"""Wraps a top-level expression in a unique function without parameters for immediate JIT execution."""
		cls._anonymous_function_counter += 1
		anon_prototype = PrototypeAST(f"_anon{cls._anonymous_function_counter}", [])
		return cls(anon_prototype, expr)

	def is_anonymous(self):
		return self.proto.name.startswith('_anon')
	
	def dump(self, indent=0):
		s = f"{' ' * indent}{self.__class__.__name__}[{self.proto.dump()}"
		if self.is_anonymous():
			s += f", anonymous, anonymous_counter={self._anonymous_function_counter}"
		else:
			s += ", stored"
		s += ']\n'
		s += self.body.dump(indent + 2) + '\n'
		return s