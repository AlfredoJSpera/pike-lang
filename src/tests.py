import unittest
from evaluator import KaleidoscopeEvaluator

class TestEvaluator(unittest.TestCase):
	def setUp(self):
		"""
		Create a fresh evaluator for each test to ensure 
		a clean LLVM module and symbol table.
		"""
		self.evaluator = KaleidoscopeEvaluator()

	def test_arithmetic_basic(self):
		"""Test basic floating point arithmetic."""
		self.assertEqual(self.evaluator.evaluate('1 + 2'), 3.0)
		self.assertEqual(self.evaluator.evaluate('10 - 4'), 6.0)
		self.assertEqual(self.evaluator.evaluate('2 * 3'), 6.0)
		self.assertEqual(self.evaluator.evaluate('10 / 2'), 5.0)

	def test_arithmetic_precedence(self):
		"""
		Test that standard order of operations (PEMDAS) is respected.
		Multiplication/Division (40) > Addition/Subtraction (20) > Relation (10).
		"""
		# 2 + (3 * 4) = 14
		self.assertEqual(self.evaluator.evaluate('2 + 3 * 4'), 14.0)
		
		# (2 + 3) * 4 = 20
		self.assertEqual(self.evaluator.evaluate('(2 + 3) * 4'), 20.0)
		
		# 10 - 2 + 3 = 11 (Left associative)
		self.assertEqual(self.evaluator.evaluate('10 - 2 + 3'), 11.0)
		
		# 10 + 2 < 20 = 1.0 (True)
		self.assertEqual(self.evaluator.evaluate('10 + 2 < 20'), 1.0)

	def test_function_definition_and_call(self):
		"""Test defining a simple function and calling it."""
		# Define function
		self.evaluator.evaluate('def square(x) x * x')
		
		# Call it
		result = self.evaluator.evaluate('square(5)')
		self.assertEqual(result, 25.0)
		
		# Call it with complex expression
		result_complex = self.evaluator.evaluate('square(2 + 2)')
		self.assertEqual(result_complex, 16.0)

	def test_multi_argument_functions(self):
		"""Test functions with multiple arguments."""
		self.evaluator.evaluate('def average(a b c) (a + b + c) / 3')
		self.assertEqual(self.evaluator.evaluate('average(10, 20, 30)'), 20.0)

	def test_recursion_factorial(self):
		"""Test recursive logic using a factorial function."""
		# Define factorial
		self.evaluator.evaluate('''
			def factorial(x) 
				if x < 1 then 
					1 
				else 
					x * factorial(x - 1)
		''')
		
		self.assertEqual(self.evaluator.evaluate('factorial(5)'), 120.0)
		self.assertEqual(self.evaluator.evaluate('factorial(0)'), 1.0)

	def test_recursion_fibonacci(self):
		"""Test deep recursion with Fibonacci sequence."""
		self.evaluator.evaluate('''
			def fib(x) 
				if x < 3 then 
					1 
				else 
					fib(x-1) + fib(x-2)
		''')
		
		# Fib sequence: 1, 1, 2, 3, 5, 8, 13
		self.assertEqual(self.evaluator.evaluate('fib(6)'), 8.0)
		self.assertEqual(self.evaluator.evaluate('fib(7)'), 13.0)

	def test_boolean_logic(self):
		"""
		Test logic gates implementation.
		In this language, 0.0 is false, anything else is true.
		The '<' operator returns 1.0 for true, 0.0 for false.
		"""
		# Define logical NOT
		self.evaluator.evaluate('def not(x) if x then 0 else 1')
		
		self.assertEqual(self.evaluator.evaluate('not(0)'), 1.0)
		self.assertEqual(self.evaluator.evaluate('not(1)'), 0.0)
		self.assertEqual(self.evaluator.evaluate('not(100)'), 0.0)

		# Define logical OR
		self.evaluator.evaluate('def or(x y) if x then 1 else (if y then 1 else 0)')
		
		self.assertEqual(self.evaluator.evaluate('or(0, 0)'), 0.0)
		self.assertEqual(self.evaluator.evaluate('or(1, 0)'), 1.0)
		self.assertEqual(self.evaluator.evaluate('or(0, 5)'), 1.0)

	def test_for_loop_return_value(self):
		"""
		Test that the for-loop construct compiles and runs.
		Note: In this implementation, 'for' loops always return 0.0.
		Testing side effects (like printing) is hard, so we test strict execution.
		"""
		# Loop from 1 to 5. Body is just a calculation that is discarded.
		loop_code = 'for i = 1, i < 5, 1.0 in i * i'
		result = self.evaluator.evaluate(loop_code)
		self.assertEqual(result, 0.0)

	def test_nested_nested_calls(self):
		"""Test calling functions within functions within conditionals."""
		self.evaluator.evaluate('def add(a b) a + b')
		self.evaluator.evaluate('def small(x) if x < 10 then 1 else 0')
		
		# if (10+10 < 10) then 100 else 10+10
		# if (20 < 10) -> False -> 20
		code = '''
			def complex(x) 
				if small(x) 
				then 100 
				else add(x, x)
		'''
		self.evaluator.evaluate(code)
		
		self.assertEqual(self.evaluator.evaluate('complex(5)'), 100.0)
		self.assertEqual(self.evaluator.evaluate('complex(10)'), 20.0)

	def test_shadowing_args(self):
		"""Test that function arguments shadow global functions or other names correctly."""
		# 'a' is a function argument, 'b' is a function argument
		self.evaluator.evaluate('def test(a b) a + b')
		
		# Here we ensure LLVM doesn't get confused if we use variable names 
		# that might look like hex code or existing globals.
		self.assertEqual(self.evaluator.evaluate('test(10, 20)'), 30.0)

	def test_extern_putchard(self):
		"""
		Test the external function call 'putchard'.
		We verify it returns 0.0 (as defined in _add_builtins) and runs without crashing.
		"""
		# Note: This will actually print to your console during tests.
		self.assertEqual(self.evaluator.evaluate('putchard(65)'), 0.0)
	
	def test_basic_if(self):
		e = KaleidoscopeEvaluator()
		e.evaluate('def foo(a b) a * if a < b then a + 1 else b + 1')
		self.assertEqual(e.evaluate('foo(3, 4)'), 12)
		self.assertEqual(e.evaluate('foo(5, 4)'), 25)

	def test_nested_if(self):
		e = KaleidoscopeEvaluator()
		e.evaluate('''
			def foo(a b c)
				if a < b
					then if a < c then a * 2 else c * 2
					else b * 2''')
		self.assertEqual(e.evaluate('foo(1, 20, 300)'), 2)
		self.assertEqual(e.evaluate('foo(10, 2, 300)'), 4)
		self.assertEqual(e.evaluate('foo(100, 2000, 30)'), 60)

	def test_for(self):
		e = KaleidoscopeEvaluator()
		e.evaluate('''
			def foo(a b c)
				if a < b
					then for x = 1.0, x < b, c in x+a+c*b
					else c * 2''')
		self.assertEqual(e.evaluate('foo(1, 2, 3)'), 0)
		self.assertEqual(e.evaluate('foo(3, 2, 30)'), 60)