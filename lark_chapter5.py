from ctypes import CFUNCTYPE, c_double
from lark import Lark, Transformer

import llvmlite.ir as ir
import llvmlite.binding as llvm

# --- 1. AST Classes ---

class ASTNode(object):
	def dump(self, indent=0):
		raise NotImplementedError

class ExprAST(ASTNode): pass

class NumberExprAST(ExprAST):
	def __init__(self, val):
		self.val = val
	def dump(self, indent=0):
		return '{0}{1}[{2}]'.format(' ' * indent, self.__class__.__name__, self.val)

class VariableExprAST(ExprAST):
	def __init__(self, name):
		self.name = name
	def dump(self, indent=0):
		return '{0}{1}[{2}]'.format(' ' * indent, self.__class__.__name__, self.name)

class BinaryExprAST(ExprAST):
	def __init__(self, op, lhs, rhs):
		self.op = op
		self.lhs = lhs
		self.rhs = rhs
	def dump(self, indent=0):
		s = '{0}{1}[{2}]\n'.format(' ' * indent, self.__class__.__name__, self.op)
		s += self.lhs.dump(indent + 2) + '\n'
		s += self.rhs.dump(indent + 2)
		return s

class IfExprAST(ExprAST):
	def __init__(self, cond_expr, then_expr, else_expr):
		self.cond_expr = cond_expr
		self.then_expr = then_expr
		self.else_expr = else_expr
	def dump(self, indent=0):
		prefix = ' ' * indent
		s = '{0}{1}\n'.format(prefix, self.__class__.__name__)
		s += '{0} Condition:\n{1}\n'.format(prefix, self.cond_expr.dump(indent + 2))
		s += '{0} Then:\n{1}\n'.format(prefix, self.then_expr.dump(indent + 2))
		s += '{0} Else:\n{1}'.format(prefix, self.else_expr.dump(indent + 2))
		return s

class ForExprAST(ExprAST):
	def __init__(self, id_name, start_expr, end_expr, step_expr, body):
		self.id_name = id_name
		self.start_expr = start_expr
		self.end_expr = end_expr
		self.step_expr = step_expr
		self.body = body
	def dump(self, indent=0):
		prefix = ' ' * indent
		s = '{0}{1}\n'.format(prefix, self.__class__.__name__)
		s += '{0} Start [{1}]:\n{2}\n'.format(prefix, self.id_name, self.start_expr.dump(indent + 2))
		s += '{0} End:\n{1}\n'.format(prefix, self.end_expr.dump(indent + 2))
		s += '{0} Step:\n{1}\n'.format(prefix, self.step_expr.dump(indent + 2))
		s += '{0} Body:\n{1}\n'.format(prefix, self.body.dump(indent + 2))
		return s

class CallExprAST(ExprAST):
	def __init__(self, callee, args):
		self.callee = callee
		self.args = args
	def dump(self, indent=0):
		s = '{0}{1}[{2}]\n'.format(' ' * indent, self.__class__.__name__, self.callee)
		for arg in self.args:
			s += arg.dump(indent + 2) + '\n'
		return s[:-1]

class PrototypeAST(ASTNode):
	def __init__(self, name, argnames):
		self.name = name
		self.argnames = argnames
	def dump(self, indent=0):
		return '{0}{1}[{2}]'.format(' ' * indent, self.__class__.__name__, ', '.join(self.argnames))

class FunctionAST(ASTNode):
	def __init__(self, proto, body):
		self.proto = proto
		self.body = body
	
	_anonymous_function_counter = 0

	@classmethod
	def create_anonymous(cls, expr):
		cls._anonymous_function_counter += 1
		return cls(
			PrototypeAST('_anon{0}'.format(cls._anonymous_function_counter), []),
			expr)

	def is_anonymous(self):
		return self.proto.name.startswith('_anon')
	
	def dump(self, indent=0):
		s = '{0}{1}[{2}]\n'.format(' ' * indent, self.__class__.__name__, self.proto.dump())
		s += self.body.dump(indent + 2) + '\n'
		return s

# --- 2. Lark Grammar and Transformer ---

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


