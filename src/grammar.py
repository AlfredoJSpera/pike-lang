PIKE_GRAMMAR = r"""
    start: top_level*

    ?top_level: function_def
              | stmt                    -> top_level_stmt

    // Function Definition
    // items: 0=NAME, 1=args(opt), 2=ret(opt), 3=body
    function_def: "defunc" NAME "(" [args] ")" ["%" NAME] "{" body "}"
    
    args: arg ("," arg)*
    arg: NAME ":" NAME

    body: stmt*

    // Statements
    ?stmt: assignment ";"
         | return_stmt ";"
         | print_stmt ";"
         | if_stmt
         | for_stmt
         | expr ";"             -> expr_stmt

    assignment: NAME ":=" expr
    return_stmt: "ret" expr
    print_stmt: "!" "(" expr ")"   -> print_no_nl
              | "!!" "(" expr ")"  -> print_nl

    // If: items: 0=expr, 1=body, 2=else_body(opt)
    if_stmt: "if" "(" expr ")" "{" body "}" ["else" "{" body "}"]
    
    // For loop: for (x, 0; x < max_val; 1)
    for_stmt: "for" "(" NAME "," expr ";" expr ";" expr ")" "{" body "}"

    // Expressions with Precedence
    // Precedence: (<, >) -> (+, -) -> (*, /)
    
    ?expr: comparison

    ?comparison: sum
               | sum "<" sum  -> lt
               | sum ">" sum  -> gt

    ?sum: product
        | sum "+" product -> add
        | sum "-" product -> sub

    ?product: atom
            | product "*" atom -> mul
            | product "/" atom -> div

    ?atom: NUMBER           -> number
         | ESCAPED_STRING   -> string
         | NAME             -> var_load
         | "(" expr ")"

    // Terminals
    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /\d+(\.\d+)?/
    
    %import common.ESCAPED_STRING
    %import common.WS
    %import common.SH_COMMENT
    
    %ignore WS
    %ignore SH_COMMENT
"""