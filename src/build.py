"""Build the portfolio site: static HTML, two languages, no dependencies.

    python src/build.py

Reads content/site.json and writes the pages next to it. Nothing is fetched and
nothing is installed: this is the Python standard library only, which is the same
choice Concentra made and for the same reason, a slow network.

Output layout. English sits at the root because the audience is European doctoral
programmes; Spanish sits under /es/.

    index.html              work/<slug>.html
    es/index.html           es/proyectos/<slug>.html

The generated files are overwritten every run. Edit content/ and templates/.
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "site.json"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"

# Where each language's pages live, relative to the site root. An empty "home"
# means the site root itself.
LANGS = {
    "en": {"home": "", "work": "work"},
    "es": {"home": "es", "work": "es/proyectos"},
}


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def rel(depth: int) -> str:
    """Prefix that walks back up to the site root from a page `depth` folders down.

    Every href is relative rather than absolute so the site can be reviewed from a
    plain folder or a subpath, not only from the domain it will finally live on.
    """
    return "../" * depth


def home_href(lang: str, depth: int) -> str:
    up = rel(depth)
    return up + ("index.html" if lang == "en" else "es/index.html")


def counterpart(lang: str, kind: str, slug: str = "") -> str:
    """Path of the same page in the other language, measured from the site root."""
    other = "es" if lang == "en" else "en"
    if kind == "home":
        base = LANGS[other]["home"]
        return f"{base}/index.html" if base else "index.html"
    return f"{LANGS[other]['work']}/{slug}.html"


def shell(*, title: str, desc: str, lang: str, depth: int, switch_href: str,
          ui: dict, site: dict, body: str) -> str:
    up = rel(depth)
    author = esc(site["author"])
    switch = esc(up + switch_href)
    home = home_href(lang, depth)
    other_lang = "es" if lang == "en" else "en"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<link rel="alternate" hreflang="{other_lang}" href="{switch}">
<script>document.documentElement.className="js"</script>
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<a class="skip" href="#main">{esc(ui["skip"])}</a>
<header class="wrap masthead">
  <a class="mark" href="{home}">{author} <b>/</b> {esc(site["domain"])}</a>
  <nav>
    <a href="{home}#about">{esc(ui["nav_about"])}</a>
    <a href="{home}#work">{esc(ui["nav_work"])}</a>
    <a href="{home}#notes">{esc(ui["nav_notes"])}</a>
    <a href="{switch}" rel="alternate" hreflang="{other_lang}">{esc(ui["switch_to"])}</a>
    <a class="cta" href="mailto:{esc(site["email"])}">{esc(ui["cta"])}</a>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer class="wrap foot">
  <span>&copy; 2026 {author}</span>
  <span><a href="mailto:{esc(site["email"])}">{esc(site["email"])}</a></span>
  <span><a href="https://github.com/{esc(site["github_user"])}">github.com/{esc(site["github_user"])}</a></span>
</footer>
<div class="curtain" aria-hidden="true"></div>
<script src="{up}assets/lenis.min.js" defer></script>
<script src="{up}theme.js" defer></script>
</body>
</html>
"""


def shot_block(project: dict, lang: str, depth: int) -> str:
    """The screenshot, or a labelled gap where one is still missing.

    A missing screenshot renders as an obvious placeholder rather than a broken
    image icon, so an unfinished page reads as unfinished instead of as broken.
    """
    name = project.get("shot") or ""
    if name and (ASSETS / "shots" / name).exists():
        # No lazy loading. There are four images on the whole site, they are the point
        # of the page, and deferring them means a fast scroll (or a screenshot) lands on
        # alt text instead of the work.
        return (f'<img src="{rel(depth)}assets/shots/{esc(name)}" '
                f'alt="{esc(project["shot_alt"][lang])}" '
                f'width="1440" height="900" decoding="async">')
    return '<p class="placeholder">screenshot pending</p>'