# --- 3. Code Generator ---

class CodegenError(Exception): pass

class LLVMCodeGenerator(object):
	def __init__(self):
		self.module = ir.Module()
		self.builder = None
		self.func_symtab = {}

	def generate_code(self, node):
		return self._codegen(node)

	def _codegen(self, node):
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)

	def _codegen_NumberExprAST(self, node):
		return ir.Constant(ir.DoubleType(), float(node.val))

	def _codegen_VariableExprAST(self, node):
		return self.func_symtab[node.name]

	def _codegen_BinaryExprAST(self, node):
		lhs = self._codegen(node.lhs)
		rhs = self._codegen(node.rhs)

		if self.builder is None: raise CodegenError('Builder is not initialized')

		if node.op == '+': return self.builder.fadd(lhs, rhs, 'addtmp')
		elif node.op == '-': return self.builder.fsub(lhs, rhs, 'subtmp')
		elif node.op == '*': return self.builder.fmul(lhs, rhs, 'multmp')
		elif node.op == '<':
			cmp = self.builder.fcmp_unordered('<', lhs, rhs, 'cmptmp')
			return self.builder.uitofp(cmp, ir.DoubleType(), 'booltmp')
		else: raise CodegenError('Unknown binary operator', node.op)

	def _codegen_IfExprAST(self, node):
		cond_val = self._codegen(node.cond_expr)
		if self.builder is None: raise CodegenError('Builder is not initialized')
		
		cmp = self.builder.fcmp_ordered('!=', cond_val, ir.Constant(ir.DoubleType(), 0.0))

		then_bb = self.builder.function.append_basic_block('then')
		else_bb = ir.Block(self.builder.function, 'else')
		merge_bb = ir.Block(self.builder.function, 'ifcont')
		self.builder.cbranch(cmp, then_bb, else_bb)

		self.builder.position_at_start(then_bb)
		then_val = self._codegen(node.then_expr)
		self.builder.branch(merge_bb)
		then_bb = self.builder.block

		self.builder.function.basic_blocks.append(else_bb)
		self.builder.position_at_start(else_bb)
		else_val = self._codegen(node.else_expr)
		self.builder.branch(merge_bb)

		self.builder.function.basic_blocks.append(merge_bb)
		self.builder.position_at_start(merge_bb)
		phi = self.builder.phi(ir.DoubleType(), 'iftmp')
		phi.add_incoming(then_val, then_bb)
		phi.add_incoming(else_val, else_bb)
		return phi

	def _codegen_ForExprAST(self, node):
		start_val = self._codegen(node.start_expr)
		if self.builder is None: raise CodegenError('Builder is not initialized')
		
		preheader_bb = self.builder.block
		loop_bb = self.builder.function.append_basic_block('loop')

		self.builder.branch(loop_bb)
		self.builder.position_at_start(loop_bb)

		phi = self.builder.phi(ir.DoubleType(), node.id_name)
		phi.add_incoming(start_val, preheader_bb)

		oldval = self.func_symtab.get(node.id_name)
		self.func_symtab[node.id_name] = phi

		body_val = self._codegen(node.body)

		if node.step_expr is None: stepval = ir.Constant(ir.DoubleType(), 1.0)
		else: stepval = self._codegen(node.step_expr)
		
		nextvar = self.builder.fadd(phi, stepval, 'nextvar')
		endcond = self._codegen(node.end_expr)
		cmp = self.builder.fcmp_ordered('!=', endcond, ir.Constant(ir.DoubleType(), 0.0), 'loopcond')

		loop_end_bb = self.builder.block
		after_bb = self.builder.function.append_basic_block('afterloop')
		self.builder.cbranch(cmp, loop_bb, after_bb)
		self.builder.position_at_start(after_bb)
		phi.add_incoming(nextvar, loop_end_bb)

		if oldval is None: del self.func_symtab[node.id_name]
		else: self.func_symtab[node.id_name] = oldval

		return ir.Constant(ir.DoubleType(), 0.0)

	def _codegen_CallExprAST(self, node):
		callee_func = self.module.globals.get(node.callee, None)
		if callee_func is None or not isinstance(callee_func, ir.Function):
			raise CodegenError('Call to unknown function', node.callee)
		if len(callee_func.args) != len(node.args):
			raise CodegenError('Call argument length mismatch', node.callee)
		call_args = [self._codegen(arg) for arg in node.args]
		
		if self.builder is None: raise CodegenError('Builder is not initialized')
		
		return self.builder.call(callee_func, call_args, 'calltmp')

	def _codegen_PrototypeAST(self, node):
		funcname = node.name
		func_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()] * len(node.argnames))

		if funcname in self.module.globals:
			existing_func = self.module.globals.get(funcname)
			if not isinstance(existing_func, ir.Function):
				raise CodegenError('Function/Global name collision', funcname)
			if not existing_func.is_declaration:
				raise CodegenError('Redifinition of {0}'.format(funcname))
			if len(existing_func.function_type.args) != len(func_ty.args):
				raise CodegenError('Redifinition with different number of arguments')
			func = self.module.globals[funcname]
		else:
			func = ir.Function(self.module, func_ty, funcname)
		for i, arg in enumerate(func.args):
			arg.name = node.argnames[i]
			self.func_symtab[arg.name] = arg
		return func

	def _codegen_FunctionAST(self, node):
		self.func_symtab = {}
		func = self._codegen(node.proto)
		bb_entry = func.append_basic_block('entry')
		self.builder = ir.IRBuilder(bb_entry)
		retval = self._codegen(node.body)
		self.builder.ret(retval)
		return func


