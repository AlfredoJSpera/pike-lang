import unittest
from lark import Lark, exceptions
from pike.grammar import PIKE_GRAMMAR
from pike.ast_nodes import (
	PikeTransformer, PikeType, ProgramAst, FunctionAst, BodyAst, ParameterAst,
	AssignmentAst, ReturnAst, PrintAst, IfElseAst, ForLoopAst,
	BinaryOperationAst, NumberValueAst, StringValueAst, VariableAst, FunctionCallAst
)

class TestPikeGrammarAndAST(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		"""
		Initialize the parser once for all tests to save time.
		We replicate the parser setup from evaluator.py to avoid 
		triggering LLVM initialization found in PikeEvaluator.
		"""
		cls.parser = Lark(
			PIKE_GRAMMAR,
			parser="lalr",
			start="start",
		)
		cls.transformer = PikeTransformer()

	def parse_to_ast(self, code):
		"""Helper to parse code string directly to AST."""
		tree = self.parser.parse(code)
		return self.transformer.transform(tree)

	def test_arithmetic_precedence(self):
		"""
		Verify standard mathematical precedence.
		Grammar expects: (<, >) -> (+, -) -> (*, /)
		Expression: 10 + 5 * 2 < 100
		AST Structure should group (5*2) then (10 + result) then (result < 100)
		"""
		code = "10 + 5 * 2 < 100;"
		ast = self.parse_to_ast(code)
		
		# Unpack the wrapper function created for top-level stmt
		stmt = ast.functions[0].body.statements[0]
		
		# Root should be Less Than (<)
		self.assertIsInstance(stmt, BinaryOperationAst)
		self.assertEqual(stmt.operator, '<')
		
		# Right side: 100
		self.assertIsInstance(stmt.right, NumberValueAst)
		self.assertEqual(stmt.right.value, 100.0)
		
		# Left side: Addition (+)
		left_add = stmt.left
		self.assertIsInstance(left_add, BinaryOperationAst)
		self.assertEqual(left_add.operator, '+')
		self.assertEqual(left_add.left.value, 10.0)
		
		# Right side of Addition: Multiplication (*) (demonstrating precedence)
		right_mul = left_add.right
		self.assertIsInstance(right_mul, BinaryOperationAst)
		self.assertEqual(right_mul.operator, '*')
		self.assertEqual(right_mul.left.value, 5.0)
		self.assertEqual(right_mul.right.value, 2.0)

	def test_top_level_wrapping(self):
		"""
		Ensure loose top-level statements are wrapped in a single 'main'
		function, while explicit functions remain untouched.
		"""
		code = """
		x := 1;
		defunc my_func() { ret 0; }
		y := 2;
		"""
		ast = self.parse_to_ast(code)
		
		# Expect 2 functions: 'my_func' (explicit) and 'main' (implicit wrapper)
		self.assertEqual(len(ast.functions), 2)
		
		# 1. Verify Explicit Function
		# The transformer loops through items, appending explicit functions immediately.
		f_explicit = ast.functions[0]
		self.assertEqual(f_explicit.name, "my_func")

		# 2. Verify Main Wrapper
		# The transformer appends 'main' containing all loose statements at the end.
		f_main = ast.functions[1]
		self.assertEqual(f_main.name, "main")
		
		# 'main' should contain BOTH assignments in order
		self.assertEqual(len(f_main.body.statements), 2)
		
		stmt1 = f_main.body.statements[0]
		self.assertIsInstance(stmt1, AssignmentAst)
		self.assertEqual(stmt1.variable_name, "x")
		
		stmt2 = f_main.body.statements[1]
		self.assertIsInstance(stmt2, AssignmentAst)
		self.assertEqual(stmt2.variable_name, "y")

	def test_full_function_definition(self):
		"""
		Verify parsing of a function with all optional components:
		- Arguments with types
		- Return type
		- Multiple statements in body
		"""
		code = """
		defunc calculate(a: num, b: str) %num {
			x := a;
			ret x;
		}
		"""
		ast = self.parse_to_ast(code)
		func = ast.functions[0]
		
		self.assertEqual(func.name, "calculate")
		self.assertEqual(func.ret_type, PikeType.NUM)
		
		# Parameters
		self.assertEqual(len(func.parameters), 2)
		self.assertEqual(func.parameters[0].name, "a")
		self.assertEqual(func.parameters[0].type_name, PikeType.NUM)
		self.assertEqual(func.parameters[1].name, "b")
		self.assertEqual(func.parameters[1].type_name, PikeType.STR)
		
		# Body
		self.assertEqual(len(func.body.statements), 2)
		self.assertIsInstance(func.body.statements[0], AssignmentAst)
		self.assertIsInstance(func.body.statements[1], ReturnAst)

	def test_function_definition_return_types(self):
		code = """
		defunc fun(a: num, b: num) % num {ret a + b;}
		"""
		ast = self.parse_to_ast(code)
		func = ast.functions[0]
		self.assertEqual(func.ret_type, PikeType.NUM)

		code = """
		defunc fun2(a: str) {!!(a);}
		"""
		ast = self.parse_to_ast(code)
		func = ast.functions[0]
		self.assertEqual(func.ret_type, PikeType.VOID)

		code = """
		defunc fun2(a: str) % str {ret a;}
		"""
		with self.assertRaises(exceptions.UnexpectedInput):
			self.parse_to_ast(code)

	def test_if_else_nested(self):
		"""
		Verify nested If/Else structures and block scoping.
		"""
		code = """
		if (x < 10) {
			if (x > 5) {
				print("mid");
			}
		} else {
			ret 0;
		}
		"""
		# Note: 'print' isn't a keyword in grammar, but a function call here unless strictly !, !!
		# The grammar defines ! and !! as stmt, but standard function call is expression.
		# We need to wrap this in a top level to parse.
		
		wrapped_code = f"defunc main() {{ {code} }}"
		ast = self.parse_to_ast(wrapped_code)
		
		outer_if = ast.functions[0].body.statements[0]
		self.assertIsInstance(outer_if, IfElseAst)
		
		# Check Condition
		self.assertEqual(outer_if.condition.operator, '<')
		
		# Check Then Block (Nested If)
		then_stmts = outer_if.then_block.statements
		self.assertEqual(len(then_stmts), 1)
		nested_if = then_stmts[0]
		self.assertIsInstance(nested_if, IfElseAst)
		self.assertIsNone(nested_if.else_block) # Inner if has no else
		
		# Check Else Block (Return)
		else_stmts = outer_if.else_block.statements
		self.assertEqual(len(else_stmts), 1)
		self.assertIsInstance(else_stmts[0], ReturnAst)

	def test_print_statements(self):
		"""
		Differentiate between ! (no newline) and !! (newline).
		"""
		code = """
		!("NoLine");
		!!("NewLine");
		"""
		ast = self.parse_to_ast(code)
		
		# Loose statements are grouped into a single 'main' function
		self.assertEqual(len(ast.functions), 1)
		
		main_func = ast.functions[0]
		self.assertEqual(main_func.name, "main")
		self.assertEqual(len(main_func.body.statements), 2)
		
		# Statement 1
		stmt1 = main_func.body.statements[0]
		self.assertIsInstance(stmt1, PrintAst)
		self.assertFalse(stmt1.new_line, "! should have new_line=False")
		self.assertEqual(stmt1.expression.value, "NoLine")

		# Statement 2
		stmt2 = main_func.body.statements[1]
		self.assertIsInstance(stmt2, PrintAst)
		self.assertTrue(stmt2.new_line, "!! should have new_line=True")

	def test_for_loop_structure(self):
		"""
		Verify the specific 4-part structure of the for loop.
		for (iterator, start; condition; step)
		"""
		code = "for (i, 0; i < 10; 1) { x := x + 1; }"
		ast = self.parse_to_ast(code)
		
		loop = ast.functions[0].body.statements[0]
		self.assertIsInstance(loop, ForLoopAst)
		
		self.assertEqual(loop.iterator, "i")
		self.assertIsInstance(loop.start_val, NumberValueAst)
		self.assertEqual(loop.start_val.value, 0.0)
		
		self.assertIsInstance(loop.condition, BinaryOperationAst)
		
		self.assertIsInstance(loop.step, NumberValueAst)
		self.assertEqual(loop.step.value, 1.0)
		
		self.assertEqual(len(loop.body.statements), 1)
	
	def test_negative_for_loop_invalid_types(self):
		"""
		Verify that the parser rejects invalid token types in the for loop header.
		The grammar strictly enforces: for(NAME, NUMBER; EXPRESSION; NUMBER)
		
		Input: for("st", "e"; i < 10; 2)
		1. "st" is parsed as ESCAPED_STRING, but grammar requires NAME.
		2. "e" is parsed as ESCAPED_STRING, but grammar requires NUMBER.
		"""
		code = 'for("st", "e"; i < 10; 2) {}'
		
		# This will fail at "st" because it expects a NAME token
		with self.assertRaises(exceptions.UnexpectedInput):
			self.parse_to_ast(code)

	def test_for_loop_non_boolean_conditions(self):
		"""
		Verify that the parser accepts arithmetic expressions
		as loop conditions (C-style truthy logic), not just comparisons.
		
		Grammar allow: for_stmt -> expression -> comparison -> sum
		"""
		
		# Case 1: Arithmetic Variable Expression (i + 10)
		# "for (i, 0; i + 10; 1) {}"
		code_var = "for (i, 0; i + 10; 1) {}"
		ast_var = self.parse_to_ast(code_var)
		loop_var = ast_var.functions[0].body.statements[0]
		
		# Verify the condition is parsed as a BinaryOperation (+) rather than failing
		self.assertIsInstance(loop_var.condition, BinaryOperationAst)
		self.assertEqual(loop_var.condition.operator, '+')
		self.assertIsInstance(loop_var.condition.left, VariableAst)
		self.assertEqual(loop_var.condition.left.name, 'i')

		# Case 2: Constant Arithmetic Expression (2 + 10)
		# "for (i, 0; 2 + 10; 1) {}"
		code_const = "for (i, 0; 2 + 10; 1) {}"
		ast_const = self.parse_to_ast(code_const)
		loop_const = ast_const.functions[0].body.statements[0]
		
		self.assertIsInstance(loop_const.condition, BinaryOperationAst)
		self.assertEqual(loop_const.condition.operator, '+')
		self.assertIsInstance(loop_const.condition.left, NumberValueAst)
		self.assertEqual(loop_const.condition.left.value, 2.0)

		# Case 3: Single Number Truthy Condition (Common C-style infinite loop pattern)
		# "for (i, 0; 1; 1) {}"
		code_truthy = "for (i, 0; 1; 1) {}"
		ast_truthy = self.parse_to_ast(code_truthy)
		loop_truthy = ast_truthy.functions[0].body.statements[0]
		
		self.assertIsInstance(loop_truthy.condition, NumberValueAst)
		self.assertEqual(loop_truthy.condition.value, 1.0)

	def test_function_calls_and_args(self):
		"""
		Verify function calls with complex arguments.
		"""
		code = "my_func(a + b, 10, nesting(x));"
		ast = self.parse_to_ast(code)
		
		# Expression statement wrapped in anon func
		expr_stmt = ast.functions[0].body.statements[0]
		self.assertIsInstance(expr_stmt, FunctionCallAst)
		self.assertEqual(expr_stmt.called_name, "my_func")
		
		args = expr_stmt.args
		self.assertEqual(len(args), 3)
		
		# Arg 0: Binary Op
		self.assertIsInstance(args[0], BinaryOperationAst)
		
		# Arg 1: Number
		self.assertIsInstance(args[1], NumberValueAst)
		
		# Arg 2: Nested Function Call
		self.assertIsInstance(args[2], FunctionCallAst)
		self.assertEqual(args[2].called_name, "nesting")

	def test_function_calls_in_control_flow(self):
		"""
		Verify that function calls can be used as expressions
		inside 'if' conditions and 'for' loop conditions.
		"""

		# Case 1: Function call as a direct 'if' condition
		# "if (is_ready()) { ... }"
		code_if = "if (is_ready()) { ret 1; }"
		ast_if = self.parse_to_ast(code_if)
		stmt_if = ast_if.functions[0].body.statements[0]
		
		self.assertIsInstance(stmt_if, IfElseAst)
		# Condition should be a FunctionCall, not a binary op or variable
		self.assertIsInstance(stmt_if.condition, FunctionCallAst)
		self.assertEqual(stmt_if.condition.called_name, "is_ready")

		# Case 2: Function call inside a complex comparison 'if'
		# "if (get_value(x) > 100) { ... }"
		code_complex_if = "if (get_value(x) > 100) { ret 1; }"
		ast_complex_if = self.parse_to_ast(code_complex_if)
		stmt_complex_if = ast_complex_if.functions[0].body.statements[0]
		
		self.assertIsInstance(stmt_complex_if, IfElseAst)
		# Root is comparison (>)
		self.assertIsInstance(stmt_complex_if.condition, BinaryOperationAst) 
		self.assertEqual(stmt_complex_if.condition.operator, '>')
		# Left side is the function call
		self.assertIsInstance(stmt_complex_if.condition.left, FunctionCallAst)
		self.assertEqual(stmt_complex_if.condition.left.called_name, "get_value")

		# Case 3: Function call as a 'for' loop condition
		# "for (i, 0; check_limit(i); 1) { ... }"
		code_for = "for (i, 0; check_limit(i); 1) {}"
		ast_for = self.parse_to_ast(code_for)
		loop = ast_for.functions[0].body.statements[0]
		
		self.assertIsInstance(loop, ForLoopAst)
		# The condition slot (2nd slot) should be the function call
		self.assertIsInstance(loop.condition, FunctionCallAst)
		self.assertEqual(loop.condition.called_name, "check_limit")
		# Verify arguments were parsed correctly inside that call
		self.assertIsInstance(loop.condition.args[0], VariableAst)
		self.assertEqual(loop.condition.args[0].name, "i")

	def test_negative_syntax_missing_semicolon(self):
		"""
		Expect failure on missing semicolon for assignment.
		"""
		code = "x := 10" # Missing ;
		with self.assertRaises(exceptions.UnexpectedInput):
			self.parse_to_ast(code)

	def test_negative_syntax_malformed_function(self):
		"""
		Expect failure on malformed function headers.
		"""
		# Missing parenthesis
		code = "defunc my_func { ret 1; }" 
		with self.assertRaises(exceptions.UnexpectedInput):
			self.parse_to_ast(code)

	def test_negative_syntax_invalid_assignment(self):
		"""
		Assignments expect ':=', not '='.
		"""
		code = "x = 10;"
		# Uses UnexpectedInput to catch both Token errors and Character errors
		with self.assertRaises(exceptions.UnexpectedInput):
			self.parse_to_ast(code)

	def test_string_literal_parsing(self):
		"""
		Ensure strings are parsed and quotes stripped correctly.
		"""
		code = 'x := "hello_world";'
		ast = self.parse_to_ast(code)
		
		assign = ast.functions[0].body.statements[0]
		self.assertIsInstance(assign.value, StringValueAst)
		# The AST transformer strips quotes via [1:-1]
		self.assertEqual(assign.value.value, "hello_world")

if __name__ == "__main__":
	unittest.main()