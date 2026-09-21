const codigo = document.getElementById("codigo");

const tokens = document.getElementById("tokens");

const errores = document.getElementById("errores");

const btnTokens = document.getElementById("btnTokens");

const btnParser = document.getElementById("btnParser");

const btnSemantico = document.getElementById("btnSemantico");

const btnLimpiar = document.getElementById("btnLimpiar");

const fileInput = document.getElementById("fileInput");

// ==================================
// MOSTRAR RESULTADO
// ==================================

function mostrarResultado(lista) {
  errores.value = lista.join("\n");
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
  };

  reader.readAsText(file, "UTF-8");
});

// ==================================
// SCANNER
// ==================================

btnTokens.addEventListener("click", async function () {
  tokens.value = "";
  errores.value = "";

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
      mostrarResultado(data.errores || ["Error al analizar el código."]);

      return;
    }

    tokens.value = data.tokens.join("\n");

    if (data.errores.length > 0) {
      mostrarResultado(data.errores);
    } else {
      errores.value = "";
    }
  } catch (error) {
    console.error(error);

    errores.value = "Error al comunicarse con el scanner.";
  }
});

// ==================================
// PARSER
// ==================================

btnParser.addEventListener("click", async function () {
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

    mostrarResultado(data.errores || ["Error al analizar el parser."]);
  } catch (error) {
    console.error(error);

    errores.value = "Error al comunicarse con el parser.";
  }
});

// ==================================
// ANALIZADOR SEMÁNTICO
// ==================================

btnSemantico.addEventListener("click", async function () {
  errores.value = "";

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

    mostrarResultado(data.errores || ["Error al analizar semánticamente."]);
  } catch (error) {
    console.error(error);

    errores.value = "Error al comunicarse con el analizador semántico.";
  }
});

// ==================================
// LIMPIAR
// ==================================

btnLimpiar.addEventListener("click", function () {
  errores.value = "";
});
