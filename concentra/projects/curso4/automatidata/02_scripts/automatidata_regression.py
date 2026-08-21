"""Automatidata, Course 4: predict the fare of a taxi ride before it starts.

The New York City Taxi and Limousine Commission wants riders to see an estimated fare up
front. This builds that estimator as a multiple linear regression and, just as important,
reports how much it can be trusted.

Run it:
    python projects/curso4/automatidata/02_scripts/automatidata_regression.py

It reads Kevin's CSV read-only, writes figures to 03_figures/ and every publishable number
to 04_reports/model_results.json. Nothing outside this project folder is touched.

Three models are fitted, and which one is the answer is the point of the project:

  A. With the trip's actual distance and duration. Fits beautifully and **cannot be
     deployed**, because neither value exists until the ride is over, and the client
     needs the price before it starts.
  B. With route averages computed over the whole dataset, which is what the official
     exemplar does. Those averages carry information from the test trips into training.
  C. With route averages computed **on the training set only**, which is the same model
     built honestly.

B and C differ by 0.21 of R squared. That gap is not a detail: it is the difference
between what the model looks like in a notebook and what it does in production.

The JFK flat fare gets its own indicator. 513 of the 514 trips that cost exactly $52.00
are RatecodeID 2, the airport flat rate, where the price is fixed and distance is
irrelevant. Without that flag the model is asked to explain with distance something that
distance does not drive.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.model_selection import train_test_split
from statsmodels.stats.outliers_influence import variance_inflation_factor

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # projects/, for common.py
from common import (  # noqa: E402
    ANNOTATION, CAPTION, PANEL_TITLE, SQUARE, TALL, TITLE, WIDE, save_figure,
    AZURITE, GOLD, GRAPHITE, HAIRLINE, MUTED, SURFACE, Results, banner, dataset,
    figures_dir, interactive_layout, save_interactive, style, thousands,
)

import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "automatidata"
FIGURES = figures_dir("curso4", SLUG)
SEED = 42
STAMP = "%m/%d/%Y %I:%M:%S %p"

# Everything above this percentile is pulled down to it instead of deleted. Deleting the
# tail would quietly change the population the model claims to describe.
WINSOR = 0.995


# ----------------------------------------------------------------- load and clean

def load_and_clean(results: Results) -> pd.DataFrame:
    banner("1. Los datos, y qué hubo que arreglar")
    df = pd.read_csv(dataset(SLUG), index_col=0)
    results.put("data.rows_raw", len(df), "filas en el CSV")
    results.put("data.columns", df.shape[1], "columnas")
    results.put("data.duplicates", int(df.duplicated().sum()), "filas duplicadas")
    results.put("data.missing", int(df.isna().sum().sum()), "celdas vacías")

    df["pickup"] = pd.to_datetime(df.tpep_pickup_datetime, format=STAMP)
    df["dropoff"] = pd.to_datetime(df.tpep_dropoff_datetime, format=STAMP)
    df["duration"] = (df.dropoff - df.pickup).dt.total_seconds() / 60

    # The JFK flat fare, found in Course 3 and confirmed here: it is a rate code, not a
    # coincidence, and it is the single biggest reason distance alone cannot explain fares.
    flat = df.fare_amount.eq(52.0)
    results.put("jfk.trips_at_52", int(flat.sum()), "viajes a 52,00 dólares exactos")
    results.put("jfk.of_those_ratecode_2", int((flat & df.RatecodeID.eq(2)).sum()),
                "de esos, con tarifa plana de aeropuerto")
    results.put("jfk.ratecode_2_total", int(df.RatecodeID.eq(2).sum()),
                "viajes con tarifa plana en total")

    impossible = {
        "fare_amount <= 0": df.fare_amount.le(0),
        "duration <= 0": df.duration.le(0),
        "trip_distance <= 0": df.trip_distance.le(0),
    }
    keep = pd.Series(True, index=df.index)
    for reason, mask in impossible.items():
        results.put(f"cleaning.dropped.{reason.split()[0]}", int(mask.sum()),
                    f"descartados por {reason}")
        keep &= ~mask
    df = df[keep].copy()
    results.put("cleaning.rows_dropped", int((~keep).sum()), "filas descartadas en total")
    results.put("cleaning.rows_kept", len(df), "filas que quedan")

    # Winsorising, not deleting: the trip still counts, its extreme value stops dominating.
    for column in ["fare_amount", "duration", "trip_distance"]:
        cap = df[column].quantile(WINSOR)
        touched = int(df[column].gt(cap).sum())
        results.put(f"cleaning.cap.{column}", round(float(cap), 2),
                    f"tope del {WINSOR:.1%} para {column}")
        results.put(f"cleaning.capped_rows.{column}", touched,
                    f"  filas recortadas en {column}")
        df[column] = df[column].clip(upper=cap)

    results.put("data.fare_mean", round(float(df.fare_amount.mean()), 2), "tarifa media")
    results.put("data.fare_median", round(float(df.fare_amount.median()), 2),
                "tarifa mediana")
    results.put("data.distance_median", round(float(df.trip_distance.median()), 2),
                "distancia mediana (millas)")
    results.put("data.duration_median", round(float(df.duration.median()), 2),
                "duración mediana (minutos)")
    return df


# ------------------------------------------------------------------- feature work

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pair"] = df.PULocationID.astype(str) + "-" + df.DOLocationID.astype(str)
    hour = df.pickup.dt.hour
    weekday = df.pickup.dt.dayofweek.lt(5)
    df["rush_hour"] = (weekday & (hour.between(6, 9) | hour.between(16, 19))).astype(int)
    df["airport_flat"] = df.RatecodeID.eq(2).astype(int)
    return df


def add_pair_means(train: pd.DataFrame, test: pd.DataFrame,
                   results: Results | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Average distance and duration of each origin-destination pair, learned on train.

    A route's typical trip is a strong predictor and, unlike the trip's own distance, it
    is knowable before the ride starts, which is the whole point: the estimate has to
    exist at booking time.

    Learning it on the training set alone is what keeps the evaluation honest. Routes the
    training set never saw fall back to the global average, and how badly that goes is
    measured later, because it is the real weakness of the model.
    """
    grouped = train.groupby("pair")[["trip_distance", "duration"]].mean()
    fallback = train[["trip_distance", "duration"]].mean()

    for frame in (train, test):
        frame["mean_distance"] = (frame["pair"].map(grouped["trip_distance"])
                                  .fillna(fallback["trip_distance"]))
        frame["mean_duration"] = (frame["pair"].map(grouped["duration"])
                                  .fillna(fallback["duration"]))
    test["route_seen"] = test["pair"].isin(grouped.index)

    if results is not None:
        unseen = int((~test["route_seen"]).sum())
        results.put("features.pairs_learned", len(grouped),
                    "parejas origen-destino aprendidas")
        results.put("features.test_pairs_unseen", unseen,
                    "viajes de prueba por una ruta nunca vista")
        results.put("features.test_pairs_unseen_pct", round(100 * unseen / len(test), 1),
                    "  en porcentaje")
    return train, test


