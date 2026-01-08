from evaluator import KaleidoscopeEvaluator

# TODO: make the function have 0 args
# TODO: make assign
if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	kalei.evaluate('def or(x y) if x then 1 else (if y then 1 else 0)', print_llvm_dump=True, print_ast_dump=True)
	kalei.evaluate('putchard(48 + or(0,0))')
