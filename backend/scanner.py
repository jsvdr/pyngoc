KEYWORDS = {"if", "else", "for", "print", "int", "bool", "true", "false"}


def analizar_lexico(codigo):
    tokens = []
    errores = []

    linea = 1
    indice = 0
    longitud = len(codigo)

    while indice < longitud:
        char = codigo[indice]

        # Espacios y saltos de línea
        if char == "\n":
            linea += 1
            indice += 1
            continue

        if char.isspace():
            indice += 1
            continue

        # ID o PR
        if char.isalpha():
            start = indice

            while indice < longitud and codigo[indice].isalnum():
                indice += 1

            lexema = codigo[start:indice]

            if lexema in KEYWORDS:
                tokens.append(f"<TKN KEYWORD {lexema}>")
            else:
                tokens.append(f"<TKN ID {lexema}>")

            continue

        # Números
        if char.isdigit():
            start = indice

            while indice < longitud and codigo[indice].isdigit():
                indice += 1

            lexema = codigo[start:indice]

            tokens.append(f"<TKN NUM {lexema}>")

            continue

        # Operador ==
        if indice + 1 < longitud and codigo[indice : indice + 2] == "==":
            tokens.append("<TKN OPREL ==>")

            indice += 2

            continue

        # Operadores aritméticos
        if char in {"@", "#", "&", "|"}:
            tokens.append(f"<TKN OPARIT {char}>")

            indice += 1

            continue

        # Operadores relacionales
        if char in {">", "<"}:
            tokens.append(f"<TKN OPREL {char}>")

            indice += 1

            continue

        # Puntuación y asignación
        if char in {"{", "}", ";", "=", "(", ")"}:
            tokens.append(f"<TKN PUNT {char}>")

            indice += 1

            continue

        # Caracter inválido
        errores.append(f"Línea {linea}: Caracter inválido '{char}'")

        indice += 1

    return tokens, errores
