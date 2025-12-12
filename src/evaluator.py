from codegen import LLVMCodeGenerator
import llvmlite.binding as llvm
from lark import Lark
from ctypes import CFUNCTYPE, c_double
from grammar import KaleidoscopeTransformer, grammar
from ast_nodes import *
import llvmlite.ir as ir

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