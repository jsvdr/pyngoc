const codigo = document.getElementById("codigo");
const tokens = document.getElementById("tokens");
const errores = document.getElementById("errores");
const codigoIntermedio = document.getElementById("codigoIntermedio");
const btnTokens = document.getElementById("btnTokens");
const btnParser = document.getElementById("btnParser");
const btnSemantico = document.getElementById("btnSemantico");
const btnCI = document.getElementById("btnCI");
const fileInput = document.getElementById("fileInput");

// ==================================
// COLORES Y LIMPIEZA
// ==================================

const COLOR_OK = "#1e7d32";
const COLOR_ERROR = "#cc0000";

function limpiarSalidas() {
  tokens.value = "";
  errores.value = "";
  codigoIntermedio.value = "";
}

function mostrarResultado(lista, ok) {
  errores.value = lista.join("\n");
  errores.style.color = ok ? COLOR_OK : COLOR_ERROR;
}

// ==================================
// CARGAR ARCHIVO
// ==================================

fileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = function (event) {
    codigo.value = event.target.result;
  };
  reader.onerror = function () {
    errores.value = "No se pudo leer el archivo.";
    errores.style.color = COLOR_ERROR;
  };
  reader.readAsText(file, "UTF-8");
});

// ==================================
// SCANNER
// ==================================

btnTokens.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const response = await fetch("/analizar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: codigo.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      mostrarResultado(data.errores || ["Error al analizar el código."], false);
      return;
    }
    tokens.value = data.tokens.join("\n");
    if (data.errores.length > 0) {
      mostrarResultado(data.errores, false);
    }
  } catch (error) {
    console.error(error);
    errores.value = "Error al comunicarse con el scanner.";
    errores.style.color = COLOR_ERROR;
  }
});

// ==================================
// PARSER
// ==================================

btnParser.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const response = await fetch("/parser", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: codigo.value,
      }),
    });
    const data = await response.json();
    mostrarResultado(data.errores || ["Error al analizar el parser."], data.ok === true);
  } catch (error) {
    console.error(error);
    errores.value = "Error al comunicarse con el parser.";
    errores.style.color = COLOR_ERROR;
  }
});

// ==================================
// ANALIZADOR SEMÁNTICO
// ==================================

btnSemantico.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const response = await fetch("/semantico", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: codigo.value,
      }),
    });
    const data = await response.json();
    mostrarResultado(data.errores || ["Error al analizar semánticamente."], data.ok === true);
  } catch (error) {
    console.error(error);
    errores.value = "Error al comunicarse con el analizador semántico.";
    errores.style.color = COLOR_ERROR;
  }
});

// ==================================
// CÓDIGO INTERMEDIO
// ==================================

btnCI.addEventListener("click", async function () {
  limpiarSalidas();
  try {
    const response = await fetch("/intermedio", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        codigo: codigo.value,
      }),
    });
    const data = await response.json();
    if (!data.ok) {
      mostrarResultado(data.errores || ["No se pudo generar el código intermedio."], false);
      return;
    }
    codigoIntermedio.value = data.codigo;
  } catch (error) {
    console.error(error);
    errores.value = "Error al generar el código intermedio.";
    errores.style.color = COLOR_ERROR;
  }
});
