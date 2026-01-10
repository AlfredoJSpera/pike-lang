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
function: "defunc" name "()" "{" body "}"
body: statement*

// ===== Expressions
?expression: number | string | variable
variable: name

// ===== Terminals
name: NAME
number: FLOAT_NUMBER
string: STRING

%import python (NAME, STRING, FLOAT_NUMBER, COMMENT)
%import common.WS

%ignore WS
%ignore COMMENT
"""