def streams_of(project: dict, lang: str, ui: dict) -> str:
    return "".join(
        f"<div><dt>{esc(ui[key])}</dt><dd>{esc(project[lang][key])}</dd></div>"
        for key in ("feed", "process", "concentrate")
    )


def assay_figure(project: dict, lang: str, ui: dict) -> str:
    p = project[lang]
    return f"""<div class="assay-figure">
        <p class="eyebrow">{esc(ui["assay"])}</p>
        <q>{esc(p["assay"])}</q>
        <p>{esc(p["assay_detail"])}</p>
      </div>"""


def stack_of(project: dict) -> str:
    return "".join(f"<li>{esc(s)}</li>" for s in project["stack"])


def work_index(data: dict, lang: str, ui: dict, depth: int) -> str:
    """The projects as an index with a preview panel, instead of four tall cards.

    The cards said everything twice: `project_page()` already carries the problem, the
    method, the measured result, the prose and the stack. Repeating all of it on the home
    page cost a very long scroll and would have been unreadable at ten projects.

    What each row keeps is the part that cannot be inferred: the name and the number the
    project actually measured. Only the picture is behind the hover, so the page still
    works on a phone, under a screen reader, and with the script switched off.
    """
    live = [project for project in data["projects"] if not project.get("archive")]

    rows = []
    for number, project in enumerate(live, start=1):
        p = project[lang]
        href = f"{rel(depth)}{LANGS[lang]['work']}/{project['slug']}.html"
        rows.append(
            f'<li class="index-row reveal" data-slug="{esc(project["slug"])}" '
            f'data-accent="{esc(project["accent"])}">'
            f'<a href="{href}">'
            f'<span class="index-num">{number:02d}</span>'
            f'<span class="index-thumb">{shot_block(project, lang, depth)}</span>'
            f'<span class="index-name">{esc(p["name"])}</span>'
            f'<span class="index-assay">{esc(p["mark"])}</span>'
            f'<span class="index-area">{esc(p["area"])}</span>'
            f'</a></li>')

    # The panel holds every screenshot stacked. The first is marked visible at build time,
    # so with no JavaScript the panel shows a real image rather than an empty box.
    panes = "".join(
        f'<div class="index-pane{" on" if index == 0 else ""}" '
        f'data-slug="{esc(project["slug"])}">{shot_block(project, lang, depth)}</div>'
        for index, project in enumerate(live))

    return f'''<div class="index-layout">
    <ol class="index">{"".join(rows)}</ol>
    <div class="index-panel" aria-hidden="true">{panes}</div>
  </div>'''


def archive_section(data: dict, lang: str, ui: dict, depth: int) -> str:
    """Older projects as compact rows. Nothing is drawn while nothing is archived.

    This is the half that makes the page survive growth: the index stays short and
    readable, and everything that has had its turn moves down here, where a row costs one
    line instead of a screenshot and four paragraphs.
    """
    old = [project for project in data["projects"] if project.get("archive")]
    if not old:
        return ""

    rows = "".join(
        f'<li class="archive-row">'
        f'<a href="{rel(depth)}{LANGS[lang]["work"]}/{project["slug"]}.html">'
        f'<span class="archive-name">{esc(project[lang]["name"])}</span>'
        f'<span class="archive-area">{esc(project[lang]["area"])}</span>'
        f'<span class="archive-year">{esc(project.get("year", ""))}</span>'
        f'</a></li>'
        for project in old)

    return f'''<section id="archive" class="wrap section">
  <div class="section-head reveal">
    <h2>{esc(ui["archive_title"])}</h2>
    <p>{esc(ui["archive_note"])}</p>
  </div>
  <ul class="archive">{rows}</ul>
</section>'''


def marquee(data: dict, lang: str) -> str:
    """The numbers, scrolling. Vlad uses a marquee as decoration; this one carries the
    four measured results, so it earns the space it takes."""
    items = data["marquee"][lang]
    run = "".join(f"<span>{esc(text)}</span>" for text in items)
    # The track is duplicated so the loop has no visible seam when it wraps.
    return f'''<div class="marquee" aria-hidden="true">
  <div class="marquee-track">{run}{run}</div>
</div>'''


