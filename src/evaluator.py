import pprint
from ast_nodes import PikeTransformer
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
		# print_llvm_dump: bool = False,
	):
		lark_tree = self.parser.parse(code)
		
		if print_lark_dump:
			print_boxed(
				f"Lark parse tree ({type(lark_tree)})",
				pretty_lark_tree(lark_tree)
			)
		
		parsed_ast = PikeTransformer.transform(lark_tree)
		
		if print_ast_dump:
			print_boxed(
				f"AST ({type(parsed_ast)})",
				pretty_ast(parsed_ast)
			)