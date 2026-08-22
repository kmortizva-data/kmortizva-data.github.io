# Portafolio web (`sitio/`) — memoria del proyecto

> Sitio estático bilingüe (inglés en la raíz, español en `/es/`), publicado en
> **https://kmortizva-data.github.io/** (repo de usuario `kmortizva-data.github.io`, rama
> `master`, carpeta raíz). Generador: `src/build.py` (solo librería estándar). Contenido:
> `content/site.json`. Puerta antes de cada commit: `python src/check_site.py`.
> El README.md (inglés) explica el build para un extraño; este archivo guarda lo que Kevin
> decidió y por qué.

## Comandos

```bash
python src/build.py && python src/check_site.py
```

- El build espeja dentro del sitio los proyectos estáticos (`silice/curso`,
  `concentra/cursos`, `geostat/curso`), neutraliza los enlaces que salen del sitio y
  **borra `prueba_scrolly.html`** (página de prueba del motor de Geoestadística).
- `python src/shoot.py <proyecto>` retoma las capturas de `assets/shots/` (Chrome headless;
  `geostat` se lee de disco con `file://`, los demás necesitan su servidor).
- `CNAME` solo se escribe con `"publish_domain": true`; hoy está en `false` porque el
  dominio datageeksunited.com **no se paga** (decisión de Kevin, 2026-08-22).

## Reglas que Kevin ha dictado (no negociables)

1. **Sin rayas** (`—`, `–`) ni **guionado** (`hyphens: auto`) en ninguna prosa publicada. La
   puerta las caza.
2. **Sin palabras clave sueltas** en la prosa visible: la línea bajo el hero va en frases
   habladas («Modelling flotation circuits from real plant data»), nunca «Li · Ta · Nb · W».
3. **Números literales**: cada cifra de un proyecto sale de su medición; no se redondea ni
   se adorna. Los «marks» del índice son positivos y verificables.
4. **Justificado desde 33rem de columna; rasgado en celular.** Kevin pidió justificado en
   móvil, vio la medición (huecos de 7,65× y ríos en 5 de 6 líneas a 375 px) y eligió
   «celular quede bien, estilizado» (2026-08-22). Nada de `hyphens`.
5. **Sin Coursera** ni nombres de plataformas en Concentra; son «mis apuntes, espero que le
   sirvan a alguien más».
6. Froth se vende como necesidad cumplida, sin exagerar; el 42 % sin enlazar se queda dentro
   del texto «Measured» como dato honesto, no como titular.
7. Los botones de abrir/ver un proyecto se abren en **pestaña nueva**; bg-remover sigue
   **oculto** (`hidden: true`) hasta que se arreglen sus bugs (recordatorio cada 8 días).

## Inventario de UI (estado 2026-08-22, noche)

| Pieza | Qué es | Dónde |
|---|---|---|
| Cabecera | Monograma SVG (burbuja con cruz) + «Kevin Ortiz», enlaza a la portada desde todas las páginas; nav About / Work / idioma / **Get in touch → `#contact`** | `build.py` `LOGO`, `shell()` |
| Hero | Aforismo partido palabra a palabra, lede, **pieza viva** (puntos medidos y curva ajustada, SVG generado en el build, ciclo CSS de 12 s solo con `html.js`, completa sin JS, quieta con reduced-motion) y la línea `meta` | `hero_art()`, `.hero-art*`, `@keyframes hero-draw` |
| Marquee | Seis frases habladas por idioma | `site.json` `marquee` |
| Who I am | Tres párrafos (identidad / crisis de los metales críticos / postura y autoformación); el de «quality control» se quitó | `site.json` `about` |
| Credenciales | Cuatro filas (MSc, BEng, becas y honores, idiomas) | `credentials` |
| The work | Índice con panel de imagen: filas numeradas (nombre, tagline, mark, área, botón abrir ↗); el panel **sigue al cursor ±6 px** y toma el acento del proyecto activo en el borde (solo con `hover: hover` y sin reduced-motion) | `work_index()`, `theme.js`, `.index-*` |
| Proyectos visibles | Froth (amber) · Sílice (iron) · Concentra (mint) · **Oro bajo el ruido** (gold, sin repo público: el enlace al código no se imprime) | `site.json` `projects` |
| Página de proyecto | Estado, título, tagline, captura, bloque «Measured», **figura calculada** si `inline_figure` (Geoestadística trae su variograma dibujado con las reglas `.dibujar`), prosa, stack, botón abrir | `project_page()`, `inline_figure()` |
| Get in touch | Texto, **dirección grande con `mailto:`**, botón **Copy address** (solo con JS; si el portapapeles se niega, selecciona la dirección), LinkedIn (cuando `linkedin` tenga valor), GitHub, y **formulario Formspree** (cuando `form_endpoint` tenga valor; honeypot `_gotcha`, `_subject`, envío con `fetch` y respuesta en la página, POST normal sin JS) | `contact_ways()`, `theme.js`, `.contact-*` |
| Pie | © año, correo, GitHub | `shell()` |
| Móvil (≤40rem) | Cabecera de dos filas (marca + botón / enlaces), cifras en una fila de tres, filas de proyecto con el número sobre la miniatura 2:1 y botón de abrir a todo el ancho con el acento, credenciales justas, pie centrado; medido a 375 px: cabecera 96 px, cifras 101 px, filas 436 a 459 px, sin desbordes | bloque «Mobile craft» al final de `style.css` |

## Huecos que solo Kevin puede llenar

- `site.json` → `"form_endpoint": ""` (`https://formspree.io/f/<ID>`; crear la cuenta
  gratuita y **apuntar el límite mensual**, que no se pudo leer desde aquí).
- Confirmar el mark nuevo de Froth («44 subtopics, named and bridged») o volver al de
  1.290 vs 4.045.

## Lecciones de verificación

- La portada usa telón + `reveal` por IntersectionObserver + Lenis: **Chrome headless
  normal la fotografía negra**. Capturar con `--force-prefers-reduced-motion` (el sitio
  respeta la preferencia y pinta el estado final) y desde `file://` (sin servidor).
- El panel del navegador de esta herramienta no compone frames: sirve para **DOM y medidas
  por JS**, no para píxeles. Las animaciones solo las ve Kevin en su navegador.
- Chrome headless con `--window-size=414,…` maqueta a su ancho mínimo (~500 px) y recorta:
  los «desbordamientos» móviles que enseña son falsos; el móvil se mide con
  `resize_window` + `scrollWidth`.
- El `http.server` del panel sirve `theme.js` desde caché aunque cambie en disco: por eso
  los assets llevan huella de contenido en la URL (`?v=hash`), que además evita que un
  visitante de GitHub Pages se quede con el JS viejo tras un despliegue.
- Ríos en texto justificado: medir con el script de estiramiento de espacios (espacio
  natural ≈ 4,5 px a 16,5 px de fuente; río = línea con hueco medio > 1,5×).

## Pendientes fuera de esta ronda

- **Siguiente tramo: traducir Sílice (14 módulos) y Concentra (25 módulos + 12 casos)**
  al inglés con la infraestructura bilingüe de Geoestadística, Sílice primero. Kevin
  (2026-08-22): «cursos individuales no tienen interruptor idioma». Hasta entonces, cada
  curso lleva en su cabecera «English summary on the portfolio ↗» hacia su página del
  proyecto en inglés; no se finge un interruptor que lleve a una página en español.
- Repo público para Geoestadística si Kevin quiere el botón «Read the code».
- Retomar la captura de bg-remover cuando se arregle y se muestre.
