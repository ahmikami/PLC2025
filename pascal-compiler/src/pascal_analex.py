import ply.lex as lex
import sys

#palavras reservadas
reserved_map = {
    'program': 'PROGRAM', 
    'begin': 'BEGIN', 
    'end': 'END', 
    'var': 'VAR', 
    'integer': 'INTEGER', 
    'boolean': 'BOOLEAN', 
    'for': 'FOR', 
    'to': 'TO', 
    'do': 'DO', 
    'while': 'WHILE', 
    'if': 'IF', 
    'then': 'THEN', 
    'else': 'ELSE', 
    'div': 'DIV', 
    'mod': 'MOD', 
    'and': 'AND', 
    'array': 'ARRAY', 
    'of': 'OF', 
    'function': 'FUNCTION', 
    'procedure': 'PROCEDURE', 
    'string': 'STRING', 
    'downto': 'DOWNTO',
    'readln': 'READLN', 
    'writeln': 'WRITELN',
    'true': 'BOOL_LITERAL', 
    'false': 'BOOL_LITERAL' 
}
#tokens
tokens = list(set(reserved_map.values())) + ['ID','INT_LITERAL','STR_LITERAL',
    'OP_ASSIGN',
    'OP_LE',
    'OP_GE',
    'OP_NE',
    'OP_DOTDOT'
    ]

#simbolos literais
literals = [
    ';', ':', '.', ',', '(', ')', '[', ']',
    '=', '<', '>', '+', '-', '*'
]


#expressões regulares
t_OP_ASSIGN = r':=' #atribuição
t_OP_LE     = r'<=' 
t_OP_GE     = r'>='
t_OP_NE     = r'<>' #diferente
t_OP_DOTDOT = r'\.\.' #intervalo

#strings literais
def t_STR_LITERAL(t):
    r"'([^']|'')*'"
    return t

#inteiros literais
def t_INT_LITERAL(t):
    r'\d+'
    t.value = int(t.value) 
    t.type = 'INT_LITERAL'
    return t

#identificaderes de palavras reservadas
def t_ID(t): 
    r'[a-zA-Z_][a-zA-Z0-9_]*' 
    t.type = reserved_map.get(t.value.lower(), 'ID')
    return t

t_ignore = ' \t'

#tratamento de comentários da forma (* ___ *) ou { ___ } ou  // ___
def t_COMMENT(t):
    r'(\(\*[\s\S]*?\*\))|(\{[\s\S]*?\})|(//[^\n]*)'  
    pass


def t_newline(t): 
    r'\n+' 
    t.lexer.lineno += len(t.value)

def t_error(t): 
    print('Carácter desconhecido: ', t.value[0], 'Linha: ', t.lexer.lineno) 
    t.lexer.skip(1) 


lexer = lex.lex()


if __name__ == "__main__":
    
    
    input_code = sys.stdin.read()
    lexer.input(input_code)

    print("{:<15} {:<20} {:<10}".format("TIPO DO TOKEN", "VALOR (LEXEMA)", "LINHA"))
    print("-" * 45)

    while True:
        tok = lexer.token()
        if not tok:
            break
        print("{:<15} {:<20} {:<10}".format(tok.type, tok.value, tok.lineno))


#para testar cenas
# cat tests/bin_to_int.pas | python3 src/pascal_analex.py
# cat tests/fatorial.pas | python3 src/pascal_analex.py
# cat tests/hello.pas | python3 src/pascal_analex.py
# cat tests/primo_check.pas | python3 src/pascal_analex.py
# cat tests/soma_array.pas | python3 src/pascal_analex.py
