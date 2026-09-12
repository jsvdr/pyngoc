const codigo = document.getElementById("codigo");
const tokens = document.getElementById("tokens");
const errores = document.getElementById("errores");

const btnTokens = document.getElementById("btnTokens");
const fileInput = document.getElementById("fileInput");

const erroresPanel = document.getElementById("erroresPanel");
const app = document.querySelector(".app");

// CARGAR ARCHIVO
fileInput.addEventListener("change", () => {
  const file = this.files[0];

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

// EJECUTAR SCANNER
btnTokens.addEventListener("click", async function () {
  // Limpiar resultados anteriores

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
      throw new Error(
        data.errores?.join("\n") || "Error al analizar el código.",
      );
    }

    // MOSTRAR TOKENS

    tokens.value = data.tokens.join("\n");

    // MOSTRAR ERRORES

    if (data.errores.length > 0) {
      errores.value = data.errores.join("\n");

      erroresPanel.classList.remove("hidden");
      app.classList.add("has-errors");
    } else {
      erroresPanel.classList.add("hidden");
      app.classList.remove("has-errors");
    }
  } catch (error) {
    console.error(error);

    alert("Error al comunicarse con el compilador.");
  }
});
