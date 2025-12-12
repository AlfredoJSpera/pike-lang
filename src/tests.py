import unittest

from evaluator import KaleidoscopeEvaluator

class TestEvaluator(unittest.TestCase):
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