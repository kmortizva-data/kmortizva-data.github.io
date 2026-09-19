/* El panel del gemelo. Módulo 30.
 *
 * No decide nada. Cada día llega ya calculado y escrito desde src/twin/panel.py,
 * con su frase en el idioma de la página, y aquí solo se suman minutos para
 * dibujar las curvas y se cambia de texto. La cuenta de `camino` es la misma que
 * la de src/site/render_panel.py, que dibuja el día de partida sin JavaScript.
 *
 * No anima nada: dos días distintos no son dos momentos de una misma cosa, así
 * que pasar de una curva a otra con una transición no explicaría nada. El cambio
 * es instantáneo, y no hay movimiento que parar.
 */
(function () {
  "use strict";

  document.documentElement.classList.remove("no-js");

  function camino(tramos, paso, techo) {
    var d = "M0 " + techo, total = 0;
    for (var k = 0; k < tramos.length; k++) {
      total += tramos[k];
      d += " L" + ((k + 1) * paso) + " " + (techo - total);
    }
    return d;
  }

  function pct(x, total) {
    return (100 * x / total).toFixed(3) + "%";
  }

  function span(clase, estilo, texto, atributos) {
    var s = document.createElement("span");
    s.className = clase;
    s.setAttribute("style", estilo);
    if (texto) s.textContent = texto;
    for (var clave in atributos || {}) {
      if (atributos.hasOwnProperty(clave)) s.setAttribute(clave, atributos[clave]);
    }
    return s;
  }

  function monta(caja) {
    var q = function (s) { return caja.querySelector(s); };
    var fuente = caja.getAttribute("data-panel");
    var enlazable = caja.hasAttribute("data-enlazable");
    var cursor = q(".pg-cursor"), fecha = q(".pg-fecha"), clase = q(".pg-clase");
    var frase = q(".pg-frase"), maquina = q(".pg-maquina"), gemelo = q(".pg-gemelo");
    var zona = q(".pg-zona"), huecos = q(".pg-huecos"), marcas = q(".pg-marcas");
    var barras = q(".pg-barras"), linea = q(".pg-t-cursor");
    var leyenda = caja.querySelectorAll(".pg-leyenda b[data-k]");
    var mandos = caja.querySelectorAll(".pg-paso, .pg-atajo");
    var atajos = caja.querySelectorAll(".pg-atajo");
    if (!fuente || !cursor || !maquina) return;

    var datos = null;
    var actual = parseInt(cursor.value, 10) || 0;

    function pinta(i) {
      var n = datos.dias.length;
      i = Math.max(0, Math.min(n - 1, i | 0));
      var d = datos.dias[i];
      var paso = datos.minutos_por_punto, techo = datos.techo_min;
      var ancho = datos.puntos * paso;

      maquina.setAttribute("d", camino(d.maquina, paso, techo));
      gemelo.setAttribute("d", camino(d.gemelo, paso, techo));
      zona.setAttribute("d", camino(d.zona, paso, techo) + " L" + ancho + " " + techo + " Z");

      huecos.textContent = "";
      d.huecos.forEach(function (h) {
        huecos.appendChild(span("pg-hueco", "left:" + pct(h[0], datos.puntos)
          + ";width:" + pct(h[1] - h[0], datos.puntos)));
      });

      // Las rayas primero y las etiquetas después, como en render_panel.py:
      // así ninguna raya tacha la etiqueta de otra marca cercana.
      marcas.textContent = "";
      d.marcas.forEach(function (m) {
        marcas.appendChild(span("pg-raya", "left:" + pct(m.x, datos.puntos), "",
          {"data-tipo": m.tipo}));
      });
      d.marcas.forEach(function (m) {
        marcas.appendChild(span("pg-marca", "left:" + pct(m.x, datos.puntos), m.t, {
          "data-tipo": m.tipo, "data-fila": String(m.fila),
          // El mismo corte que render_panel.py: en el último tercio del día la
          // etiqueta se escribe hacia la izquierda de su raya.
          "data-lado": m.x / datos.puntos > 0.68 ? "izq" : "der"
        }));
      });

      fecha.textContent = d.fecha;
      clase.textContent = d.etiqueta;
      clase.setAttribute("data-clase", d.clase);
      frase.textContent = d.frase;
      for (var k = 0; k < leyenda.length; k++) {
        leyenda[k].textContent = d.leyenda[leyenda[k].getAttribute("data-k")];
      }

      var antes = barras.children[actual];
      if (antes) antes.classList.remove("pg-b-elegido");
      barras.children[i].classList.add("pg-b-elegido");
      linea.setAttribute("d", "M" + (i + 0.5) + " 0 V110");
      cursor.value = String(i);
      cursor.setAttribute("aria-valuetext", d.fecha + ", " + d.etiqueta);
      for (var a = 0; a < atajos.length; a++) {
        atajos[a].setAttribute("aria-pressed",
          String(parseInt(atajos[a].getAttribute("data-i"), 10) === i));
      }
      actual = i;

      if (enlazable && window.history && history.replaceState) {
        history.replaceState(null, "", "#" + d.dia);
      }
    }

    function desdeLaUrl() {
      var buscado = (window.location.hash || "").slice(1);
      if (!buscado) return null;
      for (var k = 0; k < datos.dias.length; k++) {
        if (datos.dias[k].dia === buscado) return k;
      }
      return null;
    }

    fetch(fuente).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    }).then(function (j) {
      datos = j;
      cursor.disabled = false;
      for (var k = 0; k < mandos.length; k++) mandos[k].disabled = false;
      var pedido = enlazable ? desdeLaUrl() : null;
      if (pedido !== null) pinta(pedido);
    }).catch(function () {
      // Si los datos no llegan, se queda el día de partida dibujado por el
      // servidor, que se lee entero. Los mandos siguen desactivados.
    });

    cursor.addEventListener("input", function () {
      if (datos) pinta(parseInt(cursor.value, 10));
    });
    caja.addEventListener("click", function (e) {
      var boton = e.target.closest ? e.target.closest("button") : null;
      if (!boton || !datos || !caja.contains(boton)) return;
      if (boton.hasAttribute("data-paso")) {
        pinta(actual + parseInt(boton.getAttribute("data-paso"), 10));
      } else if (boton.hasAttribute("data-i")) {
        pinta(parseInt(boton.getAttribute("data-i"), 10));
      }
    });
  }

  document.querySelectorAll(".pg[data-panel]").forEach(monta);
})();
