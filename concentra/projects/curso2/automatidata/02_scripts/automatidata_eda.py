"""Automatidata, Course 2: what is in this file, and when New York takes a taxi.

The exploration pass over the taxi file. The quality half finds the impossible trips that
the later courses had to clean; the story half is the one thing about this dataset that
neither Course 3 nor Course 4 ever asked: what time of day the business happens.

Run it:
    python projects/curso2/automatidata/02_scripts/automatidata_eda.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))       # projects/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # projects/curso2/
from common import (  # noqa: E402
    ANNOTATION, CAPTION, PANEL_TITLE, SQUARE, TALL, TITLE, WIDE, interactive_layout, save_figure, save_interactive,
    AZURITE, GOLD, GRAPHITE, MUTED, SURFACE, Results, banner, dataset, figures_dir,
    style, thousands,
)
from quality import full_report  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "automatidata"
COURSE = "curso2"
FIGURES = figures_dir(COURSE, SLUG)
STAMP = "%m/%d/%Y %I:%M:%S %p"


def figure_hours(df: pd.DataFrame, results: Results) -> None:
    """When the business happens, which is a question nobody asked of this file."""
    style()
    by_hour = df.groupby(df.pickup.dt.hour).size()
    peak_hour = int(by_hour.idxmax())
    quiet_hour = int(by_hour.idxmin())
    results.put("story.peak_hour", peak_hour, "la hora con más viajes")
    results.put("story.peak_trips", int(by_hour.max()))
    results.put("story.quiet_hour", quiet_hour, "la hora con menos")
    results.put("story.quiet_trips", int(by_hour.min()))
    results.put("story.peak_over_quiet", round(float(by_hour.max() / by_hour.min()), 1),
                "cuántas veces más")

    fig, ax = plt.subplots(figsize=WIDE)
    colours = [AZURITE if 17 <= hour <= 21 else GOLD for hour in by_hour.index]
    ax.bar(by_hour.index, by_hour.values, color=colours, width=0.78,
           edgecolor=SURFACE, linewidth=1.1, zorder=2)

    evening = int(by_hour.loc[17:21].sum())
    share = f"{100 * evening / len(df):.1f}".replace(".", ",")
    results.put("story.evening_trips", evening, "viajes entre las 17 y las 21")
    results.put("story.evening_share", round(100 * evening / len(df), 1), "  en porcentaje")
    ax.annotate(f"de 17 a 21 h se hacen {thousands(evening)} viajes,\nel {share} % del día",
                xy=(19, by_hour.max()), xytext=(0, 16), textcoords="offset points",
                ha="center", fontsize=ANNOTATION, weight="bold", color=AZURITE)

    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Hora de recogida")
    ax.set_ylabel("Número de viajes")
    ax.set_ylim(0, by_hour.max() * 1.22)
    ax.set_title("El taxi de Nueva York es un negocio de tarde y noche", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    times = f"{results.data['story']['peak_over_quiet']}".replace(".", ",")
    fig.text(0.005, -0.05,
             f"Qué mirar: la hora punta es la de las {peak_hour} y la más floja la de las "
             f"{quiet_hour}, con {times} veces más viajes en la primera.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             "Es la variable que el modelo del Curso 4 acabó usando como hora punta, y aquí "
             "se ve de dónde salen sus horas: no de una convención, del propio reparto.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_viajes_por_hora.png")
    plt.close(fig)

    # Interactive twin: twenty-four bars is exactly the case where counting them by eye is
    # annoying and hovering answers it at once.
    import plotly.graph_objects as go

    plot = go.Figure(go.Bar(
        x=list(by_hour.index), y=list(by_hour.values), marker_color=colours,
        marker_line_color=SURFACE, marker_line_width=1,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=[f"de {h}:00 a {h}:59<br><b>{thousands(v)} viajes</b>"
                    for h, v in zip(by_hour.index, by_hour.values)]))
    plot.update_layout(**interactive_layout(
        "El taxi de Nueva York es un negocio de tarde y noche",
        f"En azul, de 17 a 21 h: {thousands(evening)} viajes, el {share} % del día. "
        f"La hora punta es la de las {peak_hour} y la más floja la de las {quiet_hour}."))
    plot.update_xaxes(title_text="Hora de recogida", dtick=2)
    plot.update_yaxes(title_text="Número de viajes")
    save_interactive(plot, FIGURES, "01_viajes_por_hora.html")


def figure_impossible(df: pd.DataFrame, results: Results) -> None:
    """The trips that cannot have happened, one bar each."""
    style()
    checks = {
        "Tarifa cero o negativa": df.fare_amount.le(0),
        "Distancia cero": df.trip_distance.le(0),
        "Termina antes de empezar": df.duration.le(0),
        "Cero pasajeros": df.passenger_count.eq(0),
        "Importe total negativo": df.total_amount.lt(0),
    }
    counts = {name: int(mask.sum()) for name, mask in checks.items()}
    for name, value in counts.items():
        results.put(f"impossible_detail.{name}", value)
    any_problem = int(np.logical_or.reduce([m.values for m in checks.values()]).sum())
    results.put("impossible_detail.rows_with_any", any_problem,
                "viajes con al menos un problema")

    fig, ax = plt.subplots(figsize=WIDE)
    names = list(counts)[::-1]
    values = [counts[n] for n in names]
    bars = ax.barh(names, values, color=GOLD, height=0.62, edgecolor=SURFACE,
                   linewidth=1.1, zorder=2)
    for bar, value in zip(bars, values):
        ax.annotate(thousands(value), xy=(value, bar.get_y() + bar.get_height() / 2),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=ANNOTATION, weight="bold", color=GRAPHITE)
    ax.set_xlim(0, max(values) * 1.25)
    ax.set_xlabel("Número de viajes")
    ax.set_title("Viajes que no pudieron ocurrir", loc="left", fontsize=TITLE,
                 weight="bold", pad=16)
    ax.grid(axis="y", visible=False)

    share = f"{100 * any_problem / len(df):.2f}".replace(".", ",")
    fig.text(0.005, -0.08,
             f"Qué mirar: son {thousands(any_problem)} viajes en total, el {share} % del "
             f"archivo. Pocos, y hay que quitarlos igual: una tarifa negativa no es un "
             f"valor extremo, es una devolución que no describe un viaje.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "02_viajes_imposibles.png")
    plt.close(fig)


def main() -> None:
    results = Results(SLUG, "Automatidata: qué hay en el archivo de viajes", COURSE)
    raw = pd.read_csv(dataset(SLUG), index_col=0)
    raw["pickup"] = pd.to_datetime(raw.tpep_pickup_datetime, format=STAMP)
    raw["dropoff"] = pd.to_datetime(raw.tpep_dropoff_datetime, format=STAMP)
    raw["duration"] = (raw.dropoff - raw.pickup).dt.total_seconds() / 60

    full_report(
        raw, results,
        numeric_expected=["fare_amount", "trip_distance", "total_amount"],
        outlier_columns=["fare_amount", "trip_distance", "duration", "total_amount"],
        impossible={
            "tarifa cero o negativa": lambda d: d.fare_amount.le(0),
            "distancia cero": lambda d: d.trip_distance.le(0),
            "termina antes de empezar": lambda d: d.duration.le(0),
            "cero pasajeros": lambda d: d.passenger_count.eq(0),
            "mas de 24 horas de viaje": lambda d: d.duration.gt(24 * 60),
        },
    )

    banner("7. Las fechas, que aquí llegan como texto")
    results.put("dates.format", "MM/DD/YYYY hh:mm:ss AM/PM",
                "el formato en que vienen las dos marcas de tiempo")
    results.put("dates.span_days",
                int((raw.pickup.max() - raw.pickup.min()).days), "días que cubre el archivo")
    results.put("dates.first", raw.pickup.min().strftime("%Y-%m-%d"), "el primer viaje")
    results.put("dates.last", raw.pickup.max().strftime("%Y-%m-%d"), "el último")

    banner("8. El pico que no es un atípico")
    flat = raw.fare_amount.eq(52.0)
    results.put("flat_fare.trips", int(flat.sum()), "viajes que cuestan 52,00 exactos")
    results.put("flat_fare.ratecode_2", int((flat & raw.RatecodeID.eq(2)).sum()),
                "  de ellos, con código de tarifa 2")
    results.put("flat_fare.pct_of_file", round(100 * flat.mean(), 2), "  del archivo (%)")

    banner("9. Figuras")
    figure_hours(raw, results)
    figure_impossible(raw, results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
