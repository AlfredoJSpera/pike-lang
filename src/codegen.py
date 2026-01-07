from ast_nodes import BinaryExprAST, CallExprAST, FunctionAST, IfExprAST, NumberExprAST, PrototypeAST, VariableExprAST
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
		entry_basic_block = function.append_basic_block('entry')
		
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
		return self.function_symbol_table[node.name]

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

		then_bb = self.builder.function.append_basic_block('then')
		else_bb = ir.Block(self.builder.function, 'else')
		merge_bb = ir.Block(self.builder.function, 'ifcont')
		self.builder.cbranch(is_condition_true, then_bb, else_bb)

		self.builder.position_at_start(then_bb)
		then_val = self._codegen(node.then_expr)
		self.builder.branch(merge_bb)
		then_bb = self.builder.block

		self.builder.function.basic_blocks.append(else_bb)
		self.builder.position_at_start(else_bb)
		else_val = self._codegen(node.else_expr)
		self.builder.branch(merge_bb)

		self.builder.function.basic_blocks.append(merge_bb)
		self.builder.position_at_start(merge_bb)
		phi = self.builder.phi(ir.DoubleType(), 'iftmp')
		phi.add_incoming(then_val, then_bb)
		phi.add_incoming(else_val, else_bb)
		return phi

	def _codegen_ForExprAST(self, node):
		start_val = self._codegen(node.start_expr)
		if self.builder is None: raise CodegenError('Builder is not initialized')
		
		preheader_bb = self.builder.block
		loop_bb = self.builder.function.append_basic_block('loop')

		self.builder.branch(loop_bb)
		self.builder.position_at_start(loop_bb)

		phi = self.builder.phi(ir.DoubleType(), node.id_name)
		phi.add_incoming(start_val, preheader_bb)

		oldval = self.function_symbol_table.get(node.id_name)
		self.function_symbol_table[node.id_name] = phi

		body_val = self._codegen(node.body)

		if node.step_expr is None: stepval = ir.Constant(ir.DoubleType(), 1.0)
		else: stepval = self._codegen(node.step_expr)
		
		nextvar = self.builder.fadd(phi, stepval, 'nextvar')
		endcond = self._codegen(node.end_expr)
		cmp = self.builder.fcmp_ordered('!=', endcond, ir.Constant(ir.DoubleType(), 0.0), 'loopcond')

		loop_end_bb = self.builder.block
		after_bb = self.builder.function.append_basic_block('afterloop')
		self.builder.cbranch(cmp, loop_bb, after_bb)
		self.builder.position_at_start(after_bb)
		phi.add_incoming(nextvar, loop_end_bb)

		if oldval is None: del self.function_symbol_table[node.id_name]
		else: self.function_symbol_table[node.id_name] = oldval

		return ir.Constant(ir.DoubleType(), 0.0)

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