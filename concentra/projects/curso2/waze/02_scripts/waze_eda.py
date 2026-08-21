"""Waze, Course 2: what is in this file, and what nobody downstream noticed.

The exploration pass over the churn dataset. It finds the 700 unlabelled users that the
Course 4 model had to deal with, and something the Course 3 and Course 4 work never
flagged: a set of users whose recorded driving is physically impossible.

Run it:
    python projects/curso2/waze/02_scripts/waze_eda.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))       # projects/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # projects/curso2/
from common import (  # noqa: E402
    ANNOTATION, CAPTION, PANEL_TITLE, SQUARE, TALL, TITLE, WIDE, interactive_layout, save_figure,
    log_bars, save_interactive,
    AZURITE, GOLD, GRAPHITE, MUTED, SURFACE, Results, banner, dataset, figures_dir,
    style, thousands,
)
from quality import full_report  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "waze"
COURSE = "curso2"
FIGURES = figures_dir(COURSE, SLUG)

# A car sustaining this for a whole day is already implausible; the file goes much higher.
PLAUSIBLE_KM_PER_DAY = 1000


def figure_impossible(df: pd.DataFrame, results: Results) -> None:
    """Kilometres per driving day, with the line beyond which a car cannot go."""
    style()
    per_day = df.km_per_driving_day.replace([np.inf, -np.inf], np.nan).dropna()
    fig, ax = plt.subplots(figsize=WIDE)

    edges = np.logspace(0, np.log10(per_day.max() * 1.1), 46)
    ax.hist(per_day, bins=edges, color=GOLD, alpha=0.95, edgecolor=SURFACE,
            linewidth=0.6, zorder=2)
    ax.axvline(PLAUSIBLE_KM_PER_DAY, color=AZURITE, linewidth=2, zorder=4)

    beyond = int((per_day > PLAUSIBLE_KM_PER_DAY).sum())
    share = f"{100 * beyond / len(per_day):.1f}".replace(".", ",")
    ax.annotate(f"{thousands(beyond)} usuarios ({share} %)\npor encima de "
                f"{thousands(PLAUSIBLE_KM_PER_DAY)} km al día",
                xy=(PLAUSIBLE_KM_PER_DAY, 0.88), xycoords=("data", "axes fraction"),
                xytext=(12, 0), textcoords="offset points", va="top",
                fontsize=ANNOTATION, weight="bold", color=AZURITE)
    ax.annotate(f"el máximo del archivo:\n{thousands(per_day.max())} km en un solo día",
                xy=(per_day.max(), 0.30), xycoords=("data", "axes fraction"),
                xytext=(-10, 0), textcoords="offset points", ha="right", va="center",
                fontsize=CAPTION, weight="bold", color=GRAPHITE)

    ax.set_xscale("log")
    ax.set_xlabel("Kilómetros por día conducido (escala logarítmica)")
    ax.set_ylabel("Usuarios")
    ax.set_title("Hay usuarios que conducen más de lo que un coche puede", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="x", visible=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    fig.text(0.005, -0.05,
             "Qué mirar: la línea azul son 1.000 km en un solo día, que ya exige diez "
             "horas a cien por hora. Todo lo que queda a su derecha no describe a un "
             "conductor, describe un defecto del dato.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.13,
             "Ni el análisis del Curso 3 ni el modelo del Curso 4 marcaron esto, porque "
             "ninguno de los dos miró el reparto de esta variable derivada.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_kilometros_imposibles.png")
    plt.close(fig)

    # The interactive twin. This one earns it: 14.299 users behind the shape, and the
    # question the reader has is "how far does the tail go", which is a zoom.
    import plotly.graph_objects as go

    # The same bins as the static figure above, so the two versions of this chart are the
    # same chart. Recomputing them from the data gave a different first edge and the shapes
    # did not match.
    log_edges = np.log10(edges)
    counts, _ = np.histogram(np.log10(per_day), bins=log_edges)
    # Centres and widths both come from log_bars: plotly measures bar width in raw values
    # even here, so each bar needs its own. Left to plotly, every bar gets the width of the
    # narrowest one and they render as slivers next to the reference line.
    centres, widths = log_bars(log_edges)
    plot = go.Figure(go.Bar(
        x=centres, y=counts, width=widths,
        marker_color=GOLD, marker_line_color=SURFACE,
        marker_line_width=1, hovertemplate="%{customdata}<extra></extra>",
        customdata=[f"{thousands(round(lo))} a {thousands(round(hi))} km al día"
                    f"<br><b>{thousands(c)} usuarios</b>"
                    for lo, hi, c in zip(10 ** log_edges[:-1],
                                         10 ** log_edges[1:], counts)],
        name="Usuarios"))
    plot.add_vline(x=PLAUSIBLE_KM_PER_DAY, line_color=AZURITE, line_width=2)
    plot.update_layout(**interactive_layout(
        "Hay usuarios que conducen más de lo que un coche puede",
        f"La línea son 1.000 km en un solo día. A su derecha hay {thousands(beyond)} "
        f"usuarios ({share} %). Pasa el ratón para ver el tramo y haz zoom en la cola."))
    plot.update_xaxes(type="log", title_text="Kilómetros por día conducido")
    plot.update_yaxes(title_text="Usuarios")
    save_interactive(plot, FIGURES, "01_kilometros_imposibles.html")


def figure_labels(raw: pd.DataFrame, results: Results) -> None:
    """The 700 with no label, next to the two that do have one."""
    style()
    counts = raw.label.fillna("sin etiqueta").value_counts()
    order = ["retained", "churned", "sin etiqueta"]
    labels = ["Se quedan", "Abandonan", "Sin etiqueta"]
    colours = [GOLD, AZURITE, MUTED]

    fig, ax = plt.subplots(figsize=WIDE)
    bars = ax.barh(labels[::-1], [counts[k] for k in order][::-1], color=colours[::-1],
                   height=0.58, edgecolor=SURFACE, linewidth=1.2, zorder=2)
    for bar, key in zip(bars, order[::-1]):
        share = f"{100 * counts[key] / len(raw):.1f}".replace(".", ",")
        ax.annotate(f"{thousands(counts[key])}   {share} %",
                    xy=(counts[key], bar.get_y() + bar.get_height() / 2), xytext=(10, 0),
                    textcoords="offset points", va="center", fontsize=ANNOTATION,
                    weight="bold", color=GRAPHITE)
    ax.set_xlim(0, counts.max() * 1.3)
    ax.set_xlabel("Usuarios")
    ax.set_title("Uno de cada veintiuno no tiene etiqueta", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    fig.text(0.005, -0.10,
             "Qué mirar: los 700 sin etiqueta no son un grupo aparte, son usuarios de los "
             "que no se sabe si se quedaron. Antes de excluirlos hay que comprobar que se "
             "parecen al resto, que es lo que hace el paso siguiente.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "02_etiquetas.png")
    plt.close(fig)


def main() -> None:
    results = Results(SLUG, "Waze: qué hay en el archivo antes de modelar nada", COURSE)
    raw = pd.read_csv(dataset(SLUG))
    raw["km_per_driving_day"] = raw.driven_km_drives / raw.driving_days.replace(0, np.nan)

    full_report(
        raw, results,
        numeric_expected=["sessions", "drives", "driven_km_drives"],
        outlier_columns=["sessions", "drives", "driven_km_drives",
                         "duration_minutes_drives", "activity_days", "driving_days"],
        impossible={
            "dias de actividad fuera de 0 a 31": lambda d: ~d.activity_days.between(0, 31),
            "dias conduciendo mayores que dias activo":
                lambda d: d.driving_days.gt(d.activity_days),
            "mas de 1000 km en un solo dia conducido":
                lambda d: d.km_per_driving_day.gt(PLAUSIBLE_KM_PER_DAY),
            "mas de 24 horas al volante en un dia conducido":
                lambda d: (d.duration_minutes_drives / d.driving_days.replace(0, np.nan))
                .gt(24 * 60),
        },
    )

    banner("7. Cuánto de lejos llega lo imposible")
    per_day = raw.km_per_driving_day.replace([np.inf, -np.inf], np.nan).dropna()
    results.put("extremes.km_per_day_max", round(float(per_day.max()), 1),
                "el máximo de km en un día conducido")
    results.put("extremes.km_per_day_median", round(float(per_day.median()), 1),
                "la mediana, para comparar")
    results.put("extremes.hours_per_day_max",
                round(float((raw.duration_minutes_drives
                             / raw.driving_days.replace(0, np.nan)).max() / 60), 1),
                "el máximo de horas al volante en un día conducido")
    results.put("extremes.zero_driving_days", int(raw.driving_days.eq(0).sum()),
                "usuarios con cero días conduciendo, que dividen por cero")

    banner("8. Los 700 sin etiqueta, comparados con el resto")
    missing = raw.label.isna()
    results.put("labels.unlabelled", int(missing.sum()), "usuarios sin etiqueta")
    for column in ["sessions", "drives", "driven_km_drives", "activity_days"]:
        with_label = float(raw.loc[~missing, column].median())
        without = float(raw.loc[missing, column].median())
        gap = 100 * (without - with_label) / with_label
        results.put(f"labels.median_gap.{column}", round(gap, 1),
                    f"diferencia de mediana en {column} (%)")
    labelled = raw.dropna(subset=["label"])
    results.put("labels.churn_rate",
                round(100 * float(labelled.label.eq("churned").mean()), 2),
                "tasa de abandono entre los etiquetados (%)")

    banner("9. Figuras")
    figure_impossible(raw, results)
    figure_labels(raw, results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
