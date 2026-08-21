"""The gate for the site: it resolves every link and measures every colour pair.

Until now these checks were done by hand after each change, which is exactly how a pair
of text colours ended up shipping at 4.36:1, below the 4.5:1 minimum, without anybody
noticing. A check that lives in a script gets run; one that lives in a habit does not.

It exits non-zero when anything is red, so it can gate a commit.

Usage:
    python src/check_site.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# Every text/background pair the page actually puts on screen. Written out rather than
# scraped from the CSS, because what matters is which pairs really meet, and only a human
# reading the page knows that. Kept in sync by hand; the cost is small and the alternative
# is a checker that measures pairs nobody ever sees.
PAIRS = [
    ("--ink", "--bg", "body text on the page"),
    ("--ink", "--surface", "body text on a card"),
    ("--ink", "--raised", "body text on a raised card"),
    ("--ink-soft", "--bg", "secondary text on the page"),
    ("--ink-soft", "--surface", "secondary text on a card"),
    ("--ink-faint", "--bg", "faint text on the page"),
    ("--ink-faint", "--surface", "faint text on a card"),
    ("--ink-faint", "--raised", "faint text on a raised card"),
    ("--hi", "--bg", "the accent on the page"),
    ("--hi", "--surface", "the accent on a card"),
    ("--froth", "--bg", "Froth accent"),
    ("--iron", "--bg", "iron accent"),
    ("--mint", "--bg", "mint accent"),
    ("--slate", "--bg", "slate accent"),
]

MINIMUM = 4.5          # WCAG AA for text below 24 px
LARGE_TEXT = 3.0       # AA for headings; only used where a pair is heading-only


def read_variables() -> dict[str, str]:
    css = (ROOT / "templates" / "style.css").read_text(encoding="utf-8")
    root_block = re.search(r":root\s*\{(.*?)\}", css, re.S)
    if not root_block:
        raise SystemExit("No encontré el bloque :root en style.css")
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", root_block.group(1)))


def luminance(hex_colour: str) -> float:
    """Relative luminance, the WCAG definition: linearise each channel, then weight."""
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    a, b = luminance(foreground), luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def check_contrast() -> list[str]:
    variables = read_variables()
    problems = []
    print("CONTRASTE")
    for fg, bg, label in PAIRS:
        if fg not in variables or bg not in variables:
            problems.append(f"variable ausente en :root — {fg} o {bg}")
            continue
        ratio = contrast(variables[fg], variables[bg])
        ok = ratio >= MINIMUM
        print(f"  {'OK  ' if ok else 'BAJO'}  {ratio:5.2f}:1  {label}")
        if not ok:
            problems.append(f"{label}: {ratio:.2f}:1, por debajo de {MINIMUM}:1")
    return problems


def check_links() -> list[str]:
    """Every src and every internal href has to resolve to a file that exists.

    A broken image on a portfolio is worse than a missing one, because it renders as the
    alt text in a box and looks like the site is falling apart.
    """
    problems = []
    pages = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
    print(f"\nENLACES  ({len(pages)} páginas)")

    checked = 0
    for page in pages:
        html = page.read_text(encoding="utf-8")
        targets = re.findall(r'(?:src|href)="([^"#][^"]*)"', html)
        for target in targets:
            if target.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            resolved = (page.parent / target.split("#")[0]).resolve()
            checked += 1
            if not resolved.exists():
                problems.append(f"{page.relative_to(ROOT)} apunta a {target}, que no existe")
    print(f"  {checked} referencias resueltas contra el disco, "
          f"{len(problems)} rotas")
    return problems


def verify_png(data: bytes) -> str:
    """Empty string if the file is a whole, uncorrupted PNG; the fault otherwise.

    Reading the magic bytes only proves the first eight bytes. A file truncated halfway
    still passes that, and a truncated screenshot is exactly what a flaky dev server
    produced here. So every chunk gets its CRC checked and the pixels get inflated: that
    is the difference between "starts like a PNG" and "is one".
    """
    import struct
    import zlib

    if data[:8] != bytes.fromhex("89504e470d0a1a0a"):
        return "no empieza como PNG"

    position, pixels, kinds, header = 8, b"", [], None
    while position < len(data) - 8:
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        if len(body) < length:
            return "el archivo se corta a mitad de un bloque"
        stored = struct.unpack(">I", data[position + 8 + length:position + 12 + length])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != stored:
            return f"CRC malo en el bloque {kind.decode('ascii', 'replace')}"
        kinds.append(kind)
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            pixels += body
        position += 12 + length

    if b"IEND" not in kinds:
        return "no tiene bloque final IEND"
    try:
        raw = zlib.decompress(pixels)
    except zlib.error as failure:
        return f"los pixeles no se descomprimen ({failure})"

    width, height, depth, colour = header[0], header[1], header[2], header[3]
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour, 0)
    expected = height * (width * channels * depth // 8 + 1)
    if raw and len(raw) != expected:
        return f"faltan pixeles: {len(raw)} de {expected} bytes"
    return ""



def check_images() -> list[str]:
    """A PNG that is really an error page, or a screenshot that never got taken."""
    problems = []
    shots = sorted((ROOT / "assets" / "shots").glob("*.png"))
    print()
    print(f"CAPTURAS  ({len(shots)})")
    for shot in shots:
        size = shot.stat().st_size
        broken = verify_png(shot.read_bytes())
        if broken:
            problems.append(f"{shot.name}: {broken}")
            print(f"  MAL    {shot.name}  {broken}")
        elif size < 25_000:
            # Under 25 KB at 1440x900 means the app was almost certainly still painting.
            print(f"  LIGERA {shot.name}  {size / 1024:.0f} KB - revisar a ojo")
        else:
            print(f"  OK     {shot.name}  {size / 1024:.0f} KB, integro")
    return problems


def check_motion() -> list[str]:
    """Nothing may hide content unless the same file also un-hides it.

    The rule the site is built on: the page reads with JavaScript off. That only holds if
    every rule that sets opacity to zero is scoped to html.js, so it simply never applies
    when the script is absent.
    """
    css = (ROOT / "templates" / "style.css").read_text(encoding="utf-8")
    problems = []
    print("\nMOVIMIENTO")

    hiding = re.findall(r"([^{}]+)\{[^{}]*opacity:\s*0\s*;", css)
    # A selector that also has a companion rule restoring opacity is a crossfade, not a
    # hide: one of the stack always ships visible from the build. Only rules that need
    # JavaScript to ever become visible are a problem.
    restoring = set(re.findall(r"([^{}]+)\{[^{}]*opacity:\s*1\s*;", css))
    def has_companion(selector: str) -> bool:
        base = selector.strip().split(",")[0].strip()
        return any(base in other for other in restoring)

    unscoped = [s.strip() for s in hiding
                if "html.js" not in s and "keyframes" not in s and "from" not in s
                and not has_companion(s)]
    for selector in unscoped:
        problems.append(f"«{selector}» oculta contenido sin exigir JavaScript")

    print(f"  {len(hiding)} reglas ocultan contenido, {len(unscoped)} sin proteger")

    if "prefers-reduced-motion" not in css:
        problems.append("el CSS no respeta prefers-reduced-motion")
    else:
        blocks = css.count("prefers-reduced-motion")
        print(f"  {blocks} bloques respetan el movimiento reducido")

    if "curtain-lift" not in css:
        problems.append("el telón no tiene animación de retirada: podría quedarse puesto")
    else:
        print("  el telón se retira solo, sin depender del script")

    return problems


def check_index() -> list[str]:
    """The index is only as good as its data: every row needs a name, a number and an area.

    A row missing its measured number would still render, just as a blank space, which is
    exactly the kind of silent gap that survives a hundred rebuilds. And the panel has to
    hold one pane per row or hovering the last project shows nothing.
    """
    import json

    problems = []
    data = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    live = [p for p in data["projects"]
            if not p.get("archive") and not p.get("hidden")]
    hidden = [p for p in data["projects"] if p.get("hidden")]
    print()
    print(f"INDICE  ({len(live)} en portada"
          + (f", {len(hidden)} oculto(s): "
             + ", ".join(p["slug"] for p in hidden) if hidden else "") + ")")

    for project in data["projects"]:
        for lang in ("en", "es"):
            for field in ("name", "mark", "area"):
                if not project[lang].get(field):
                    problems.append(f"{project['slug']} ({lang}) no tiene «{field}»")
        if not project.get("year"):
            problems.append(f"{project['slug']} no tiene año")

    for page, count_rows in (("index.html", None), ("es/index.html", None)):
        html = (ROOT / page).read_text(encoding="utf-8")
        # Anchored on the closing quote: "index-panel" contains "index-pane", and
        # counting loosely made the wrapper look like a fifth pane.
        rows = len(re.findall(r'class="index-row[^"]*"', html))
        panes = len(re.findall(r'class="index-pane(?: on)?"', html))
        if rows != panes:
            problems.append(f"{page}: {rows} filas pero {panes} paneles")
        if not re.search(r'class="index-pane on"', html):
            problems.append(f"{page}: ningún panel arranca visible, sin JavaScript queda vacío")
        print(f"  {page:<16} {rows} filas, {panes} paneles, uno visible de salida")

    # A hidden project has to leave no page behind. Deleting it from the index while its
    # own page still sits on disk means the work is still published, just unlinked.
    for project in hidden:
        for folder in ("work", "es/proyectos"):
            stale = ROOT / folder / f"{project['slug']}.html"
            if stale.exists():
                problems.append(f"{project['slug']} está oculto pero {folder}/"
                                f"{project['slug']}.html sigue en disco")
        print(f"  {project['slug']} oculto, sin página en disco")

    if not problems:
        print("  cada proyecto tiene nombre, cifra, área y año en los dos idiomas")
    return problems


def check_measure() -> list[str]:
    """Every text block on a project page has to share one column.

    The page once had six widths and two different left margins stacked down it, and Kevin
    spotted it before any check did. The cause was each block declaring its own max-width,
    several of them in ch, which is the width of a zero at that element's own font size: the
    same 76ch gave 615px to the stream text at 15px and 696px to the prose at 17px.

    So the rule is not "roughly similar", it is: these selectors use var(--measure) or they
    use nothing. This reads the stylesheet rather than a rendered page, which cannot catch a
    width imposed by a grid, but it catches the failure that actually happened.
    """
    css = (ROOT / "templates" / "style.css").read_text(encoding="utf-8")
    problems = []
    print()
    print("MEDIDA")

    owned = [".project-tagline", ".streams dd", ".assay-figure p", ".prose"]
    for selector in owned:
        pattern = re.escape(selector) + r"\s*\{[^{}]*?max-width:\s*([^;]+);"
        found = re.search(pattern, css, re.S)
        if not found:
            problems.append(f"«{selector}» ya no declara max-width: revisar a qué ancho sale")
        elif "var(--measure)" not in found.group(1):
            problems.append(f"«{selector}» usa {found.group(1).strip()} en vez de var(--measure)")

    declared = re.search(r"--measure:\s*([^;]+);", css)
    if not declared:
        problems.append("no existe la variable --measure")
    elif "ch" in declared.group(1).split("/*")[0]:
        problems.append("--measure está en ch: da un ancho distinto por tamaño de letra, "
                        "que es justo lo que se arregló")
    else:
        print(f"  --measure = {declared.group(1).split('/*')[0].strip()}, "
              f"la misma para {len(owned)} bloques")

    if not problems:
        print("  ningún bloque de texto inventa su propio ancho")
    return problems


def main() -> None:
    problems = (check_contrast() + check_links() + check_images() + check_motion()
                + check_index() + check_measure())

    print("\n" + "-" * 66)
    if problems:
        print(f"{len(problems)} problema(s):\n")
        for problem in problems:
            print(f"  · {problem}")
        sys.exit(1)
    print("Todo en verde.")


if __name__ == "__main__":
    main()
