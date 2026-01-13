import argparse
import os
import sys
from pike.evaluator import PikeEvaluator

# Default code to run if no arguments are passed
DEFAULT_CODE = """
defunc hello(a: num) %num {ret a;}
!!(hello(1));
"""

def main(args):
    source_code = DEFAULT_CODE

    # 1. Determine Source Code
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        
        with open(args.file, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
    elif args.code:
        source_code = args.code

    # 2. Initialize Evaluator
    pike = PikeEvaluator()

    # 3. Evaluate with flags
    
    pike.evaluate(
        source_code, 
        optimize_llvm=not args.no_opt,      # Default True unless --no-opt is passed
        print_lark_dump=args.dump_lark, 
        print_ast_dump=args.dump_ast,
        print_llvm_dump=args.dump_llvm,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compiler and Evaluator for the Pike language.",
        prog="pike_compiler.py"
    )
    
    # Input source options (mutually exclusive)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-f", "--file", 
        help="Path to a .pike source file to execute"
    )
    group.add_argument(
        "-c", "--code", 
        help="Raw code string to execute directly from CLI"
    )

    # Debug / Output flags
    parser.add_argument(
        "--dump-lark", 
        action="store_true", 
        help="Print the Lark parse tree"
    )
    parser.add_argument(
        "--dump-ast", 
        action="store_true", 
        help="Print the Abstract Syntax Tree (AST)"
    )
    parser.add_argument(
        "--dump-llvm", 
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