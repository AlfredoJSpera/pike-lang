from lark import Lark, Tree, Token

def print_tree_pretty(node, prefix="", is_last=True):
	"""
	Prints a Lark Tree using custom ASCII characters.
	"""
	# Define the symbols as requested
	elbow = "└──"
	pipe  = "│  "
	tee   = "├──"
	blank = "   "
	
	# Determine the connector for the current node
	connector = elbow if is_last else tee
	
	# Determine the content to print (Rule name for Trees, Value for Tokens)
	if isinstance(node, Tree):
		content = node.data
		children = node.children
	else:
		# It's a Token (leaf node)
		content = f"{node.type}: {repr(node.value)}"
		children = []

	# Print the current node
	print(f"{prefix}{connector} {content}")

	# Prepare the prefix for the children
	# If this node is the last one, its children don't see the pipe from this level
	child_prefix = prefix + (blank if is_last else pipe)

	# Recurse through children
	for i, child in enumerate(children):
		is_last_child = (i == len(children) - 1)
		print_tree_pretty(child, child_prefix, is_last_child)


calc_grammar = r"""
	start: instruction*

	?instruction: func_definition
				| statement

	// Functions
	func_definition: "defunc" prototype body
	prototype: NAME "(" (arg_sequence)? ")" "%" type
	arg_sequence: arg ("," arg)*
	arg: NAME ":" type
	body: "{" statement* "}"

	// Statements
	statement: stmt ";"
			 | if_statement
			 | for_statement
	
	?stmt: assignment
		 | return
		 | print_no_nl
		 | print_with_nl
		 | expression_top

	assignment: NAME "=" expression
	return: "ret" expression
	print_no_nl: "!" "(" expression ")"
	print_with_nl: "!!" "(" expression ")"

	// Expressions
	expression_top: expression // Used to make an anonymous expression
	expression_sequence: expression ("," expression)*
	?expression: compare
	
	// Precedence of operators ("<, >" -> "+, -" -> "*, /" -> atom)
	?compare: compare_operand ((LESS | GREATER) compare_operand)*
		?compare_operand: add
	?add: add_operand ((PLUS | MINUS) add_operand)*
		?add_operand: product
	?product: product_operand ((STAR | SLASH) product_operand)*
		?product_operand: atom

	// Atomic objects
	?atom: number
		| string
		| variable
		| func_call
		| "(" expression ")"
	
	number: NUMBER
	string: STRING
	variable: NAME
	func_call: NAME "(" (expression_sequence)? ")"
	
	// Control flow
	if_statement: "if" "(" expression ")" body ("else" body)?
	for_statement: "for" "(" loop_header? ";" expression? ";" loop_header? ")" body
    
    // Helper to allow "i = 0" or just "func_call()" inside the loop header
    ?loop_header: assignment
                | expression

	// Types
	type: NUM_TYPE
		| STR_TYPE
	
	// Terminals
	PLUS: "+"
	MINUS: "-"
	STAR: "*"
	SLASH: "/"
	LESS: "<"
	GREATER: ">"
	
	NUM_TYPE: "num"
	STR_TYPE: "str"
	
	// Import
	%import common.SH_COMMENT 		-> COMMENT
	%import common.CNAME 			-> NAME
	%import common.ESCAPED_STRING 	-> STRING
	%import common.NUMBER
	%import common.WS
	
	// Ignore
	%ignore WS
	%ignore COMMENT
"""

if __name__ == "__main__":
	# Create parser
	parser = Lark(calc_grammar, parser='lalr')
	
	# Parse input
	text = """
# Definizione funzione, ritorna un numero
defunc somma(a: num) % num {
	if (a > 1) {
		tmp = 0 + 0;
		result = tmp;
	} else {
		result = 1 + 1;
	}
	for (i = 2; i < result; i=i+1){
		result = result + 1;
	}
	ret result;
}
r = somma(2, 3); # Chiamata funzione
!("ciao");       # Stampa la stringa senza n
!!(r);           # Stampa il numero con n
"""
	tree = parser.parse(text)
	
	print(f"'{text}'")
	# We pass is_last=True to the root so it uses the 'elbow' (or you can adjust logic to print root differently)
	print_tree_pretty(tree)