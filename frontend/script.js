const cajaCodigo = document.getElementById("codigo");
const cajaTokens = document.getElementById("tokens");
const cajaErrores = document.getElementById("errores");
const cajaIntermedio = document.getElementById("codigoIntermedio");
const btnTokens = document.getElementById("btnTokens");
const btnParser = document.getElementById("btnParser");
const btnSemantico = document.getElementById("btnSemantico");
const btnCI = document.getElementById("btnCI");
const cajaArchivo = document.getElementById("fileInput");

// ==================================
// COLORES Y LIMPIEZA
// ==================================

const COLOR_OK = "#1e7d32";
const COLOR_ERROR = "#cc0000";

function limpiarSalidas() {
  cajaTokens.value = "";
  cajaErrores.value = "";
  cajaIntermedio.value = "";
}

function pintarErrores(listaErrores, esValido) {
  cajaErrores.value = listaErrores.join("\n");
  cajaErrores.style.color = esValido ? COLOR_OK : COLOR_ERROR;
}

// ==================================
// CARGAR ARCHIVO
// ==================================

cajaArchivo.addEventListener("change", (evento) => {
  const archivo = evento.target.files[0];
  if (!archivo) {
    return;
  }
  const lector = new FileReader();
  lector.onload = function (eventoLectura) {
    cajaCodigo.value = eventoLectura.target.result;
  };
  lector.onerror = function () {
    cajaErrores.value = "No se pudo leer el archivo.";
    cajaErrores.style.color = COLOR_ERROR;
  };
  lector.readAsText(archivo, "UTF-8");
});

// ==================================
// SCANNER
// ==================================

btnTokens.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const respuesta = await fetch("/analizar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: cajaCodigo.value,
      }),
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) {
      pintarErrores(datos.errores || ["Error al analizar el código."], false);
      return;
    }
    cajaTokens.value = datos.tokens.join("\n");
    if (datos.errores.length > 0) {
      pintarErrores(datos.errores, false);
    }
  } catch (fallo) {
    console.error(fallo);
    cajaErrores.value = "Error al comunicarse con el scanner.";
    cajaErrores.style.color = COLOR_ERROR;
  }
});

// ==================================
// PARSER
// ==================================

btnParser.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const respuesta = await fetch("/parser", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: cajaCodigo.value,
      }),
    });
    const datos = await respuesta.json();
    pintarErrores(datos.errores || ["Error al analizar el parser."], datos.ok === true);
  } catch (fallo) {
    console.error(fallo);
    cajaErrores.value = "Error al comunicarse con el parser.";
    cajaErrores.style.color = COLOR_ERROR;
  }
});

// ==================================
// ANALIZADOR SEMÁNTICO
// ==================================

btnSemantico.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const respuesta = await fetch("/semantico", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: cajaCodigo.value,
      }),
    });
    const datos = await respuesta.json();
    pintarErrores(datos.errores || ["Error al analizar semánticamente."], datos.ok === true);
  } catch (fallo) {
    console.error(fallo);
    cajaErrores.value = "Error al comunicarse con el analizador semántico.";
    cajaErrores.style.color = COLOR_ERROR;
  }
});

// ==================================
// CÓDIGO INTERMEDIO
// ==================================

btnCI.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const respuesta = await fetch("/intermedio", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: cajaCodigo.value,
      }),
    });
    const datos = await respuesta.json();
    if (!datos.ok) {
      pintarErrores(datos.errores || ["No se pudo generar el código intermedio."], false);
      return;
    }
    cajaIntermedio.value = datos.codigo;
  } catch (fallo) {
    console.error(fallo);
    cajaErrores.value = "Error al generar el código intermedio.";
    cajaErrores.style.color = COLOR_ERROR;
  }
});
