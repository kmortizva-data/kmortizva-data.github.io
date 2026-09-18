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
  `concentra/cursos`, `geostat/curso`, y **`fuelle/curso` con `fuelle/figuras` y
  `fuelle/assets` al lado**, porque sus páginas piden `../figuras/` y `../assets/`),
  neutraliza los enlaces que salen del sitio y **borra `prueba_scrolly.html` y
  `prueba_visual.html`** (páginas de prueba de Geoestadística y de Fuelle).
- `python src/shoot.py <proyecto>` retoma las capturas de `assets/shots/` (Chrome headless;
  `geostat` y `fuelle` se leen de disco con `file://`, los demás necesitan su servidor).
  **La de Fuelle va en oscuro** (`--force-dark-mode`): en claro es papel, como Sílice y
  Geoestadística, y la sala de control oscura es lo que la distingue.
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
| Proyectos visibles | Froth (amber) · Sílice (iron) · Concentra (mint) · **Oro bajo el ruido** (gold, sin repo público: el enlace al código no se imprime) · **Fuelle** (air, desde el 2026-09-18, partes 1 a 6, repo público `kmortizva-data/fuelle`) | `site.json` `projects` |
| Página de proyecto | Estado, título, tagline, captura, bloque «Measured», **figura calculada** si `inline_figure` (Geoestadística trae su variograma dibujado con las reglas `.dibujar`), prosa, stack, botón abrir | `project_page()`, `inline_figure()` |
| Get in touch | Texto, **dirección grande con `mailto:`**, botón **Copy address** (solo con JS; si el portapapeles se niega, selecciona la dirección), LinkedIn y GitHub. **Sin formulario, por decisión de Kevin (2026-08-23)**: las tres llamadas a la acción (cabecera, héroe y páginas de proyecto) bajan a esta sección, donde están el correo y LinkedIn. El formulario Formspree se quitó entero (generador, `site.json`, JS y CSS) para no dejar código muerto | `contact_ways()`, `theme.js`, `.contact-*` |
| Pie | © año, correo, GitHub | `shell()` |
| Tarjeta social | `og:image` (absoluta, la exige el que la lee), `og:image:alt` y `twitter:card`. La imagen **es la portada** a 1200×630, capturada por `python src\shoot.py home` con `--force-prefers-reduced-motion` (sin eso headless caza la cortina a medias y sale negro). La URL base sigue el interruptor `publish_domain`: github.io mientras el dominio no se pague | `site_base()`, `shell()`, `shoot.py` entrada `home` |
| Móvil (≤40rem) | Cabecera de dos filas (marca + botón / enlaces), cifras en una fila de tres, filas de proyecto con el número sobre la miniatura 2:1 y botón de abrir a todo el ancho con el acento, credenciales justas, pie centrado; medido a 375 px: cabecera 96 px, cifras 101 px, filas 436 a 459 px, sin desbordes | bloque «Mobile craft» al final de `style.css` |

## El portafolio en LinkedIn (2026-08-23)

Kevin: «no sé por qué no puedo poner mi página así de primerazo como mi amigo».

- **La causa era un duplicado**: tenía el sitio dos veces en «Información de contacto»
  (uno con `/index.html`, otro sin), los dos como tipo «Blog». Con dos, LinkedIn no
  destaca ninguno bajo el nombre. Ahora hay **uno solo**, `https://kmortizva-data.github.io/`,
  tipo **Personal**.
- **Y una trampa de la interfaz**: LinkedIn **no pinta ese enlace en tu propia vista del
  perfil**, solo en la de los demás. Por eso lo veía en el perfil de su amigo y no en el
  suyo. Se comprueba en `linkedin.com/public-profile/settings/`, que muestra la vista
  pública real. Ahí sale «Sitio web personal ↗» y todos los interruptores («Sitios web»
  incluido) están en verde.
- **Sección «Destacado» montada** con el portafolio: título *Portfolio: four projects in
  mineral processing and data*, descripción en prosa hablada y la tarjeta social de
  imagen. Vive bajo «Acerca de» y esa sí la ve él.
- **Al montarla se destapó que faltaba `og:image`**, así que cualquier enlace suyo salía
  con un rectángulo gris en LinkedIn, WhatsApp o Slack. Arreglado en el generador (ver
  el inventario). Para forzar a LinkedIn a releer una URL cacheada:
  `linkedin.com/post-inspector/`.
