"""TikTok, Course 2: what is in this file, and what story does it already tell.

The Course 2 project is exploration, not testing and not modelling. So the deliverable is
the data-quality pass plus the one finding the data hands over without being asked.

Run it:
    python projects/curso2/tiktok/02_scripts/tiktok_eda.py

Reads Kevin's CSV read-only, writes figures to 03_figures/ and every publishable number to
04_reports/model_results.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))       # projects/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # projects/curso2/
from common import (  # noqa: E402
    ANNOTATION, CAPTION, PANEL_TITLE, SQUARE, TALL, TITLE, WIDE, interactive_layout, log_bars, save_figure, save_interactive,
    AZURITE, GOLD, GRAPHITE, MUTED, SURFACE, Results, banner, dataset, figures_dir,
    style, thousands,
)
from quality import full_report  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "tiktok"
COURSE = "curso2"
FIGURES = figures_dir(COURSE, SLUG)
COUNTS = ["video_view_count", "video_like_count", "video_share_count",
          "video_download_count", "video_comment_count"]


def figure_claim_gap(df: pd.DataFrame, results: Results) -> None:
    """The finding the file hands over: what a video says decides how far it travels."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE, sharex=True, sharey=True)
    edges = np.logspace(np.log10(20), np.log10(1_100_000), 40)

    for ax, (label, key, colour) in zip(axes, [
        ("Vídeos con reclamación", "claim", GOLD),
        ("Vídeos de opinión", "opinion", AZURITE),
    ]):
        views = df.loc[df.claim_status.eq(key), "video_view_count"]
        ax.hist(views, bins=edges, color=colour, alpha=0.95, edgecolor=SURFACE,
                linewidth=0.6, zorder=2)
        ax.axvline(views.median(), color=GRAPHITE, linewidth=1.7, zorder=4)
        ax.annotate(f"mediana\n{thousands(views.median())}",
                    xy=(views.median(), 0.94), xycoords=("data", "axes fraction"),
                    xytext=(8, 0), textcoords="offset points", va="top",
                    fontsize=ANNOTATION, weight="bold", color=GRAPHITE)
        ax.set_xscale("log")
        ax.set_title(f"{label}\n{thousands(len(views))} vídeos", loc="left",
                     fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.set_xlabel("Visualizaciones por vídeo")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Número de vídeos")
    axes[0].xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: thousands(v) if v < 1000 else
        (f"{v / 1000:g} mil" if v < 1_000_000 else f"{v / 1_000_000:g} M")))

    ratio = f"{results.data['finding']['view_ratio']}".replace(".", ",")
    fig.text(0.005, -0.04,
             f"Qué mirar: el eje es logarítmico y aun así las dos montañas no se solapan. "
             f"Un vídeo con reclamación se ve {ratio} veces más que uno de opinión.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.11,
             "Ninguna prueba estadística hizo falta para ver esto: está en el reparto. "
             "Y es la variable que los cursos siguientes van a intentar predecir.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_reclamacion_vs_opinion.png")
    plt.close(fig)

    # Interactive twin: 19.084 videos behind two shapes, and the thing worth doing is
    # reading the exact count of a bar and zooming into where the two nearly meet.
    import plotly.graph_objects as go

    plot = go.Figure()
    # The same bins for both classes, and the same ones the static figure uses. Letting
    # np.histogram choose per class gave each one its own edges, so the two overlaid shapes
    # did not line up and could not be compared bar against bar, which is the whole point
    # of overlaying them.
    shared_edges = np.log10(edges)
    for label, key, colour in [("Con reclamación", "claim", GOLD),
                               ("De opinión", "opinion", AZURITE)]:
        views = df.loc[df.claim_status.eq(key), "video_view_count"]
        counts, log_edges = np.histogram(np.log10(views.clip(lower=1)), bins=shared_edges)
        # Centres and widths both come from log_bars: plotly measures bar width in raw
        # values even here, so each bar needs its own, and the centre has to be the
        # arithmetic middle of the bin. Left to plotly, every bar gets the width of the
        # narrowest one and the whole chart renders as hairlines.
        centres, widths = log_bars(log_edges)
        plot.add_bar(x=centres, y=counts, name=label, width=widths,
                     marker_color=colour, marker_line_color=SURFACE, marker_line_width=1,
                     hovertemplate="%{customdata}<extra></extra>",
                     customdata=[f"{thousands(round(lo))} a {thousands(round(hi))} vistas"
                                 f"<br><b>{thousands(c)} vídeos</b>"
                                 for lo, hi, c in zip(10 ** log_edges[:-1],
                                                      10 ** log_edges[1:], counts)])
    plot.update_layout(**interactive_layout(
        "Una reclamación se ve cien veces más que una opinión",
        f"Un vídeo con reclamación promedia "
        f"{thousands(round(results.data['finding']['claim_mean_views']))} vistas y uno de "
        f"opinión {thousands(round(results.data['finding']['opinion_mean_views']))}. "
        f"El eje es logarítmico y aun así las dos montañas casi no se tocan."))
    plot.update_layout(barmode="overlay")
    plot.update_traces(opacity=0.85)
    plot.update_xaxes(type="log", title_text="Visualizaciones por vídeo")
    plot.update_yaxes(title_text="Número de vídeos")
    save_interactive(plot, FIGURES, "01_reclamacion_vs_opinion.html")


