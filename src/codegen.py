import llvmlite.ir as ir
from ast_nodes import *

class CodegenError(Exception): pass

class LLVMCodeGenerator:
	def __init__(self):
		self.module = ir.Module()
		self.builder = None
		self.function_symbol_table = {}
		self.double = ir.DoubleType()
		self.string = ir.IntType(8).as_pointer()
		self.void = ir.VoidType()
	
	def get_ir(self):
		return str(self.module)

	def generate_code(self, node: Program):
		"""
		Generate the LLVM code as a string from the parsed AST, 
		store it in module, and return it.
		"""
		generated_code = []
		for function in node.functions:
			generated_code.append(self._codegen(function))
		return generated_code
	
	def _codegen(self, node: AstNode):
		"""Execute the correct codegen function."""
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)
	
	def _codegen_Function(self, node: Function):
		# Initialize the symbol table
		self.function_symbol_table = {}

		# Create or retrieve the function using its prototype
		function = self._get_or_create_function(
			node.name, 
			node.parameters,
			node.ret_type
		)
		entry_basic_block = function.append_basic_block("entry")
		
		# Initialize the builder with the entry at the top
		self.builder = ir.IRBuilder(entry_basic_block)
		
		# Generate the code of the body and return the final value
		retval = self._codegen(node.body)
		self.builder.ret(retval)
		
		return function
	
	def _get_or_create_function(
			self, 
			name: str, 
			parameters: List[Parameter],
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
			self.function_symbol_table[arg.name] = arg
		
		return function