def about_section(data: dict, lang: str) -> str:
    about = data["about"][lang]
    paragraphs = "".join(f"<p>{esc(par)}</p>" for par in about["body"])
    marks = "".join(
        f'<div><span class="mark-value">{esc(m["value"])}</span>'
        f'<span class="mark-label">{esc(m["label"])}</span></div>'
        for m in about["marks"])
    return f'''<section id="about" class="wrap section band">
  <div class="about reveal">
    <h2>{esc(about["title"])}</h2>
    <div class="about-body">{paragraphs}</div>
  </div>
  <div class="marks reveal">{marks}</div>
</section>'''


def split_words(text: str) -> str:
    """Wrap each word so the headline can rise into place one word at a time.

    The reference site does this with GSAP's SplitText, which splits in the browser on
    every load. Doing it here costs nothing at runtime and the markup ships ready. The
    outer span clips, the inner one is what moves, and a plain space between them keeps
    the words selectable and readable to a screen reader.
    """
    words = esc(text).split(" ")
    return " ".join(
        f'<span class="w" style="--w:{index}"><span>{word}</span></span>'
        for index, word in enumerate(words))


def credentials_section(data: dict, lang: str) -> str:
    """The block a doctoral committee is actually looking for.

    It sits between "who I am" and the projects because the projects are the evidence and
    this is the claim. Nothing here is a logo: there are no rights to use university marks
    and the names carry more weight anyway.
    """
    block = data["credentials"][lang]
    rows = "".join(
        f'<li class="reveal">'
        f'<span class="cred-tag">{esc(item["tag"])}</span>'
        f'<span class="cred-label">{esc(item["label"])}</span>'
        f'<span class="cred-detail">{esc(item["detail"])}</span>'
        f'</li>'
        for item in block["items"])
    return f'''<section id="credentials" class="wrap section">
  <div class="section-head reveal">
    <h2>{esc(block["title"])}</h2>
    <p>{esc(block["note"])}</p>
  </div>
  <ul class="creds">{rows}</ul>
</section>'''


