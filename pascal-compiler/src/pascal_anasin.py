import ply.yacc as yacc
from pascal_analex import tokens, literals, lexer
from pascal_anasem import SymbolTable
import sys
import pprint

# inicializar a análise semântica
ts = SymbolTable()

# precedência (ordem) dos operadores
precedence = (
    ('left', 'AND'),
    ('left', '=', 'OP_NE', 'OP_LE', 'OP_GE', '<', '>'),
    ('left', '+', '-'),
    ('left', '*', 'DIV', 'MOD'),
)

# define o que é um programa
def p_programa(p):
    '''
    programa : PROGRAM ID ';' lista_definicoes bloco '.'
    '''
    # organiza a AST com o nome do programa, a lista de definições e o bloco principal
    p[0] = ('PROGRAM', p[2], p[4], p[5])

def p_lista_definicoes(p):
    '''
    lista_definicoes : lista_definicoes definicao
                     | empty
    '''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]

def p_definicao(p):
    '''
    definicao : declaracoes_var
              | subprograma
    '''
    p[0] = p[1]

#declaração de variáveis
def p_declaracoes_var(p):
    '''
    declaracoes_var : VAR lista_declaracoes_tipo
    '''
    p[0] = ('VAR_BLOCK', p[2])

def p_lista_declaracoes_tipo(p):
    '''
    lista_declaracoes_tipo : lista_declaracoes_tipo declaracao_tipo ';'
                           | declaracao_tipo ';'
    '''
    if len(p) == 4:
        p[0] = p[1] + [p[2]] 
    else:
        p[0] = [p[1]]

def p_declaracao_tipo(p):
    '''
    declaracao_tipo : lista_ids ':' tipo
    '''
    # registar variáveis na tabela de símbolos
    for nome_var in p[1]:
        ts.add(nome_var, p[3], 'VAR')
    
    p[0] = ('DECL', p[1], p[3])


def p_lista_ids(p):
    '''
    lista_ids : lista_ids ',' ID
              | ID
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

#tipos de variáveis
def p_tipo(p):
    '''
    tipo : INTEGER
         | BOOLEAN
         | STRING
         | ARRAY '[' INT_LITERAL OP_DOTDOT INT_LITERAL ']' OF tipo
    '''
    if p.slice[1].type == 'ARRAY':
        p[0] = ('ARRAY_TYPE', p[3], p[5], p[8])
    else:
        # normalizar nome do tipo para MAIÚSCULAS
        p[0] = ('TYPE', p[1].upper())

# regras auxiliares para gerir scopes
def p_config_decl_func(p):
    '''config_decl_func : FUNCTION ID'''
    # declarar função no scope externo (tipo de retorno desconhecido ainda)
    ts.add(p[2], ('TYPE', 'UNKNOWN'), 'FUNCTION')
    p[0] = p[2]
    ts.enter_scope()

#igual mas para procedimentos em vez de funções
def p_config_decl_proc(p):
    '''config_decl_proc : PROCEDURE ID'''
    ts.add(p[2], ('TYPE', 'UNKNOWN'), 'PROCEDURE')
    p[0] = p[2]
    ts.enter_scope()

def p_cabecalho_func(p):
    '''cabecalho_func : config_decl_func '(' parametros_opt ')' ':' tipo ';' '''
    # atualizar tipo de retorno no scope externo
    ts.update_type(p[1], p[6])
    p[0] = (p[1], p[3], p[6]) # nome, params, tipo_retorno

def p_cabecalho_proc(p):
    '''cabecalho_proc : config_decl_proc '(' parametros_opt ')' ';' '''
    p[0] = (p[1], p[3]) # nome, params

def p_subprograma(p):
    '''
    subprograma : cabecalho_func lista_definicoes bloco ';'
                | cabecalho_proc lista_definicoes bloco ';'
    '''
    ts.exit_scope()

    if p.slice[1].type == 'cabecalho_func':
        nome, params, tipo_retorno = p[1]
        p[0] = ('FUNCTION', nome, params, tipo_retorno, p[2], p[3])
    else:
        nome, params = p[1]
        p[0] = ('PROCEDURE', nome, params, p[2], p[3])


def p_parametros_opt(p):
    '''
    parametros_opt : lista_parametros
                   | empty
    '''
    p[0] = p[1] if p[1] else []

def p_lista_parametros(p):
    '''
    lista_parametros : lista_parametros ';' declaracao_tipo
                     | declaracao_tipo
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

