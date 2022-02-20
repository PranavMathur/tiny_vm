quack_grammar = """
//the start symbol is start, which consists of a program
?start: program

//a program can have zero or more statements
?program: classes main_block

classes: class_*

class_: class_sig class_body

class_sig: "class" NAME "(" formal_args ")" ["extends" NAME]

formal_args: (formal_arg ("," formal_arg)*)?

formal_arg: NAME ":" NAME

class_body: "{" constructor methods "}"

constructor: statement*

methods: method*

method: "def" NAME "(" formal_args ")" [":" NAME] statement_block

statement_block: "{" statement* "}"

main_block: statement*

//a statement can be a right expression, an assignment,
//an if statement, or a while loop
?statement: r_exp ";"          -> raw_rexp
          | assignment ";"
          | "return" [r_exp] ";" -> ret_exp
          | if_stmt
          | while_lp

//an if statement consists of a condition, an execution block,
//zero or more elif statements, and an optional else statement
if_stmt: "if" condition block elifs else

//collection of zero or more elif statements
//useful to have elifs grouped during code generation
elifs: elif*

//an elif statement consists of a condition and an execution block
elif: "elif" condition block

//an else statement may consist of an execution block
else: ("else" block)?

//a while loop consists of a condition and an execution block
while_lp: "while" condition block

//a condition is a right expression
//the type checker will ensure that this evaluates to a boolean
condition: r_exp

//a block may be a collection of statements within braces
//or a single statement
block: "{" statement* "}"
     | statement

assignment: l_exp [":" type] "=" r_exp -> assign
          | r_exp "." NAME "=" r_exp   -> store_field
          | op_assign

op_assign: a_exp "+=" r_exp -> plus_equals
         | a_exp "-=" r_exp -> minus_equals
         | a_exp "*=" r_exp -> times_equals
         | a_exp "/=" r_exp -> divide_equals
         | a_exp "%=" r_exp -> mod_equals

?a_exp: NAME
      | r_exp "." NAME

//a type is an identifier
?type: NAME

//a left expression is a variable name
?l_exp: NAME

//a right expression is an expression or a method call
?r_exp: expr
      | m_call
      | c_call
      | r_exp "." NAME -> load_field

//a method call is a right expression, a method name, and zero or more arguments
m_call: r_exp "." NAME "(" args ")" -> m_call

//a method argument is a right expression
//zero or more arguments may be given
//a trailing comma is allowed
args: r_exp ("," r_exp)* (",")?
    |

c_call: NAME "(" args ")"

c_args: (r_exp ("," r_exp)*)?

//an expression can be a combination of the following
//combination of nonterminals
//the following nonterminals are ordered from lowest to highest precedence
?expr: or_exp

//"or" binds less tightly than "and" and is left-associative
?or_exp: and_exp
       | or_exp "or" and_exp -> or_exp

//"and" binds less tightly than equality and is left-associative
?and_exp: equality
        | and_exp "and" equality -> and_exp

//equality binds less tightly than comparison and is left-associative
?equality: comparison
         | equality "==" comparison -> equals
         | equality "!=" comparison -> notequals

//comparison binds less tightly than addition and is left-associative
?comparison: sum
           | comparison "<"  sum -> less
           | comparison "<=" sum -> atmost
           | comparison ">"  sum -> more
           | comparison ">=" sum -> atleast

//addition and subtraction bind less tightly
//than multiplication and is left-associative
?sum: product
    | sum "+" product -> plus
    | sum "-" product -> minus

//multiplication and division are the highest precedence binary operations,
//but bind less tightly than unary operators, literals,
//and parenthesized expressions
?product: atom
        | product "*" atom -> times
        | product "/" atom -> divide
        | product "%" atom -> mod

//an atom can be a literal, a unary operation on an atom,
//or a parenthesized expression
?atom: NUMBER       -> lit_number
     | "-" atom     -> neg
     | "not" atom   -> negate
     | l_exp        -> var
     | "(" r_exp ")"
     | boolean
     | nothing
     | string       -> lit_string

//a boolean can be a literal true or false
?boolean: "true"  -> lit_true
        | "false" -> lit_false

//a "nothing" object can only be a literal "none"
?nothing: "none"  -> lit_nothing

//strings are predefined by lark
?string: ESCAPED_STRING

%import common.NUMBER
%import common.ESCAPED_STRING
%import common.CNAME -> NAME
%import common.C_COMMENT
%import common.CPP_COMMENT
%import common.WS_INLINE
%import common.WS

%ignore C_COMMENT
%ignore CPP_COMMENT
%ignore WS_INLINE
%ignore WS
"""