- Si Kevin quiere otro texto en la tarjeta: perfil → Destacado → lápiz → Editar.

## Fuelle entra al portafolio (2026-09-18)

- **Acento `air`, #83A0E0.** Ni el cian del propio curso (#8EC2C8) ni otro turquesa: el
  acento de Froth, aunque se llama `amber`, es **#6BA8B8, un turquesa**, y a la luminosidad
  de la familia (0,70 a 0,74 en OKLCH) el cian del curso sería el mismo color. Se eligió
  midiendo en OKLab el tono libre más alejado de los cinco acentos a L 0,71 y C 0,10: el
  azul de 265°. Y es el **azul claro con que se pintan las líneas de aire comprimido en
  planta**. 7,63:1 contra el fondo. Kevin lo ve antes de publicar.
- **El oro no tenía par de contraste** en `check_site.py` desde que entró Geoestadística.
  Pasa (8,52:1), pero una puerta que se salta un color no es puerta para ese color. Añadido.
- **Fuelle suma unos 49 MB** al sitio: el motor SQL del navegador son 34,3 MB de un solo
  `.wasm`, y el motor entero viaja comprimido a **8,12 MB**, medido sobre el sitio publicado.
  Solo se baja al pulsar. Sus licencias (DuckDB MIT, Apache Arrow y FlatBuffers Apache 2.0,
  tslib 0BSD) viajan en `fuelle/assets/duckdb-wasm/licenses/`.
- **La ficha salió publicada con 7,74 MB y era 8,12.** `make_sample.py` de Fuelle sumaba solo
  el wasm (la página baja también su worker y cuatro módulos) y comprimía a gzip nivel 6.
  **GitHub Pages comprime a nivel 5**: medido el 2026-09-18, el nivel 5 reproduce byte a byte
  lo que Pages manda del wasm y del worker. Corregido en el origen y en la ficha. Regla: un
  peso de descarga se mide contra el servidor de verdad, no contra una compresión local.
- **Publicado el 2026-09-18** (commit 5c4ec2a). Comprobado en vivo: los **233 ficheros** de
  `fuelle/` responden 200, el wasm llega con `Content-Encoding: gzip`, y las dos páginas del
  proyecto llevan «Read the code» / «Ver el código» a `github.com/kmortizva-data/fuelle`.
- `.claude/` en `.gitignore`: hay `.nojekyll`, así que Pages publicaría cualquier carpeta
  con punto. Ahí vive la configuración `portafolio` del panel de vista previa.
- Verificado sirviendo el sitio en local: 2.059 enlaces resueltos en 213 páginas, la perilla
  del módulo 24 moviéndose desde el origen del portafolio, los ficheros del motor, las
  muestras y las licencias en 200, y 375 px sin desbordes en la portada y en las dos páginas
  del proyecto. **La consulta viva no se puede probar en el panel** (el motor no arranca
  ahí): se prueba en Chrome sobre el sitio publicado.

## Decisiones de Kevin cerradas (2026-08-23)

- **Contacto sin formulario**: «solo mándalos al final, que está mi email y LinkedIn».
  Se eliminó la ranura `form_endpoint` y todo el código del formulario.
- **El mark de Froth («44 subtopics, named and bridged») queda confirmado.**
- **Geoestadística sin repo público**: el botón «Read the code» no se imprime y no se
  propone más.
- **bg-remover sigue oculto y sin recordatorio**: se borró la tarea programada de cada
  8 días. Republicarlo es decisión suya, cuando lo arregle.

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

- ✅ **Sílice en inglés** (2026-08-22): 14 módulos + portada como gemelas `.en.html`, con
  interruptor de idioma en cada página y puerta de paridad de cifras. El botón de la
  portada abre la edición del idioma del lector.
- ✅ **Concentra en inglés** (2026-08-23): 42 gemelas (5 portadas, 25 módulos, 12 casos)
  con la misma receta; cáscara `index.en.html` con árbol, buscador y migas en inglés, y
  un interruptor en cada página que conserva la ruta (`../index.en.html#<slug>/<stem>`,
  `target="_top"` porque las páginas viven en un iframe). El botón de la portada abre la
  edición del idioma del lector. **Los tres cursos publicados son ahora bilingües.**
- Retomar la captura de bg-remover cuando Kevin lo arregle y decida mostrarlo.
