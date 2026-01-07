import re

def visible_len(text: str) -> int:
    """Calculates the length of a string excluding ANSI escape sequences."""
    # This regex matches the ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return len(ansi_escape.sub('', text))

def print_boxed(label: str, text: str):
    """
    Print something inside a box with a label, handling ANSI colored text correctly.
    """
    lines = text.splitlines()

    # 1. Use visible_len for the width calculations
    content_width = max(visible_len(line) for line in lines) if lines else 0
    label_width = visible_len(label)
    
    # Total internal width needed
    width = max(content_width, label_width) + 2

    # 2. Draw the Top Border
    # We subtract 1 from the dash count because of the space after the label
    top_dashes = width - label_width - 1
    print(f"\n┌─ {label} {'─' * top_dashes}┐")

    # 3. Draw the Content Lines
    for line in lines:
        # Calculate how much padding is needed based on visible length
        padding = " " * (width - visible_len(line))
        print(f"│ {line}{padding} │")

    # 4. Draw the Bottom Border
    print(f"└{'─' * (width + 2)}┘")