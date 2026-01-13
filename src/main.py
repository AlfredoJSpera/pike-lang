import argparse
from evaluator import PikeEvaluator

code = """
10 + 5 * 2 < 100;
"""


def main(args):
	pike = PikeEvaluator()
	pike.evaluate(code, print_lark_dump=True, print_ast_dump=True)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="pike_compiler.py"
	)
	#parser.add_argument("code", help="Required unnamed arg")
	args = parser.parse_args()
	main(args)
