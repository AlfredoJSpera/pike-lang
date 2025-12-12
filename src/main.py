from evaluator import KaleidoscopeEvaluator

if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	kalei.evaluate('def foo(a b) for x = 65, x < a, b in putchard(x)')

	# We call these for their side effect of printing to stdout, so don't care
	# about the return value.
	kalei.evaluate('foo(79, 1)')
	kalei.evaluate('putchard(10)')