def home_page(data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    hero = data["hero"][lang]
    work = data["work_intro"][lang]
    notes = data["notes"][lang]
    contact = data["contact"][lang]
    depth = 0 if lang == "en" else 1
    up = rel(depth)

    note_items = "".join(
        f'<li><a href="{up}{esc(n["file"])}">'
        f'<span class="n-label">{esc(n["label"])}</span>'
        f'<span class="n-detail">{esc(n["detail"])}</span></a></li>'
        for n in notes["items"]
    )

    body = f"""<section class="wrap hero">
  <p class="eyebrow">{esc(hero["eyebrow"])}</p>
  <h1 class="split">{split_words(hero["headline"])}</h1>
  <div class="hero-foot">
    <p class="lede">{esc(hero["lede"])}</p>
    <p class="meta">{esc(hero["meta"])}</p>
  </div>
  <p class="hero-actions">
    <a class="cta" href="#work">{esc(ui["see_work"])}</a>
    <a class="cta cta-quiet" href="mailto:{esc(data["email"])}">{esc(ui["cta"])}</a>
  </p>
</section>

{marquee(data, lang)}

{about_section(data, lang)}

{credentials_section(data, lang)}

<section id="work" class="wrap section">
  <div class="section-head reveal">
    <h2>{esc(work["title"])}</h2>
    <p>{esc(work["text"])}</p>
  </div>
  {work_index(data, lang, ui, depth)}
</section>

{archive_section(data, lang, ui, depth)}

<section id="notes" class="wrap section band">
  <div class="section-head reveal">
    <h2>{esc(notes["title"])}</h2>
    <p>{esc(notes["text"])}</p>
  </div>
  <ul class="notes-list reveal">{note_items}</ul>
</section>

<section id="contact" class="wrap section">
  <div class="section-head reveal">
    <h2>{esc(contact["title"])}</h2>
    <p>{esc(contact["text"])}</p>
  </div>
  <ul class="contact-links reveal">
    <li><a href="mailto:{esc(data["email"])}">{esc(data["email"])}</a></li>
    <li><a href="https://github.com/{esc(data["github_user"])}">github.com/{esc(data["github_user"])}</a></li>
  </ul>
</section>"""

    return shell(title=str(data["author"]), desc=hero["lede"], lang=lang, depth=depth,
                 switch_href=counterpart(lang, "home"), ui=ui, site=data, body=body)


def project_page(project: dict, data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    p = project[lang]
    depth = len(LANGS[lang]["work"].split("/"))

    shot = shot_block(project, lang, depth)
    figure = ""
    if "placeholder" not in shot:
        figure = (f'<figure class="figure">{shot}'
                  f'<figcaption>{esc(project["shot_alt"][lang])}</figcaption></figure>')

    paragraphs = "".join(f"<p>{esc(par)}</p>" for par in p["body"])

    body = f"""<article class="wrap section">
  <a class="back" href="{home_href(lang, depth)}#work">{esc(ui["back"])}</a>
  <p class="eyebrow">{esc(p["status"])}</p>
  <h1 class="project-title">{esc(p["name"])}</h1>
  <p class="project-tagline">{esc(p["tagline"])}</p>

  {figure}

  <div class="assay assay-solo" data-accent="{esc(project["accent"])}">
    <div class="assay-body">
      <dl class="streams">{streams_of(project, lang, ui)}</dl>
      {assay_figure(project, lang, ui)}
    </div>
  </div>

  <div class="prose">{paragraphs}</div>

  <p class="eyebrow stack-label">{esc(ui["stack"])}</p>
  <ul class="stack">{stack_of(project)}</ul>

  <p class="assay-links"><a href="{esc(project["repo"])}">{esc(ui["view_repo"])}</a></p>
</article>"""

    return shell(title=f"{p['name']} - {data['author']}", desc=p["tagline"], lang=lang,
                 depth=depth, switch_href=counterpart(lang, "work", project["slug"]),
                 ui=ui, site=data, body=body)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))

    if "PENDIENTE" in str(data["author"]):
        print("  ! content/site.json still has a placeholder where the author's name goes.")
        print("    The site builds, but every page and every browser tab shows it.")

    pages = 0
    for lang in LANGS:
        base = ROOT / LANGS[lang]["home"] if LANGS[lang]["home"] else ROOT
        write(base / "index.html", home_page(data, lang))
        pages += 1
        for project in data["projects"]:
            write(ROOT / LANGS[lang]["work"] / f"{project['slug']}.html",
                  project_page(project, data, lang))
            pages += 1

    shutil.copy2(TEMPLATES / "style.css", ROOT / "style.css")
    shutil.copy2(TEMPLATES / "theme.js", ROOT / "theme.js")

    # The PDFs are built inside their own projects, which sit next to this site
    # under Portafolio/. Copying them on every build means a recompiled note reaches
    # the site by rebuilding, instead of going stale until somebody remembers.
    missing_pdfs = []
    for note in data.get("notes_files", []):
        source = ROOT.parent / note["src"]
        if not source.exists():
            missing_pdfs.append(note["src"])
            continue
        target = ROOT / note["out"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    # GitHub Pages runs Jekyll unless told otherwise, and Jekyll silently drops
    # folders whose names start with an underscore. Nothing here does today, but
    # the file costs nothing and removes a whole class of "it worked locally" bug.
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    (ROOT / "CNAME").write_text(data["domain"] + "\n", encoding="utf-8")

    missing = [p["slug"] for p in data["projects"]
               if not (ASSETS / "shots" / (p.get("shot") or "_")).exists()]
    print(f"  {pages} pages written, CNAME -> {data['domain']}")
    if missing:
        print(f"  ! still no screenshot for: {', '.join(missing)}")
    if missing_pdfs:
        print(f"  ! note PDF not found, its link on the site will 404: {', '.join(missing_pdfs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