#bloco e comandos
def p_bloco(p):
    '''
    bloco : BEGIN lista_comandos END
    '''
    p[0] = ('BLOCK', p[2])

def p_lista_comandos(p):
    '''
    lista_comandos : lista_comandos ';' comando
                   | comando
    '''
    if len(p) == 2:
        p[0] = [p[1]] if p[1] is not None else []
    else:
        if p[3] is not None:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = p[1]

def p_comando(p):
    '''
    comando : atribuicao
            | leitura
            | escrita
            | condicional
            | ciclo_for
            | ciclo_while
            | bloco
            | chamada_subprograma
            | empty
    '''
    p[0] = p[1]

#definição de cada comando
def p_atribuicao(p):
    '''
    atribuicao : ID OP_ASSIGN expressao
               | ID '[' expressao ']' OP_ASSIGN expressao
    '''
    if len(p) == 4:
        # ID := expressao
        nome_var = p[1]
        nodo_expr = p[3]
        
        # verificar existência
        sym = ts.lookup(nome_var, p.lineno(1))
        
        if sym:
            tipo_var = sym['type']
            tipo_expr = nodo_expr[-1] # extrair tipo da expressão (que é o último elemento do tuple)
        
            if tipo_var != tipo_expr:
                print(f"ERRO SEMÂNTICO: Atribuição incompatível na linha {p.lineno(2)}. Esperado {tipo_var}, encontrado {tipo_expr}")
            
        p[0] = ('ASSIGN', p[1], p[3])
    else:
        # atribuição de Array
        p[0] = ('ARRAY_ASSIGN', p[1], p[3], p[6])


def p_leitura(p):
    '''
    leitura : READLN '(' lista_expressoes_opt ')'
    '''
    p[0] = ('READLN', p[3])

def p_escrita(p):
    '''
    escrita : WRITELN '(' lista_expressoes_opt ')'
    '''
    p[0] = ('WRITELN', p[3])


def p_condicional(p):
    '''
    condicional : IF expressao THEN comando
                | IF expressao THEN comando ELSE comando
    '''
    if len(p) == 5:
        p[0] = ('IF', p[2], p[4], None)
    else:
        p[0] = ('IF', p[2], p[4], p[6])

def p_ciclo_for(p):
    '''
    ciclo_for : FOR ID OP_ASSIGN expressao TO expressao DO comando
              | FOR ID OP_ASSIGN expressao DOWNTO expressao DO comando
    '''
    p[0] = ('FOR', p[2], p[4], p[6], p[8], p[5])

def p_ciclo_while(p):
    '''
    ciclo_while : WHILE expressao DO comando
    '''
    p[0] = ('WHILE', p[2], p[4])

def p_chamada_subprograma(p):
    '''
    chamada_subprograma : ID '(' lista_expressoes_opt ')'
    '''
    p[0] = ('CALL_STMT', p[1], p[3])

