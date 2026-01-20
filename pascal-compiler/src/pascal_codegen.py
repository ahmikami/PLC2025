import sys

class CodeGenerator:
    def __init__(self, parser_result, symbol_table):
        """
        Inicializa o Gerador de Código.
        :param parser_result: A Árvore Sintática (AST).
        :param symbol_table: A Tabela de Símbolos (TS).
        """
        self.ast = parser_result
        self.ts = symbol_table
        self.label_count = 0


    #funções auxiliares
    def get_new_label(self):
        """Gera etiquetas únicas (L1, L2...) para saltos."""
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, instruction):
        """Imprime uma instrução com indentação."""
        print(f"\t{instruction}")

    def emit_label(self, label):
        """Imprime uma etiqueta (Label)."""
        print(f"{label}:")


    #visitor / o que vai percorrer a AST
    def generate(self):
        """Ponto de entrada da geração."""
        if self.ast:
            self.visit(self.ast)

    def visit(self, node):
        """Despacho dinâmico: procura o método visit_TIPO para cada nó."""
        if not isinstance(node, tuple):
            return

        node_type = node[0]
        method_name = f'visit_{node_type}'
        
        # Tenta encontrar o método específico, senão usa o genérico
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Debug: avisa se encontrarmos um nó desconhecido."""
        #print(f"; AVISO: Nó ignorado {node[0]}") #debug
        pass


    #estrutura do programa
    def visit_PROGRAM(self, node):
        print("START")
        
        definitions = node[2] # lista de variáveis e funções
        
        # percorre uma vez para declarar variáveis globais
        for idef in definitions:
            if idef[0] == 'VAR_BLOCK':
                self.visit(idef)
        
        # percorre uma segunda vez para o corpo principal do prorgama ("main")
        self.visit(node[3]) 
        
        print("STOP") # o programa acaba aqui para a VM

        # percorre uma terceira vez para funções e procedimentos isolados
        for idef in definitions:
            if idef[0] in ['FUNCTION', 'PROCEDURE']:
                self.visit(idef)

    def visit_VAR_BLOCK(self, node):
        for decl in node[1]:
            self.visit(decl)

    def visit_DECL(self, node):
        """
        Declara variáveis. 
        Se for ARRAY, aloca memória na Heap (ALLOCN).
        Se for simples, apenas reserva espaço na Stack (PUSHN).
        """
        var_names = node[1]
        var_type = node[2]
        
        # reservar espaço na stack (1 slot por variável ou pointer)
        self.emit(f"PUSHN {len(var_names)}")

        # se for array, alocar memória na heap
        if var_type[0] == 'ARRAY_TYPE':
            # var_type = ('ARRAY_TYPE', inicio, fim, tipo_elemento)
            start = int(var_type[1])
            end = int(var_type[2])
            size = end - start + 1
            
            for name in var_names:
                sym = self.ts.lookup(name)
                if not sym: continue

                # alocar n espaços na heap
                self.emit(f"PUSHI {size}")
                self.emit("ALLOCN") # coloca o endereço na stack
                
                # guardar o pointer
                if sym['scope'] == 'GLOBAL':
                    self.emit(f"STOREG {sym['offset']}")
                else:
                    self.emit(f"STOREL {sym['offset']}")

    def visit_BLOCK(self, node):
        for cmd in node[1]:
            self.visit(cmd)


    #visitar funções e procedimentos
    def visit_FUNCTION(self, node):
        func_name = node[1]
        params = node[2]
        defs = node[4]
        body = node[5]

        self.emit_label(func_name)
        
        # reconstruir o scope é necessário porque o parser apagou as variáveis locais
        self.ts.enter_scope()

        # parâmetros (offsets negativos, até -1)
        total_params = sum(len(p[1]) for p in params)
        current_idx = 0
        for decl in params:
            for name in decl[1]:
                # offset relativo ao frame pointer (FP)
                offset = -(total_params - current_idx)
                # adicionar manualmente à TS e forçar offset
                self.ts.add(name, decl[2], 'VAR')
                self.ts.scope_stack[-1][name.lower()]['offset'] = offset
                current_idx += 1

        # variáveis Locais (offsets positivos)
        for definition in defs:
            if definition[0] == 'VAR_BLOCK':
                for decl in definition[1]:
                    for name in decl[1]:
                        self.ts.add(name, decl[2], 'VAR')
                # gerar código de alocação (PUSHN/ALLOCN)
                self.visit(definition) 

        # corpo da função
        self.visit(body)

        self.ts.exit_scope()
        self.emit("RETURN")

    def visit_PROCEDURE(self, node):
        proc_name = node[1]
        params = node[2]
        # dependendo da gramática, defs pode estar em índice 3 ou 2, daí a necessidade de ajustar às vezs
        defs = node[3] if len(node) > 4 else []
        body = node[4] if len(node) > 4 else node[3]

        self.emit_label(proc_name)
        self.ts.enter_scope()

        # parametros
        total_params = sum(len(p[1]) for p in params)
        current_idx = 0
        for decl in params:
            for name in decl[1]:
                offset = -(total_params - current_idx)
                self.ts.add(name, decl[2], 'VAR')
                self.ts.scope_stack[-1][name.lower()]['offset'] = offset
                current_idx += 1

        # instancias locais
        if isinstance(defs, list):
            for definition in defs:
                if definition[0] == 'VAR_BLOCK':
                    for decl in definition[1]:
                        for name in decl[1]:
                            self.ts.add(name, decl[2], 'VAR')
                    self.visit(definition)
        
        self.visit(body)
        self.ts.exit_scope()
        self.emit("RETURN")


    #comandos / statements
    def visit_ASSIGN(self, node):
        # node = ('ASSIGN', nome, expr)
        self.visit(node[2]) #ver tipo da expressão
        
        var_name = node[1]
        sym = self.ts.lookup(var_name)
        
        if not sym:
            return #erro

        # verificar se é retorno de função
        if sym['category'] == 'FUNCTION' and sym['scope'] == 'GLOBAL':
            self.emit("STOREL -2") # slot de return padrão (ajustar se >1 param)
        elif sym['scope'] == 'GLOBAL':
            self.emit(f"STOREG {sym['offset']}")
        else:
            self.emit(f"STOREL {sym['offset']}")

    def visit_ARRAY_ASSIGN(self, node):
        # node = ('ARRAY_ASSIGN', nome, indice, valor)
        var_name = node[1]
        idx_expr = node[2]
        val_expr = node[3]
        
        sym = self.ts.lookup(var_name)
        
        # a instrução STOREN precisa que na stack haja: [endereço, indice, valor]
        
        # endereço (pointer do array)
        if sym['scope'] == 'GLOBAL':
            self.emit("PUSHGP")
            self.emit(f"PUSHI {sym['offset']}")
            self.emit("PADD")
        else:
            self.emit("PUSHFP")
            self.emit(f"PUSHI {sym['offset']}")
            self.emit("PADD")

        # indice
        self.visit(idx_expr)
        self.emit("PUSHI 1")
        self.emit("SUB")

        # valor
        self.visit(val_expr)
        
        self.emit("STOREN")

    def visit_READLN(self, node):
        for var_node in node[1]:
            # caso especial: ler para um array
            if isinstance(var_node, tuple) and var_node[0] == 'ARRAY_ACCESS':
                var_name = var_node[1]
                idx_expr = var_node[2]
                sym = self.ts.lookup(var_name)
                
                # endereço
                if sym['scope'] == 'GLOBAL':
                    self.emit(f"PUSHG {sym['offset']}")
                else:
                    self.emit(f"PUSHL {sym['offset']}")
                
                # idice
                self.visit(idx_expr)
                self.emit("PUSHI 1")
                self.emit("SUB")

                # leitura e conversão
                self.emit("READ")
                self.emit("ATOI") # assumimos que é array de inteiros
                
                # guardar
                self.emit("STOREN")

            # caso normal: ler uma variável
            else:
                var_name = var_node[1] if isinstance(var_node, tuple) else var_node
                sym = self.ts.lookup(var_name)
                
                self.emit("READ")
                if sym and sym['type'] == ('TYPE', 'INTEGER'):
                    self.emit("ATOI") # converter para inteiro
                
                if sym:
                    if sym['scope'] == 'GLOBAL':
                        self.emit(f"STOREG {sym['offset']}")
                    else:
                        self.emit(f"STOREL {sym['offset']}")

    def visit_WRITELN(self, node):
        for expr in node[1]:
            self.visit(expr)
            if expr[-1] == ('TYPE', 'STRING'):
                self.emit("WRITES")
            else:
                self.emit("WRITEI")
        self.emit("WRITELN")


    #controlo de fluxo
    def visit_IF(self, node):
        l_else = self.get_new_label()
        l_end = self.get_new_label()

        self.visit(node[1])       # if
        self.emit(f"JZ {l_else}") # jump se falso (zero)
        
        self.visit(node[2])       # then
        self.emit(f"JUMP {l_end}")
        
        self.emit_label(l_else)
        if node[3]: self.visit(node[3]) # else
        
        self.emit_label(l_end)

    def visit_WHILE(self, node):
        l_start = self.get_new_label()
        l_end = self.get_new_label()

        self.emit_label(l_start)
        self.visit(node[1])       #condição do while
        self.emit(f"JZ {l_end}")
        
        self.visit(node[2])       # corpo
        self.emit(f"JUMP {l_start}")
        self.emit_label(l_end)

    def visit_FOR(self, node):
        # ('FOR', var, start, end, body, direction)
        var_name = node[1]
        start_expr = node[2]
        end_expr = node[3]
        body = node[4] 
        direction = node[5].lower()

        sym = self.ts.lookup(var_name)
        if not sym: return

        store = f"STOREG {sym['offset']}" if sym['scope'] == 'GLOBAL' else f"STOREL {sym['offset']}"
        push = f"PUSHG {sym['offset']}" if sym['scope'] == 'GLOBAL' else f"PUSHL {sym['offset']}"

        # inicializar
        self.visit(start_expr)
        self.emit(store)

        l_loop = self.get_new_label()
        l_end = self.get_new_label()
        self.emit_label(l_loop)

        # condição de paragem
        self.emit(push)
        self.visit(end_expr)
        self.emit("INFEQ" if direction == 'to' else "SUPEQ")
        self.emit(f"JZ {l_end}")

        # corpo do for
        self.visit(body)

        # incrementar / decrementar contador
        self.emit(push)
        self.emit("PUSHI 1")
        self.emit("ADD" if direction == 'to' else "SUB")
        self.emit(store)
        self.emit(f"JUMP {l_loop}")
        self.emit_label(l_end)


    #expressões
    def visit_BINOP(self, node):
        left = node[2]
        right = node[3]
        op = node[1].upper()
        
        # se compararmos bin[i] (CHARAT devolve int) com '1' (string), convertemos o '1' para o seu valor ASCII
        
        # se bin[i] = '1'
        if left[0] == 'ARRAY_ACCESS' and right[0] == 'STRING' and len(right[1]) == 3:
            self.visit(left)
            char_val = right[1].replace("'", "")
            self.emit(f"PUSHI {ord(char_val)}") # ASCII do char
            
        # se '1' = bin[i]
        elif right[0] == 'ARRAY_ACCESS' and left[0] == 'STRING' and len(left[1]) == 3:
            char_val = left[1].replace("'", "")
            self.emit(f"PUSHI {ord(char_val)}")
            self.visit(right)
            
        # caso padrão
        else:
            self.visit(left)
            self.visit(right)

        ops = {'+':'ADD', '-':'SUB', '*': 'MUL', 'DIV':'DIV', 'MOD':'MOD', 
               '=':'EQUAL', '<':'INF', '<=': 'INFEQ', '>':'SUP', '>=':'SUPEQ', 
               'AND':'AND', 'OR':'OR'}
        self.emit(ops.get(op, 'ADD'))

    def visit_INT(self, node):
        self.emit(f"PUSHI {node[1]}")

    def visit_STRING(self, node):
        # pascal usa 'aspas simples', VM usa "aspas duplas"
        self.emit(f"PUSHS {node[1].replace(chr(39), chr(34))}")

    def visit_BOOL(self, node):
        val = 1 if node[1].lower() == 'true' else 0
        self.emit(f"PUSHI {val}")

    def visit_ID(self, node):
        sym = self.ts.lookup(node[1])
        if not sym: return

        if sym['scope'] == 'GLOBAL':
            self.emit(f"PUSHG {sym['offset']}")
        else:
            self.emit(f"PUSHL {sym['offset']}")

    def visit_ARRAY_ACCESS(self, node):
        # tipo v[i]
        sym = self.ts.lookup(node[1])
        if not sym: return

        # arranjar o pointer do array
        if sym['scope'] == 'GLOBAL':
            self.emit(f"PUSHG {sym['offset']}")
        else:
            self.emit(f"PUSHL {sym['offset']}")
            
        # arranjar o indice do array
        self.visit(node[2])
        self.emit("PUSHI 1")
        self.emit("SUB")
        
        # instrução de acesso
        # strings usam CHARAT, arrays usam LOADN
        if sym['type'] == ('TYPE', 'STRING') or sym['type'] == 'STRING':
            self.emit("CHARAT")
        else:
            self.emit("LOADN")

    def visit_CALL_EXP(self, node):
        func_name = node[1].lower()
        args = node[2]

        if func_name == 'length':
            self.visit(args[0])
            self.emit("STRLEN")
            return

        # chamar funções
        self.emit("PUSHI 0") # reservar espaço para return
        for arg in args:
            self.visit(arg)
            
        self.emit(f"PUSHA {node[1]}") # nome original (case sensitive label)
        self.emit("CALL")
        self.emit(f"POP {len(args)}") # limpar argumentos

    def visit_CALL_STMT(self, node):
        self.visit_CALL_EXP(node)