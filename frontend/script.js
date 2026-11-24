// Escala la pantalla fija de 1920x1080 a cualquier proyector o laptop.
function ajustarZoom() {
  document.documentElement.style.zoom = Math.min(
    window.innerWidth / 1920,
    window.innerHeight / 1080,
  );
}

ajustarZoom();
window.addEventListener("resize", ajustarZoom);

const cajaCodigo = document.getElementById("codigo");
const cajaTokens = document.getElementById("tokens");
const cajaErrores = document.getElementById("errores");
const cuerpoIntermedio = document.getElementById("cuerpoIntermedio");
const btnTokens = document.getElementById("btnTokens");
const btnParser = document.getElementById("btnParser");
const btnSemantico = document.getElementById("btnSemantico");
const btnCI = document.getElementById("btnCI");
const cajaArchivo = document.getElementById("fileInput");
const btnCO = document.getElementById("btnCO");
const cuerpoDatosCO = document.getElementById("cuerpoDatosCO");
const cuerpoCodigoCO = document.getElementById("cuerpoCodigoCO");
const errorCO = document.getElementById("errorCO");

// ==================================
// COLORES Y LIMPIEZA
// ==================================

const COLOR_OK = "#065F46";
const COLOR_ERROR = "#991B1B";

function limpiarSalidas() {
  cajaTokens.value = "";
  cajaErrores.value = "";
  cuerpoIntermedio.innerHTML = "";
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
// COMUNICACIÓN CON EL SERVIDOR
// ==================================

// Envía el código fuente actual al endpoint indicado.
async function enviarCodigo(ruta) {
  const respuesta = await fetch(ruta, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      codigo: cajaCodigo.value,
    }),
  });
  const datos = await respuesta.json();
  return { okHttp: respuesta.ok, datos };
}

// ==================================
// SCANNER
// ==================================

btnTokens.addEventListener("click", async () => {
  limpiarSalidas();
  try {
    const { okHttp, datos } = await enviarCodigo("/analizar");
    if (!okHttp) {
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
// PARSER Y SEMÁNTICO
// ==================================

function analizar(boton, ruta, fallo) {
  boton.addEventListener("click", async () => {
    limpiarSalidas();
    try {
      const { datos } = await enviarCodigo(ruta);
      pintarErrores(datos.errores || [fallo], datos.ok === true);
    } catch (error) {
      console.error(error);
      pintarErrores([fallo], false);
    }
  });
}

analizar(btnParser, "/parser", "Error al analizar el parser.");
analizar(btnSemantico, "/semantico", "Error al analizar semánticamente.");

// ==================================
// CÓDIGO INTERMEDIO
// ==================================

// Pinta las filas (Nombre, Operador, Atributo) en la tabla.
function pintarIntermedio(filas, mensaje) {
  cuerpoIntermedio.innerHTML = "";

  if (mensaje) {
    const fila = document.createElement("tr");
    const celda = document.createElement("td");
    celda.colSpan = 3;
    celda.textContent = mensaje;
    fila.appendChild(celda);
    cuerpoIntermedio.appendChild(fila);
    return;
  }

  for (const [nombre, operador, atributo] of filas) {
    const fila = document.createElement("tr");

    // Fila vacía = separador entre secciones.
    if (nombre === "" && operador === "" && atributo === "") {
      fila.className = "separador";
    }

    for (const campo of [nombre, operador, atributo]) {
      const celda = document.createElement("td");
      celda.textContent = campo;
      fila.appendChild(celda);
    }

    cuerpoIntermedio.appendChild(fila);
  }
}

btnCI.addEventListener("click", async () => {
  limpiarSalidas();
  try {
    const { datos } = await enviarCodigo("/intermedio");
    if (!datos.ok) {
      pintarErrores(datos.errores || ["No se pudo generar el código intermedio."], false);
      return;
    }
    pintarIntermedio(datos.filas, datos.mensaje);
  } catch (fallo) {
    console.error(fallo);
    cajaErrores.value = "Error al generar el código intermedio.";
    cajaErrores.style.color = COLOR_ERROR;
  }
});

// ==================================
// CÓDIGO OBJETO
// ==================================

// Cada fase limpia solo lo suyo: el panel CO no toca los demás paneles.
function limpiarObjeto() {
  cuerpoDatosCO.innerHTML = "";
  cuerpoCodigoCO.innerHTML = "";
  errorCO.textContent = "";
}

// Una fila por variable (DATOS) o por instrucción (CÓDIGO).
function pintarTablaCO(cuerpo, filas) {
  for (const fila of filas) {
    const renglon = document.createElement("tr");

    // El tooltip muestra la instrucción o la variable completa.
    renglon.title = fila.texto;

    for (const campo of [fila.direccion, fila.contenido, fila.hex]) {
      const celda = document.createElement("td");
      celda.textContent = campo;
      renglon.appendChild(celda);
    }

    cuerpo.appendChild(renglon);
  }
}

btnCO.addEventListener("click", async () => {
  limpiarObjeto();

  try {
    const { datos } = await enviarCodigo("/objeto");

    if (!datos.ok) {
      const listaErrores = datos.errores || ["No se pudo generar el código objeto."];
      errorCO.textContent = listaErrores.join("\n");
      return;
    }

    pintarTablaCO(cuerpoDatosCO, datos.datos);
    pintarTablaCO(cuerpoCodigoCO, datos.codigo);
  } catch (fallo) {
    console.error(fallo);
    errorCO.textContent = "Error al generar el código objeto.";
  }
});
