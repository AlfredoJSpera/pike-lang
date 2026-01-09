import argparse

def main(args):
	print("Hello, world!")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog="pike_compiler.py"
	)
	#parser.add_argument("code", help="Required unnamed arg")
	args = parser.parse_args()
	main(args)
