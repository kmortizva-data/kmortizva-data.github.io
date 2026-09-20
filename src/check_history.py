"""Before the site goes out: everything that has ever been in it, checked.

A public repository publishes its whole history, not its last commit. A file
committed by mistake and then removed is still there for anyone who clones. So
this does not look at the working tree. It asks git for every blob that any
commit has ever pointed to, and checks each one once.

This exists because the site published one for months. Nine Concentra reports
carried `"source_csv"` with the absolute path of the CSV on the author's disk,
user folder and all, live from commit ff3ec74. Nothing here was looking: the
gate next door, check_site.py, resolves links and measures contrast, and never
reads what travels inside a file. It is the same guard Bellows has had since it
went public, brought over and tuned to what this repository actually holds.

What it refuses:

  - any file over 50 MB, which is where GitHub itself starts warning
  - anything under a working folder that should never be committed
  - secrets: API keys and tokens in the shapes the common providers use
  - e-mail addresses, except the ones that are published on purpose
  - phone numbers
  - paths from this machine, which say more about the author than they should

Run:  python src/check_history.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
LIMITE_MB = 50

# Bellows uses 10 MB, because nothing there is meant to be big. Here the SQL
# engine of the live queries is a single 34.25 MB wasm that is supposed to be
# committed, so the useful line is GitHub's own: it warns over 50 MB and
# refuses over 100.

NUNCA = (".venv/", "assets/.chrome-profile/", "node_modules/")

# Carpetas de trabajo: las que empiezan por guion bajo. El build ya las salta al
# espejar desde que un perfil de Chromium entero, 337 ficheros, se coló en un
# commit. Esto es la segunda red, por si alguna llega por otro camino.
TRABAJO = re.compile(r"(^|/)_[^/]+/")

SECRETOS = {
    "clave de OpenAI o Anthropic": re.compile(rb"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    "token de GitHub": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "clave de AWS": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "clave de Google": re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b"),
    "contraseña escrita": re.compile(rb"(?i)\b(?:password|passwd|contrase\xc3\xb1a)\s*[=:]\s*\S{4,}"),
}
CORREO = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TELEFONO = re.compile(rb"\+\d{2}[ .]?\d{3}[ .]?\d{3}[ .]?\d{3}")

# Lo binario no lleva una ruta escrita a mano, y leerlo todo costaría minutos
# por nada. El tamaño y la carpeta sí se le miran.
BINARIO = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".parquet",
           ".woff2", ".woff", ".ttf", ".wasm", ".zip", ".mp4", ".webm")

# El correo de contacto está publicado a propósito: es el botón de la sección
# «Get in touch». Los otros nueve son de los autores de librerías ajenas que
# viajan con el sitio (Plotly, DuckDB wasm y las licencias que trae dentro:
# zlib, OpenSSL, Expat, jemalloc). No son de nadie de aquí, y borrarlos de una
# licencia ajena sería romperla. Si aparece uno nuevo, la guarda lo dice y se
# mira a mano antes de añadirlo.
CORREOS_PERMITIDOS = {
    b"kmortizva@datageeksunited.com",
    b"noreply@anthropic.com",
    b"feross@feross.org", b"emn178@gmail.com", b"bjoern@hoehrmann.de",
    b"jloup@gzip.org", b"jasone@canonware.com", b"rene.nyffenegger@adp-gmbh.ch",
    b"tjh@cryptsoft.com", b"sebastian@pipping.org", b"eay@cryptsoft.com",
    b"j@w1.fi", b"madler@alumni.caltech.edu", b"oneill@pcg-random.org",
    b"openssl-core@openssl.org", b"songweijia@gmail.com",
}


def rutas_de_esta_maquina() -> re.Pattern:
    """Las rutas de esta máquina, sacadas de ella y no escritas aquí.

    Escribir el nombre de usuario en el patrón haría que la guarda se cazase a
    sí misma en cuanto entrara en un commit, que es justo lo que existe para
    impedir. Se construye al correr, desde la carpeta de usuario.
    """
    casa = Path.home()
    trozos = {casa.name, str(casa), casa.as_posix(),
              "/" + casa.as_posix().replace(":", "").lower()}
    return re.compile(b"|".join(re.escape(t.encode("utf-8")) for t in trozos if t),
                      re.IGNORECASE)


RUTAS = rutas_de_esta_maquina()


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True).stdout


def todos_los_blobs() -> dict[str, str]:
    """Cada blob que algún commit ha tocado, con una de las rutas que tuvo."""
    salida: dict[str, str] = {}
    for linea in git("rev-list", "--all", "--objects").decode("utf-8", "replace").splitlines():
        partes = linea.split(" ", 1)
        if len(partes) == 2:
            salida.setdefault(partes[0], partes[1])
    return salida


def main() -> None:
    blobs = todos_los_blobs()
    commits = len(git("rev-list", "--all").split())
    tamanos: dict[str, int] = {}
    entrada = "\n".join(blobs).encode("utf-8")
    info = subprocess.run(["git", "cat-file", "--batch-check"], cwd=ROOT,
                          input=entrada, capture_output=True, check=True).stdout
    for linea in info.decode("utf-8").splitlines():
        sha, tipo, tam = linea.split()
        if tipo == "blob":
            tamanos[sha] = int(tam)

    problemas = []
    for sha, tam in tamanos.items():
        ruta = blobs[sha]
        if tam > LIMITE_MB * 1024 * 1024:
            problemas.append(f"{ruta}: {tam / 1048576:.1f} MB, más de {LIMITE_MB}")
        if ruta.startswith(NUNCA):
            problemas.append(f"{ruta}: esta carpeta no puede estar en el historial")
        if TRABAJO.search(ruta):
            problemas.append(f"{ruta}: carpeta de trabajo, no se publica")
        if ruta.lower().endswith(BINARIO):
            continue
        contenido = git("cat-file", "blob", sha)
        for nombre, patron in SECRETOS.items():
            for hit in patron.findall(contenido):
                problemas.append(f"{ruta}: {nombre} ({hit[:12].decode('utf-8', 'replace')}...)")
        for hit in set(CORREO.findall(contenido)) - CORREOS_PERMITIDOS:
            problemas.append(f"{ruta}: correo {hit.decode('utf-8', 'replace')}")
        for hit in set(TELEFONO.findall(contenido)):
            problemas.append(f"{ruta}: teléfono {hit.decode('utf-8', 'replace')}")
        for hit in set(RUTAS.findall(contenido)):
            problemas.append(f"{ruta}: ruta de esta máquina ({hit.decode('utf-8', 'replace')})")

    print(f"  {commits} commits, {len(tamanos)} ficheros distintos en todo el historial")
    mayor = max(tamanos.items(), key=lambda kv: kv[1])
    print(f"  el mayor: {blobs[mayor[0]]}, {mayor[1] / 1048576:.2f} MB")
    print()
    if problemas:
        for p in sorted(set(problemas)):
            print(f"  {p}")
        raise SystemExit(f"{len(set(problemas))} problemas. No se publica.")
    print("Nada en el historial que no deba salir. Se puede publicar.")


if __name__ == "__main__":
    main()
