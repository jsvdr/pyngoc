const codigo = document.getElementById("codigo");
const tokens = document.getElementById("tokens");
const errores = document.getElementById("errores");

const btnTokens = document.getElementById("btnTokens");
const btnParser = document.getElementById("btnParser");
const btnLimpiar = document.getElementById("btnLimpiar");

const fileInput = document.getElementById("fileInput");
const parserResultado = document.getElementById("parserResultado");

// CARGAR ARCHIVO

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];

  if (!file) {
    return;
  }

  const reader = new FileReader();

  reader.onload = function (event) {
    codigo.value = event.target.result;
  };

  reader.onerror = function () {
    alert("No se pudo leer el archivo.");
  };

  reader.readAsText(file, "UTF-8");
});

// SCANNER

btnTokens.addEventListener("click", async function () {
  tokens.value = "";
  errores.value = "";
  parserResultado.textContent = "";

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
      throw new Error(
        data.errores?.join("\n") || "Error al analizar el código.",
      );
    }

    tokens.value = data.tokens.join("\n");

    if (data.errores.length > 0) {
      errores.value = data.errores.join("\n");
    }
  } catch (error) {
    console.error(error);

    alert("Error al comunicarse con el compilador.");
  }
});

// PARSER

btnParser.addEventListener("click", async function () {
  parserResultado.textContent = "";
  errores.value = "";

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

    parserResultado.textContent = data.resultado;

    if (data.resultado === "Syntax Error") {
      errores.value = data.errores.join("\n");
    }
  } catch (error) {
    console.error(error);

    parserResultado.textContent = "Syntax Error";
    errores.value = "Error al comunicarse con el compilador.";
  }
});

// LIMPIAR

btnLimpiar.addEventListener("click", function () {
  errores.value = "";
  parserResultado.textContent = "";
});
