import ctypes
import llvmlite.binding as llvm
from lark import Lark
from pike.ast_nodes import PikeTransformer, ProgramAst, FunctionAst
from pike.codegen import LLVMCodeGenerator
from pike.grammar import PIKE_GRAMMAR
from pike.utils import *

class ParsingException(Exception): pass

class PikeEvaluator():
	def __init__(self):
		# Initialize llvmlite
		llvm.initialize_native_target()
		llvm.initialize_native_asmprinter()
		self.llvm_code_generator = LLVMCodeGenerator()
		self.target = llvm.Target.from_default_triple()
		
		# Initialize the lark parser
		self.parser = Lark(
			PIKE_GRAMMAR, 
			parser="lalr",
			start="start",
		)

	def evaluate(
		self, 
		code: str, 
		optimize_llvm: bool = True,
		print_lark_dump: bool = False,
		print_ast_dump: bool = False,
		print_llvm_dump: bool = False,
	):
		# ==========================================
		# PARSE GRAMMAR
		# ==========================================
		try:
			lark_tree = self.parser.parse(code)
		except Exception as e:
			print_error("Error parsing to lark tree:")
			raise e
		
		if print_lark_dump:
			print_boxed(
				f"Lark parse tree ({type(lark_tree)})",
				pretty_lark_tree(lark_tree)
			)

		# ==========================================
		# PARSE AST
		# ==========================================
		try:
			parsed_ast: ProgramAst = PikeTransformer().transform(lark_tree)
		except Exception as e:
			print_error("Error parsing to AST:")
			raise e
		
		if print_ast_dump:
			print_boxed(
				f"AST ({type(parsed_ast)})",
				pretty_ast(parsed_ast)
			)
		
		# ==========================================
		# GENERATE LLVM
		# ==========================================
		try:
			self.llvm_code_generator.generate_code(parsed_ast)
		except Exception as e:
			print_error("Error generating LLVM IR:")
			raise e

		unoptimized = self.llvm_code_generator.get_ir()
		
		if print_llvm_dump:
			print_boxed("Unoptimized LLVM IR:", unoptimized)
		
		# ==========================================
		# EXECUTE LLVM IR 
		# ==========================================
		try:
			# 1. Parse the IR string into a Binding Module
			# This is different from the ir.Module used in codegen
			mod = llvm.parse_assembly(unoptimized)
			mod.verify()
			
			target_machine = self.target.create_target_machine()
			
			if optimize_llvm:
				pto = llvm.create_pipeline_tuning_options(speed_level=2)
				pass_builder = llvm.create_pass_builder(target_machine, pto)
				pass_manager = pass_builder.getModulePassManager()
				
				# Run optimization passes on the module in-place
				pass_manager.run(mod, pass_builder)

				# Optional: print optimized IR if dumping is enabled
				if print_llvm_dump:
					print_boxed("Optimized LLVM IR:", str(mod))
			
			# 2. Create the JIT Execution Engine
			# We use the target machine initialized in __init__
			engine = llvm.create_mcjit_compiler(mod, target_machine)
			
			# 3. Finalize the object code
			# This maps the IR to executable memory addresses
			engine.finalize_object()
			engine.run_static_constructors()

			# 4. Look up the 'main' function
			# The transformer wraps top-level code in a function named 'main'
			func_ptr = engine.get_function_address("main")
			
			if not func_ptr:
				raise Exception("Entry function 'main' not found in generated code.")

			# 5. Execute using ctypes
			# Define the C function prototype: void main()
			c_func = ctypes.CFUNCTYPE(None)(func_ptr)
			
			# Call the function
			c_func()

		except Exception as e:
			print_error(f"Error during execution: {e}")
			raise e