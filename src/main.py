import argparse
#import pretty_errors
from evaluator import PikeEvaluator

valid_code = """
x := 10.5;

defunc myFunc() {
    !!("I am inside a function");
    if (x) {
        !!("I am inside an if");
    }
}

if (x) {
    !!("Top level if");
}
"""

invalid_code = """
if (x) {
    defunc nestedFunc() { } 
}
"""


def main(args):
	pike = PikeEvaluator()
	pike.evaluate(valid_code, print_lark_dump=True, print_ast_dump=True)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="pike_compiler.py"
	)
	#parser.add_argument("code", help="Required unnamed arg")
	args = parser.parse_args()
	main(args)
