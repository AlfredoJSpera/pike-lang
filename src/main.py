from evaluator import KaleidoscopeEvaluator

if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	kalei.evaluate('putchard(55<2)', print_ast_dump=True)
	#kalei.evaluate('def foo(a b) for x = 65, x < a, b in putchard(x)', print_ast_dump=True)

	# We call these for their side effect of printing to stdout, so don't care
	# about the return value.
	#kalei.evaluate('foo(79, 1)', print_ast_dump=True)
	#kalei.evaluate('putchard(10)', print_ast_dump=False)