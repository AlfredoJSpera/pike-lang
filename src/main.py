from evaluator import KaleidoscopeEvaluator

# TODO: make the function have 0 args
# TODO: make assign
if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	kalei.evaluate('def foo(x) for i = x, i < 5, 1.0 in i+1', print_llvm_dump=True, print_ast_dump=False)
	kalei.evaluate('foo(1)')