def add_leaky_pair_means(df: pd.DataFrame) -> pd.DataFrame:
    """The shortcut the official exemplar takes: route averages over the whole dataset.

    Kept in the script on purpose. Measuring how much it flatters the result is more
    convincing than asserting that it is wrong.
    """
    df = df.copy()
    means = df.groupby("pair")[["trip_distance", "duration"]].transform("mean")
    df["mean_distance"] = means["trip_distance"]
    df["mean_duration"] = means["duration"]
    return df


# ------------------------------------------------------------------------- models

def vif_table(frame: pd.DataFrame) -> pd.DataFrame:
    matrix = sm.add_constant(frame).values
    rows = [(name, variance_inflation_factor(matrix, i + 1))
            for i, name in enumerate(frame.columns)]
    return pd.DataFrame(rows, columns=["variable", "vif"]).sort_values("vif",
                                                                       ascending=False)


def fit(train: pd.DataFrame, features: list[str]) -> sm.regression.linear_model.OLS:
    return sm.OLS(train.fare_amount, sm.add_constant(train[features])).fit()


def score(model, frame: pd.DataFrame, features: list[str]) -> dict[str, float]:
    predicted = model.predict(sm.add_constant(frame[features]))
    residuals = frame.fare_amount - predicted
    sse = float((residuals ** 2).sum())
    sst = float(((frame.fare_amount - frame.fare_amount.mean()) ** 2).sum())
    return {
        "r2": 1 - sse / sst,
        "rmse": float(np.sqrt((residuals ** 2).mean())),
        "mae": float(residuals.abs().mean()),
        "predicted": predicted,
        "residuals": residuals,
    }


