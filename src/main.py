from evaluator import KaleidoscopeEvaluator

# TODO: make the function have 0 args
if __name__ == '__main__':
	# Evaluate some code.
	kalei = KaleidoscopeEvaluator()
	# kalei.evaluate('def one(a) 1', print_ast_dump=True)
	# kalei.evaluate('def foo(a b) for x = 65, x < a, b in putchard(x)', print_ast_dump=True)

	# # We call these for their side effect of printing to stdout, so don't care
	# # about the return value.
	# kalei.evaluate('foo(79, one(5))', print_ast_dump=True)
	# kalei.evaluate('putchard(10)', print_ast_dump=True)
	kalei.evaluate('if 1 then putchard(65) else putchard(66)', print_ast_dump=True)
