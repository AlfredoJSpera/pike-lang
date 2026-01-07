from ast_nodes import BinaryExprAST, CallExprAST, ForExprAST, FunctionAST, IfExprAST, NumberExprAST, PrototypeAST, VariableExprAST
import llvmlite.ir as ir

class CodegenError(Exception): 
	pass


class LLVMCodeGenerator(object):
	"""
	Uses the visitor pattern.
	"""
	def __init__(self):
		self.module = ir.Module()
		self.builder = None # initialized in _codegen_FunctionAST
		self.function_symbol_table = {}

	def generate_code(self, node):
		"""
		Generate the LLVM code as a string from the parsed AST 
		and store it in module.
		"""
		return self._codegen(node)

	def _codegen(self, node):
		"""Execute the correct codegen function."""
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)
	
	def _codegen_FunctionAST(self, node: FunctionAST):
		# Initialize the symbol table
		self.function_symbol_table = {}

		# Create or retrieve the function using its prototype
		function = self._codegen(node.prototype)
		entry_basic_block = function.append_basic_block("entry")
		
		# Initialize the builder with the entry at the top
		self.builder = ir.IRBuilder(entry_basic_block)
		
		# Generate the code of the body and return the final value
		#! Based on the content of the body (the function can be anonymous), 
		#! this is the main codegen caller
		retval = self._codegen(node.body)
		self.builder.ret(retval)
		
		return function

	def _codegen_PrototypeAST(self, node: PrototypeAST):
		# Get the function signature
		proto_func_name = node.name
		proto_func_types = ir.FunctionType(
			return_type=ir.DoubleType(), 
			args=[ir.DoubleType()] * len(node.arg_names) # A list of arguments of variable length
		)

		# Search if the function has already been declared
		if proto_func_name in self.module.globals:
			# The function already exists, get it
			existing_func = self.module.globals.get(proto_func_name)
			
			# Error checking
			if not isinstance(existing_func, ir.Function):
				raise CodegenError("Function/Global name collision", proto_func_name)
			if not existing_func.is_declaration:
				raise CodegenError(f"Re-definition of {proto_func_name}")
			
			# Args length check
			existing_func_args_number = len(existing_func.function_type.args)
			proto_func_args_number = len(proto_func_types.args)
			if existing_func_args_number != proto_func_args_number:
				raise CodegenError(f"Re-definition of {proto_func_name} with different number of arguments ({proto_func_args_number} instead of {existing_func_args_number})")
			
			# Get the function from globals
			function = self.module.globals[proto_func_name]
		else:
			# Create the new function
			function = ir.Function(
				module=self.module, 
				ftype=proto_func_types, 
				name=proto_func_name
			)

		for i, arg in enumerate(function.args):
			# Change the default indexed LLVM variable names
			# to the ones defined in the passed node
			# e.g. ".1" -> "my_arg"
			arg.name = node.arg_names[i]
			self.function_symbol_table[arg.name] = arg
		
		return function

	def _codegen_NumberExprAST(self, node: NumberExprAST):
		value = float(node.value)
		return ir.Constant(ir.DoubleType(), value)

	def _codegen_VariableExprAST(self, node: VariableExprAST):
		# Get the variable from the symbol table
		variable = self.function_symbol_table.get(node.name)
		
		# Error checking
		if variable is None:
			raise CodegenError("Using unknown variable", node.name)
		
		return variable

	def _codegen_BinaryExprAST(self, node: BinaryExprAST):
		# Recursion on the node's children
		left = self._codegen(node.left_operand)
		right = self._codegen(node.right_operand)

		if self.builder is None:
			raise CodegenError("Builder is not initialized")

		# Select and return the operation
		if node.operator == '+': 
			return self.builder.fadd(left, right, "addtmp")
		elif node.operator == '-': 
			return self.builder.fsub(left, right, "subtmp")
		elif node.operator == '*': 
			return self.builder.fmul(left, right, "multmp")
		elif node.operator == '<':
			cmp_func = self.builder.fcmp_unordered('<', left, right, "cmptmp")
			# Convert the integer (boolean) to a double
			return self.builder.uitofp(cmp_func, ir.DoubleType(), "booltmp")
		else:
			raise CodegenError("Unknown binary operator", node.operator)
	
	def _codegen_CallExprAST(self, node: CallExprAST):
		called_function_name = node.called_function_name
		
		# Get the function from the globals
		called_function = self.module.globals.get(called_function_name, None)
		
		# Error checking
		if called_function is None or not isinstance(called_function, ir.Function):
			raise CodegenError("Call to unknown function",called_function_name)
		
		# Args length checking
		called_function_args_length = len(called_function.args)
		args_passed_length = len(node.args)
		if called_function_args_length != args_passed_length:
			raise CodegenError(f"Call argument length mismatch for {called_function_name} (passed {args_passed_length} instead of {called_function_args_length})")
		
		# Generate the code for each argument
		args_passed = [self._codegen(arg) for arg in node.args]
		
		if self.builder is None:
			raise CodegenError("Builder is not initialized")
		
		# Call the function and return the reference to the call
		return self.builder.call(called_function, args_passed, "calltmp")

	def _codegen_IfExprAST(self, node: IfExprAST):
		# Generate the code for the condition
		condition_result = self._codegen(node.condition_expr)

		if self.builder is None: 
			raise CodegenError("Builder is not initialized")
		
		# Check if the condition is true
		# 1 != 0 => true
		# 0 != 0 => false
		zero_false = ir.Constant(ir.DoubleType(), 0.0)
		is_condition_true = self.builder.fcmp_ordered('!=', condition_result, zero_false)

		# Build the control flow basic blocks
		then_block = self.builder.function.append_basic_block("then") # Attach the first block too
		else_block = ir.Block(self.builder.function, "else")
		merge_block = ir.Block(self.builder.function, "ifcont")

		# Execute the branching
		self.builder.cbranch(is_condition_true, then_block, else_block)

		# THEN block
		self.builder.position_at_start(then_block)
		then_value = self._codegen(node.then_expr)
		self.builder.branch(merge_block)
		then_block = self.builder.block

		# ELSE block
		self.builder.function.basic_blocks.append(else_block)
		self.builder.position_at_start(else_block)
		else_value = self._codegen(node.else_expr)
		self.builder.branch(merge_block)

		# MERGE
		self.builder.function.basic_blocks.append(merge_block)
		self.builder.position_at_start(merge_block)
		
		# Decide the path taken with phi
		phi = self.builder.phi(ir.DoubleType(), "iftmp")
		phi.add_incoming(then_value, then_block)
		phi.add_incoming(else_value, else_block)
		
		return phi

	def _codegen_ForExprAST(self, node: ForExprAST):
		# Generate the code for the starting condition
		counter_start_value = self._codegen(node.start_expr)
		
		if self.builder is None:
			raise CodegenError("Builder is not initialized")

		# Keep track of the block we are currently in before entering the loop
		pre_header_block = self.builder.block

		# Explicitly jump from the current position into the loop
		loop_block = self.builder.function.append_basic_block("loop_header")
		self.builder.branch(loop_block)
		self.builder.position_at_start(loop_block)

		# Create a PHI node to track the named counter, 
		# by initializing it with the starting value from the pre header block
		counter_current_phi_value = self.builder.phi(ir.DoubleType(), node.id_name)
		counter_current_phi_value.add_incoming(counter_start_value, pre_header_block)

		# Save any existing variable with the same name as the counter and hide it (shadowing)
		shadowed_value = self.function_symbol_table.get(node.id_name)
		self.function_symbol_table[node.id_name] = counter_current_phi_value

		# Generate code for the loop body
		self._codegen(node.body)

		# Calculate the step (default to 1.0 if not provided)
		if node.step_expr:
			step_value = self._codegen(node.step_expr)
		else:
			step_value = ir.Constant(ir.DoubleType(), 1.0)
		
		# Increment the current phi value with the step value
		counter_incremented_value = self.builder.fadd(counter_current_phi_value, step_value, "next_iterator_val")

		# Check if the end condition is true
		end_condition = self._codegen(node.end_expr)
		is_loop_active = self.builder.fcmp_ordered(
			'!=', 
			end_condition, 
			ir.Constant(ir.DoubleType(), 0.0), 
			"loop_active_bool"
		)

		# Record the block where the loop logic ends
		loop_end_block = self.builder.block

		# Create the block for the code following the loop
		after_loop_block = self.builder.function.append_basic_block("after_loop")

		# If active, jump back to the header, exit the loop otherwise
		self.builder.cbranch(is_loop_active, loop_block, after_loop_block)
		
		# If we loop back, the value is now the incremented counter
		counter_current_phi_value.add_incoming(counter_incremented_value, loop_end_block)

		# Move the builder to the block after the loop so codegen can continue
		self.builder.position_at_start(after_loop_block)

		# Restore the original variable to the symbol table (un-shadowing)
		if shadowed_value is None:
			# No variable was shadowed, delete the entry
			del self.function_symbol_table[node.id_name]
		else:
			self.function_symbol_table[node.id_name] = shadowed_value

		# For loops in this language traditionally return 0.0
		return ir.Constant(ir.DoubleType(), 0.0)

	