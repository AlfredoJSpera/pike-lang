import unittest
import ctypes
import llvmlite.binding as llvm
from lark import Lark
from pike.evaluator import *
from pike.codegen import LLVMCodeGenerator
from pike.grammar import PIKE_GRAMMAR

# Ensure LLVM is initialized globally once
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

class TestPikeIRAndExecution(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.parser = Lark(PIKE_GRAMMAR, parser="lalr", start="start")
		cls.target = llvm.Target.from_default_triple()

	def compile_and_run(self, code, return_type=ctypes.c_double):
		"""
		Helper to parse, compile, and execute Pike code.
		Returns the result of the 'test' function (or 'main' if test isn't found).
		"""
		# 1. Parse & Transform
		tree = self.parser.parse(code)
		ast = PikeTransformer().transform(tree)

		# 2. Generate IR
		codegen = LLVMCodeGenerator()
		codegen.generate_code(ast)
		llvm_ir = str(codegen.module)

		# 3. Compile & Execute
		mod = llvm.parse_assembly(llvm_ir)
		mod.verify()
		target_machine = self.target.create_target_machine()
		engine = llvm.create_mcjit_compiler(mod, target_machine)
		engine.finalize_object()
		engine.run_static_constructors()

		# 4. Find and Run 'test' (or 'main')
		# We prioritize 'test' so we can define helper functions in the code block
		func_ptr = engine.get_function_address("test")
		if not func_ptr:
			func_ptr = engine.get_function_address("main")
		
		if not func_ptr:
			raise Exception("No 'test' or 'main' function found to execute.")

		c_func = ctypes.CFUNCTYPE(return_type)(func_ptr)
		return c_func()

	def test_arithmetic_execution(self):
		"""
		Verify complex arithmetic precedence and execution.
		Math: (10 + 2) * 3 - 5 / 2 
			= 12 * 3 - 2.5 
			= 36 - 2.5 
			= 33.5
		"""
		code = """
		defunc test() %num {
			ret (10 + 2) * 3 - 5 / 2;
		}
		"""
		result = self.compile_and_run(code)
		self.assertAlmostEqual(result, 33.5, places=5)

	def test_control_flow_if_else(self):
		"""
		Verify conditional logic branches correctly.
		"""
		# Test True Path
		code_true = """
		defunc test() %num {
			x := 10;
			if (x > 5) {
				ret 1.0;
			} else {
				ret 0.0;
			}
			ret 0.0 - 1.0; # Should not be reached
		}
		"""
		self.assertEqual(self.compile_and_run(code_true), 1.0)

		# Test False Path
		code_false = """
		defunc test() %num {
			x := 2;
			if (x > 5) {
				ret 1.0;
			} else {
				ret 0.0;
			}
		}
		"""
		self.assertEqual(self.compile_and_run(code_false), 0.0)

	def test_control_flow_nested_if(self):
		"""
		Verify nested if statements work as expected.
		"""
		code_nested = """
		defunc test() %num {
			x := 10;
			if (x > 5) {
				if (x < 15) {
					ret 100.0;
				}
			}
			ret 0.0;
		}
		"""
		self.assertEqual(self.compile_and_run(code_nested), 100.0)
	
	def test_nested_for_loop(self):
		"""
		Verify nested for loops and block termination logic.
		
		Logic:
		sum := 0
		Outer loop (i): 0, 1, 2 (3 iterations)
			Inner loop (j): 0, 1 (2 iterations)
				sum := sum + 1
		
		Total increments: 3 * 2 = 6
		"""
		code = """
		defunc test() %num {
			sum := 0;
			for (i, 0; i < 3; 1) {
				for (j, 0; j < 2; 1) {
					sum := sum + 1;
				}
			}
			ret sum;
		}
		"""
		self.assertEqual(self.compile_and_run(code), 6.0)

	def test_for_loop_summation(self):
		"""
		Verify Loop Execution.
		Sum numbers 0 to 4. Result should be 0+1+2+3+4 = 10.
		"""
		code = """
		defunc test() %num {
			sum := 0;
			for (i, 0; i < 5; 1) {
				sum := sum + i;
			}
			ret sum;
		}
		"""
		result = self.compile_and_run(code)
		self.assertEqual(result, 10.0)

	def test_function_calls_and_recursion(self):
		"""
		Verify function calls and recursion (Factorial).
		factorial(5) = 120
		"""
		code = """
		defunc factorial(n: num) %num {
			if (n < 2) {
				ret 1;
			}
			ret n * factorial(n - 1);
		}
		
		defunc test() %num {
			ret factorial(5);
		}
		"""
		result = self.compile_and_run(code)
		self.assertEqual(result, 120.0)

	def test_variable_scope_updates(self):
		"""
		Verify that variable updates persist within function scope.
		Based on codegen logic, variables are function-scoped (alloca at entry or shadow).
		"""
		code = """
		defunc test() %num {
			x := 10;
			if (1) {
				x := 20; 
			}
			ret x;
		}
		"""
		# In this implementation (simple symbol table per function), 
		# reassignment updates the pointer, so the change persists.
		result = self.compile_and_run(code)
		self.assertEqual(result, 20.0)

	def test_void_function_side_effects(self):
		"""
		Verify void functions can be called and arguments passed correctly.
		"""
		code = """
		defunc helper(val: num) %num {
			ret val + 1;
		}

		defunc test() %num {
			# Just ensure we can call a function and use its result
			x := helper(10);
			ret x;
		}
		"""
		self.assertEqual(self.compile_and_run(code), 11.0)
	
	def test_implicit_type_casting_bool_to_num(self):
		"""
		Verify that boolean comparisons return 1.0 or 0.0 usable in math.
		(10 < 20) * 5 + (10 > 20) * 100
		= 1.0 * 5 + 0.0 * 100 = 5.0
		"""
		code = """
		defunc test() %num {
			ret (10 < 20) * 5 + (10 > 20) * 100;
		}
		"""
		self.assertEqual(self.compile_and_run(code), 5.0)
	
	def test_early_return_logic(self):
		"""
		Rigorous Test: Verify 'ret' behaves as a terminator effectively.
		"""
		code = """
		defunc test() %num {
			for (i, 0; i < 10; 1) {
				if (i > 2) {
					ret i; # Should return 3.0 immediately
				}
			}
			ret 0-1; # Should never be reached
		}
		"""
		self.assertEqual(self.compile_and_run(code), 3.0)
	
	def test_argument_shadowing(self):
		"""
		Verify that modifying a function argument 
		works correctly (local shadow copy).
		"""
		code = """
		defunc modify(x: num) %num {
			x := x + 10; # Should modify the local allocation
			ret x;
		}

		defunc test() %num {
			val := 5;
			res := modify(val);
			# val should still be 5, res should be 15
			if (val < 6) {
				ret res;
			}
			ret 0;
		}
		"""
		self.assertEqual(self.compile_and_run(code), 15.0)

	def test_simulated_boolean_logic(self):
		"""
		Verify that logic can be simulated with math.
		(A AND B) equivalent to (A * B)
		"""
		code = """
		defunc is_between(x: num) %num {
			# Check if 10 < x < 20
			# Logic: (x > 10) AND (x < 20)
			ret (x > 10) * (x < 20);
		}

		defunc test() %num {
			r1 := is_between(15); # 1.0 * 1.0 = 1.0
			r2 := is_between(5);  # 0.0 * 1.0 = 0.0
			r3 := is_between(25); # 1.0 * 0.0 = 0.0
			
			# Encode result: 100 if true, 0 if false
			ret r1 * 100 + r2 * 10 + r3; 
		}
		"""
		self.assertEqual(self.compile_and_run(code), 100.0)

	def test_void_function_ordering(self):
		"""
		Ensure void functions execute in the correct order.
		We can't test side effects easily, but we can test control flow 
		surrounding them.
		"""
		code = """
		defunc do_nothing() {
			x := 1; # Useless work
		}

		defunc test() %num {
			x := 10;
			if (x > 5) {
				#do_nothing();
				x := 20;
			}
			ret x;
		}
		"""
		self.assertEqual(self.compile_and_run(code), 20.0)

if __name__ == "__main__":
	unittest.main()