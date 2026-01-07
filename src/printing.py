

def print_boxed(label: str, text: str):
	"""
	Print something inside a box with a label.
	
	:param label: A label for the box.
	:param text: The text to show, even if it has new lines.
	"""
	lines = text.splitlines()

	# Determine the width based on the longest line or the title
	content_width = max(len(line) for line in lines) if lines else 0
	width = max(content_width, len(label)) + 4

	# Draw the box
	print(f"\n┌─ {label} {'─' * (width - len(label) - 3)}┐")
	for line in lines:
		print(f"│ {line.ljust(width - 2)} │")
	print(f"└{'─' * width}┘")