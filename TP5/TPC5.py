import ply.lex as lex
import json
import sys
import datetime as datetime

tokens = (
    'MOEDA',
    'EUROS',
    'CENTIMOS',
    'DOT',
    'SELECIONAR',
    'CODIGO',
    'SALDO',
    'LISTAR',
    'SAIR',
    'VIRGULA',
)

t_DOT = r'\.'
t_VIRGULA = r','

def t_MOEDA(t):
    r'MOEDA'
    return t

def t_EUROS(t):
    r'(2e|1e)'
    t.value = int(t.value[:-1]) * 100
    return t

def t_CENTIMOS(t):
    r'(50c|20c|10c|5c|2c|1c)'
    t.value = int(t.value[:-1])
    return t

def t_SELECIONAR(t):
    r'SELECIONAR'
    return t   

def t_CODIGO(t):
    r'[A-Z]\d{2}'
    return t

def t_SALDO(t):
    r'SALDO'
    return t

def t_LISTAR(t):
    r'LISTAR'
    return t

def t_SAIR(t):
    r'SAIR'
    return t

t_ignore = ' \t\n'

def t_error(t):
    print(f"Carácter ilegal: {t.value[0]}")
    t.lexer.skip(1)

lexer = lex.lex()

def format_saldo(valor):
    e, c = divmod(valor, 100)
    return f"{e}e{c:02d}c" if e else f"{c}c"

def calcula_troco(valor):
    moedas = [200, 100, 50, 20, 10, 5, 2, 1]
    troco = []
    for m in moedas:
        qtd, valor = divmod(valor, m)
        if qtd:
            troco.append(f"{qtd}x {format_saldo(m)}")
    return ", ".join(troco) if troco else "sem troco"

try:
    with open("stock.json", "r") as f:
        stock = json.load(f)
except FileNotFoundError:
    stock = [
        {"cod": "A23", "nome": "água 0.5L", "quant": 8, "preco": 0.7},
        {"cod": "B11", "nome": "Cookies", "quant": 5, "preco": 0.9},
        {"cod": "F37", "nome": "Palmier", "quant": 3, "preco": 0.75},
    ]

lexer.saldo = 0

print(f"maq: {datetime.date.today()}, Stock carregado, Estado atualizado.")
print("maq: Bom dia. Estou disponível para atender o seu pedido.")

while True:
    linha = input(">> ").strip()
    if not linha:
        continue

    lexer.input(linha)
    tokens_list = list(lexer)

    if not tokens_list:
        continue

    tok0 = tokens_list[0]

    if tok0.type == 'MOEDA':
        for t in tokens_list[1:]:
            if t.type in ('EUROS', 'CENTIMOS'):
                lexer.saldo += t.value
            elif t.type == 'DOT':
                break
        print(f"maq: Saldo = {format_saldo(lexer.saldo)}")

    elif tok0.type == 'LISTAR':
        print("maq:")
        print("cod | nome | quant | preço")
        print("---------------------------------")
        for item in stock:
            print(f"{item['cod']:4} | {item['nome']:<12} | {item['quant']:5} | {item['preco']:.2f}")

    elif tok0.type == 'SALDO':
        print(f"maq: Saldo = {format_saldo(lexer.saldo)}")

    elif tok0.type == 'SELECIONAR':
        if len(tokens_list) < 2 or tokens_list[1].type != 'CODIGO':
            print("maq: Código de produto em falta.")
            continue
        cod = tokens_list[1].value
        produto = next((i for i in stock if i["cod"] == cod), None)
        if not produto:
            print("maq: Produto inexistente.")
            continue
        if produto["quant"] == 0:
            print("maq: Produto esgotado.")
            continue
        preco = int(produto["preco"] * 100)
        if lexer.saldo < preco:
            print(f"maq: Saldo insuficiente ({format_saldo(lexer.saldo)}); Pedido = {format_saldo(preco)}")
            continue
        produto["quant"] -= 1
        lexer.saldo -= preco
        print(f'maq: Pode retirar o produto "{produto["nome"]}".')
        print(f"maq: Saldo = {format_saldo(lexer.saldo)}")

    elif tok0.type == 'SAIR':
        print("maq: Pode retirar o troco:", calcula_troco(lexer.saldo))
        print("maq: Até à próxima.")
        with open("stock.json", "w") as f:
            json.dump(stock, f, indent=4)
        sys.exit(0)

    else:
        print("maq: Comando não reconhecido.")

