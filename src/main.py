import argparse
import os
import sys
from pike.evaluator import PikeEvaluator
from pike.utils import print_error

def main(args):
	source_code = get_source_code(args.file, args.code)

	pike = PikeEvaluator()
	pike.evaluate(
		source_code, 
		optimize_llvm=not args.no_opt,
		print_lark_dump=args.lark,
		print_ast_dump=args.ast,
		print_llvm_dump=args.llvm,
	)

def get_source_code(file, code_string):
	source_code = """
	defunc hello(a: num) %num {ret a;}
	!!(hello(1));
	"""

	if file:
		if not os.path.exists(file):
			print_error(f"Error: File '{file}' not found.")
			sys.exit(1)
		
		with open(file, 'r', encoding='utf-8') as f:
			source_code = f.read()
	elif code_string:
		source_code = code_string
	
	return source_code

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="Compiler and Evaluator for the Pike language.",
		prog="pike_compiler.py"
	)

	group = parser.add_mutually_exclusive_group()
	group.add_argument(
		"-f", "--file", 
		help="Path to a .pike source file to execute"
	)
	group.add_argument(
		"-c", "--code", 
		help="Raw code string to execute directly from CLI (NOTE: for printing, !! does not work, but ! does)"
	)

	# Debug / Output flags
	parser.add_argument(
		"--lark", 
		action="store_true", 
		help="Print the Lark parse tree"
	)
	parser.add_argument(
		"--ast", 
		action="store_true", 
		help="Print the Abstract Syntax Tree (AST)"
	)
	parser.add_argument(
		"--llvm", 
		action="store_true", 
		help="Print the generated LLVM IR (both unoptimized and optimized)"
	)
	parser.add_argument(
		"--no-opt", 
		action="store_true", 
		help="Disable LLVM level 2 optimizations"
	)
	
	args = parser.parse_args()
	main(args)