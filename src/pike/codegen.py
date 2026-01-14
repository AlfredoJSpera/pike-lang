from typing import Literal
import llvmlite.ir as ir
from pike.ast_nodes import *

class CodegenError(Exception): pass

class LLVMCodeGenerator:
	def __init__(self):
		self.module = ir.Module()
		self.builder = None
		self.symbol_table = {}
		
		# Track the return type of the function currently being compiled
		self.current_function_ret_type = None
		
		# Types
		self.double = ir.DoubleType()
		self.int8 = ir.IntType(8)
		self.string = self.int8.as_pointer() # i8*
		self.void = ir.VoidType()
	
	# ==========================================
	# MARK: PUBLIC FUNCTIONS
	# ==========================================

	def get_ir(self):
		"""
		Returns a string representation of the currently generated IR.
		"""
		return str(self.module)
	
	def generate_code(self, node: ProgramAst):
		"""
		Generates LLVM code from the given program AST.

		This method iterates over all functions in the provided AST node,
		generates LLVM code for each function, and returns a list of the
		generated code strings.
		"""
		generated_code = []
		for function in node.functions:
			generated_code.append(self._codegen(function))
		return generated_code
	
	# ==========================================
	# MARK: MAIN CODEGEN FUNCTIONS
	# ==========================================
	
	def _codegen(self, node: NodeAst):
		"""Execute the correct codegen function."""
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)
	
	def _codegen_FunctionAst(self, node: FunctionAst):
		# Clear the symbol table for the new function scope
		self.symbol_table = {}

		# Save the previous function's return type 
		# and set the new function's return type
		previous_ret_type = self.current_function_ret_type
		self.current_function_ret_type = node.ret_type
		
		# Create or retrieve the function using its prototype
		function = self._get_or_create_function(
			node.name, 
			node.parameters,
			node.ret_type
		)
		entry_basic_block = function.append_basic_block("entry")
		
		# Initialize the builder with the entry at the top
		self.builder = ir.IRBuilder(entry_basic_block)

		# This ensures all variables in symbol_table are pointers to storage.
		# - 'num' (double) becomes 'double*' (load returns double)
		# - 'str' (i8*)    becomes 'i8**'    (load returns i8*)
		for arg in function.args:
			self._create_stack_variable(arg.name, arg, arg.type)
		
		# Generate the code of the body
		last_val = self._codegen(node.body)

		if self.builder.block is None:
			raise CodegenError("Function builder.block is None")
		
		# Only add a return if the block hasn't been terminated yet.
		if not self.builder.block.is_terminated:
			if node.ret_type is None or node.ret_type == PikeType.VOID:
				self.builder.ret_void()
			else:
				# If we have a value from the last statement, return it
				# Otherwise, return a default 0.0 for safety
				if last_val is not None:
					self.builder.ret(last_val)
				else:
					self.builder.ret(ir.Constant(self.double, 0.0))
		
		# Restore previous return type context
		self.current_function_ret_type = previous_ret_type

		return function
	
	def _codegen_BodyAst(self, node: BodyAst):
		last_instruction = None
		for stmt in node.statements:
			last_instruction = self._codegen(stmt)
		return last_instruction
	
	# ==========================================
	# MARK: VALUES AST CODEGEN
	# ==========================================

	def _codegen_NumberValueAst(self, node: NumberValueAst):
		"""
		Creates the IR for a double constant.
		"""
		return ir.Constant(
			typ=self.double, 
			constant=float(node.value)
		)
	
	def _codegen_StringValueAst(self, node: StringValueAst):
		"""
		Creates the IR that defines the string literal as a global constant.
		This ensures it has static storage duration and resides in read-only memory.
		"""
		# Add null terminator
		string_val = node.value + '\0'
		# Create the array type (e.g. [12 x i8])
		c_str_type = ir.ArrayType(
			element=self.int8, 
			count=len(string_val)
		)
		
		# Define the constant
		global_var = ir.GlobalVariable(
			module=self.module, 
			typ=c_str_type, 
			name=f".str_{id(node)}"
		)
		global_var.linkage = "internal"
		global_var.global_constant = True
		global_var.initializer = ir.Constant( # type: ignore
			typ=c_str_type, 
			constant=bytearray(string_val.encode("utf8"))
		)
		
		# Bitcast the array pointer to i8* (char*) for generic use
		return global_var.bitcast(typ=self.string)

	def _codegen_VariableAst(self, node: VariableAst):
		"""
		Creates the IR that loads a variable from the symbol table.
		"""
		# Retrieve the value or pointer from the symbol table
		if node.name not in self.symbol_table:
			raise CodegenError(f"Undefined variable: {node.name}")
		
		value = self.symbol_table[node.name]
		
		if self.builder is None:
			raise CodegenError("Variable builder is None")

		# If it's a pointer (alloca), we load the value
		if isinstance(value.type, ir.PointerType):
			return self.builder.load(ptr=value, name=node.name)
		
		# If it's a direct value (function arg), return it
		return value
	
	# ==========================================
	# MARK: EXPRESSION AST CODEGEN
	# ==========================================

	def _codegen_FunctionCallAst(self, node: FunctionCallAst):
		"""
		Creates the IR for a function call.
		"""
		# Retrieve the called function from the module
		if node.called_name not in self.module.globals:
			raise CodegenError(f"Call to undefined function: {node.called_name}")
		
		called_function = self.module.globals[node.called_name]
		
		if not isinstance(called_function, ir.Function):
			raise CodegenError(f"Call to something that is not a function: {node.called_name}")

		# Compile arguments
		call_args = []
		for arg in node.args:
			# Note: arg can be any of the AST under ExpressionAST
			call_args.append(self._codegen(arg))

		# Verify argument count
		if len(called_function.args) != len(call_args):
			raise CodegenError(f"Incorrect number of arguments for {node.called_name}")

		if self.builder is None:
			raise CodegenError("Function Call builder is None")
		
		return self.builder.call(
			fn=called_function,
			args=call_args,
			name="calltmp"
		)

	def _codegen_BinaryOperationAst(self, node: BinaryOperationAst):
		"""
		Creates the IR for a binary operation and its operands.
		"""
		# Generate the IR for the two expressions recursively
		left_exp = self._codegen(node.left)
		right_exp = self._codegen(node.right)

		if self.builder is None:
			raise CodegenError("Binary Operation builder is None")

		# Select the correct operation
		if node.operator == '+':
			return self.builder.fadd(left_exp, right_exp, name="addtmp")
		elif node.operator == '-':
			return self.builder.fsub(left_exp, right_exp, name="subtmp")
		elif node.operator == '*':
			return self.builder.fmul(left_exp, right_exp, name="multmp")
		elif node.operator == '/':
			return self.builder.fdiv(left_exp, right_exp, name="divtmp")
		elif node.operator == '<':
			return self._compare_to_double(left_exp, right_exp, '<')
		elif node.operator == '>':
			return self._compare_to_double(left_exp, right_exp, '>')
		else:
			raise CodegenError(f"Unknown operator '{node.operator}'")

	# ==========================================
	# MARK: STATEMENT AST CODEGEN
	# ==========================================
	
	def _codegen_AssignmentAst(self, node: AssignmentAst):
		variable_name = node.variable_name
		expression_result = self._codegen(node.value)

		if self.builder is None:
			raise CodegenError("Assignment builder is None")

		if variable_name not in self.symbol_table:
			# New variable definition
			self._create_stack_variable(
				name=variable_name, 
				value=expression_result, 
				var_type=expression_result.type
			)
		else:
			# Existing variable (local or function arg)
			ptr = self.symbol_table[variable_name]
			self.builder.store(expression_result, ptr)

		return expression_result

	def _codegen_ReturnAst(self, node: ReturnAst):
		if self.builder is None:
			raise CodegenError("Return builder is None")
		
		if node.expression:
			if (self.current_function_ret_type is None
				or self.current_function_ret_type == PikeType.VOID):
				raise CodegenError("Cannot return a value from a void function.")
			
			retval = self._codegen(node.expression)
			self.builder.ret(retval)
		else:
			self.builder.ret_void()
		
		# Return a dummy value as the builder has stopped
		return ir.Constant(self.double, 0.0)

	

	def _codegen_PrintAst(self, node: PrintAst):
		printf = self._declare_printf()
		val = self._codegen(node.expression)
		
		# Determine format string based on type
		if val.type == self.double:
			fmt = "%f"
		elif val.type == self.string:
			fmt = "%s"
		else:
			raise CodegenError("Cannot print unknown type")

		if node.new_line:
			fmt += "\n"
		
		# Create format string constant
		c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt) + 1), bytearray((fmt + "\0").encode("utf8")))
		global_fmt = ir.GlobalVariable(self.module, c_fmt.type, name=f"fmt_{id(node)}")
		global_fmt.linkage = 'internal'
		global_fmt.global_constant = True
		global_fmt.initializer = c_fmt # type: ignore
		
		if self.builder is None:
			raise CodegenError("Print builder is None")
		
		fmt_arg = self.builder.bitcast(global_fmt, self.string)
		
		return self.builder.call(printf, [fmt_arg, val])

	def _codegen_IfElseAst(self, node: IfElseAst):
		cond_val = self._codegen(node.condition)

		if self.builder is None:
			raise CodegenError("If/Else builder is None")
		
		# Convert double condition to i1 (boolean)
		# 0.0 is false, anything else is true
		cmp = self.builder.fcmp_ordered('!=', cond_val, ir.Constant(self.double, 0.0), name="ifcond")

		# Create blocks
		then_bb = self.builder.function.append_basic_block("then")
		else_bb = self.builder.function.append_basic_block("else")
		merge_bb = self.builder.function.append_basic_block("ifcont")

		# Conditional Branch
		self.builder.cbranch(cmp, then_bb, else_bb)

		# -- Then Block --
		self.builder.position_at_end(then_bb)
		self._codegen(node.then_block)

		if self.builder.block is None:
			raise CodegenError("If/Else builder.block is None")
		
		# Check if the block was already terminated (e.g. by return)
		if not self.builder.block.is_terminated:
			self.builder.branch(merge_bb)
		
		# -- Else Block --
		self.builder.position_at_end(else_bb)
		if node.else_block:
			self._codegen(node.else_block)
		
		if not self.builder.block.is_terminated:
			self.builder.branch(merge_bb)

		# -- Merge Block --
		self.builder.position_at_end(merge_bb)
		return ir.Constant(self.double, 0.0)

	def _codegen_ForLoopAst(self, node: ForLoopAst):
		# 1. Initialization (executed once)
		# We assume the iterator is a variable assignment logic
		start_val = self._codegen(node.start_val)

		if self.builder is None:
			raise CodegenError("For builder is None")
		
		# Allocate iterator
		iter_ptr = self.builder.alloca(self.double, name=node.iterator)
		self.builder.store(start_val, iter_ptr)
		self.symbol_table[node.iterator] = iter_ptr

		# Create blocks
		cond_bb = self.builder.function.append_basic_block("loop_cond")
		body_bb = self.builder.function.append_basic_block("loop_body")
		after_bb = self.builder.function.append_basic_block("loop_end")

		# Jump to Condition
		self.builder.branch(cond_bb)

		# 2. Condition Block
		self.builder.position_at_end(cond_bb)
		cond_val = self._codegen(node.condition)
		# Convert to bool (i1)
		cmp = self.builder.fcmp_ordered('!=', cond_val, ir.Constant(self.double, 0.0), name="loopcond")
		self.builder.cbranch(cmp, body_bb, after_bb)

		# 3. Body Block
		self.builder.position_at_end(body_bb)
		self._codegen(node.body)
		
		# Step: Load, Add, Store
		step_val = self._codegen(node.step)
		curr_val = self.builder.load(iter_ptr)
		next_val = self.builder.fadd(curr_val, step_val, name="nextvar")
		self.builder.store(next_val, iter_ptr)

		if self.builder.block is None:
			raise CodegenError("For builder.block is None")
		
		# Loop back to condition
		if not self.builder.block.is_terminated:
			self.builder.branch(cond_bb)

		# 4. After Block
		self.builder.position_at_end(after_bb)
		return ir.Constant(self.double, 0.0)
	
	# ==========================================
	# MARK: HELPERS
	# ==========================================

	def _get_or_create_function(
			self, 
			name: str, 
			parameters: List[ParameterAst],
			return_type: PikeType | None
		):
		"""Helper that returns a new or existing function based on its prototype."""
		# Set the return type for the prototype
		prototype_return_ty = self.void
		if return_type == PikeType.NUM:
			prototype_return_ty = self.double

		# Set the args for the prototype
		prototype_args_ty = []
		for param in parameters:
			if param.type_name == PikeType.NUM:
				prototype_args_ty.append(self.double)
			elif param.type_name == PikeType.STR:
				prototype_args_ty.append(self.string)

		# Create the prototype
		function_type = ir.FunctionType(
			return_type=prototype_return_ty,
			args=prototype_args_ty
		)

		# Get or create the function
		if name in self.module.globals:
			# The function already exists, get it
			function = self.module.globals.get(name)
			
			# Error checking
			if not isinstance(function, ir.Function):
				raise CodegenError("Function/Global name collision", name)
			if not function.is_declaration:
				raise CodegenError(f"Re-definition of function {name}")
			
			# Args length check
			existing_args_number = len(function.function_type.args)
			passed_args_number = len(parameters)
			if existing_args_number != passed_args_number:
				raise CodegenError(f"Re-definition of {name} with different number of arguments ({passed_args_number} instead of {existing_args_number})")
		else:
			# Create the new function
			function = ir.Function(
				module=self.module, 
				ftype=function_type, 
				name=name
			)

		for i, arg in enumerate(function.args):
			# Change the default indexed LLVM variable names
			# to the ones defined in the passed node
			# e.g. ".1" -> "my_arg"
			arg.name = parameters[i].name
			self.symbol_table[arg.name] = arg
		
		return function
	
	def _declare_printf(self):
		"""Helper to declare printf if it does not exists."""
		if "printf" in self.module.globals:
			return self.module.globals["printf"]
		
		# Create the printf prototype
		# int printf(char *, ...)
		printf_ty = ir.FunctionType(
			return_type=ir.IntType(32),
			args=[self.string], 
			var_arg=True
		)
		return ir.Function(
			module=self.module, 
			ftype=printf_ty, 
			name="printf"
		)
	
	def _compare_to_double(self, left, right, operation: Literal['<', '>']):
		"""Helper to create the IR for a compare and return the result as a double."""
		cmp = self.builder.fcmp_ordered(operation, left, right, name="cmptmp") # type: ignore
		# Convert the i1 to double
		return self.builder.uitofp(cmp, self.double, name="bool_to_double") # type: ignore
	
	def _create_stack_variable(self, name: str, value: ir.Value, var_type: ir.Type) -> ir.AllocaInstr:
		"""Allocates stack memory, stores the value, and updates the symbol table."""
		# Allocate memory on stack
		ptr = self.builder.alloca(var_type, name=name) # type: ignore
		
		# Store the value
		self.builder.store(value, ptr) # type: ignore
		
		# Register in symbol table
		self.symbol_table[name] = ptr
		
		return ptr