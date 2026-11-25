// Scale the fixed 1920x1080 screen to any projector or laptop.
function fitZoom() {
  document.documentElement.style.zoom = Math.min(
    window.innerWidth / 1920,
    window.innerHeight / 1080,
  );
}

fitZoom();
window.addEventListener("resize", fitZoom);

const sourceBox = document.getElementById("source");
const tokensBox = document.getElementById("tokens");
const errorsBox = document.getElementById("errors");
const irBody = document.getElementById("irBody");
const btnTokens = document.getElementById("btnTokens");
const btnParser = document.getElementById("btnParser");
const btnSemantic = document.getElementById("btnSemantic");
const btnIR = document.getElementById("btnIR");
const fileInput = document.getElementById("fileInput");
const btnObject = document.getElementById("btnObject");
const dataBody = document.getElementById("dataBody");
const codeBody = document.getElementById("codeBody");
const objectError = document.getElementById("objectError");

// ==================================
// COLORS AND CLEANUP
// ==================================

const COLOR_OK = "#065F46";
const COLOR_ERROR = "#991B1B";

function clearOutputs() {
  tokensBox.value = "";
  errorsBox.value = "";
  irBody.innerHTML = "";
}

function paintErrors(errorList, isValid) {
  errorsBox.value = errorList.join("\n");
  errorsBox.style.color = isValid ? COLOR_OK : COLOR_ERROR;
}

// ==================================
// LOAD FILE
// ==================================

fileInput.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = function (readEvent) {
    sourceBox.value = readEvent.target.result;
  };
  reader.onerror = function () {
    errorsBox.value = "Could not read the file.";
    errorsBox.style.color = COLOR_ERROR;
  };
  reader.readAsText(file, "UTF-8");
});

// ==================================
// SERVER COMMUNICATION
// ==================================

const actionButtons = [btnTokens, btnParser, btnSemantic, btnIR, btnObject];

// Send the current source code to the given endpoint.
async function sendSource(path) {
  actionButtons.forEach((button) => (button.disabled = true));
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        source: sourceBox.value,
      }),
    });
    const data = await response.json();
    return { okHttp: response.ok, data };
  } finally {
    actionButtons.forEach((button) => (button.disabled = false));
  }
}

// ==================================
// LEXER
// ==================================

btnTokens.addEventListener("click", async () => {
  clearOutputs();
  try {
    const { okHttp, data } = await sendSource("/tokens");
    if (!okHttp) {
      paintErrors(data.errors || ["Error while analyzing the code."], false);
      return;
    }
    tokensBox.value = data.tokens.join("\n");
    if (data.errors.length > 0) {
      paintErrors(data.errors, false);
    }
  } catch (failure) {
    console.error(failure);
    errorsBox.value = "Error talking to the lexer.";
    errorsBox.style.color = COLOR_ERROR;
  }
});

// ==================================
// PARSER AND SEMANTIC
// ==================================

function analyze(button, path, failureMessage) {
  button.addEventListener("click", async () => {
    clearOutputs();
    try {
      const { data } = await sendSource(path);
      paintErrors(data.errors || [failureMessage], data.ok === true);
    } catch (error) {
      console.error(error);
      paintErrors([failureMessage], false);
    }
  });
}

analyze(btnParser, "/parser", "Error while analyzing the parser.");
analyze(btnSemantic, "/semantic", "Error while analyzing semantics.");

// ==================================
// INTERMEDIATE CODE
// ==================================

// Paint the rows (Name, Operator, Attribute) in the table.
function paintIR(rows, message) {
  irBody.innerHTML = "";

  if (message) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = message;
    row.appendChild(cell);
    irBody.appendChild(row);
    return;
  }

  for (const [name, operator, attribute] of rows) {
    const row = document.createElement("tr");

    // Empty row = separator between sections.
    if (name === "" && operator === "" && attribute === "") {
      row.className = "separator";
    }

    for (const field of [name, operator, attribute]) {
      const cell = document.createElement("td");
      cell.textContent = field;
      row.appendChild(cell);
    }

    irBody.appendChild(row);
  }
}

btnIR.addEventListener("click", async () => {
  clearOutputs();
  try {
    const { data } = await sendSource("/ir");
    if (!data.ok) {
      paintErrors(data.errors || ["Could not generate intermediate code."], false);
      return;
    }
    paintIR(data.rows, data.message);
  } catch (failure) {
    console.error(failure);
    errorsBox.value = "Error while generating intermediate code.";
    errorsBox.style.color = COLOR_ERROR;
  }
});

// ==================================
// OBJECT CODE
// ==================================

// Each phase cleans only its own output: the object panel does not touch the others.
function clearObject() {
  dataBody.innerHTML = "";
  codeBody.innerHTML = "";
  objectError.textContent = "";
}

// One row per variable (DATA) or per instruction (CODE).
function paintObjectTable(body, rows) {
  for (const row of rows) {
    const rowElement = document.createElement("tr");

    // The tooltip shows the full instruction or variable.
    rowElement.title = row.text;

    for (const field of [row.address, row.content, row.hex]) {
      const cell = document.createElement("td");
      cell.textContent = field;
      rowElement.appendChild(cell);
    }

    body.appendChild(rowElement);
  }
}

btnObject.addEventListener("click", async () => {
  clearObject();

  try {
    const { data } = await sendSource("/object");

    if (!data.ok) {
      const errorList = data.errors || ["Could not generate object code."];
      objectError.textContent = errorList.join("\n");
      return;
    }

    paintObjectTable(dataBody, data.data);
    paintObjectTable(codeBody, data.code);
  } catch (failure) {
    console.error(failure);
    objectError.textContent = "Error while generating object code.";
  }
});