def figure_missing(raw: pd.DataFrame, results: Results) -> None:
    """Where the 298 gaps are: all in the same seven columns, all in the same rows."""
    style()
    missing = raw.isna().sum()
    missing = missing[missing > 0]

    fig, ax = plt.subplots(figsize=WIDE)
    bars = ax.barh(list(missing.index)[::-1], list(missing.values)[::-1], color=GOLD,
                   height=0.6, edgecolor=SURFACE, linewidth=1.1, zorder=2)
    for bar, value in zip(bars, list(missing.values)[::-1]):
        ax.annotate(thousands(value), xy=(value, bar.get_y() + bar.get_height() / 2),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=ANNOTATION, weight="bold", color=GRAPHITE)
    ax.set_xlim(0, missing.max() * 1.22)
    ax.set_xlabel("Casillas vacías")
    ax.set_title("Los huecos no están repartidos: son siempre las mismas filas",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)

    rows = results.data["quality"]["incomplete_rows"]
    fig.text(0.005, -0.10,
             f"Qué mirar: las siete columnas tienen exactamente {thousands(rows)} huecos "
             f"cada una, y son {thousands(rows)} filas, no {thousands(rows * 7)}. "
             f"El registro entró vacío de golpe.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "02_ausentes.png")
    plt.close(fig)


def main() -> None:
    results = Results(SLUG, "TikTok: qué hay en el archivo antes de analizar nada", COURSE)
    raw = pd.read_csv(dataset(SLUG))

    full_report(
        raw, results,
        numeric_expected=COUNTS + ["video_duration_sec"],
        outlier_columns=COUNTS + ["video_duration_sec"],
        impossible={
            "vistas negativas": lambda d: d.video_view_count.lt(0),
            "me gusta por encima de las vistas": lambda d: d.video_like_count.gt(
                d.video_view_count),
            "duracion fuera de 1 a 60 segundos": lambda d: ~d.video_duration_sec.between(
                1, 60),
        },
    )

    banner("7. Si los huecos son de filas enteras o de casillas sueltas")
    incomplete = raw[raw.isna().any(axis=1)]
    results.put("missing_shape.rows", len(incomplete))
    results.put("missing_shape.columns_affected", int(raw.isna().sum().gt(0).sum()))
    results.put("missing_shape.rows_missing_all_seven",
                int((incomplete.isna().sum(axis=1) == 7).sum()),
                "filas a las que les faltan las siete columnas a la vez")

    df = raw.dropna().copy()
    results.put("quality.rows_complete", len(df), "filas completas")

    banner("8. Lo que el archivo cuenta sin que nadie le pregunte")
    by_claim = df.groupby("claim_status").video_view_count.agg(["count", "mean", "median"])
    print(by_claim.round(1).to_string())
    for key in ("claim", "opinion"):
        results.put(f"finding.{key}_videos", int(by_claim.loc[key, "count"]))
        results.put(f"finding.{key}_mean_views", round(float(by_claim.loc[key, "mean"]), 1))
        results.put(f"finding.{key}_median_views",
                    round(float(by_claim.loc[key, "median"]), 1))
    ratio = by_claim.loc["claim", "mean"] / by_claim.loc["opinion", "mean"]
    results.put("finding.view_ratio", round(float(ratio), 1),
                "cuántas veces más se ve una reclamación")

    banner("9. Figuras")
    figure_claim_gap(df, results)
    figure_missing(raw, results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
