import llvmlite.ir as ir
from pike.ast_nodes import *

class CodegenError(Exception): pass

class LLVMCodeGenerator:
	def __init__(self):
		self.module = ir.Module()
		self.builder = None
		self.symbol_table = {}
		self.double = ir.DoubleType()
		self.string = ir.IntType(8).as_pointer()
		self.void = ir.VoidType()
	
	def get_ir(self):
		return str(self.module)
	
	def generate_code(self, node: ProgramAst):
		"""
		Generate the LLVM code as a string from the parsed AST, 
		store it in module, and return it.
		"""
		generated_code = []
		for function in node.functions:
			generated_code.append(self._codegen(function))
		return generated_code
	
	def _codegen(self, node: NodeAst):
		"""Execute the correct codegen function."""
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)
	
	def _codegen_FunctionAst(self, node: FunctionAst):
		# Create or retrieve the function using its prototype
		function = self._get_or_create_function(
			node.name, 
			node.parameters,
			node.ret_type
		)
		entry_basic_block = function.append_basic_block("entry")
		
		# Initialize the builder with the entry at the top
		self.builder = ir.IRBuilder(entry_basic_block)
		
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
		
		return function
	
	def _get_or_create_function(
			self, 
			name: str, 
			parameters: List[ParameterAst],
			return_type: PikeType | None
		):
		r_type = self.void
		if return_type == PikeType.NUM:
			r_type = self.double

		arg_types = []
		for param in parameters:
			if param.type_name == PikeType.NUM:
				arg_types.append(self.double)
			elif param.type_name == PikeType.STR:
				arg_types.append(self.string)

		function_type = ir.FunctionType(
			return_type=r_type,
			args=arg_types
		)

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

	def _codegen_BodyAst(self, node: BodyAst):
		last_instruction = None
		for stmt in node.statements:
			last_instruction = self._codegen(stmt)
		return last_instruction

	def _codegen_NumberValueAst(self, node: NumberValueAst):
		return ir.Constant(self.double, float(node.value))

	def _codegen_StringValueAst(self, node: StringValueAst):
		# Create a global constant string
		# 1. Add null terminator
		string_val = node.value + '\0'
		# 2. Create the array type (e.g. [12 x i8])
		c_str_type = ir.ArrayType(ir.IntType(8), len(string_val))
		# 3. Define the constant
		global_var = ir.GlobalVariable(self.module, c_str_type, name=f".str_{id(node)}")
		global_var.linkage = 'internal'
		global_var.global_constant = True
		global_var.initializer = ir.Constant(c_str_type, bytearray(string_val.encode("utf8"))) # type: ignore
		
		# 4. Bitcast the array pointer to i8* (char*) for generic use
		return global_var.bitcast(self.string)

	def _codegen_VariableAst(self, node: VariableAst):
		# Retrieve the value or pointer from the symbol table
		if node.name not in self.symbol_table:
			raise CodegenError(f"Undefined variable: {node.name}")
		
		val = self.symbol_table[node.name]
		
		if self.builder is None:
			raise CodegenError("Variable builder is None")

		# If it's a pointer (alloca), we load the value
		if isinstance(val.type, ir.PointerType):
			return self.builder.load(val, name=node.name)
		
		# If it's a direct value (function arg), return it
		return val

	def _codegen_AssignmentAst(self, node: AssignmentAst):
		value = self._codegen(node.value)
		name = node.variable_name

		if self.builder is None:
			raise CodegenError("Assignment builder is None")

		if name not in self.symbol_table:
			# New variable: Allocate memory on stack
			ptr = self.builder.alloca(self.double, name=name)
			self.symbol_table[name] = ptr
			self.builder.store(value, ptr)
		else:
			ptr = self.symbol_table[name]
			if isinstance(ptr.type, ir.PointerType):
				# Existing variable: Store new value
				self.builder.store(value, ptr)
			else:
				# It is a function argument (SSA value). 
				# To support mutation, we must "shadow" it with a new stack allocation.
				new_ptr = self.builder.alloca(self.double, name=f"{name}_shadow")
				self.builder.store(value, new_ptr)
				self.symbol_table[name] = new_ptr

		return value

	def _codegen_BinaryOperationAst(self, node: BinaryOperationAst):
		lhs = self._codegen(node.left)
		rhs = self._codegen(node.right)

		if self.builder is None:
			raise CodegenError("Binary Operation builder is None")

		if node.operator == '+':
			return self.builder.fadd(lhs, rhs, name="addtmp")
		elif node.operator == '-':
			return self.builder.fsub(lhs, rhs, name="subtmp")
		elif node.operator == '*':
			return self.builder.fmul(lhs, rhs, name="multmp")
		elif node.operator == '/':
			return self.builder.fdiv(lhs, rhs, name="divtmp")
		elif node.operator == '<':
			# Compare returns an i1 (boolean)
			cmp = self.builder.fcmp_ordered('<', lhs, rhs, name="cmptmp")
			# Convert i1 to double (0.0 or 1.0) for the language's type consistency
			return self.builder.uitofp(cmp, self.double, name="bool_to_double")
		elif node.operator == '>':
			cmp = self.builder.fcmp_ordered('>', lhs, rhs, name="cmptmp")
			return self.builder.uitofp(cmp, self.double, name="bool_to_double")
		else:
			raise CodegenError(f"Unknown operator {node.operator}")

	def _codegen_FunctionCallAst(self, node: FunctionCallAst):
		# Retrieve the function from the module
		callee_func = self.module.globals.get(node.called_name)
		if not callee_func or not isinstance(callee_func, ir.Function):
			raise CodegenError(f"Call to undefined function: {node.called_name}")

		# Compile arguments
		call_args = [self._codegen(arg) for arg in node.args]

		# Verify argument count
		if len(callee_func.args) != len(call_args):
			raise CodegenError(f"Incorrect number of arguments for {node.called_name}")

		if self.builder is None:
			raise CodegenError("Function Call builder is None")
		
		return self.builder.call(callee_func, call_args, name="calltmp")

	def _codegen_ReturnAst(self, node: ReturnAst):
		if self.builder is None:
			raise CodegenError("Return builder is None")
		
		if node.expression:
			retval = self._codegen(node.expression)
			self.builder.ret(retval)
		else:
			self.builder.ret_void()
		# Return a dummy value as the builder has stopped
		return ir.Constant(self.double, 0.0)

	def _declare_printf(self):
		"""Helper to declare printf if not exists."""
		if 'printf' in self.module.globals:
			return self.module.globals['printf']
		
		# int printf(char *, ...)
		void_ptr_ty = ir.IntType(8).as_pointer()
		printf_ty = ir.FunctionType(ir.IntType(32), [void_ptr_ty], var_arg=True)
		return ir.Function(self.module, printf_ty, name="printf")

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