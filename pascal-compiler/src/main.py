import sys
from pascal_analex import lexer
from pascal_anasin import parser, ts
from pascal_codegen import CodeGenerator

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 main.py <ficheiro.pas>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        content = f.read()

    #analise léxica e sintática (constroi a AST)
    result = parser.parse(content, lexer=lexer)

    if result:
        # geração de código
        codegen = CodeGenerator(result, ts)
        codegen.generate()
    else:
        print("Erro na compilação.")