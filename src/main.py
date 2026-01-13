import argparse
#import pretty_errors
from evaluator import PikeEvaluator

valid_code = """
defunc greeter() {
    !!("Hello"); # Print with NL
}

# Assignment
max_val := 10;
1+1;

# Function with typed arguments and return type
defunc add_numbers(a: num, b: num) %num {
	!!("printing");
    ret a + b;
}

max_example := 50 +1;

# For loop
for (x, 0; x < max_val; 1) { 
    if (x < 5) {
		greeter();
        !("Small: "); # Print without NL
        !!(x);
    } else {
		x := add_numbers(1, 2);
        !("Large: ");
        !!(x);
    }
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
