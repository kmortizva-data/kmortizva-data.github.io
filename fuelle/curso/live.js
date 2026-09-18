/* La consulta viva y el reto: SQL que se ejecuta de verdad, en el navegador.
 *
 * Esto es lo que impide que el curso sea un PDF que se lee de recorrido. El
 * lector escribe una consulta contra los datos reales del compresor y la pagina
 * la ejecuta. En los retos, ademas, la corrige.
 *
 * Tres decisiones que estan detras de este fichero:
 *
 * 1. EL MOTOR NO SE DESCARGA HASTA QUE SE PULSA. Son unos 8 MB, y quien solo
 *    quiere leer la leccion no paga nada. La primera pulsacion de la pagina lo
 *    trae; el resto de bloques comparten la misma base de datos.
 *
 * 2. SIN JAVASCRIPT LA LECCION SE LEE ENTERA. La consulta y su resultado ya
 *    estan impresos en el HTML. Esto solo anade poder tocarlos.
 *
 * 3. EL RETO COMPARA EL RESULTADO, NUNCA EL TEXTO DE LA CONSULTA. Hay muchas
 *    formas de escribir la misma pregunta y todas valen. Comparar cadenas seria
 *    castigar por no adivinar el estilo del autor.
 */

const BASE = document.documentElement.dataset.assets || "../assets";

/* Que tablas necesita ESTA leccion, declaradas por la pagina como
 * "vista=fichero.parquet,vista=fichero.parquet".
 *
 * No todas las lecciones necesitan lo mismo y la diferencia es grande: la
 * muestra del modulo 13 lleva la hora exacta y la de los demas no, porque la
 * hora cuesta 5,16 MB si se lleva el lago entero. Cada pagina baja lo suyo. */
const TABLES = (document.documentElement.dataset.tablas || "telemetria=sin_timestamp_ligera.parquet")
  .split(",")
  .map((pair) => {
    const [view, file] = pair.split("=");
    return { view: view.trim(), file: file.trim() };
  })
  .filter((t) => t.view && t.file);

let dbPromise = null;

/* Carga el motor una sola vez por pagina y registra la muestra como fichero. */
function boot(onProgress) {
  if (dbPromise) return dbPromise;

  dbPromise = (async () => {
    onProgress("cargando el motor, unos 8 MB la primera vez");
    const duckdb = await import(`${BASE}/duckdb-wasm/duckdb.mjs`);

    const worker = new Worker(`${BASE}/duckdb-wasm/duckdb-browser-eh.worker.js`);
    const logger = new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING);
    const db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(`${BASE}/duckdb-wasm/duckdb-eh.wasm`);

    onProgress("trayendo los datos del compresor");
    const con = await db.connect();
    for (const { view, file } of TABLES) {
      const sample = await fetch(`${BASE}/muestras/${file}`);
      if (!sample.ok) throw new Error(`no se pudo leer ${file} (${sample.status})`);
      const bytes = new Uint8Array(await sample.arrayBuffer());
      await db.registerFileBuffer(file, bytes);
      await con.query(`CREATE VIEW ${view} AS SELECT * FROM read_parquet('${file}')`);
    }
    return con;
  })();

  return dbPromise;
}

/* Arrow devuelve BigInt para los enteros grandes, y JSON no sabe serializarlos. */
function plain(value) {
  if (typeof value === "bigint") return Number(value);
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return value;
}

function toRows(result) {
  const columns = result.schema.fields.map((f) => f.name);
  const rows = result.toArray().map((row) => columns.map((c) => plain(row[c])));
  return { columns, rows };
}

/* Todo lo que entra en innerHTML aqui abajo pasa antes por escapeHtml(). Los
 * nombres de columna y los valores vienen de una consulta que escribe el propio
 * lector, asi que se tratan como texto ajeno siempre. */
function renderTable(target, { columns, rows }, limit = 12) {
  const head = columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  const body = rows
    .slice(0, limit)
    .map((r) => `<tr>${r.map((v) => `<td>${escapeHtml(fmt(v))}</td>`).join("")}</tr>`)
    .join("");
  const more =
    rows.length > limit
      ? `<p class="live-status" style="padding:8px 14px">y ${rows.length - limit} filas más</p>`
      : "";
  target.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>${more}`;
}

function fmt(v) {
  if (v === null) return "NULL";
  if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(2);
  return String(v);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
  );
}

/* La comparacion del reto. Normaliza antes: los numeros se redondean a dos
 * decimales y las filas se ordenan, para que el lector no tenga que acertar el
 * ORDER BY salvo que el enunciado lo pida. */
// Separador que no puede aparecer dentro de un dato. Se declara con su codigo
// y no literal, porque un caracter de control invisible en el fuente es una
// trampa para quien lea esto despues.
const FIELD_SEP = String.fromCharCode(1);

function normalise(rows) {
  const asText = rows.map((r) =>
    r.map((v) => {
      if (typeof v === "number") return v.toFixed(2);
      if (v === null) return "NULL";
      return String(v).trim();
    })
  );
  return asText.map((r) => r.join(FIELD_SEP)).sort();
}

function judge(got, expected) {
  const a = normalise(got.rows);
  const b = normalise(expected);
  if (a.length !== b.length) {
    return { ok: false, why: `esperaba ${b.length} filas y devolviste ${a.length}` };
  }
  const wrong = a.findIndex((row, i) => row !== b[i]);
  if (wrong !== -1) {
    return {
      ok: false,
      why: `hay ${b.length} filas en las dos, pero una no cuadra: tú «${a[wrong].split(FIELD_SEP).join(" | ")}», se esperaba «${b[wrong].split(FIELD_SEP).join(" | ")}»`,
    };
  }
  return { ok: true, why: `${b.length} filas, todas correctas` };
}

function wire(block) {
  const editor = block.querySelector(".live-editor");
  const button = block.querySelector(".live-run");
  const status = block.querySelector(".live-status");
  const out = block.querySelector(".live-out");
  const verdict = block.querySelector(".verdict");
  const expected = block.dataset.expected
    ? JSON.parse(block.dataset.expected)
    : null;

  const say = (text) => {
    status.textContent = text;
  };

  button.addEventListener("click", async () => {
    button.disabled = true;
    if (verdict) {
      verdict.textContent = "";
      verdict.className = "verdict";
    }
    try {
      const started = performance.now();
      const con = await boot(say);
      say("ejecutando");
      const result = await con.query(editor.value);
      const table = toRows(result);
      const ms = Math.round(performance.now() - started);
      renderTable(out, table);
      say(`${table.rows.length} filas en ${ms} ms`);

      if (expected) {
        const { ok, why } = judge(table, expected);
        verdict.textContent = ok ? `Correcto: ${why}` : `Todavía no: ${why}`;
        verdict.className = `verdict ${ok ? "ok" : "no"}`;
      }
    } catch (error) {
      out.innerHTML = `<div class="live-err">${escapeHtml(error.message || error)}</div>`;
      say("la consulta no corrió");
      if (verdict) {
        verdict.textContent = "";
        verdict.className = "verdict";
      }
    } finally {
      button.disabled = false;
    }
  });
}

document.documentElement.classList.remove("no-js");
document.querySelectorAll(".live").forEach(wire);
