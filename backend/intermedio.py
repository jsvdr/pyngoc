# Intermedio: tabla -> texto assembler. int es DW, bool es DB.
# Si no hay variables se avisa con texto, no con lista vacía.
def generar_codigo_intermedio(tabla: dict[str, str]) -> str:
    lineas: list[str] = []

    for nombre_variable, tipo_declarado in tabla.items():
        if tipo_declarado == "int":
            lineas.append(f"{nombre_variable} DW ?")

        elif tipo_declarado == "bool":
            lineas.append(f"{nombre_variable} DB ?")

    if len(lineas) == 0:
        return "No hay variables para generar."

    return "\n".join(lineas)
