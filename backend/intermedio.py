def generar_codigo_intermedio(tabla):
    codigo = []

    for nombre, tipo in tabla.items():
        if tipo == "int":
            codigo.append(f"{nombre} DW ?")

        elif tipo == "bool":
            codigo.append(f"{nombre} DB ?")

    if len(codigo) == 0:
        return "No hay variables para generar."

    return "\n".join(codigo)
