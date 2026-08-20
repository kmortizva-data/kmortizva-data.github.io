"""Capture the project screenshots the home page shows.

The site declares four screenshots in content/site.json and for a long time had none of
them, so every project card said "screenshot pending". This takes them.

It drives headless Chrome from the command line rather than a browser extension, which
means the shots can be retaken later by anyone with the repo, and that a broken preview
pane cannot block them.

Each project has to be serving first. Start them however you like; the URLs are below and
the script tells you which ones are not answering instead of writing a blank image.

Usage:
    python src/shoot.py            # every project that is up
    python src/shoot.py froth      # just one
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "assets" / "shots"

WIDTH, HEIGHT = 1440, 900
SETTLE_MS = 6000        # default: enough for a static page with figures

# Streamlit paints a grey skeleton first and only fills it once its websocket has
# delivered the app, so the default budget caught the loader instead of the product.
# bg-remover kicks off a demo render on load, and a longer budget caught it mid-spinner
# with an empty error banner. Short enough catches the clean idle state.
SETTLE_BY_PROJECT = {"froth": 40000, "bg-remover": 2500}

# Where each browser lives on Windows, most preferred first.
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# The file name of each shot is already declared in content/site.json, so these have to
# match it or shot_block() will not find them.
PROJECTS = {
    "froth": ("http://localhost:8501/", "froth-network.png",
              "Froth: el mapa semantico. Arranca con la config 'froth-web'."),
    "silica": ("http://localhost:8792/out/index.html", "silica-horizons.png",
               "El curso Silice. Arranca con la config 'silice'."),
    "concentra": ("http://localhost:8791/out/index.html", "concentra-site.png",
                  "Concentra. Arranca con la config 'concentra'."),
    "bg-remover": ("http://127.0.0.1:8000/", "bg-remover.png",
                   "bg-remover. Arranca con .\\run.ps1 en su carpeta."),
}


def find_browser() -> str:
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("chrome") or shutil.which("msedge")
    if found:
        return found
    raise SystemExit("No se encontró Chrome ni Edge. Se buscó en:\n  "
                     + "\n  ".join(BROWSERS))


def is_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            return response.status < 400
    except (urllib.error.URLError, OSError):
        return False


def capture(browser: str, url: str, target: Path, settle: int = SETTLE_MS) -> bool:
    """One screenshot. Chrome needs its own profile directory or it refuses to write."""
    profile = SHOTS.parent / ".chrome-profile"
    finished = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         f"--window-size={WIDTH},{HEIGHT}", f"--user-data-dir={profile}",
         f"--screenshot={target}", f"--virtual-time-budget={settle}", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    if target.exists() and target.stat().st_size > 5000:
        return True
    print(f"      {(finished.stderr or finished.stdout).strip()[-200:]}")
    return False


def main() -> None:
    wanted = sys.argv[1:] or list(PROJECTS)
    unknown = [name for name in wanted if name not in PROJECTS]
    if unknown:
        raise SystemExit(f"No conozco: {', '.join(unknown)}. "
                         f"Hay: {', '.join(PROJECTS)}")

    browser = find_browser()
    SHOTS.mkdir(parents=True, exist_ok=True)
    print(f"{Path(browser).name} · {WIDTH}x{HEIGHT}\n")

    taken, missing = 0, []
    for name in wanted:
        url, filename, hint = PROJECTS[name]
        if not is_up(url):
            print(f"  APAGADO  {name:<12} {url}")
            missing.append(f"{name}: {hint}")
            continue
        target = SHOTS / filename
        settle = SETTLE_BY_PROJECT.get(name, SETTLE_MS)
        if capture(browser, url, target, settle):
            size = target.stat().st_size / 1024
            # A near-empty PNG usually means the app was still painting its loader.
            flag = "  <- revisar, muy ligera" if size < 25 else ""
            print(f"  OK       {name:<12} {filename}  {size:.0f} KB{flag}")
            taken += 1
        else:
            print(f"  FALLA    {name:<12} {url}")
            missing.append(f"{name}: la captura no se escribió")

    print(f"\n{'-' * 62}")
    print(f"{taken} de {len(wanted)} capturas en assets/shots/")
    for note in missing:
        print(f"  pendiente · {note}")


if __name__ == "__main__":
    main()
