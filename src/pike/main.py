import argparse
from pike.evaluator import PikeEvaluator

code = """
!!("--- Counting to 4 ---");
for (i, 0; i < 5; 1) {
    !("Number: ");
    !!(i);
}
"""

def main(args):
	pike = PikeEvaluator()
	pike.evaluate(
		code, 
		print_lark_dump=False, 
		print_ast_dump=False,
		print_llvm_dump=False,
	)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="pike_compiler.py"
	)
	#parser.add_argument("code", help="Required unnamed arg")
	args = parser.parse_args()
	main(args)