#expressões
def p_expressao_binaria(p):
    '''
    expressao : expressao '+' expressao
              | expressao '-' expressao
              | expressao '*' expressao
              | expressao DIV expressao
              | expressao MOD expressao
              | expressao '<' expressao
              | expressao '>' expressao
              | expressao OP_LE expressao
              | expressao OP_GE expressao
              | expressao OP_NE expressao
              | expressao '=' expressao
              | expressao AND expressao
    '''
    op = p[2].upper() #normalizar operadores para maiúsculas
    esq = p[1]
    dir = p[3]
    
    tipo1 = esq[-1]
    tipo2 = dir[-1]
    
    tipo_resultado = None
    
    # aritmética
    if op in ['+', '-', '*', 'DIV', 'MOD']:
        if tipo1 == ('TYPE', 'INTEGER') and tipo2 == ('TYPE', 'INTEGER'):
            tipo_resultado = ('TYPE', 'INTEGER')
        else:
            print(f"ERRO SEMÂNTICO: Operação aritmética '{op}' requer INTEGERS. Encontrado {tipo1} e {tipo2} na linha {p.lineno(2)}")
            tipo_resultado = ('TYPE', 'ERROR')
            
    # relações e boleanos
    elif op in ['<', '>', '<=', '>=', '<>', '=', 'AND']:
         # Verificação simplificada: tipos devem ser iguais
         if tipo1 == tipo2:
             tipo_resultado = ('TYPE', 'BOOLEAN')
         else:
             print(f"ERRO SEMÂNTICO: Operação '{op}' tipos incompatíveis {tipo1}, {tipo2} na linha {p.lineno(2)}")
             tipo_resultado = ('TYPE', 'ERROR')
             
    p[0] = ('BINOP', op, esq, dir, tipo_resultado)


def p_expressao_grupo(p):
    '''
    expressao : '(' expressao ')'
    '''
    p[0] = p[2]

def p_expressao_valor(p):
    '''
    expressao : ID
              | INT_LITERAL
              | STR_LITERAL
              | BOOL_LITERAL
              | ID '[' expressao ']'
              | ID '(' lista_expressoes_opt ')'
    '''
    if len(p) == 2:
        if p.slice[1].type == 'ID':
            # consultar ID
            sym = ts.lookup(p[1], p.lineno(1))

            if sym:
                p[0] = ('ID', p[1], sym['type'])
            else:
                p[0] = ('ID', p[1], ('TYPE', 'ERROR'))

        elif p.slice[1].type == 'INT_LITERAL':
            p[0] = ('INT', p[1], ('TYPE', 'INTEGER'))
        elif p.slice[1].type == 'STR_LITERAL':
            p[0] = ('STRING', p[1], ('TYPE', 'STRING'))
        elif p.slice[1].type == 'BOOL_LITERAL':
            p[0] = ('BOOL', p[1], ('TYPE', 'BOOLEAN'))
    
    elif p[2] == '[':
        sym = ts.lookup(p[1], p.lineno(1))
        tipo_elemento = ('TYPE', 'UNKNOWN')
        
        if sym:
            tipo_sym = sym['type']
            if tipo_sym[0] == 'ARRAY_TYPE':
                tipo_elemento = tipo_sym[3]
            elif tipo_sym == ('TYPE', 'STRING'):
                tipo_elemento = ('TYPE', 'STRING')

        p[0] = ('ARRAY_ACCESS', p[1], p[3], tipo_elemento)
    
    else:

        sym = ts.lookup(p[1], p.lineno(1))
        tipo_ret = ('TYPE', 'ERROR')
        
        if sym:
            tipo_ret = sym['type']
        
        p[0] = ('CALL_EXP', p[1], p[3], tipo_ret)

def p_lista_expressoes_opt(p):
    '''
    lista_expressoes_opt : lista_expressoes
                         | empty
    '''
    p[0] = p[1] if p[1] else []

def p_lista_expressoes(p):
    '''
    lista_expressoes : lista_expressoes ',' expressao
                     | expressao
    '''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_empty(p):
    'empty :'
    pass

def p_error(p):
    if p:
        print(f"ERRO SINTÁTICO: Token inesperado '{p.value}' na linha {p.lineno}")
    else:
        print("ERRO SINTÁTICO: Fim de ficheiro inesperado")

#execução
parser = yacc.yacc()

if __name__ == "__main__":
    input_code = sys.stdin.read()
    if input_code.strip():
        result = parser.parse(input_code, lexer=lexer)
        print("\nÁrvore Sintática (AST)")
        print("-" * 50)
        pprint.pprint(result) if result else print("Erro: AST não gerada")