# --- 4. Evaluator ---

class KaleidoscopeEvaluator(object):
	def __init__(self):
		llvm.initialize()
		llvm.initialize_native_target()
		llvm.initialize_native_asmprinter()

		self.codegen = LLVMCodeGenerator()
		self._add_builtins(self.codegen.module)
		self.target = llvm.Target.from_default_triple()

		# Initialize Lark
		self.parser = Lark(grammar, parser='lalr', transformer=KaleidoscopeTransformer())

	def evaluate(self, codestr, optimize=True, llvmdump=False):
		"""
		Parse and evaluate the code.
		"""
		try:
			# Parsing with Lark: Return the AST object directly thanks to the Transformer
			ast = self.parser.parse(codestr)
		except Exception as e:
			print(f"Error parsing code: {e}")
			return None

		self.codegen.generate_code(ast)

		if llvmdump:
			print('======== Unoptimized LLVM IR')
			print(str(self.codegen.module))

		if not (isinstance(ast, FunctionAST) and ast.is_anonymous()):
			return None

		llvmmod = llvm.parse_assembly(str(self.codegen.module))

		if optimize:
			pmb = llvm.create_pass_manager_builder()
			pmb.opt_level = 2
			pm = llvm.create_module_pass_manager()
			pmb.populate(pm)
			pm.run(llvmmod)
			if llvmdump:
				print('======== Optimized LLVM IR')
				print(str(llvmmod))

		target_machine = self.target.create_target_machine()
		with llvm.create_mcjit_compiler(llvmmod, target_machine) as ee:
			ee.finalize_object()
			fptr = CFUNCTYPE(c_double)(ee.get_function_address(ast.proto.name))
			result = fptr()
			return result

	def _add_builtins(self, module):
		putchar_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(32)])
		putchar = ir.Function(module, putchar_ty, 'putchar')
		putchard_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()])
		putchard = ir.Function(module, putchard_ty, 'putchard')
		irbuilder = ir.IRBuilder(putchard.append_basic_block('entry'))
		ival = irbuilder.fptoui(putchard.args[0], ir.IntType(32), 'intcast')
		irbuilder.call(putchar, [ival])
		irbuilder.ret(ir.Constant(ir.DoubleType(), 0))


# --- 5. Unit Tests ---
import unittest

class TestEvaluator(unittest.TestCase):
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

if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	kalei.evaluate('def foo(a b) for x = 65, x < a, b in putchard(x)')

	# We call these for their side effect of printing to stdout, so don't care
	# about the return value.
	kalei.evaluate('foo(79, 1)')
	kalei.evaluate('putchard(10)')