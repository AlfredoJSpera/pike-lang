from ast_nodes import PikeTransformer, Program
from codegen import LLVMCodeGenerator
from grammar import PIKE_GRAMMAR
import llvmlite.binding as llvm
from lark import Lark
from utils import *

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
		#optimize_llvm: bool = True,
		print_lark_dump: bool = False,
		print_ast_dump: bool = False,
		print_llvm_dump: bool = False,
	):
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
		
		try:
			parsed_ast: Program = PikeTransformer().transform(lark_tree)
		except Exception as e:
			print_error("Error parsing to AST:")
			raise e
		
		if print_ast_dump:
			print_boxed(
				f"AST ({type(parsed_ast)})",
				pretty_ast(parsed_ast)
			)
		
		try:
			self.llvm_code_generator.generate_code(parsed_ast)
		except Exception as e:
			print_error("Error generating LLVM IR:")
			raise e

		if print_llvm_dump:
			unoptimized = str(self.llvm_code_generator.module)
			print_boxed(f"Unoptimized LLVM IR: '{code}'", unoptimized) 