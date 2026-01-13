PIKE_GRAMMAR = r"""
	start: top_level*

	?top_level: function_def
		| statement -> top_level_stmt
	
	// Function Definition
	function_def: "defunc" NAME "(" [parameters] ")" ["%" NAME] "{" body "}"
	
	parameters: par ("," par)*
	par: NAME ":" NAME

	body: statement*

	// Statements
	?statement: assignment ";"
		| return_stmt ";"
		| print_stmt ";"
		| if_stmt
		| for_stmt
		| expression ";" -> expr_stmt

	assignment: NAME ":=" expression
	return_stmt: "ret" expression
	print_stmt: "!" "(" expression ")" -> print_no_nl
		| "!!" "(" expression ")" -> print_nl
	
	if_stmt: "if" "(" expression ")" "{" body "}" ["else" "{" body "}"]
	for_stmt: "for" "(" NAME "," NUMBER ";" expression ";" NUMBER ")" "{" body "}"

	// Expressions with Precedence: (<, >) -> (+, -) -> (*, /)	
	?expression: comparison

	?comparison: sum
		| sum "<" sum  -> lt
		| sum ">" sum  -> gt

	?sum: product
		| sum "+" product -> add
		| sum "-" product -> sub

	?product: atom
		| product "*" atom -> mul
		| product "/" atom -> div

	?atom: NUMBER        -> number
		| ESCAPED_STRING -> string
		| NAME           -> var_load
		| function_call
		| "(" expression ")"

	function_call : NAME "(" [args] ")"
	args: expression ("," expression)*

	// Terminals
	NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
	NUMBER: /\d+(\.\d+)?/
	
	%import common.ESCAPED_STRING
	%import common.WS
	%import common.SH_COMMENT
	
	%ignore WS
	%ignore SH_COMMENT
"""