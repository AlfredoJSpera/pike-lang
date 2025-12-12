import llvmlite.ir as ir

class CodegenError(Exception): pass

class LLVMCodeGenerator(object):
	def __init__(self):
		self.module = ir.Module()
		self.builder = None
		self.func_symtab = {}

	def generate_code(self, node):
		return self._codegen(node)

	def _codegen(self, node):
		method = '_codegen_' + node.__class__.__name__
		return getattr(self, method)(node)

	def _codegen_NumberExprAST(self, node):
		return ir.Constant(ir.DoubleType(), float(node.val))

	def _codegen_VariableExprAST(self, node):
		return self.func_symtab[node.name]

	def _codegen_BinaryExprAST(self, node):
		lhs = self._codegen(node.lhs)
		rhs = self._codegen(node.rhs)

		if self.builder is None: raise CodegenError('Builder is not initialized')

		if node.op == '+': return self.builder.fadd(lhs, rhs, 'addtmp')
		elif node.op == '-': return self.builder.fsub(lhs, rhs, 'subtmp')
		elif node.op == '*': return self.builder.fmul(lhs, rhs, 'multmp')
		elif node.op == '<':
			cmp = self.builder.fcmp_unordered('<', lhs, rhs, 'cmptmp')
			return self.builder.uitofp(cmp, ir.DoubleType(), 'booltmp')
		else: raise CodegenError('Unknown binary operator', node.op)

	def _codegen_IfExprAST(self, node):
		cond_val = self._codegen(node.cond_expr)
		if self.builder is None: raise CodegenError('Builder is not initialized')
		
		cmp = self.builder.fcmp_ordered('!=', cond_val, ir.Constant(ir.DoubleType(), 0.0))

		then_bb = self.builder.function.append_basic_block('then')
		else_bb = ir.Block(self.builder.function, 'else')
		merge_bb = ir.Block(self.builder.function, 'ifcont')
		self.builder.cbranch(cmp, then_bb, else_bb)

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

		oldval = self.func_symtab.get(node.id_name)
		self.func_symtab[node.id_name] = phi

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

		if oldval is None: del self.func_symtab[node.id_name]
		else: self.func_symtab[node.id_name] = oldval

		return ir.Constant(ir.DoubleType(), 0.0)

	def _codegen_CallExprAST(self, node):
		callee_func = self.module.globals.get(node.callee, None)
		if callee_func is None or not isinstance(callee_func, ir.Function):
			raise CodegenError('Call to unknown function', node.callee)
		if len(callee_func.args) != len(node.args):
			raise CodegenError('Call argument length mismatch', node.callee)
		call_args = [self._codegen(arg) for arg in node.args]
		
		if self.builder is None: raise CodegenError('Builder is not initialized')
		
		return self.builder.call(callee_func, call_args, 'calltmp')

	def _codegen_PrototypeAST(self, node):
		funcname = node.name
		func_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()] * len(node.argnames))

		if funcname in self.module.globals:
			existing_func = self.module.globals.get(funcname)
			if not isinstance(existing_func, ir.Function):
				raise CodegenError('Function/Global name collision', funcname)
			if not existing_func.is_declaration:
				raise CodegenError('Redifinition of {0}'.format(funcname))
			if len(existing_func.function_type.args) != len(func_ty.args):
				raise CodegenError('Redifinition with different number of arguments')
			func = self.module.globals[funcname]
		else:
			func = ir.Function(self.module, func_ty, funcname)
		for i, arg in enumerate(func.args):
			arg.name = node.argnames[i]
			self.func_symtab[arg.name] = arg
		return func

	def _codegen_FunctionAST(self, node):
		self.func_symtab = {}
		func = self._codegen(node.proto)
		bb_entry = func.append_basic_block('entry')
		self.builder = ir.IRBuilder(bb_entry)
		retval = self._codegen(node.body)
		self.builder.ret(retval)
		return func