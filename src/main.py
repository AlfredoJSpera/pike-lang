import argparse
from pike.evaluator import PikeEvaluator

code = """
defunc hello(a: num) %num {ret a;}
!!(hello(1));
"""

def main(args):
	pike = PikeEvaluator()
	pike.evaluate(
		code, 
		print_lark_dump=False, 
		print_ast_dump=False,
		print_llvm_dump=True,
	)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="pike_compiler.py"
	)
	#parser.add_argument("code", help="Required unnamed arg")
	args = parser.parse_args()
	main(args)
