from tokens import Token, TokenKind


# Recorrido compartido: la lista de tokens y la posición actual.
# Parser, semántico, intermedio y objeto heredan estos cuatro métodos.
class Recorrido:
    tokens: list[Token]
    posicion: int

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.posicion = 0

    def token_actual_es(self, kind_esperado: TokenKind) -> bool:
        return self.token_actual().kind == kind_esperado

    def token_actual(self) -> Token:
        return self.tokens[self.posicion]

    def avanzar(self) -> None:
        # No pasa del último para no salirse de la lista.
        if self.posicion < len(self.tokens) - 1:
            self.posicion += 1

    def avanzar_si_es(self, kind_esperado: TokenKind) -> None:
        if self.token_actual_es(kind_esperado):
            self.avanzar()
