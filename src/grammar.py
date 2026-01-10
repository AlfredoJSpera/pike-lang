PIKE_GRAMMAR = r"""
?start: program
program: instruction*
?instruction: function | statement

// ===== Statement
?statement: assignment | if_statement | print_nl


assignment: variable ":=" expression ";"

if_statement: "if" "(" expression ")" "{" body "}"

print_nl: "!!(" expression ");"

// ===== Function
function: "defunc" prototype "{" body "}"
prototype: NAME "(" arg_sequence ")" ("%" type)?
arg_sequence: (arg ("," arg)*)?
arg: NAME ":" type
body: statement*

// ===== Expressions
?expression: number | string | variable
variable: NAME

// ===== Terminals
?number: FLOAT_NUMBER
?string: STRING
?type: TYPE_NAME

TYPE_NAME: "num" | "str"

%import python (NAME, STRING, FLOAT_NUMBER, COMMENT)
%import common.WS

%ignore WS
%ignore COMMENT
"""