/* La perilla del doble trazo. Módulos 24 y 25.
 *
 * No simula nada. **Toda la física está en Python**, en src/twin/, y aquí solo
 * se cambia de serie: cada posición del deslizador trae su trazo ya calculado.
 *
 * Es una decisión, no una comodidad. Escribir la física otra vez en JavaScript
 * dejaría dos implementaciones que se pueden separar, y en esta máquina no hay
 * node, ni deno, ni bun con los que compararlas. Una sola implementación no se
 * puede contradecir.
 *
 * Sin JavaScript el bloque ya está dibujado por el servidor en su posición de
 * referencia, así que la lección se lee entera igual.
 */
(function () {
  "use strict";

  var quieto = window.matchMedia
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function traza(serie, ancho, alto, margen, techo) {
    if (!serie.length) return "";
    var util = ancho - margen * 2;
    var altoUtil = alto - margen * 2;
    var d = "";
    for (var i = 0; i < serie.length; i++) {
      var x = margen + (util * i) / (serie.length - 1);
      var y = alto - margen - (altoUtil * serie[i]) / techo;
      d += (i ? " L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
    }
    return d;
  }

  function monta(caja) {
    var fuente = caja.getAttribute("data-perilla");
    var mando = caja.querySelector(".perilla-mando");
    var salida = caja.querySelector(".perilla-valor");
    var trazo = caja.querySelector(".perilla-actual");
    var svg = caja.querySelector("svg");
    var nota = caja.querySelector(".perilla-nota");
    if (!fuente || !mando || !trazo || !svg) return;

    var caja_ = svg.viewBox.baseVal;
    var ancho = caja_.width, alto = caja_.height;
    var margen = parseFloat(svg.getAttribute("data-margen")) || 12;
    var techo = parseFloat(svg.getAttribute("data-techo")) || 1;
    var datos = null;
    // El separador decimal lo dice la página, no el navegador: la edición
    // española escribe 0,12 y la inglesa 0.12, y este fichero sirve a las dos.
    var coma = caja.getAttribute("data-decimal") || ".";

    function numero(v) {
      return String(v).replace(".", coma);
    }

    function pinta() {
      if (!datos) return;
      var pos = datos.posiciones[mando.value | 0];
      if (!pos) return;
      trazo.setAttribute("d", traza(pos.trazo, ancho, alto, margen, techo));
      salida.textContent = numero(pos.valor) + " " + datos.unidad;
      if (nota) {
        // La plantilla puede pedir cualquier campo numerico de la posicion, y
        // no solo la carga y los arranques. El modulo 27 necesita el residual,
        // que no es ni una cosa ni la otra, y anadir un caso por perilla
        // acabaria en una lista que hay que tocar en cada modulo nuevo.
        var texto = nota.getAttribute("data-plantilla")
          .replace("{carga}", numero((pos.carga * 100).toFixed(1)))
          .replace("{arranques}", pos.arranques);
        for (var clave in pos) {
          if (!pos.hasOwnProperty(clave) || clave === "trazo") continue;
          texto = texto.split("{" + clave + "}").join(
            typeof pos[clave] === "number" ? numero(pos[clave]) : pos[clave]);
        }
        nota.textContent = texto;
      }
    }

    function carga() {
      if (datos) { pinta(); return; }
      fetch(fuente).then(function (r) { return r.json(); }).then(function (j) {
        datos = j;
        mando.max = String(j.posiciones.length - 1);
        mando.disabled = false;
        pinta();
      }).catch(function () {
        // Si no llega, el trazo del servidor se queda como estaba: la lección
        // no depende de esto para poder leerse.
        mando.disabled = true;
      });
    }

    // La transición se apaga con prefers-reduced-motion, como todo lo que se
    // mueve en este curso.
    if (quieto) trazo.style.transition = "none";
    mando.addEventListener("input", carga);
    mando.addEventListener("change", carga);
    carga();
  }

  document.querySelectorAll(".perilla[data-perilla]").forEach(monta);
})();
