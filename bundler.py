import ast
import os
import sys
from collections import deque

class PythonBundler:
	def __init__(self, entry_point, module_files, output_filename='bundle.py'):
		"""
		:param entry_point: The main file (e.g., 'lark_chapter5.py')
		:param module_files: List of library files (e.g., ['ast_nodes.py', 'codegen.py', ...])
		:param output_filename: Name of the resulting bundled file.
		"""
		self.entry_point = entry_point
		# Create a map of module_name -> file_path
		self.modules = {self._get_module_name(f): f for f in module_files}
		# Add entry point to the modules map as well for processing
		self.modules[self._get_module_name(entry_point)] = entry_point
		
		self.output_filename = output_filename
		self.dependencies = {name: set() for name in self.modules}
		self.external_imports = set()
		
		# Determine python version for AST compatibility
		self.use_end_lineno = sys.version_info >= (3, 8)

	def _get_module_name(self, filename):
		return os.path.splitext(os.path.basename(filename))[0]

	def analyze_dependencies(self):
		"""Parse all files to find local vs external imports."""
		print("Analyzing dependencies...")
		for mod_name, file_path in self.modules.items():
			with open(file_path, 'r', encoding='utf-8') as f:
				source = f.read()
			
			tree = ast.parse(source)
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					for alias in node.names:
						base_mod = alias.name.split('.')[0]
						if base_mod in self.modules:
							self.dependencies[mod_name].add(base_mod)
						else:
							self._add_external_import(node)
							
				elif isinstance(node, ast.ImportFrom):
					if node.module and node.module in self.modules:
						self.dependencies[mod_name].add(node.module)
					else:
						self._add_external_import(node)

	def _add_external_import(self, node):
		"""Reconstruct the import string for external libraries."""
		if isinstance(node, ast.Import):
			names = ', '.join(a.name + (f' as {a.asname}' if a.asname else '') for a in node.names)
			self.external_imports.add(f"import {names}")
		elif isinstance(node, ast.ImportFrom):
			module = node.module or ''
			names = ', '.join(a.name + (f' as {a.asname}' if a.asname else '') for a in node.names)
			level = '.' * node.level
			self.external_imports.add(f"from {level}{module} import {names}")

	def get_topological_order(self):
		"""Sort modules so dependencies come before the modules that use them."""
		# Calculate in-degrees
		in_degree = {name: 0 for name in self.modules}
		graph = {name: [] for name in self.modules}
		
		for u in self.modules:
			for v in self.dependencies[u]:
				# u depends on v, so v must come before u. Edge v -> u
				graph[v].append(u)
				in_degree[u] += 1
		
		queue = deque([n for n in self.modules if in_degree[n] == 0])
		sorted_modules = []
		
		while queue:
			u = queue.popleft()
			sorted_modules.append(u)
			for v in graph[u]:
				in_degree[v] -= 1
				if in_degree[v] == 0:
					queue.append(v)
					
		if len(sorted_modules) != len(self.modules):
			print("Warning: Circular dependency detected or disconnected graph.")
			# Fallback: Add remaining modules
			remaining = set(self.modules.keys()) - set(sorted_modules)
			sorted_modules.extend(list(remaining))
			
		# Ensure entry point is strictly last
		entry_name = self._get_module_name(self.entry_point)
		if entry_name in sorted_modules:
			sorted_modules.remove(entry_name)
		sorted_modules.append(entry_name)
		
		return sorted_modules

	def process_file_content(self, file_path):
		"""Read file and strip out lines containing local imports."""
		with open(file_path, 'r', encoding='utf-8') as f:
			lines = f.readlines()
		
		source = "".join(lines)
		tree = ast.parse(source)
		
		# Identify lines to skip (local imports)
		lines_to_skip = set()
		for node in ast.walk(tree):
			if isinstance(node, (ast.Import, ast.ImportFrom)):
				is_local = False
				if isinstance(node, ast.Import):
					for alias in node.names:
						if alias.name.split('.')[0] in self.modules:
							is_local = True
				elif isinstance(node, ast.ImportFrom):
					if node.module and node.module in self.modules:
						is_local = True
				
				if is_local:
					# Mark lines for removal
					start = node.lineno - 1
					end = getattr(node, 'end_lineno', node.lineno) - 1 # Python 3.8+ support
					for i in range(start, end + 1):
						lines_to_skip.add(i)

		# Rebuild content without local imports
		cleaned_lines = []
		for i, line in enumerate(lines):
			if i not in lines_to_skip:
				cleaned_lines.append(line)
		
		return "".join(cleaned_lines).strip()

	def bundle(self):
		self.analyze_dependencies()
		sorted_modules = self.get_topological_order()
		
		print(f"Merge Order: {sorted_modules}")
		
		with open(self.output_filename, 'w', encoding='utf-8') as out:
			# 1. Header
			out.write(f"# Bundled from: {', '.join(self.modules.keys())}\n")
			out.write("# Auto-generated bundle\n\n")
			
			# 2. External Imports
			out.write("# --- External Imports ---\n")
			# Sort imports for cleanliness
			for imp in sorted(self.external_imports):
				out.write(imp + "\n")
			out.write("\n")
			
			# 3. Module Contents
			for mod_name in sorted_modules:
				out.write(f"# --- Module: {mod_name} ---\n")
				content = self.process_file_content(self.modules[mod_name])
				out.write(content)
				out.write("\n\n")
		
		print(f"Successfully created {self.output_filename}")

# --- Configuration to run the bundler on your files ---
if __name__ == "__main__":
	# Define your project structure here
	ENTRY_FILE = "src/main.py"
	
	# List all other modules your project relies on
	MODULES = [
		"src/ast_nodes.py", 
		"src/codegen.py", 
		"src/evaluator.py", 
		"src/grammar.py",
		"src/printing.py",
		"src/tests.py"
	]
	
	OUTPUT = "pike_standalone.py"

	bundler = PythonBundler(ENTRY_FILE, MODULES, OUTPUT)
	bundler.bundle()