# ------------------------------------------------------------------------ figures

def figure_fares(df: pd.DataFrame, results: Results) -> None:
    """Where the money is, and the flat fare that breaks the pattern."""
    style()
    fig, ax = plt.subplots(figsize=WIDE)

    bins = np.arange(0, 60.5, 1.0)
    ax.hist(df.fare_amount.clip(upper=60), bins=bins, color=GOLD, alpha=0.95,
            edgecolor=SURFACE, linewidth=0.7, zorder=2)

    # Counted on the cleaned data, so the figure and model_results.json agree: six of the
    # original 514 were dropped for having no distance.
    spike = int(df.fare_amount.eq(52.0).sum())
    results.put("jfk.trips_at_52_clean", spike, "viajes a 52 dólares tras la limpieza")
    ax.annotate(f"tarifa plana del aeropuerto\n{thousands(spike)} viajes a 52 dólares",
                xy=(52, spike), xytext=(-14, 34), textcoords="offset points",
                ha="right", fontsize=CAPTION, weight="bold", color=AZURITE,
                arrowprops=dict(arrowstyle="-", color=AZURITE, linewidth=1.2))

    segments = [(0, 10, "Carreras cortas"), (10, 30, "Carreras medias"),
                (30, 1e9, "Carreras largas")]
    parts = []
    for low, high, name in segments:
        count = int(df.fare_amount.between(low, high, inclusive="left").sum())
        # Only the decimal gets a comma. Adjacent literals merge before .replace runs, so
        # applying it to the whole string also turned the 11.837 into 11,837.
        share = 100 * count / len(df)
        # Only the decimal gets a comma. Adjacent literals merge before .replace runs, so
        # applying it to the whole string also turned the 11.837 into 11,837.
        decimal = f"{share:.1f}".replace(".", ",")
        parts.append(f"{name}: {thousands(count)} viajes ({decimal} %)")
        results.put(f"segments.{name.split()[-1]}", round(share, 1), f"{name} (%)")
    ax.set_title("Casi todo el negocio son carreras baratas", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.set_xlabel("Tarifa del viaje (dólares)")
    ax.set_ylabel("Número de viajes")
    ax.set_xlim(0, 60)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    fig.text(0.005, -0.04, "Qué mirar: " + " · ".join(parts), fontsize=CAPTION,
             color=GRAPHITE, style="italic")
    fig.text(0.005, -0.10,
             "El pico de la derecha no es una carrera cara cualquiera: es un precio fijo "
             "que no depende de la distancia, y por eso el modelo necesita saber cuándo "
             "se aplica.", fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_tarifas.png")
    plt.close(fig)


def figure_distance(df: pd.DataFrame) -> None:
    """One panel per rate type, because they are two different pricing rules."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE, sharey=True)
    groups = [("Tarifa por taxímetro", df[df.airport_flat.eq(0)], GOLD),
              ("Tarifa plana de aeropuerto", df[df.airport_flat.eq(1)], AZURITE)]

    for ax, (name, part, colour) in zip(axes, groups):
        sample = part.sample(min(len(part), 3000), random_state=SEED)
        ax.scatter(sample.trip_distance, sample.fare_amount, s=7, color=colour,
                   alpha=0.28, edgecolors="none", zorder=2)
        if len(part) > 2:
            line = stats.linregress(part.trip_distance, part.fare_amount)
            span = np.array([part.trip_distance.min(), part.trip_distance.max()])
            ax.plot(span, line.intercept + line.slope * span, color=GRAPHITE,
                    linewidth=1.8, zorder=3)
            ax.annotate(f"{line.slope:.2f} $ por milla".replace(".", ","),
                        xy=(0.04, 0.93), xycoords="axes fraction", fontsize=ANNOTATION,
                        weight="bold", color=GRAPHITE)
        ax.set_title(f"{name}\n{thousands(len(part))} viajes", loc="left",
                     fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.set_xlabel("Distancia (millas)")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Tarifa (dólares)")

    fig.text(0.005, -0.04,
             "Qué mirar: a la izquierda la tarifa sube con la distancia, que es lo que un "
             "modelo lineal sabe hacer. A la derecha es una línea horizontal: el precio "
             "está fijado y la distancia no lo mueve.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "02_tarifa_vs_distancia.png")
    plt.close(fig)


def figure_residuals(test: pd.DataFrame, scored: dict, results: Results) -> None:
    """The two assumption checks that a picture answers faster than a number.

    Two shapes in the left panel are not noise, and both were verified before being
    labelled: the vertical stripe is every unseen route getting the same fallback
    prediction, and the descending diagonal is the airport flat fare, where the real fare
    is always 52 so the residual is 52 minus the prediction, a perfect line.
    """
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE)

    axes[0].scatter(scored["predicted"], scored["residuals"], s=7, color=GOLD,
                    alpha=0.3, edgecolors="none", zorder=2)
    axes[0].axhline(0, color=GRAPHITE, linewidth=1.4, zorder=3)

    fallback = float(test.loc[~test.route_seen & test.rush_hour.eq(0)
                              & test.airport_flat.eq(0), "predicted"].median())
    results.put("residuals.fallback_prediction", round(fallback, 2),
                "predicción de respaldo para una ruta nueva ($)")
    axes[0].annotate("todas las rutas nuevas\nreciben la misma predicción",
                     xy=(fallback, 30), xytext=(26, 8), textcoords="offset points",
                     fontsize=CAPTION, weight="bold", color=AZURITE,
                     arrowprops=dict(arrowstyle="-", color=AZURITE, linewidth=1.1))
    axes[0].annotate("tarifa plana:\nsiempre 52 $",
                     xy=(56, -4), xytext=(-6, -34), textcoords="offset points",
                     ha="right", fontsize=CAPTION, weight="bold", color=AZURITE,
                     arrowprops=dict(arrowstyle="-", color=AZURITE, linewidth=1.1))
    axes[0].set_title("Residuos contra lo predicho", loc="left", fontsize=PANEL_TITLE,
                      weight="bold", pad=12)
    axes[0].set_xlabel("Tarifa predicha (dólares)")
    axes[0].set_ylabel("Residuo (dólares)")
    axes[0].grid(axis="x", visible=False)

    axes[1].hist(scored["residuals"], bins=60, color=AZURITE, alpha=0.95,
                 edgecolor=SURFACE, linewidth=0.6, zorder=2)
    axes[1].axvline(0, color=GRAPHITE, linewidth=1.4, zorder=3)
    axes[1].set_title("Reparto de los residuos", loc="left", fontsize=PANEL_TITLE,
                      weight="bold", pad=12)
    axes[1].set_xlabel("Residuo (dólares)")
    axes[1].set_ylabel("Número de viajes")
    axes[1].grid(axis="x", visible=False)
    axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    fig.text(0.005, -0.04,
             "Qué mirar: la nube debería estar centrada en el cero y tener el mismo grosor "
             "de izquierda a derecha, y la campana debería ser simétrica. Ni una cosa ni "
             "la otra se cumplen aquí, y las dos anotaciones dicen por qué.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "03_residuos.png")
    plt.close(fig)


def figure_coefficients(model, features: list[str], labels: dict[str, str]) -> None:
    """The mandatory effect figure: every coefficient with its interval and a zero line.

    The intervals here are narrower than the dot that marks the estimate, which is itself
    the result and would be invisible if it were not written out. So each row carries its
    interval in words next to the value.
    """
    style()
    bounds = model.conf_int()
    rows = [(labels.get(name, name), float(model.params[name]),
             float(bounds.loc[name, 0]), float(bounds.loc[name, 1]))
            for name in reversed(features)]

    fig, ax = plt.subplots(figsize=(WIDE[0], 0.52 * len(rows) + 2.0))
    for index, (name, value, low, high) in enumerate(rows):
        crosses_zero = low <= 0 <= high
        colour = AZURITE if crosses_zero else GOLD
        ax.plot([low, high], [index, index], color=colour, linewidth=3.4,
                solid_capstyle="butt", zorder=3)
        ax.plot(value, index, "o", markersize=8, color=colour,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=4)
        text = f"{value:+.2f}   entre {low:+.2f} y {high:+.2f}".replace(".", ",")
        # Anchored to the right edge of the axes rather than to the end of its own bar.
        # Offsetting from the bar let the longest label run off the canvas, and a tight
        # bounding box then widened the whole figure to 3080 px against a library that
        # sits near 2000, which shows this figure's text a third smaller than its
        # neighbours on the page. As a bonus the numbers now line up in a column.
        ax.annotate(text, xy=(0.995, index), xycoords=("axes fraction", "data"),
                    ha="right", va="center", fontsize=CAPTION, weight="bold",
                    color=colour)

    ax.axvline(0, color=GRAPHITE, linewidth=1.4, zorder=2)
    ax.set_yticks(range(len(rows)), [name for name, *_ in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("Efecto sobre la tarifa (dólares)")
    ax.set_title("Cuánto mueve cada variable la tarifa, con su intervalo del 95 %",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.62)

    fig.text(0.005, -0.10,
             "Qué mirar: la línea vertical es el cero, y ninguno de los cuatro intervalos "
             "la toca, así que los cuatro efectos están demostrados.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    # Wrapped by hand: a caption is one long line unless you break it, and a line wider
    # than the canvas silently widens the whole figure, which shows its text smaller than
    # every neighbour on the page. save_figure now warns when that happens.
    fig.text(0.005, -0.19,
             "Los intervalos son tan estrechos que no se ven, y esa es la noticia: con "
             "16.900 viajes el tamaño de cada efecto está muy bien acotado.\nLo que no se "
             "puede hacer es comparar las barras entre sí, porque cada una está en sus "
             "unidades: una milla y un viaje de aeropuerto no son la misma cosa.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "04_coeficientes.png")
    plt.close(fig)


def figure_routes(error: pd.Series, seen: pd.Series, results: Results) -> None:
    """One panel per group, because the two groups are the finding of the project."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE, sharex=True)
    bins = np.arange(0, 26.25, 0.75)   # last edge 25.50, so the clip pile lands inside

    for ax, mask, name, colour in [
        (axes[0], seen, "Ruta ya vista en el entrenamiento", GOLD),
        (axes[1], ~seen, "Ruta nueva para el modelo", AZURITE),
    ]:
        part = error[mask]
        ax.hist(part.clip(upper=25), bins=bins, color=colour, alpha=0.95,
                edgecolor=SURFACE, linewidth=0.7, zorder=2)
        ax.axvline(part.mean(), color=GRAPHITE, linewidth=1.6, zorder=4)
        ax.annotate(f"error medio\n{part.mean():.2f} $".replace(".", ","),
                    xy=(part.mean(), 0.92), xycoords=("data", "axes fraction"),
                    xytext=(8, 0), textcoords="offset points", fontsize=ANNOTATION,
                    weight="bold", color=GRAPHITE, va="top")
        ax.set_title(f"{name}\n{thousands(len(part))} viajes", loc="left",
                     fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.set_xlabel("Error de la predicción (dólares)")
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))
    axes[0].set_ylabel("Número de viajes")

    piled = int(error.ge(bins[-2]).sum())
    results.put("routes.errors_piled", piled,
                f"viajes en la última barra, con error de {bins[-2]} $ o más")
    fig.text(0.005, -0.04,
             "Qué mirar: los dos paneles tienen el mismo eje horizontal. A la izquierda "
             "casi todo cae pegado al cero; a la derecha la cola se estira, y ahí es donde "
             "el modelo se equivoca de verdad.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.11,
             f"La última barra de cada panel amontona los {piled} viajes cuyo error pasa "
             f"de 24,75 $, para que la cola no estire el eje y aplaste todo lo demás.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "05_rutas_nuevas.png")
    plt.close(fig)

    # Interactive twin: the two tails are the finding, and comparing them is a zoom.
    import plotly.graph_objects as go

    plot = go.Figure()
    for mask, name, colour in [(seen, "Ruta ya vista en el entrenamiento", GOLD),
                               (~seen, "Ruta nueva para el modelo", AZURITE)]:
        part = error[mask]
        counts, edges = np.histogram(part.clip(upper=25), bins=bins)
        plot.add_bar(x=(edges[:-1] + edges[1:]) / 2, y=counts,
                     name=f"{name} ({thousands(len(part))})", marker_color=colour,
                     marker_line_color=SURFACE, marker_line_width=1,
                     hovertemplate="error de %{x:.1f} $<br><b>%{y} viajes</b>"
                                   "<extra></extra>")
    plot.update_layout(**interactive_layout(
        "Dónde se equivoca de verdad: la ruta que no ha visto nunca",
        f"Error medio de {results.data['routes']['seen_mae']} $ en las rutas conocidas y "
        f"{results.data['routes']['new_mae']} $ en las nuevas. La última barra amontona "
        f"los {piled} viajes cuyo error pasa de 24,75 $."))
    plot.update_layout(barmode="overlay")
    plot.update_traces(opacity=0.8)
    plot.update_xaxes(title_text="Error de la predicción (dólares)")
    plot.update_yaxes(title_text="Número de viajes")
    save_interactive(plot, FIGURES, "05_rutas_nuevas.html")


# ---------------------------------------------------------------------------- run

def main() -> None:
    results = Results(SLUG, "Automatidata: estimar la tarifa antes del viaje")
    df = add_features(load_and_clean(results))

    banner("2. Separar entrenamiento y prueba antes de tocar nada más")
    train, test = train_test_split(df, test_size=0.25, random_state=SEED)
    results.put("split.train_rows", len(train), "viajes de entrenamiento")
    results.put("split.test_rows", len(test), "viajes de prueba")
    train, test = add_pair_means(train.copy(), test.copy(), results)

    banner("3. Multicolinealidad: por qué no pueden estar todas las variables")
    everything = ["trip_distance", "duration", "mean_distance", "mean_duration",
                  "passenger_count", "rush_hour", "airport_flat"]
    vif = vif_table(train[everything])
    print(vif.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    for _, row in vif.iterrows():
        results.put(f"vif_full.{row.variable}", round(float(row.vif), 2))
    print("\n  La distancia real y la media de la ruta miden lo mismo: VIF de 32 y 29.\n"
          "  Y hay una razón de negocio, más fuerte que la estadística, para separarlas.")

    banner("4. Tres modelos, y solo uno se puede entregar")
    after = ["trip_distance", "duration", "rush_hour", "airport_flat"]
    before = ["mean_distance", "mean_duration", "rush_hour", "airport_flat"]

    # A: everything known once the ride is over.
    model_a = fit(train, after)
    test_a = score(model_a, test, after)

    # B: the exemplar's shortcut, route averages taken over the whole dataset.
    leaky = add_leaky_pair_means(df)
    train_b, test_b = train_test_split(leaky, test_size=0.25, random_state=SEED)
    model_b = fit(train_b, before)
    test_b_score = score(model_b, test_b, before)

    # C: the same model as B, built without looking at the test set.
    model = fit(train, before)
    on_train = score(model, train, before)
    on_test = score(model, test, before)

    for key, label, scored, mdl in [
        ("a_after_the_ride", "A  con la distancia real del viaje ", test_a, model_a),
        ("b_leaky", "B  medias de ruta de todo el dataset", test_b_score, model_b),
        ("c_honest", "C  medias de ruta solo del entrenamiento", on_test, model),
    ]:
        results.put(f"models.{key}.r2_test", round(scored["r2"], 4))
        results.put(f"models.{key}.rmse_test", round(scored["rmse"], 3))
        results.put(f"models.{key}.mae_test", round(scored["mae"], 3))
        results.put(f"models.{key}.r2_adjusted_train", round(float(mdl.rsquared_adj), 4))
        print(f"  {label:<40} R2 {scored['r2']:.4f}   RMSE {scored['rmse']:5.2f} $   "
              f"MAE {scored['mae']:.2f} $")

    inflation = test_b_score["r2"] - on_test["r2"]
    results.put("leakage.r2_inflation", round(inflation, 4),
                "\n  cuánto infla el R2 la fuga de información")
    results.put("leakage.rmse_hidden", round(on_test["rmse"] - test_b_score["rmse"], 3),
                "  dólares de error que esconde")

    banner("5. El modelo que se entrega: solo lo que se sabe al reservar")
    results.put("model.features", before)
    results.put("model.excluded_by_design", ["trip_distance", "duration"],
                "fuera por diseño: no existen antes del viaje")
    results.put("model.dropped", ["passenger_count"], "fuera por no aportar")

    vif_final = vif_table(train[before])
    for _, row in vif_final.iterrows():
        results.put(f"vif_final.{row.variable}", round(float(row.vif), 2))
    print(vif_final.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print()
    bounds = model.conf_int()
    for name in ["const"] + before:
        results.put(f"coefficients.{name}.value", round(float(model.params[name]), 4))
        results.put(f"coefficients.{name}.p", float(f"{model.pvalues[name]:.3g}"))
        results.put(f"coefficients.{name}.ci_low", round(float(bounds.loc[name, 0]), 4))
        results.put(f"coefficients.{name}.ci_high", round(float(bounds.loc[name, 1]), 4))
        print(f"  {name:<16} {model.params[name]:+9.4f}   "
              f"IC95 [{bounds.loc[name, 0]:+.3f}, {bounds.loc[name, 1]:+.3f}]   "
              f"p = {model.pvalues[name]:.3g}")

    results.put("fit.r2_train", round(float(model.rsquared), 4), "R2 en entrenamiento")
    results.put("fit.r2_adjusted", round(float(model.rsquared_adj), 4), "R2 ajustado")
    results.put("fit.r2_test", round(on_test["r2"], 4), "R2 en prueba")
    results.put("fit.rmse_train", round(on_train["rmse"], 3), "RMSE en entrenamiento ($)")
    results.put("fit.rmse_test", round(on_test["rmse"], 3), "RMSE en prueba ($)")
    results.put("fit.mae_test", round(on_test["mae"], 3), "MAE en prueba ($)")

    banner("6. Dónde falla: la ruta nueva")
    test["predicted"] = on_test["predicted"]
    error = on_test["residuals"].abs()
    seen = test["route_seen"]
    results.put("routes.seen_trips", int(seen.sum()), "viajes por una ruta conocida")
    results.put("routes.seen_mae", round(float(error[seen].mean()), 2), "  su error medio ($)")
    results.put("routes.new_trips", int((~seen).sum()), "viajes por una ruta nueva")
    results.put("routes.new_mae", round(float(error[~seen].mean()), 2), "  su error medio ($)")
    results.put("routes.ratio", round(float(error[~seen].mean() / error[seen].mean()), 1),
                "  cuántas veces peor")

    banner("7. Los cuatro supuestos")
    residuals = on_test["residuals"]
    results.put("assumptions.residual_mean", round(float(residuals.mean()), 4),
                "media de los residuos")
    results.put("assumptions.residual_skew", round(float(stats.skew(residuals)), 3),
                "asimetría de los residuos")
    results.put("assumptions.residual_kurtosis",
                round(float(stats.kurtosis(residuals)), 3), "curtosis de los residuos")
    inside = float((residuals.abs() <= 2).mean() * 100)
    results.put("assumptions.within_2_dollars", round(inside, 1),
                "% de viajes con error menor de 2 dólares")

    # Breusch-Pagan for constant variance: regress squared residuals on the predictions.
    helper = sm.OLS(residuals ** 2, sm.add_constant(on_test["predicted"])).fit()
    results.put("assumptions.bp_r2", round(float(helper.rsquared), 4),
                "R2 de los residuos al cuadrado contra lo predicho")
    results.put("assumptions.bp_p", float(f"{helper.f_pvalue:.3g}"),
                "  su valor p (bajo = varianza no constante)")

    banner("8. Figuras")
    figure_fares(df, results)
    figure_distance(df)
    figure_residuals(test, on_test, results)
    figure_coefficients(model, before, {
        "mean_distance": "Distancia media de la ruta (milla)",
        "mean_duration": "Duración media de la ruta (minuto)",
        "rush_hour": "Hora punta",
        "airport_flat": "Tarifa plana de aeropuerto",
    })
    figure_routes(error, seen, results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
