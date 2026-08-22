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
import re
import shutil
from urllib.parse import unquote
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


# Spelled out, because "Four projects" reads like prose and "4 projects" reads like a
# database. Beyond twelve the digit is the better choice anyway.
NUMBER_WORDS = {
    "en": ["no", "one", "two", "three", "four", "five", "six",
           "seven", "eight", "nine", "ten", "eleven", "twelve"],
    "es": ["ningún", "un", "dos", "tres", "cuatro", "cinco", "seis",
           "siete", "ocho", "nueve", "diez", "once", "doce"],
}


def spell(count: int, lang: str) -> str:
    words = NUMBER_WORDS[lang]
    return words[count] if count < len(words) else str(count)


def fill_counts(text: str, count: int, lang: str) -> str:
    """Replace {n} with the spelled count, and {N} with it capitalised.

    The project count used to be typed into six strings across two languages. Hiding one
    project made all six wrong at once, and nothing complained. Now it is computed.
    """
    word = spell(count, lang)
    return text.replace("{n}", word).replace("{N}", word[0].upper() + word[1:])


def open_href(project: dict, depth: int) -> str:
    """Resolve a project's open destination for a page `depth` folders down.

    External URLs pass through; site-relative ones get the same ../ prefix every other
    internal link uses, so the button works from the root and from /es/ alike.
    """
    href = project.get("open_href", "")
    if href.startswith(("http://", "https://")):
        return href
    return rel(depth) + href


def work_index(data: dict, lang: str, ui: dict, depth: int) -> str:
    """The projects as an index with a preview panel, instead of four tall cards.

    The cards said everything twice: `project_page()` already carries the problem, the
    method, the measured result, the prose and the stack. Repeating all of it on the home
    page cost a very long scroll and would have been unreadable at ten projects.

    What each row keeps is the part that cannot be inferred: the name and the number the
    project actually measured. Only the picture is behind the hover, so the page still
    works on a phone, under a screen reader, and with the script switched off.
    """
    live = [p for p in shown_projects(data) if not p.get("archive")]

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
            f'<span class="index-say">{esc(p["tagline"])}</span>'
            f'<span class="index-assay">{esc(p["mark"])}</span>'
            f'<span class="index-area">{esc(p["area"])}</span>'
            f'</a>'
            + (f'<a class="index-open" href="{esc(open_href(project, depth))}" '
               f'target="_blank" rel="noopener">'
               f'{esc(p["open_label"])} ↗</a>' if project.get("open_href") else "")
            + '</li>')

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
    old = [p for p in shown_projects(data) if p.get("archive")]
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


def shown_projects(data: dict) -> list:
    """The projects the site actually publishes. One definition, used by every builder."""
    return [p for p in data["projects"] if not p.get("hidden")]


def about_section(data: dict, lang: str) -> str:
    about = data["about"][lang]
    count = len([p for p in shown_projects(data) if not p.get("archive")])
    paragraphs = "".join(f"<p>{esc(fill_counts(par, count, lang))}</p>"
                         for par in about["body"])
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
    # An empty note used to render as an empty <p>, which still takes its grid column and
    # leaves the heading looking like it lost something.
    note = f'<p>{esc(block["note"])}</p>' if block.get("note") else ""
    return f'''<section id="credentials" class="wrap section">
  <div class="section-head reveal">
    <h2>{esc(block["title"])}</h2>
    {note}
  </div>
  <ul class="creds">{rows}</ul>
</section>'''


