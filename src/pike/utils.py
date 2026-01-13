import dataclasses
import re
import sys
from lark import Tree

def print_error(message: str):
	"""Prints a message on stderr."""
	print(message, file=sys.stderr)


def print_boxed(label: str, text: str):
	"""Prints something inside a box with a label."""

	def visible_len(text: str) -> int:
		"""Calculates the length of a string excluding ANSI escape sequences."""
		ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
		return len(ansi_escape.sub('', text))
	
	lines = text.splitlines()

	# Calculate the width needed
	content_width = max(visible_len(line) for line in lines) if lines else 0
	label_width = visible_len(label)
	width = max(content_width, label_width) + 2
	
	# Draw the Top Border
	top_dashes = width - label_width - 1
	print(f"\n┌─ {label} {'─' * top_dashes}┐")

	# Draw the Content Lines
	for line in lines:
		padding = " " * (width - visible_len(line))
		print(f"│ {line}{padding} │")

	# Draw the Bottom Border
	print(f"└{'─' * (width + 2)}┘")


def pretty_lark_tree(node, prefix="", is_last=True, is_root=True):
	"""Returns a string representation of a Lark Tree."""
	elbow = "└── "
	pipe  = "│   "
	tee   = "├── "
	blank = "    "
	
	# Determine the connector
	if is_root:
		connector = ""
	else:
		connector = elbow if is_last else tee

	# Determine the content
	if isinstance(node, Tree):
		content = str(node.data)
		children = node.children
	else:
		# It's a Token (leaf node)
		if node is not None:
			content = f"{node.type}: {repr(node.value)}"
		else:
			content = node
		
		children = []

	# Start the result with the current node
	lines = [f"{prefix}{connector}{content}"]

	# Prepare the prefix for the children
	if is_root:
		new_prefix = ""
	else:
		new_prefix = prefix + (blank if is_last else pipe)

	# Recurse through children and collect their strings
	for i, child in enumerate(children):
		is_last_child = (i == len(children) - 1)
		# Capture the returned string from the child
		child_str = pretty_lark_tree(child, new_prefix, is_last_child, is_root=False)
		lines.append(child_str)
	
	# Join everything with newlines
	return "\n".join(lines)

def pretty_ast(node, prefix="", is_last=True, is_root=True):
	"""
	Returns a formatted string representation of a custom dataclass AST.
	Recursive function that handles Lists and Primitives gracefully.
	"""
	elbow = "└── "
	pipe  = "│   "
	tee   = "├── "
	blank = "    "

	# 1. Determine the connector
	if is_root:
		connector = ""
	else:
		connector = elbow if is_last else tee

	# 2. Get the Node Name
	node_name = node.__class__.__name__
	lines = [f"{prefix}{connector}{node_name}"]

	# 3. Calculate new prefix for children
	if is_root:
		new_prefix = ""
	else:
		new_prefix = prefix + (blank if is_last else pipe)

	# 4. Collect Children
	# We separate actual AST nodes from primitive values (like strings/numbers)
	children = []
	
	if dataclasses.is_dataclass(node):
		for field in dataclasses.fields(node):
			value = getattr(node, field.name)
			
			# Case A: List of nodes (e.g. Body.statements)
			if isinstance(value, list):
				for item in value:
					children.append(item)
			
			# Case B: Nested AST Node (e.g. Assignment.variable)
			elif dataclasses.is_dataclass(value):
				children.append(value)
			
			# Case C: Primitive Value (e.g. Name.value, Number.value)
			else:
				# We format this as a string to be a "leaf" child
				children.append(f"{field.name}: {repr(value)}")

	# 5. Process Children
	for i, child in enumerate(children):
		is_last_child = (i == len(children) - 1)
		
		if isinstance(child, str):
			# It's a primitive leaf (e.g., "value: 'x'")
			child_connector = elbow if is_last_child else tee
			lines.append(f"{new_prefix}{child_connector}{child}")
		else:
			# It's a complex node, recurse
			lines.append(pretty_ast(child, new_prefix, is_last_child, is_root=False))

	return "\n".join(lines)