class ASTNode(object):
	"""A node that defines a structure."""

	def dump(self, prefix="", is_last=True, is_root=True):
		"""Print the AST structure recursively."""
		# Identify Attributes and Children
		attrs = []
		children = []

		for key, value in vars(self).items():
			if isinstance(value, list):
				# Flatten lists of nodes into the children queue
				if any(isinstance(item, ASTNode) for item in value):
					for item in value:
						children.append(item)
				else:
					attrs.append(f"{key}={value}")
			elif isinstance(value, ASTNode):
				children.append(value)
			else:
				attrs.append(str(value))

		# Build the current line
		# Use corner if it's the last child, otherwise junction
		connector = "" if is_root else ("└── " if is_last else "├── ")
		header = f"{prefix}{connector}{self.__class__.__name__}[{', '.join(attrs)}]"
		
		lines = [header]

		# Handle recursion for children
		# New prefix for children: add a pipe if there are more siblings to follow
		new_prefix = prefix if is_root else (prefix + ("    " if is_last else "│   "))
		
		for i, child in enumerate(children):
			last_child = (i == len(children) - 1)
			lines.append(child.dump(new_prefix, last_child, is_root=False))

		return "\n".join(lines)

class ExprAST(ASTNode): 
	"""A node that defines logic that results in a value."""
	pass


class NumberExprAST(ExprAST):
	def __init__(self, val: float):
		"""
		An expression node that represents a number.
		
		Args:
			val (float): The number.
		
		Example:
			>>> # 1
			>>> node = NumberExprAST(1.0)
		"""
		self.val = val


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
	def __init__(self, op: str, lhs, rhs):
		"""
		An expression node that represents a binary expression.
		
		Args:
			op : The central operator.
			lhs: The left operand of the expression.
			rhs: The right operand of the expression.
		
		Example:
			>>> # x + 5
			>>> node = BinaryExprAST("+", VariableExprAST("a"), NumberExprAST(5.0))
		"""
		self.op = op
		self.lhs = lhs
		self.rhs = rhs


class IfExprAST(ExprAST):
	def __init__(self, cond_expr, then_expr, else_expr):
		"""
		An expression node that represents an if/then/else control flow.
		
		Args:
			cond_expr: The "condition" expression. If true, makes the flow continue to the "then" expression ("else" otherwise).
			then_expr: The "then" expression.
			else_expr: The "else" expression.
		
		Example:
			>>> # if x < 10 then 1 else 0
			>>> condition = BinaryExprAST("<", VariableExprAST("x"), NumberExprAST(10.0))
			>>> node = IfExprAST(condition, NumberExprAST(1.0), NumberExprAST(0.0))
		"""
		self.cond_expr = cond_expr
		self.then_expr = then_expr
		self.else_expr = else_expr


class ForExprAST(ExprAST):
	def __init__(self, id_name, start_expr, end_expr, step_expr, body):
		"""
		An expression node that represents a for loop.
		
		Args:
			id_name   : The loop's counter variable name.
			start_expr: The expression that determines the initial value of the loop counter.
			end_expr  : The expression that, if true, ends the loop.
			step_expr : The expression that is added to the counter.
			body      : The expression to execute in the loop.
		
		Example:
			>>> # for i = 65, i < 79, 1.0 in i+1
			>>> id_n  = "i"
			>>> start = NumberExprAST(65.0)
			>>> end   = BinaryExprAST("<", "i", 79.0)
			>>> step  = NumberExprAST(1.0)
			>>> body  = BinaryExprAST("+", VariableExprAST("i"), NumberExprAST(1.0))
			>>> node  = ForExprAST(id_n, start, end, step, body)
		"""
		self.id_name = id_name
		self.start_expr = start_expr
		self.end_expr = end_expr
		self.step_expr = step_expr
		self.body = body


class CallExprAST(ExprAST):
	def __init__(self, callee, args):
		"""
		An expression node that represents a call to a function.
		
		Args:
			callee: The name of the called function.
			args  : A list of arguments passed in the call.
		
		Example:
			>>> # foo(a, 10)
			>>> callee = "foo"
			>>> args = [VariableExprAST("a"), NumberExprAST(1.0)]
			>>> node = CallExprAST(callee, args)
		"""
		self.callee = callee
		self.args = args


class PrototypeAST(ASTNode):
	def __init__(self, name, argnames):
		"""
		A node that represents a prototype of a function. 
		Is a part of the FunctionAST node.
		
		Args:
			name: The name of the function.
			argnames: A list of names of the arguments required.
		
		Example:
			>>> # def foo(x y)
			>>> node = PrototypeAST("foo", ["x", "y"])
		"""
		self.name = name
		self.argnames = argnames


class FunctionAST(ASTNode):
	def __init__(self, proto, body):
		"""
		A node that represents a callable function.
		Can also create an anonymous function.
		
		Args:
			proto (PrototypeAST): The prototype of the function.
			body: An expression for the body of the function.
		
		Example:
			>>> # def foo(x y) x + 1
			>>> proto = PrototypeAST("foo", ["x"])
			>>> body = BinaryExprAST("+", VariableExprAST("x"), NumberExprAST(1.0))
			>>> node = FunctionAST(proto, body)
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