def home_page(data: dict, lang: str) -> str:
    ui = data["ui"][lang]
    hero = data["hero"][lang]
    work = data["work_intro"][lang]
    contact = data["contact"][lang]
    depth = 0 if lang == "en" else 1
    up = rel(depth)
    live_count = len([p for p in shown_projects(data) if not p.get("archive")])

    body = f"""<section class="wrap hero">
  <p class="eyebrow">{esc(hero["eyebrow"])}</p>
  <h1 class="split">{split_words(hero["headline"])}</h1>
  <div class="hero-foot">
    <p class="lede">{esc(hero["lede"])}</p>
    <p class="meta">{esc(fill_counts(hero["meta"], live_count, lang))}</p>
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
    <p>{esc(fill_counts(work["text"], live_count, lang))}</p>
  </div>
  {work_index(data, lang, ui, depth)}
</section>

{archive_section(data, lang, ui, depth)}

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

    # The open action leads the links, unless it IS the repo (Froth), where one link is
    # honest and two would be the same door twice.
    open_link = ""
    if project.get("open_href") and project["open_href"] != project["repo"]:
        open_link = (f'<a class="cta" href="{esc(open_href(project, depth))}" '
                     f'target="_blank" rel="noopener">{esc(p["open_label"])}</a>')

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

  <p class="assay-links">{open_link}<a href="{esc(project["repo"])}" target="_blank" rel="noopener">{esc(ui["view_repo"])}</a></p>
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
            if project.get("hidden"):
                continue
            write(ROOT / LANGS[lang]["work"] / f"{project['slug']}.html",
                  project_page(project, data, lang))
            pages += 1

    shutil.copy2(TEMPLATES / "style.css", ROOT / "style.css")
    shutil.copy2(TEMPLATES / "theme.js", ROOT / "theme.js")

    # The two static projects are published INSIDE this site, so a recruiter can open
    # them instead of reading about them. Mirrored on every build (the lesson from the
    # Notes PDFs: a copy that is not part of the build goes stale until somebody
    # remembers). The folder names preserve each build's relative geometry, measured
    # before writing this: Silice pages reference ../figuras/ and Concentra pages
    # reference ../../figures/, so pages and figures must keep their relative depth.
    EMBEDDED = [
        ("Exc-1-Learn Machine Learning/2_Curso/out",     "silice/curso"),
        ("Exc-1-Learn Machine Learning/2_Curso/figuras", "silice/figuras"),
        ("Concentra/out",     "concentra/cursos"),
        ("Concentra/figures", "concentra/figures"),
    ]
    neutralised = 0
    for source_rel, target_rel in EMBEDDED:
        source = ROOT.parent / source_rel
        if not source.exists():
            print(f"  ! embedded source missing, not copied: {source_rel}")
            continue
        # Every file travels, .md included: the Silice course index links its own
        # cerebro, and the Concentra case pages link report .md files as material.
        # Excluding them broke a link the gate caught. The cerebros are up to date now.
        shutil.copytree(source, ROOT / target_rel, dirs_exist_ok=True)

        # The Concentra case pages link to files on Kevin's machine (scripts, cheatsheets
        # under 03_Data Analysis Coursera). Published, every one would 404 and the paths
        # would leak his local folder layout. Any link that climbs out of the site root
        # becomes plain text: the reference stays readable, the dead door is gone.
        for page in (ROOT / target_rel).rglob("*.html"):
            html = page.read_text(encoding="utf-8")

            def _neutralise(match: "re.Match") -> str:
                nonlocal neutralised
                href = unquote(match.group("href"))
                if href.startswith(("http://", "https://", "mailto:", "#")):
                    return match.group(0)
                resolved = (page.parent / href.split("#")[0]).resolve()
                if ROOT.resolve() in resolved.parents or resolved == ROOT.resolve():
                    return match.group(0)
                neutralised += 1
                return f'<span class="local-ref">{match.group("text")}</span>'

            rewritten = re.sub(
                r'<a\s[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<text>.*?)</a>',
                _neutralise, html, flags=re.S)
            if rewritten != html:
                page.write_text(rewritten, encoding="utf-8", newline="\n")
    if neutralised:
        print(f"  {neutralised} enlaces locales neutralizados en los sitios embebidos")

    # Concentra's case pages also reference sibling material that lives NEXT to out/
    # rather than inside it: figures, scripts and notebooks under projects/curso5. The
    # whole folder is 36 MB with __pycache__ in it, so instead of mirroring it, exactly
    # the files the published pages reference are copied, resolved the same way the link
    # checker resolves them. A reference that cannot be satisfied from the source either
    # becomes plain text (href) or stays red in the gate (src), never a silent 404.
    concentra_src = ROOT.parent / "Concentra"
    croot = (ROOT / "concentra").resolve()
    demand_copied = 0
    # Ran to a fixpoint, because a copied page can itself reference more files: the
    # interactive Plotly figures are HTML pages that each want a plotly.min.js beside
    # them, and one pass only discovers them after copying their referrer.
    passes = 0
    while True:
      passes += 1
      copied_this_pass = 0
      for page in (ROOT / "concentra").rglob("*.html"):
          html_text = page.read_text(encoding="utf-8")
          dead_hrefs = []
          for kind, target in re.findall(r'(src|href)="([^"#][^"]*)"', html_text):
              if target.startswith(("http://", "https://", "mailto:", "data:")):
                  continue
              resolved = (page.parent / unquote(target).split("#")[0]).resolve()
              if croot not in resolved.parents or resolved.exists():
                  continue
              rel_parts = resolved.relative_to(croot).parts
              mapped = ("out",) + rel_parts[1:] if rel_parts[0] == "cursos" else rel_parts
              candidate = concentra_src.joinpath(*mapped)
              if candidate.is_file():
                  resolved.parent.mkdir(parents=True, exist_ok=True)
                  shutil.copy2(candidate, resolved)
                  demand_copied += 1
                  copied_this_pass += 1
              elif kind == "href":
                  dead_hrefs.append(target)
          if dead_hrefs:
              for target in dead_hrefs:
                  html_text = re.sub(
                      r'<a\s[^>]*href="' + re.escape(target) + r'"[^>]*>(.*?)</a>',
                      r'<span class="local-ref">\1</span>', html_text, flags=re.S)
                  neutralised += 1
              page.write_text(html_text, encoding="utf-8", newline="\n")
      if copied_this_pass == 0 or passes >= 6:
          break
    if demand_copied:
        print(f"  {demand_copied} archivos de material copiados bajo demanda (Concentra)")

    # GitHub Pages runs Jekyll unless told otherwise, and Jekyll silently drops
    # folders whose names start with an underscore. Nothing here does today, but
    # the file costs nothing and removes a whole class of "it worked locally" bug.
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    # CNAME only once the domain's DNS points at GitHub. With the file present and the
    # DNS not set, Pages fails its domain check and the github.io URL redirects to a dead
    # domain, so the first publication lives on github.io and the domain comes later.
    cname = ROOT / "CNAME"
    if data.get("publish_domain"):
        cname.write_text(data["domain"] + "\n", encoding="utf-8")
    elif cname.exists():
        cname.unlink()

    missing = [p["slug"] for p in data["projects"]
               if not (ASSETS / "shots" / (p.get("shot") or "_")).exists()]
    where = data["domain"] if data.get("publish_domain") else "github.io (CNAME off)"
    print(f"  {pages} pages written, domain -> {where}")
    if missing:
        print(f"  ! still no screenshot for: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
