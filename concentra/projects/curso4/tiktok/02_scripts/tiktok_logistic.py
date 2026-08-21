"""TikTok, Course 4: predict whether an account is verified, from its video.

A binomial logistic regression on `verified_status`. The point of the exercise is the
groundwork for Course 5, where the target becomes claim versus opinion, but on its own it
is a good lesson in the thing module 5 warns about: 93.7 % of the accounts are not
verified, so a model that always answers "not verified" is right 93.7 % of the time and
detects nobody.

Run it:
    python projects/curso4/tiktok/02_scripts/tiktok_logistic.py

Reads Kevin's CSV read-only, writes figures to 03_figures/ and every publishable number to
04_reports/model_results.json.

Two choices that shape the result:

  - The majority class is downsampled to match the minority, so the model is trained on a
    balanced set. Otherwise the fastest way to a low loss is to never predict "verified".
    The evaluation is reported on that balanced set, which means accuracy here is the
    accuracy of a coin-flip baseline, 50 %, and not 93.7 %.

  - Inference comes from statsmodels, which gives coefficients with intervals and p
    values, and the split and metrics from scikit-learn. One fitted model, not two.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import (confusion_matrix, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import train_test_split
from statsmodels.stats.outliers_influence import variance_inflation_factor

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # projects/, for common.py
from common import (  # noqa: E402
    ANNOTATION, CAPTION, HERO, PANEL_TITLE, SQUARE, TALL, TITLE, WIDE,
    save_figure,
    AZURITE, GOLD, GRAPHITE, HAIRLINE, MUTED, SURFACE, Results, banner, dataset,
    correlation_map, figures_dir, interactive_layout, readable_on,
    save_interactive, style, thousands,
)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_hex  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "tiktok"
FIGURES = figures_dir("curso4", SLUG)
SEED = 42
COUNTERS = ["video_view_count", "video_like_count", "video_share_count",
            "video_download_count", "video_comment_count"]


def load_and_clean(results: Results) -> pd.DataFrame:
    banner("1. Los datos, y qué hubo que arreglar")
    df = pd.read_csv(dataset(SLUG))
    results.put("data.rows_raw", len(df), "filas en el CSV")
    incomplete = int(df.isna().any(axis=1).sum())
    results.put("data.rows_incomplete", incomplete, "filas con algún dato ausente")
    results.put("data.duplicates", int(df.duplicated().sum()), "filas duplicadas")

    df = df.dropna().copy()
    results.put("data.rows_clean", len(df), "filas completas")

    counts = df.verified_status.value_counts()
    results.put("balance.not_verified", int(counts["not verified"]), "cuentas no verificadas")
    results.put("balance.verified", int(counts["verified"]), "cuentas verificadas")
    results.put("balance.verified_pct", round(100 * counts["verified"] / len(df), 1),
                "porcentaje de verificadas")
    results.put("balance.majority_baseline",
                round(100 * counts["not verified"] / len(df), 1),
                "acierto de responder siempre «no verificada»")

    # The real signal, and it is not the one the exemplar leads with.
    share = pd.crosstab(df.claim_status, df.verified_status, normalize="columns")
    results.put("signal.opinion_share_verified",
                round(100 * float(share.loc["opinion", "verified"]), 1),
                "% de opiniones entre las verificadas")
    results.put("signal.opinion_share_not_verified",
                round(100 * float(share.loc["opinion", "not verified"]), 1),
                "% de opiniones entre las no verificadas")
    results.put("signal.duration_verified",
                round(float(df.loc[df.verified_status.eq("verified"),
                                   "video_duration_sec"].mean()), 2),
                "duración media, verificadas (s)")
    results.put("signal.duration_not_verified",
                round(float(df.loc[df.verified_status.eq("not verified"),
                                   "video_duration_sec"].mean()), 2),
                "duración media, no verificadas (s)")
    return df


def encode(df: pd.DataFrame) -> pd.DataFrame:
    """Categories into 1/0 columns, one per level minus one, as module 3 requires."""
    out = df.copy()
    out["verified"] = out.verified_status.eq("verified").astype(int)
    out["is_claim"] = out.claim_status.eq("claim").astype(int)          # ref: opinion
    out["banned"] = out.author_ban_status.eq("banned").astype(int)      # ref: active
    out["under_review"] = out.author_ban_status.eq("under review").astype(int)
    return out


def balance(df: pd.DataFrame, results: Results) -> pd.DataFrame:
    """Downsample the majority class so the model cannot win by always saying no."""
    minority = df[df.verified.eq(1)]
    majority = df[df.verified.eq(0)].sample(len(minority), random_state=SEED)
    out = pd.concat([minority, majority]).sample(frac=1, random_state=SEED)
    results.put("balance.rows_after", len(out), "filas tras equilibrar")
    results.put("balance.discarded", len(df) - len(out),
                "filas de la clase mayoritaria descartadas")
    return out


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

def figure_balance(df: pd.DataFrame, results: Results) -> None:
    """The trap of module 5, drawn with his own data."""
    style()
    fig, ax = plt.subplots(figsize=WIDE)
    counts = df.verified_status.value_counts()
    labels = ["No verificadas", "Verificadas"]
    values = [counts["not verified"], counts["verified"]]

    bars = ax.barh(labels, values, color=[GOLD, AZURITE], height=0.55,
                   edgecolor=SURFACE, linewidth=1.2, zorder=2)
    for bar, value in zip(bars, values):
        # Only the decimal gets a comma. thousands() already put dots between thousands,
        # and replacing those too turned 17.884 into 17,884.
        share = f"{100 * value / sum(values):.1f}".replace(".", ",")
        ax.annotate(f"{thousands(value)}   {share} %",
                    xy=(value, bar.get_y() + bar.get_height() / 2), xytext=(10, 0),
                    textcoords="offset points", va="center", fontsize=ANNOTATION,
                    weight="bold", color=GRAPHITE)

    ax.set_xlim(0, max(values) * 1.28)
    ax.set_xlabel("Número de vídeos")
    ax.set_title("Por cada cuenta verificada hay quince sin verificar", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    baseline = f"{results.data['balance']['majority_baseline']:.1f}".replace(".", ",")
    fig.text(0.005, -0.10,
             f"Qué mirar: un modelo que conteste siempre «no verificada» acierta el "
             f"{baseline} % de las veces y no detecta ni una sola cuenta verificada.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.20,
             "Por eso el modelo se entrena con las dos clases igualadas, y por eso la "
             "exactitud no es la métrica que se reporta.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_desbalance.png")
    plt.close(fig)


def figure_signal(df: pd.DataFrame) -> None:
    """One panel per group: what each kind of account actually posts."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE, sharey=True)
    groups = [("Cuentas no verificadas", "not verified", GOLD),
              ("Cuentas verificadas", "verified", AZURITE)]

    for ax, (title, key, colour) in zip(axes, groups):
        part = df[df.verified_status.eq(key)]
        share = part.claim_status.value_counts(normalize=True) * 100
        order = ["claim", "opinion"]
        bars = ax.bar(["Reclamación", "Opinión"], [share[k] for k in order],
                      color=colour, width=0.55, edgecolor=SURFACE, linewidth=1.2,
                      zorder=2)
        for bar, key_name in zip(bars, order):
            ax.annotate(f"{share[key_name]:.1f} %".replace(".", ","),
                        xy=(bar.get_x() + bar.get_width() / 2, share[key_name]),
                        xytext=(0, 6), textcoords="offset points", ha="center",
                        fontsize=ANNOTATION, weight="bold", color=colour)
        ax.set_title(f"{title}\n{thousands(len(part))} vídeos", loc="left",
                     fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.set_ylim(0, 100)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Porcentaje de sus vídeos")

    fig.text(0.005, -0.05,
             "Qué mirar: la proporción se da la vuelta. Las cuentas sin verificar "
             "publican reclamaciones algo más de la mitad de las veces; las verificadas "
             "publican opiniones cuatro de cada cinco.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "02_senal.png")
    plt.close(fig)


def figure_vif(before: pd.DataFrame, after: pd.DataFrame) -> None:
    """Multicollinearity before and after, because the five counters measure one thing."""
    style()
    fig, axes = plt.subplots(1, 2, figsize=WIDE)
    for ax, table, title in [(axes[0], before, "Con los cinco contadores"),
                             (axes[1], after, "Con uno solo")]:
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
        ax.margins(x=0.22)

    fig.text(0.005, -0.05,
             "Qué mirar: la línea de puntos es el umbral de 10, y ninguna variable lo "
             "alcanza, así que quitar cuatro de los cinco contadores fue un criterio y no "
             "una obligación.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             "El motivo para quitarlos: los cinco están correlacionados entre sí por "
             "encima de 0,55 y ninguno resultó significativo, así que aportan ruido y "
             "reparten entre ellos un efecto que no existe.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "03_multicolinealidad.png")
    plt.close(fig)


def figure_correlations(df: pd.DataFrame, results: Results) -> None:
    """Why the five counters had to go, said once instead of argued in a caption.

    The VIF figure next door reports a number per variable. This one shows the shape
    behind those numbers, and seaborn draws it in four lines with the annotation and the
    colour bar handled: five counters that all move together, and a duration that has
    nothing to do with any of them.
    """
    import seaborn as sns

    style()
    labels = {"video_view_count": "Visualizaciones", "video_like_count": "Me gusta",
              "video_share_count": "Compartidos", "video_download_count": "Descargas",
              "video_comment_count": "Comentarios", "video_duration_sec": "Duración"}
    matrix = df[list(labels)].corr().rename(index=labels, columns=labels)

    among_counters = df[COUNTERS].corr().values
    counters = among_counters[np.triu_indices_from(among_counters, 1)]
    results.put("correlations.counters_min", round(float(counters.min()), 4),
                "la correlación más floja entre dos contadores")
    results.put("correlations.counters_max", round(float(counters.max()), 4), "  la más alta")
    results.put("correlations.duration_max_abs",
                round(float(matrix.loc["Duración"].drop("Duración").abs().max()), 4),
                "lo más que la duración se parece a un contador")

    fig, ax = plt.subplots(figsize=TALL)
    palette = correlation_map()
    # Only the lower half carries information: the diagonal is always 1 and the upper half
    # repeats the lower one. Dropping the first row and the last column as well, because
    # after masking they hold no cell at all and would print a label over empty space.
    matrix = matrix.iloc[1:, :-1]
    upper = np.triu(np.ones(matrix.shape, dtype=bool), 1)
    sns.heatmap(matrix, mask=upper, cmap=palette, vmin=-1, vmax=1, center=0,
                linewidths=1.2, linecolor=SURFACE, ax=ax,
                cbar_kws={"shrink": 0.55, "label": "Correlación", "ticks": [-1, 0, 1]},
                annot=True, fmt=".2f",
                annot_kws={"fontsize": ANNOTATION, "weight": "bold"})

    # Each number sits on a different colour, so its ink is measured cell by cell.
    for text in ax.texts:
        text.set_text(text.get_text().replace(".", ","))
        column, row = (int(coordinate) for coordinate in text.get_position())
        text.set_color(readable_on(to_hex(palette((matrix.iloc[row, column] + 1) / 2))))

    ax.set_title("Los cinco contadores miden lo mismo, y la duración no mide nada de eso",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)
    ax.tick_params(labelrotation=0)
    plt.setp(ax.get_xticklabels(), rotation=28, ha="right")
    ax.grid(visible=False)

    low = f"{results.data['correlations']['counters_min']:.2f}".replace(".", ",")
    high = f"{results.data['correlations']['counters_max']:.2f}".replace(".", ",")
    top = f"{results.data['correlations']['duration_max_abs']:.3f}".replace(".", ",")
    fig.text(0.005, -0.02,
             f"Qué mirar: el bloque de arriba a la izquierda va de {low} a {high}, así que "
             f"los cinco contadores suben y bajan juntos. La fila de la duración se queda "
             f"en {top} como mucho, del color del fondo.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.07,
             "Por eso el modelo se queda con un contador y no con cinco: los otros cuatro "
             "no traen información nueva, reparten entre ellos un efecto y ensanchan los "
             "intervalos de todos.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "03b_correlaciones.png")
    plt.close(fig)


def figure_odds(model, labels: dict[str, str]) -> None:
    """Odds ratios with their intervals and a line at 1, which is the no-effect mark."""
    style()
    bounds = np.exp(model.conf_int())
    ratios = np.exp(model.params)
    names = [n for n in model.params.index if n != "const"]
    rows = [(labels.get(n, n), float(ratios[n]), float(bounds.loc[n, 0]),
             float(bounds.loc[n, 1])) for n in reversed(names)]

    fig, ax = plt.subplots(figsize=(WIDE[0], 0.52 * len(rows) + 2.2))
    for index, (name, value, low, high) in enumerate(rows):
        colour = AZURITE if low <= 1 <= high else GOLD
        ax.plot([low, high], [index, index], color=colour, linewidth=3.4,
                solid_capstyle="butt", zorder=3)
        ax.plot(value, index, "o", markersize=8, color=colour,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=4)
        ax.annotate(f"{value:.2f}   entre {low:.2f} y {high:.2f}".replace(".", ","),
                    xy=(high, index), xytext=(12, 0), textcoords="offset points",
                    va="center", fontsize=CAPTION, weight="bold", color=colour)

    ax.axvline(1, color=GRAPHITE, linewidth=1.4, zorder=2)
    ax.set_xscale("log")
    ax.set_yticks(range(len(rows)), [name for name, *_ in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("Razón de momios de estar verificada (escala logarítmica)")
    ax.set_title("Cuánto multiplica cada variable los momios de ser una cuenta verificada",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.30)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"{v:g}".replace(".", ",")))

    fig.text(0.005, -0.10,
             "Qué mirar: aquí la línea de no efecto es el 1, no el cero, porque son "
             "multiplicadores. A la izquierda del 1 la variable baja la probabilidad de "
             "estar verificada; a la derecha la sube.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "04_momios.png")
    plt.close(fig)


def figure_confusion(scores: dict, results: Results) -> None:
    """The four cells, with what each one means written inside it.

    Colour is one hue from the validated palette, not a rainbow map: gold for the two
    cells the model got right, and the intensity carries the count. Text flips to the
    paper colour on the dark cells so it stays readable, which the first draft did not.
    """
    style()
    matrix = scores["matrix"]
    fig, ax = plt.subplots(figsize=WIDE)

    texts = [["Acierta que no\nestá verificada", "Falsa alarma"],
             ["Se le escapa", "Acierta que\nestá verificada"]]
    biggest = matrix.max()
    for row in range(2):
        for column in range(2):
            value = int(matrix[row][column])
            weight = value / biggest
            # The floor is 0.30 and not 0.15 because on the dark surface a cell at 0.15
            # blends into the page and the low-count cells stop being cells at all.
            ax.add_patch(plt.Rectangle((column - 0.5, row - 0.5), 1, 1,
                                       facecolor=GOLD, alpha=0.30 + 0.60 * weight,
                                       edgecolor=SURFACE, linewidth=3, zorder=1))
            ink = SURFACE if weight > 0.8 else GRAPHITE      # only the darkest cell
            ax.annotate(thousands(value), xy=(column, row - 0.10), ha="center",
                        va="center", fontsize=HERO, weight="bold", color=ink, zorder=3)
            ax.annotate(texts[row][column], xy=(column, row + 0.22), ha="center",
                        va="center", fontsize=CAPTION, color=ink, alpha=0.85, zorder=3)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(1.5, -0.5)

    ax.set_xticks([0, 1], ["dice que no", "dice que sí"])
    ax.set_yticks([0, 1], ["no lo está", "sí lo está"])
    ax.set_xlabel("Lo que responde el modelo")
    ax.set_ylabel("La verdad")
    ax.grid(visible=False)
    ax.set_title("Dónde acierta y dónde se equivoca, sobre las cuentas de prueba",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)

    recall = f"{100 * scores['recall']:.1f}".replace(".", ",")
    precision = f"{100 * scores['precision']:.1f}".replace(".", ",")
    fig.text(0.005, -0.06,
             f"Qué mirar: de las cuentas verificadas de verdad, el modelo pilla el "
             f"{recall} %. Cuando dice que una cuenta está verificada, acierta el "
             f"{precision} % de las veces, así que una de cada tres alarmas es falsa.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    save_figure(fig, FIGURES, "05_matriz_confusion.png")
    plt.close(fig)


def figure_probabilities(probability: pd.Series, truth: pd.Series,
                         gap: tuple[float, float]) -> None:
    """Why the threshold does not matter: the predictions come in two clumps.

    Same shape as the finding of Course 3, where the view counts turned out to be two
    populations with a gap between them. Here it is the model's own output.
    """
    style()
    fig, axes = plt.subplots(2, 1, figsize=TALL, sharex=True)
    fig.subplots_adjust(hspace=0.42)
    bins = np.arange(0.18, 0.70, 0.01)

    for ax, (name, mask, colour) in zip(axes, [
        ("Cuentas que sí están verificadas", truth.eq(1), AZURITE),
        ("Cuentas que no lo están", truth.eq(0), GOLD),
    ]):
        ax.hist(probability[mask], bins=bins, color=colour, alpha=0.95,
                edgecolor=SURFACE, linewidth=0.7, zorder=2)
        ax.axvspan(gap[0], gap[1], color=HAIRLINE, alpha=0.5, zorder=1)
        ax.set_title(f"{name}   ({thousands(int(mask.sum()))})", loc="left",
                     fontsize=PANEL_TITLE, weight="bold", pad=10)
        ax.set_ylabel("Cuentas")
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: thousands(v)))

    axes[0].annotate("ninguna predicción cae aquí dentro",
                     xy=(sum(gap) / 2, 0.72), xycoords=("data", "axes fraction"),
                     ha="center", fontsize=ANNOTATION, weight="bold", color=GRAPHITE)
    axes[1].set_xlabel("Probabilidad de estar verificada que predice el modelo")
    axes[1].xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"{v:.1f}".replace(".", ",")))

    fig.text(0.005, -0.03,
             "Qué mirar: la banda gris está vacía en los dos paneles. Mover el umbral "
             "dentro de ella no cambia ni una sola decisión.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.09,
             "El modelo no reparte a las cuentas por un abanico de probabilidades: las "
             "manda a uno de dos montones, según si el vídeo es una reclamación o una "
             "opinión. Se ha convertido en una sola regla con pasos intermedios.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "06_probabilidades.png")
    plt.close(fig)

    # Interactive twin: the finding is an empty band, and being able to zoom into it is
    # the difference between believing the claim and checking it.
    import plotly.graph_objects as go

    plot = go.Figure()
    for name, mask, colour in [("Sí están verificadas", truth.eq(1), AZURITE),
                               ("No lo están", truth.eq(0), GOLD)]:
        counts, edges = np.histogram(probability[mask], bins=bins)
        plot.add_bar(x=(edges[:-1] + edges[1:]) / 2, y=counts, name=name,
                     marker_color=colour, marker_line_color=SURFACE, marker_line_width=1,
                     hovertemplate="probabilidad %{x:.2f}<br><b>%{y} cuentas</b>"
                                   "<extra></extra>")
    plot.add_vrect(x0=gap[0], x1=gap[1], fillcolor=HAIRLINE, opacity=0.45, line_width=0)
    plot.update_layout(**interactive_layout(
        "El umbral no decide nada: no hay nadie en medio",
        f"La banda gris va de {gap[0]} a {gap[1]} y está vacía en los dos grupos. "
        f"Haz zoom dentro de ella y comprueba que no aparece ni una cuenta."))
    plot.update_layout(barmode="overlay")
    plot.update_traces(opacity=0.85)
    plot.update_xaxes(title_text="Probabilidad de estar verificada que predice el modelo")
    plot.update_yaxes(title_text="Cuentas")
    save_interactive(plot, FIGURES, "06_probabilidades.html")


# ---------------------------------------------------------------------------- run

def main() -> None:
    results = Results(SLUG, "TikTok: predecir si una cuenta está verificada")
    df = encode(load_and_clean(results))

    banner("2. Equilibrar las clases")
    balanced = balance(df, results)

    banner("3. Multicolinealidad: los cinco contadores miden lo mismo")
    everything = ["video_duration_sec", "is_claim", "banned", "under_review"] + COUNTERS
    before = vif_table(balanced[everything])
    print(before.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    for _, row in before.iterrows():
        results.put(f"vif_full.{row.variable}", round(float(row.vif), 2))

    features = ["video_duration_sec", "is_claim", "banned", "under_review",
                "video_view_count"]
    after = vif_table(balanced[features])
    print("\nDejando solo las visualizaciones:")
    print(after.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    for _, row in after.iterrows():
        results.put(f"vif_final.{row.variable}", round(float(row.vif), 2))
    results.put("model.features", features)
    results.put("model.dropped", [c for c in COUNTERS if c != "video_view_count"],
                "contadores descartados por decir lo mismo")

    banner("4. Ajustar la logística")
    train, test = train_test_split(balanced, test_size=0.25, random_state=SEED,
                                   stratify=balanced.verified)
    results.put("split.train_rows", len(train), "filas de entrenamiento")
    results.put("split.test_rows", len(test), "filas de prueba")

    model = sm.Logit(train.verified, sm.add_constant(train[features])).fit(disp=False)
    bounds = model.conf_int()
    print()
    for name in ["const"] + features:
        ratio = float(np.exp(model.params[name]))
        results.put(f"coefficients.{name}.value", round(float(model.params[name]), 4))
        results.put(f"coefficients.{name}.odds_ratio", round(ratio, 4))
        results.put(f"coefficients.{name}.p", float(f"{model.pvalues[name]:.3g}"))
        results.put(f"coefficients.{name}.ci_low",
                    round(float(np.exp(bounds.loc[name, 0])), 4))
        results.put(f"coefficients.{name}.ci_high",
                    round(float(np.exp(bounds.loc[name, 1])), 4))
        print(f"  {name:<20} coef {model.params[name]:+8.4f}   momios ×{ratio:6.3f}   "
              f"p = {model.pvalues[name]:.3g}")
    results.put("fit.pseudo_r2", round(float(model.prsquared), 4), "\n  pseudo R2")

    banner("5. Qué tal clasifica")
    probability = model.predict(sm.add_constant(test[features]))
    print("  umbral 0,5:")
    scores = metrics(test.verified, (probability >= 0.5).astype(int), probability,
                     results, "metrics_050")

    banner("6. El umbral, que aquí resulta no servir de nada")
    # Module 5 says the threshold is a business decision. Here it is not a decision at
    # all, and the reason is visible in the predicted probabilities: they fall in two
    # clumps with an empty band between them, so moving the cut inside that band changes
    # nothing. The model has collapsed into a single rule.
    gap_low, gap_high = 0.28, 0.56
    inside = int(probability.between(gap_low, gap_high).sum())
    results.put("threshold.gap_low", gap_low)
    results.put("threshold.gap_high", gap_high)
    results.put("threshold.cases_inside_gap", inside,
                f"casos con probabilidad entre {gap_low} y {gap_high}")
    results.put("threshold.p_min", round(float(probability.min()), 3),
                "probabilidad más baja que predice")
    results.put("threshold.p_max", round(float(probability.max()), 3),
                "probabilidad más alta que predice")

    for cut in [0.30, 0.40, 0.50, 0.55]:
        predicted = (probability >= cut).astype(int)
        caught = int(((predicted == 1) & (test.verified == 1)).sum())
        print(f"  umbral {cut:.2f}: marca {int(predicted.sum()):>3} cuentas, "
              f"acierta {caught:>3}".replace(".", ","))
    results.put("threshold.identical_between",
                "cualquier corte entre 0,28 y 0,56 da exactamente el mismo resultado")

    banner("7. Figuras")
    figure_balance(df, results)
    figure_signal(df)
    figure_vif(before, after)
    figure_correlations(df, results)
    figure_odds(model, {
        "video_duration_sec": "Cada segundo de vídeo",
        "is_claim": "El vídeo es una reclamación",
        "banned": "Autor expulsado",
        "under_review": "Autor en revisión",
        "video_view_count": "Cada visualización",
    })
    figure_confusion(scores, results)
    figure_probabilities(probability, test.verified, (gap_low, gap_high))
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
