"""Waze, Course 4: predict whether a user will abandon the app.

A binomial logistic regression on `label`, churned against retained. Waze wants to know
who is about to leave so it can act before they do.

Run it:
    python projects/curso4/waze/02_scripts/waze_logistic.py

Reads Kevin's CSV read-only, writes figures to 03_figures/ and every publishable number to
04_reports/model_results.json.

The expectation, stated before the model is fitted so it cannot be adjusted afterwards:
this is likely to end up with poor recall. Only 17.7 % of the users churn, the variables
are behavioural rather than causal, and nothing in the dataset records why anyone left.
A model that misses most of the churners is a result and gets reported as one, the same
way Course 3 reported that Waze showed no difference between devices.

Three things the data forces before any modelling:

  - 700 users have no label at all, 4.7 % of the file. Whether they can be dropped
    depends on whether they resemble everyone else, which is checked and not assumed.
  - 983 users drove on zero days, so kilometres per driving day divides by zero.
  - sessions and drives correlate at 0.997, and activity_days with driving_days at 0.948.
    Those pairs cannot both be in the model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import (confusion_matrix, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split
from statsmodels.stats.outliers_influence import variance_inflation_factor

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # projects/, for common.py
from common import (  # noqa: E402
    ANNOTATION, CAPTION, PANEL_TITLE, SQUARE, TALL, TITLE, WIDE, save_figure,
    AZURITE, GOLD, GRAPHITE, HAIRLINE, MUTED, SURFACE, Results, banner, dataset,
    correlation_map, figures_dir, interactive_layout, readable_on,
    save_interactive, style, thousands,
)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_hex  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "waze"
FIGURES = figures_dir("curso4", SLUG)
SEED = 42


def load_and_check_missing(results: Results) -> pd.DataFrame:
    """Load, and decide what to do with the 700 unlabelled users by looking at them."""
    banner("1. Los datos, y las 700 etiquetas que faltan")
    df = pd.read_csv(dataset(SLUG))
    results.put("data.rows_raw", len(df), "filas en el CSV")
    results.put("data.duplicates", int(df.duplicated().sum()), "filas duplicadas")

    missing = df.label.isna()
    results.put("missing.rows", int(missing.sum()), "usuarios sin etiqueta")
    results.put("missing.pct", round(100 * missing.mean(), 1), "  en porcentaje")

    # Dropping them is only safe if they look like everybody else. Comparing medians,
    # which do not move with the extreme values this dataset is full of.
    columns = ["sessions", "drives", "driven_km_drives", "activity_days", "driving_days",
               "n_days_after_onboarding"]
    worst = 0.0
    for column in columns:
        with_label = float(df.loc[~missing, column].median())
        without = float(df.loc[missing, column].median())
        gap = 100 * (without - with_label) / with_label if with_label else 0.0
        worst = max(worst, abs(gap))
        results.put(f"missing.median_gap.{column}", round(gap, 1))
    results.put("missing.worst_gap_pct", round(worst, 1),
                "mayor diferencia de medianas entre los dos grupos (%)")

    share_missing = df.loc[missing, "device"].value_counts(normalize=True)
    share_rest = df.loc[~missing, "device"].value_counts(normalize=True)
    results.put("missing.iphone_share_missing", round(100 * share_missing["iPhone"], 1),
                "% de iPhone entre los que no tienen etiqueta")
    results.put("missing.iphone_share_rest", round(100 * share_rest["iPhone"], 1),
                "% de iPhone entre el resto")

    df = df.dropna(subset=["label"]).copy()
    results.put("data.rows_labelled", len(df), "usuarios con etiqueta")
    churn = df.label.eq("churned")
    results.put("balance.churned", int(churn.sum()), "usuarios que abandonan")
    results.put("balance.churn_rate", round(100 * churn.mean(), 2), "tasa de abandono (%)")
    return df


def add_features(df: pd.DataFrame, results: Results) -> pd.DataFrame:
    banner("2. Variables construidas, y la división por cero que esconden")
    df = df.copy()
    df["churned"] = df.label.eq("churned").astype(int)
    df["iphone"] = df.device.eq("iPhone").astype(int)

    zero_days = int(df.driving_days.eq(0).sum())
    results.put("features.zero_driving_days", zero_days,
                "usuarios que condujeron cero días")
    # Dividing by zero gives inf, which propagates silently into the model as a value the
    # optimiser cannot handle. Those users drove nothing, so their rate is zero.
    df["km_per_driving_day"] = np.where(df.driving_days.gt(0),
                                        df.driven_km_drives / df.driving_days.replace(0, 1),
                                        0.0)
    results.put("features.km_per_day_median",
                round(float(df.km_per_driving_day.median()), 1),
                "kilómetros por día conducido, mediana")

    # Waze's own definition in the course material: a lot of drives on few days.
    df["professional_driver"] = ((df.drives >= 60) & (df.driving_days >= 15)).astype(int)
    results.put("features.professional_drivers", int(df.professional_driver.sum()),
                "usuarios marcados como conductores profesionales")
    results.put("features.professional_churn",
                round(100 * float(df.loc[df.professional_driver.eq(1), "churned"].mean()), 2),
                "  su tasa de abandono (%)")
    results.put("features.other_churn",
                round(100 * float(df.loc[df.professional_driver.eq(0), "churned"].mean()), 2),
                "  tasa del resto (%)")
    return df


def vif_table(frame: pd.DataFrame) -> pd.DataFrame:
    matrix = sm.add_constant(frame).values
    rows = [(name, variance_inflation_factor(matrix, i + 1))
            for i, name in enumerate(frame.columns)]
    return pd.DataFrame(rows, columns=["variable", "vif"]).sort_values("vif",
                                                                        ascending=False)


def metrics(truth, predicted, probability, results: Results, prefix: str) -> dict:
    matrix = confusion_matrix(truth, predicted)
    (tn, fp), (fn, tp) = matrix
    scores = {
        "accuracy": (tp + tn) / matrix.sum(),
        "precision": precision_score(truth, predicted, zero_division=0),
        "recall": recall_score(truth, predicted, zero_division=0),
        "auc": roc_auc_score(truth, probability),
    }
    scores["f1"] = (2 * scores["precision"] * scores["recall"]
                    / (scores["precision"] + scores["recall"])
                    if scores["precision"] + scores["recall"] else 0.0)
    for name in ["accuracy", "precision", "recall", "f1", "auc"]:
        results.put(f"{prefix}.{name}", round(scores[name], 4))
    for name, value in [("tn", tn), ("fp", fp), ("fn", fn), ("tp", tp)]:
        results.put(f"{prefix}.matrix.{name}", int(value))
    print(f"  exactitud {scores['accuracy']:.3f}   precisión {scores['precision']:.3f}   "
          f"sensibilidad {scores['recall']:.3f}   F1 {scores['f1']:.3f}   "
          f"AUC {scores['auc']:.3f}")
    scores["matrix"] = matrix
    return scores


# ------------------------------------------------------------------------ figures

def figure_missing(raw: pd.DataFrame, results: Results) -> None:
    """Whether the 700 unlabelled users can be dropped, drawn instead of asserted."""
    style()
    missing = raw.label.isna()
    columns = ["sessions", "drives", "driven_km_drives", "activity_days", "driving_days"]
    labels = ["Sesiones", "Trayectos", "Kilómetros", "Días activo", "Días conduciendo"]
    gaps = [100 * (raw.loc[missing, c].median() - raw.loc[~missing, c].median())
            / raw.loc[~missing, c].median() for c in columns]

    fig, ax = plt.subplots(figsize=WIDE)
    colours = [AZURITE if abs(g) > 20 else GOLD for g in gaps]
    bars = ax.barh(labels[::-1], gaps[::-1], color=colours[::-1], height=0.58,
                   edgecolor=SURFACE, linewidth=1.1, zorder=2)
    for bar, gap in zip(bars, gaps[::-1]):
        offset = 6 if gap >= 0 else -6
        ax.annotate(f"{gap:+.1f} %".replace(".", ","),
                    xy=(gap, bar.get_y() + bar.get_height() / 2), xytext=(offset, 0),
                    textcoords="offset points", va="center",
                    ha="left" if gap >= 0 else "right",
                    fontsize=ANNOTATION, weight="bold", color=GRAPHITE)
    ax.axvline(0, color=GRAPHITE, linewidth=1.4, zorder=3)
    ax.set_xlim(-25, 25)
    ax.set_xlabel("Diferencia de la mediana respecto de los usuarios con etiqueta")
    ax.set_title("Los 700 usuarios sin etiqueta se parecen a todos los demás", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"{v:+.0f} %" if v else "0"))

    # Only the decimals get a comma: replacing every dot also ate the full stops.
    iphone_missing = f"{results.data['missing']['iphone_share_missing']}".replace(".", ",")
    iphone_rest = f"{results.data['missing']['iphone_share_rest']}".replace(".", ",")
    fig.text(0.005, -0.10,
             f"Qué mirar: ninguna barra llega al 20 %, y el reparto de dispositivo es casi "
             f"idéntico ({iphone_missing} % de iPhone frente a {iphone_rest} %). "
             f"Por eso se pueden excluir sin sesgar el análisis.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.19,
             "Si alguna barra se hubiera disparado, excluirlos habría cambiado a quién "
             "describe el modelo, y habría habido que decirlo o imputarlos.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_ausentes.png")
    plt.close(fig)


def figure_activity(df: pd.DataFrame) -> None:
    """One panel per group: the variable that turns out to matter."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE, sharex=True, sharey=True)
    bins = np.arange(0, 32, 1)

    for ax, (name, mask, colour) in zip(axes, [
        ("Se quedan", df.churned.eq(0), GOLD),
        ("Abandonan", df.churned.eq(1), AZURITE),
    ]):
        part = df.loc[mask, "activity_days"]
        ax.hist(part, bins=bins, color=colour, alpha=0.95, edgecolor=SURFACE,
                linewidth=0.7, zorder=2)
        ax.axvline(part.median(), color=GRAPHITE, linewidth=1.6, zorder=4)
        ax.annotate(f"mediana\n{part.median():.0f} días",
                    xy=(part.median(), 0.93), xycoords=("data", "axes fraction"),
                    xytext=(8, 0), textcoords="offset points", va="top",
                    fontsize=ANNOTATION, weight="bold", color=GRAPHITE)
        ax.set_title(f"{name}\n{thousands(int(mask.sum()))} usuarios", loc="left",
                     fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.set_xlabel("Días con actividad en el último mes")
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))
    axes[0].set_ylabel("Usuarios")

    fig.text(0.005, -0.04,
             "Qué mirar: los dos paneles comparten los dos ejes. Quien abandona se "
             "amontona en la izquierda, con pocos días de uso; quien se queda se reparte "
             "por todo el mes.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "02_actividad.png")
    plt.close(fig)


def figure_vif(before: pd.DataFrame, after: pd.DataFrame) -> None:
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE)
    for ax, table, title in [
        (axes[0], before, "Con las variables correlacionadas"),
        (axes[1], after, "Modelo final"),
    ]:
        colours = [AZURITE if v >= 10 else GOLD for v in table.vif]
        bars = ax.barh(table.variable[::-1], table.vif[::-1], color=colours[::-1],
                       height=0.6, edgecolor=SURFACE, linewidth=1.0, zorder=2)
        for bar, value in zip(bars, table.vif[::-1]):
            ax.annotate(f"{value:.1f}".replace(".", ","),
                        xy=(value, bar.get_y() + bar.get_height() / 2), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=CAPTION,
                        weight="bold", color=GRAPHITE)
        ax.axvline(10, color=GRAPHITE, linewidth=1.3, linestyle=(0, (4, 3)), zorder=3)
        ax.set_title(title, loc="left", fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.set_xlabel("Factor de inflación de la varianza")
        ax.grid(axis="y", visible=False)
        ax.margins(x=0.24)

    fig.text(0.005, -0.05,
             "Qué mirar: a la izquierda, en azul, las que pasan de 10. Sesiones y "
             "trayectos correlacionan a 0,997 y días activo con días conduciendo a 0,948: "
             "son la misma información contada dos veces.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "03_multicolinealidad.png")
    plt.close(fig)


def figure_correlations(df: pd.DataFrame, columns: list[str], results: Results) -> None:
    """Eleven variables, and far fewer separate things than eleven.

    The VIF figure next door says which variables had to go. This one says why, and it is
    the shape of the file rather than a property of the model: three pairs that measure
    the same behaviour twice, and a majority of pairs that have nothing to do with each
    other. Reading it is what makes dropping three variables a decision instead of a rule.
    """
    import seaborn as sns

    style()
    labels = {
        "sessions": "Sesiones", "drives": "Trayectos", "total_sessions": "Sesiones totales",
        "n_days_after_onboarding": "Días desde el alta", "driven_km_drives": "Km recorridos",
        "duration_minutes_drives": "Minutos al volante", "activity_days": "Días activo",
        "driving_days": "Días conduciendo", "km_per_driving_day": "Km por día conducido",
        "professional_driver": "Conductor profesional", "iphone": "iPhone",
    }
    matrix = df[columns].corr().rename(index=labels, columns=labels)

    pairs = matrix.values[np.triu_indices_from(matrix.values, 1)]
    results.put("correlations.pairs", int(pairs.size), "pares de variables")
    results.put("correlations.above_80", int((np.abs(pairs) > 0.8).sum()),
                "  pares que pasan de 0,80: la misma información dos veces")
    results.put("correlations.below_10", int((np.abs(pairs) < 0.1).sum()),
                "  pares que no llegan a 0,10: no se parecen en nada")
    results.put("correlations.strongest", round(float(pairs.max()), 4), "  el par más alto")

    fig, ax = plt.subplots(figsize=SQUARE)
    palette = correlation_map()
    matrix = matrix.iloc[1:, :-1]                # the row and column the mask empties
    upper = np.triu(np.ones(matrix.shape, dtype=bool), 1)
    sns.heatmap(matrix, mask=upper, cmap=palette, vmin=-1, vmax=1, center=0,
                linewidths=1.0, linecolor=SURFACE, ax=ax,
                cbar_kws={"shrink": 0.45, "label": "Correlación", "ticks": [-1, 0, 1]},
                annot=True, fmt=".2f", annot_kws={"fontsize": CAPTION, "weight": "bold"})

    for text in ax.texts:
        text.set_text(text.get_text().replace(".", ","))
        column, row = (int(coordinate) for coordinate in text.get_position())
        text.set_color(readable_on(to_hex(palette((matrix.iloc[row, column] + 1) / 2))))

    ax.set_title("Once variables, y muchas menos cosas distintas que once", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.tick_params(labelrotation=0, labelsize=CAPTION)
    plt.setp(ax.get_xticklabels(), rotation=32, ha="right")
    ax.grid(visible=False)

    counts = results.data["correlations"]
    strongest = f"{counts['strongest']:.4f}".replace(".", ",")
    fig.text(0.005, -0.02,
             f"Qué mirar: de los {counts['pairs']} pares, {counts['below_10']} no llegan a "
             f"0,10 y se quedan del color del fondo. Los que se ven son pocos, y dos de "
             f"ellos pasan de 0,80: ahí hay una variable de sobra.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.06,
             f"Son sesiones con trayectos, que valen {strongest} y el dibujo redondea a "
             f"1,00, y días activo con días conduciendo. Dos formas de contar la misma "
             f"conducta, y el modelo se queda con una de cada par.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "03b_correlaciones.png")
    plt.close(fig)


def figure_odds(model, labels: dict[str, tuple[str, float]]) -> None:
    """Odds ratios rescaled to units a person can picture.

    Per one unit, most of these read 1.000 with an interval of 1.000 to 1.000, which says
    nothing even where the p value is 3e-48. The variable is not weak, the unit is: one
    day out of two thousand since signing up, one minute out of an hour of driving. So
    each coefficient is scaled to a unit that means something, which is the same rule the
    lessons give for reporting a coefficient with its units.
    """
    style()
    bounds = model.conf_int()
    rows = []
    for name in reversed([n for n in model.params.index if n != "const"]):
        label, scale = labels[name]
        rows.append((label,
                     float(np.exp(model.params[name] * scale)),
                     float(np.exp(bounds.loc[name, 0] * scale)),
                     float(np.exp(bounds.loc[name, 1] * scale))))

    fig, ax = plt.subplots(figsize=(WIDE[0], 0.52 * len(rows) + 2.2))
    for index, (name, value, low, high) in enumerate(rows):
        colour = AZURITE if low <= 1 <= high else GOLD
        ax.plot([low, high], [index, index], color=colour, linewidth=3.4,
                solid_capstyle="butt", zorder=3)
        ax.plot(value, index, "o", markersize=8, color=colour,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=4)
        ax.annotate(f"{value:.3f}   entre {low:.3f} y {high:.3f}".replace(".", ","),
                    xy=(high, index), xytext=(12, 0), textcoords="offset points",
                    va="center", fontsize=CAPTION, weight="bold", color=colour)

    ax.axvline(1, color=GRAPHITE, linewidth=1.4, zorder=2)
    ax.set_yticks(range(len(rows)), [name for name, *_ in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("Razón de momios de abandonar")
    ax.set_title("Cuánto multiplica cada variable los momios de abandonar la aplicación",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.34)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"{v:g}".replace(".", ",")))

    fig.text(0.005, -0.10,
             "Qué mirar: la línea de no efecto es el 1. Por debajo, la variable protege "
             "contra el abandono; por encima, lo empuja.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.18,
             "Cada fila está escalada a una unidad que se pueda imaginar, no a una unidad "
             "suelta. Por trayecto o por minuto, todas estas razones saldrían 1,000 y no "
             "dirían nada, aunque el efecto sea real.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "04_momios.png")
    plt.close(fig)


def figure_threshold(truth, probability, results: Results) -> None:
    """What the model can and cannot buy by moving the cut."""
    style()
    cuts = np.arange(0.05, 0.65, 0.01)
    recalls, precisions = [], []
    for cut in cuts:
        predicted = (probability >= cut).astype(int)
        recalls.append(recall_score(truth, predicted, zero_division=0))
        precisions.append(precision_score(truth, predicted, zero_division=0))

    fig, ax = plt.subplots(figsize=WIDE)
    ax.plot(cuts, recalls, color=AZURITE, linewidth=2.4, zorder=3,
            label="Sensibilidad: cuántos de los que se van detecta")
    ax.plot(cuts, precisions, color=GOLD, linewidth=2.4, zorder=3,
            label="Precisión: cuántas de sus alarmas son ciertas")
    ax.axvline(0.5, color=GRAPHITE, linewidth=1.3, linestyle=(0, (4, 3)), zorder=2)
    ax.annotate("umbral por defecto", xy=(0.5, 0.94), xycoords=("data", "axes fraction"),
                xytext=(-8, 0), textcoords="offset points", ha="right", fontsize=CAPTION,
                weight="bold", color=GRAPHITE)

    base = float(np.mean(truth))
    ax.axhline(base, color=MUTED, linewidth=1.2, linestyle=(0, (2, 3)), zorder=2)
    ax.annotate(f"tasa de abandono real: {100 * base:.1f} %".replace(".", ","),
                xy=(0.63, base), xytext=(0, 8), textcoords="offset points",
                ha="right", fontsize=CAPTION, color=MUTED)

    ax.set_xlabel("Umbral de clasificación")
    ax.set_ylabel("Proporción")
    ax.set_ylim(0, 1)
    ax.set_title("Lo que se compra y lo que se paga al mover el umbral", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    # Lower left: the only corner both curves leave empty, and the default-threshold
    # label needs the top right.
    ax.legend(loc="lower left", frameon=False, fontsize=ANNOTATION)
    ax.grid(axis="x", visible=False)
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(plt.FuncFormatter(
            lambda v, _: f"{v:.1f}".replace(".", ",")))

    reachable = max(r for r, c in zip(recalls, cuts) if c >= 0.2)
    results.put("threshold.recall_at_020", round(float(reachable), 4),
                "sensibilidad máxima bajando el umbral a 0,20")
    fig.text(0.005, -0.05,
             "Qué mirar: bajando el umbral se detecta a más gente que se va, y cada punto "
             "ganado se paga con alarmas falsas. Las dos curvas nunca están altas a la vez.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "05_umbral.png")
    plt.close(fig)

    # Interactive twin: the whole point of this figure is reading what a given cut buys
    # and costs, and a still image makes you estimate it off two curves.
    import plotly.graph_objects as go

    plot = go.Figure()
    for values, colour, name in [(recalls, AZURITE, "Sensibilidad: a cuántos de los que se van detecta"),
                                 (precisions, GOLD, "Precisión: cuántas de sus alarmas son ciertas")]:
        plot.add_scatter(x=cuts, y=values, mode="lines", name=name,
                         line={"color": colour, "width": 3},
                         hovertemplate="umbral %{x:.2f}<br><b>%{y:.1%}</b><extra></extra>")
    plot.add_vline(x=0.5, line_color=GRAPHITE, line_dash="dash")
    plot.update_layout(**interactive_layout(
        "Lo que se compra y lo que se paga al mover el umbral",
        "La línea de puntos es el umbral por defecto. Pasa el ratón por las dos curvas a "
        "la vez para leer qué detecta y qué acierta cada corte."))
    plot.update_layout(hovermode="x unified")
    plot.update_xaxes(title_text="Umbral de clasificación")
    plot.update_yaxes(title_text="Proporción", tickformat=".0%", range=[0, 1])
    save_interactive(plot, FIGURES, "05_umbral.html")


def figure_roc(truth, probability, auc: float) -> None:
    style()
    false_rate, true_rate, _ = roc_curve(truth, probability)
    fig, ax = plt.subplots(figsize=TALL)
    ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1.3, linestyle=(0, (4, 3)), zorder=2)
    ax.plot(false_rate, true_rate, color=AZURITE, linewidth=2.6, zorder=3)
    ax.fill_between(false_rate, true_rate, color=AZURITE, alpha=0.12, zorder=1)
    ax.annotate(f"AUC = {auc:.3f}".replace(".", ","), xy=(0.55, 0.30),
                fontsize=TITLE, weight="bold", color=AZURITE)
    ax.annotate("una moneda", xy=(0.62, 0.58), rotation=33, fontsize=CAPTION, color=MUTED)
    ax.set_xlabel("Falsas alarmas, sobre los que se quedan")
    ax.set_ylabel("Aciertos, sobre los que se van")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("El modelo separa algo, pero poco", loc="left", fontsize=TITLE,
                 weight="bold", pad=16)
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(plt.FuncFormatter(
            lambda v, _: f"{v:.1f}".replace(".", ",")))

    fig.text(0.005, -0.06,
             "Qué mirar: la diagonal es lo que conseguiría tirar una moneda. Cuanto más se "
             "despega la curva de ella, mejor ordena el modelo a los usuarios por riesgo.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "06_roc.png")
    plt.close(fig)


# ---------------------------------------------------------------------------- run

def main() -> None:
    results = Results(SLUG, "Waze: predecir qué usuario abandona la aplicación")
    raw = pd.read_csv(dataset(SLUG))
    df = add_features(load_and_check_missing(results), results)

    banner("3. Multicolinealidad")
    everything = ["sessions", "drives", "total_sessions", "n_days_after_onboarding",
                  "driven_km_drives", "duration_minutes_drives", "activity_days",
                  "driving_days", "km_per_driving_day", "professional_driver", "iphone"]
    before = vif_table(df[everything])
    print(before.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    for _, row in before.iterrows():
        results.put(f"vif_full.{row.variable}", round(float(row.vif), 2))

    features = ["drives", "total_sessions", "n_days_after_onboarding",
                "duration_minutes_drives", "activity_days", "km_per_driving_day",
                "professional_driver", "iphone"]
    after = vif_table(df[features])
    print("\nModelo final:")
    print(after.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    for _, row in after.iterrows():
        results.put(f"vif_final.{row.variable}", round(float(row.vif), 2))
    results.put("model.features", features)
    results.put("model.dropped", ["sessions", "driving_days", "driven_km_drives"],
                "descartadas por decir lo mismo que otra")

    banner("4. Ajustar la logística")
    train, test = train_test_split(df, test_size=0.25, random_state=SEED,
                                   stratify=df.churned)
    results.put("split.train_rows", len(train), "filas de entrenamiento")
    results.put("split.test_rows", len(test), "filas de prueba")

    model = sm.Logit(train.churned, sm.add_constant(train[features])).fit(disp=False)
    bounds = model.conf_int()
    print()
    for name in ["const"] + features:
        ratio = float(np.exp(model.params[name]))
        results.put(f"coefficients.{name}.value", round(float(model.params[name]), 5))
        results.put(f"coefficients.{name}.odds_ratio", round(ratio, 5))
        results.put(f"coefficients.{name}.p", float(f"{model.pvalues[name]:.3g}"))
        results.put(f"coefficients.{name}.ci_low",
                    round(float(np.exp(bounds.loc[name, 0])), 5))
        results.put(f"coefficients.{name}.ci_high",
                    round(float(np.exp(bounds.loc[name, 1])), 5))
        print(f"  {name:<26} momios ×{ratio:8.4f}   p = {model.pvalues[name]:.3g}")
    results.put("fit.pseudo_r2", round(float(model.prsquared), 4), "\n  pseudo R2")

    banner("5. Qué tal clasifica, y aquí está el resultado incómodo")
    probability = model.predict(sm.add_constant(test[features]))
    scores = metrics(test.churned, (probability >= 0.5).astype(int), probability,
                     results, "metrics_050")
    results.put("metrics_050.churners_missed",
                int(scores["matrix"][1][0]), "usuarios que se van y no detecta")
    results.put("metrics_050.churners_total",
                int(scores["matrix"][1].sum()), "  de un total de")

    print("\n  bajando el umbral a 0,20:")
    metrics(test.churned, (probability >= 0.20).astype(int), probability,
            results, "metrics_020")

    banner("6. Figuras")
    figure_missing(raw, results)
    figure_activity(df)
    figure_vif(before, after)
    figure_correlations(df, everything, results)
    # Label and the unit each coefficient is scaled to, so the ratios can be read.
    units = {
        "drives": ("Cada 10 trayectos más", 10),
        "total_sessions": ("Cada 10 sesiones históricas más", 10),
        "n_days_after_onboarding": ("Cada año más de antigüedad", 365),
        "duration_minutes_drives": ("Cada hora más al volante", 60),
        "activity_days": ("Cada día de actividad más", 1),
        "km_per_driving_day": ("Cada 100 km por día conducido", 100),
        "professional_driver": ("Ser conductor profesional", 1),
        "iphone": ("Usar iPhone", 1),
    }
    for name, (label, scale) in units.items():
        ratio = float(np.exp(model.params[name] * scale))
        results.put(f"scaled_odds.{name}.unit", label)
        results.put(f"scaled_odds.{name}.odds_ratio", round(ratio, 4))
    figure_odds(model, units)
    figure_threshold(test.churned, probability, results)
    figure_roc(test.churned, probability, scores["auc"])
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
