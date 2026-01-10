# pike

Algorithm to determine AST structure from grammar:

1. For each line of the grammar, see the name of the rule.
2. Ignore "start", it is handled in ToAst.
3. If the rule is only a terminal, develop it in the `ToAst` class, do eventual adjustments, and make it return something that it should reflect.

```
rule_A: TERMINAL
--> class RuleA
--> def TERMINAL(self, token): return elaborated_token
```

4. If it is a rule with options, make it into an abstract class.

```
rule_A: a | b | c  -->  class _RuleA
```

5. If the rule A is an option in a rule B with options, the rule A will extend the rule B.

```
rule_A: rule_B | C  --> RuleB(RuleA)
```

6. If the rule B is just part of other rules A that are not options, it will extend the `_Ast` class.

```
rule_A: "(" rule_B ")" rule_C "+" rule_D
rule_E: rule_B  -->  RuleB(_Ast)
```

7. If the rule has only a rule and `*`, make the rule extend also `AsList`.

```
rule_A: rule_B*  -->  class RuleA(..., AsList): rule_bs: List[RuleB]
```