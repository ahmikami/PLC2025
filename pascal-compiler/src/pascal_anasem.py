class SymbolTable:
    def __init__(self):
        """
        Inicializa a tabela de símbolos.
        - scope_stack é uma stack de funçãoes (scopes)
        - o indice 0 correspode ao proprio programa / scope global
        - offset_stack armazena contadores de endereços
        """
        self.scope_stack = [{}]
        self.offset_stack = [0]
        self._init_builtins()

    def _init_builtins(self):
        """
        carrega funções que são builtin no pascal
        """
        #length dá return a um int
        self.add('length', ('TYPE', 'INTEGER'), 'FUNCTION')
        
        #inputs sem return (não são exatamente funções, daí procedure)
        self.add('writeln', ('TYPE', 'VOID'), 'PROCEDURE')
        self.add('readln', ('TYPE', 'VOID'), 'PROCEDURE')
        self.add('write', ('TYPE', 'VOID'), 'PROCEDURE')
        self.add('read', ('TYPE', 'VOID'), 'PROCEDURE')

    def enter_scope(self):
        """
        adiciona um dicionário que representa um scope\n
        adiciona também um novo contador de endereços a 0.
        """
        self.scope_stack.append({})
        self.offset_stack.append(0)

    def exit_scope(self):
        """
        remove o scope e respectivo counter do topo da stack
        """
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.offset_stack.pop()
        else:
            print("Erro: Tentativa de fechar o próprio programa!")

    def add(self, name, type_info, category):
        """
        guarda um identificador (variável ou função) no scope atual e dá um endereço.
        """
        current_scope = self.scope_stack[-1]
        name = name.lower() # Pascal não diferencia maiúsculas e minúsculas
        
        if name in current_scope:
            print(f"Aviso: O nome '{name}' já está a ser usado neste scope.")
        
        current_offset = self.offset_stack[-1]

        if category == 'VAR':
            self.offset_stack[-1] += 1

        # grava os dados (tipo e categoria)
        current_scope[name] = {
            'type': type_info, 
            'category': category,
            'offset': current_offset
            }

    def lookup(self, name, line=0):
        """
        Procura um identificador em todos os scopes abertos.
        """
        name_lower = name.lower()
        
        # percorre a stack ao contrário (do mais recente para o mais antigo)
        for i, scope in enumerate(reversed(self.scope_stack)):
            if name_lower in scope:
                symbol = scope[name_lower]
                # se i == len - 1, estamos no scope global
                is_global = (i == len(self.scope_stack) - 1)
                # flag para saber se é global ou local
                symbol['scope'] = 'GLOBAL' if is_global else 'LOCAL'
                return symbol
        
        # se não encontrou em lado nenhum, mostra erro
        if line > 0:
            print(f"Erro Semântico: '{name}' não foi declarado (linha {line})")
        
        return None

    def update_type(self, name, new_type):
        """
        Atualiza o tipo no scope principal.
        Usado para definir o tipo de retorno da função atual.
        """
        name = name.lower()
        # precisa ter pelo menos 2 scopes (global + função atual)
        if len(self.scope_stack) >= 2:
            parent_scope = self.scope_stack[-2]
            if name in parent_scope:
                parent_scope[name]['type'] = new_type