from codegen import LLVMCodeGenerator
import llvmlite.binding as llvm
from lark import Lark
from ctypes import CFUNCTYPE, c_double
from grammar import KaleidoscopeTransformer, grammar
from ast_nodes import *
import llvmlite.ir as ir
from utils import print_boxed

class KaleidoscopeEvaluator(object):
	"""Responsible for evaluating expressions and statements in the Kaleidoscope language."""

	def __init__(self):
		# Initialize llvmlite
		llvm.initialize()
		llvm.initialize_native_target()
		llvm.initialize_native_asmprinter()

		# Initialize the llvm code generation an evaluation
		self.llvm_code_generator = LLVMCodeGenerator()
		self._add_builtins(self.llvm_code_generator.module)
		self.target = llvm.Target.from_default_triple()

		# Initialize the Lark parser
		self.parser = Lark(grammar, parser="lalr", transformer=KaleidoscopeTransformer())

	def evaluate(self, 
			code_string: str, 
			optimize_llvm: bool = True, 
			print_ast_dump: bool = False,
			print_llvm_dump: bool = False,
		):
		"""
		Parse and evaluate the code.
		
		:param code_string: The code to evaluate.
		:type code_string: str
		
		:param optimize_llvm: Optimize the generated llvm code.
		:type optimize_llvm: bool

		:param print_ast_dump: AST debug flag.
		:type print_ast_dump: bool

		:param print_llvm_dump: LLVM debug flag.
		:type print_llvm_dump: bool
		"""
		
		# Parse the code string with Lark to return an AST
		try:
			parsed_ast = self.parser.parse(code_string)
		except Exception as e:
			print(f"Error parsing code: {e}")
			exit(1)
		
		if print_ast_dump:
			dump = parsed_ast.dump() # type: ignore
			print_boxed(f"AST Tree Dump: '{code_string}'", dump) 

		# Generate the llvm code
		try:
			self.llvm_code_generator.generate_code(parsed_ast)
		except Exception as e:
			print(f"Error generating llvm: {e}")
			exit(1)

		if print_llvm_dump:
			unoptimized = str(self.llvm_code_generator.module)
			print_boxed(f"Unoptimized LLVM IR: '{code_string}'", unoptimized) 

		# If the AST is a function definition (not anonymous), store it and do not execute it
		# Else, continue with the execution
		if not (isinstance(parsed_ast, FunctionAST) and parsed_ast.is_anonymous()):
			return None

		# Convert the LLVM IR string into a binary-like module and store it in a reference
		module_ref = llvm.parse_assembly(str(self.llvm_code_generator.module))

		# Optimize the LLVM IR
		if optimize_llvm:
			pm_builder = llvm.create_pass_manager_builder()
			pm_builder.opt_level = 2
			pm = llvm.create_module_pass_manager()
			pm_builder.populate(pm)
			pm.run(module_ref)

			if print_llvm_dump:
				optimized = str(module_ref)
				print_boxed(f"Optimized LLVM IR: '{code_string}'", optimized) 

		# Select the right set of machine code instructions
		target_machine = self.target.create_target_machine()

		# Compile the LLVM IR into machine code with a JIT compiler
		with llvm.create_mcjit_compiler(module_ref, target_machine) as jit_engine:
			# Resolve all memory addresses and "bake" the binary
			jit_engine.finalize_object()
			
			# Locate the compiled function's address in memory
			func_name = parsed_ast.prototype.name
			func_address = jit_engine.get_function_address(func_name)

			# Wrap the memory address as a Python-callable function (returning a double)
			native_func = CFUNCTYPE(c_double)(func_address)
			
			# Execute the function and return the result
			return native_func()

	def _add_builtins(self, module):
		"""Register external C functions and define helper functions in the LLVM module."""
		# int putchar(int)
		int32 = ir.IntType(32)
		putchar_signature = ir.FunctionType(int32, [int32])
		putchar = ir.Function(module, putchar_signature, 'putchar')

		# double putchard(double)
		double = ir.DoubleType()
		putchard_signature = ir.FunctionType(double, [double])
		putchard = ir.Function(module, putchard_signature, 'putchard')

		# Implement 'putchard' logic
		entry_block = putchard.append_basic_block('entry')
		builder = ir.IRBuilder(entry_block)
		
		# Convert input double to int32 so putchar can consume it
		char_value = builder.fptoui(putchard.args[0], int32, name='intcast')
		
		# Call the actual C putchar
		builder.call(putchar, [char_value])
		
		# Kaleidoscope functions must return a value; return 0.0 by default
		builder.ret(ir.Constant(double, 0.0))