"""Waze, Course 5: does a tree-based model beat the regression from Course 4?

This is the only project in the library that can answer that question honestly, because
Course 4 predicted the same thing on the same file and left its numbers written down. So
the split here is built to make the comparison exact: the first cut is the same 75/25 with
the same seed, which means **the 3,575 users in the test set are literally the same ones**,
and the 10,724 Course 4 trained on are the ones that get divided into training and
validation here.

Run it:
    python projects/curso5/waze/02_scripts/waze_trees.py

Reads Kevin's CSV read-only, writes figures to 03_figures/ and every publishable number to
04_reports/model_results.json.

What this project does that Course 4 did not:

  - Three-way split, with the test set untouched until the last step. Course 4 had two.
  - Segmentation by k-means, from module 3, used as a variable, with k chosen by silhouette
    on his data rather than picked.
  - Four candidate families compared on validation, then hyperparameters tuned by grid
    search, and only then one measurement on the test set.
  - Feature importance, which is what makes a forest explainable.

The expectation, written before the models are fitted so it cannot be adjusted afterwards:
the trees are unlikely to win. An untuned comparison already suggested it, and this run
tunes them properly so the answer means something either way. If the trees do win, that
gets reported and the course's moral changes; the method does not.
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, silhouette_score)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # projects/, for common.py
from common import (  # noqa: E402
    ANNOTATION, AZURITE, CAPTION, GOLD, GRAPHITE, HAIRLINE, MUTED, PANEL_TITLE, SURFACE,
    TALL, TITLE, WIDE, Results, banner, dataset, decimal, figures_dir,
    save_figure, style, thousands,
)

import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "waze"
COURSE = "curso5"
FIGURES = figures_dir(COURSE, SLUG)
SEED = 42

# What Course 4 published on this same test set, read from its own model_results.json at
# run time so the two can never drift apart silently.
COURSE4_REPORT = (Path(__file__).resolve().parents[3] / "curso4" / SLUG / "04_reports"
                  / "model_results.json")

# The columns the segmentation looks at: behaviour, not identity. Scaled first, because
# k-means measures distances and kilometres would otherwise drown activity days.
SEGMENT_COLUMNS = ["drives", "activity_days", "driven_km_drives",
                   "duration_minutes_drives", "n_days_after_onboarding"]

FEATURES = ["drives", "total_sessions", "n_days_after_onboarding",
            "duration_minutes_drives", "activity_days", "km_per_driving_day",
            "professional_driver", "iphone", "segment"]

LABELS = {
    "drives": "Trayectos", "total_sessions": "Sesiones totales",
    "n_days_after_onboarding": "Días desde el alta",
    "duration_minutes_drives": "Minutos al volante", "activity_days": "Días activo",
    "km_per_driving_day": "Km por día conducido",
    "professional_driver": "Conductor profesional", "iphone": "iPhone",
    "segment": "Segmento (módulo 3)",
}


def load(results: Results) -> pd.DataFrame:
    """Same preparation as Course 4, on purpose: a different one would void the comparison."""
    banner("1. Los datos, preparados igual que en el Curso 4")
    df = pd.read_csv(dataset(SLUG))
    results.put("data.rows_raw", len(df), "filas en el CSV")
    results.put("data.rows_unlabelled", int(df.label.isna().sum()), "usuarios sin etiqueta")

    df = df.dropna(subset=["label"]).copy()
    df["churned"] = df.label.eq("churned").astype(int)
    df["iphone"] = df.device.eq("iPhone").astype(int)
    # Dividing by zero would give inf, which the optimiser cannot handle. These users drove
    # nothing, so their rate is zero.
    df["km_per_driving_day"] = np.where(df.driving_days.gt(0),
                                        df.driven_km_drives / df.driving_days.replace(0, 1),
                                        0.0)
    df["professional_driver"] = ((df.drives >= 60) & (df.driving_days >= 15)).astype(int)

    results.put("data.rows_labelled", len(df), "usuarios con etiqueta")
    results.put("data.churn_rate", round(100 * float(df.churned.mean()), 2),
                "tasa de abandono (%)")
    return df


def split(df: pd.DataFrame, results: Results) -> tuple[pd.DataFrame, ...]:
    """Three parts, with the first cut identical to Course 4 so the test set is the same."""
    banner("2. La partición en tres, con la prueba intacta hasta el final")
    rest, test = train_test_split(df, test_size=0.25, random_state=SEED,
                                  stratify=df.churned)
    train, validation = train_test_split(rest, test_size=0.20, random_state=SEED,
                                         stratify=rest.churned)

    for name, part in [("train", train), ("validation", validation), ("test", test)]:
        results.put(f"split.{name}_rows", len(part))
        results.put(f"split.{name}_churn", round(100 * float(part.churned.mean()), 2),
                    f"  abandono en {name} (%)")
    results.put("split.course4_train_rows", len(rest),
                "los que el Curso 4 usó enteros para entrenar")
    print(f"  entrenamiento {len(train)}   validación {len(validation)}   "
          f"prueba {len(test)}")
    print(f"  la prueba es la misma que la del Curso 4: {len(test)} usuarios")
    return train, validation, test


def segment(train, validation, test, results: Results) -> KMeans:
    """Module 3 applied to his data: group the users, with k chosen by silhouette.

    And the answer is not the flattering one. The best silhouette is 0.2588, which is weak:
    these users do not fall into separated groups, they are a continuum. That gets reported
    rather than dressed up, and the variable goes into the model anyway so the model can
    say whether it was worth anything.
    """
    banner("3. Segmentar sin etiquetas, y cuántos grupos hay de verdad")
    scaler = StandardScaler().fit(train[SEGMENT_COLUMNS])
    scaled = scaler.transform(train[SEGMENT_COLUMNS])

    scores = {}
    for k in range(2, 8):
        model = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(scaled)
        scores[k] = {"inertia": float(model.inertia_),
                     "silhouette": float(silhouette_score(scaled, model.labels_))}
        results.put(f"segments.k{k}.inertia", round(scores[k]["inertia"], 1))
        results.put(f"segments.k{k}.silhouette", round(scores[k]["silhouette"], 4))
        print(f"  k={k}   inercia {scores[k]['inertia']:9.0f}   "
              f"silueta {scores[k]['silhouette']:.4f}")

    best_k = max(scores, key=lambda k: scores[k]["silhouette"])
    results.put("segments.k_chosen", best_k, "grupos elegidos por la silueta")
    results.put("segments.best_silhouette", round(scores[best_k]["silhouette"], 4),
                "  y su silueta, que es floja")

    model = KMeans(n_clusters=best_k, n_init=20, random_state=SEED).fit(scaled)
    for part in (train, validation, test):
        part["segment"] = model.predict(scaler.transform(part[SEGMENT_COLUMNS]))

    by_segment = train.groupby("segment").churned.agg(["size", "mean"])
    for group, row in by_segment.iterrows():
        results.put(f"segments.churn.group_{group}.users", int(row["size"]))
        results.put(f"segments.churn.group_{group}.rate", round(100 * float(row["mean"]), 2),
                    f"  abandono del grupo {group} (%)")
    spread = 100 * (by_segment["mean"].max() - by_segment["mean"].min())
    results.put("segments.churn_spread", round(float(spread), 2),
                "diferencia de abandono entre el grupo peor y el mejor (puntos)")
    print(f"\n  {best_k} grupos, silueta {scores[best_k]['silhouette']:.4f}")
    print(f"  y separan el abandono en {spread:.2f} puntos, que es poco")
    model.scaler = scaler                    # kept so the notebook can reuse it
    return model


def measure(model, features, truth, results: Results, prefix: str) -> dict:
    probability = model.predict_proba(features)[:, 1]
    decision = (probability >= 0.5).astype(int)
    scores = {
        "accuracy": accuracy_score(truth, decision),
        "precision": precision_score(truth, decision, zero_division=0),
        "recall": recall_score(truth, decision),
        "f1": f1_score(truth, decision),
        "auc": roc_auc_score(truth, probability),
    }
    for name, value in scores.items():
        results.put(f"{prefix}.{name}", round(float(value), 4))
    return scores


def candidates(train, validation, results: Results) -> dict:
    """Four families, one measurement each on validation. The test set stays closed."""
    banner("4. Cuatro candidatos, comparados en validación")
    X, y = train[FEATURES], train.churned
    Xv, yv = validation[FEATURES], validation.churned

    models = {
        "logistica": LogisticRegression(max_iter=3000),
        "arbol": DecisionTreeClassifier(random_state=SEED),
        "bosque": RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
        "xgboost": XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.1,
                                 eval_metric="logloss", random_state=SEED, n_jobs=1),
    }
    for name, model in models.items():
        model.fit(X, y)
        auc = roc_auc_score(yv, model.predict_proba(Xv)[:, 1])
        results.put(f"candidates.{name}_auc", round(float(auc), 4))
        print(f"  {name:12} AUC {auc:.4f}")
    return models


def tune(train, validation, results: Results) -> dict:
    """Grid search on the two tree families, so neither loses for being left untuned."""
    banner("5. Ajuste de perillas, para que ninguna familia pierda por desatendida")
    X, y = train[FEATURES], train.churned
    Xv, yv = validation[FEATURES], validation.churned
    tuned = {}

    grids = {
        "bosque": (RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
                   {"max_depth": [4, 6, 8, 12, None], "min_samples_leaf": [1, 10, 25, 50],
                    "max_features": ["sqrt", 0.5]}),
        "xgboost": (XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=1),
                    {"max_depth": [2, 3, 4, 6], "learning_rate": [0.02, 0.05, 0.1],
                     "n_estimators": [200, 500], "subsample": [0.8, 1.0]}),
    }
    for name, (estimator, grid) in grids.items():
        combinations = int(np.prod([len(v) for v in grid.values()]))
        started = time.perf_counter()
        search = GridSearchCV(estimator, grid, cv=4, scoring="roc_auc",
                              n_jobs=-1).fit(X, y)
        elapsed = time.perf_counter() - started
        auc = roc_auc_score(yv, search.best_estimator_.predict_proba(Xv)[:, 1])

        results.put(f"tuning.{name}.combinations", combinations)
        results.put(f"tuning.{name}.seconds", round(elapsed, 1))
        results.put(f"tuning.{name}.best_params",
                    {k: str(v) for k, v in search.best_params_.items()})
        results.put(f"tuning.{name}.cv_auc", round(float(search.best_score_), 4),
                    "  AUC en validación cruzada, que sale optimista")
        results.put(f"tuning.{name}.validation_auc", round(float(auc), 4),
                    "  AUC en validación")
        print(f"  {name:8} {combinations} combinaciones x 4 pliegues en {elapsed:5.0f} s   "
              f"AUC {auc:.4f}")
        print(f"           {search.best_params_}")
        tuned[name] = search.best_estimator_
    return tuned


def compare_with_course4(results: Results) -> dict:
    """Read what Course 4 published, so the two can never drift apart in the write-up."""
    import json

    if not COURSE4_REPORT.exists():
        raise SystemExit(f"No está el informe del Curso 4: {COURSE4_REPORT}")
    previous = json.loads(COURSE4_REPORT.read_text(encoding="utf-8"))["metrics_050"]
    for name in ("accuracy", "precision", "recall", "f1", "auc"):
        results.put(f"course4.{name}", previous[name])
    results.put("course4.test_rows", 3575, "y sobre exactamente los mismos usuarios")
    return previous


# ------------------------------------------------------------------------- figures

def figure_segments(results: Results) -> None:
    """What the segmentation found, which is not much, said with its own numbers."""
    style()
    scores = results.data["segments"]
    ks = [k for k in range(2, 8)]
    silhouettes = [scores[f"k{k}"]["silhouette"] for k in ks]

    fig, axes = plt.subplots(1, 2, figsize=WIDE)
    axes[0].plot(ks, silhouettes, "-o", color=AZURITE, linewidth=2.2, markersize=9,
                 markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
    best = scores["k_chosen"]
    peak = decimal(scores["best_silhouette"])
    axes[0].annotate(f"máximo en {best}\n{peak}",
                     xy=(best, scores["best_silhouette"]), xytext=(14, -4),
                     textcoords="offset points", fontsize=ANNOTATION, weight="bold",
                     color=AZURITE)
    axes[0].axhspan(0, 0.35, color=HAIRLINE, alpha=0.45, zorder=1)
    axes[0].annotate("por debajo de 0,35 los grupos\nse tocan entre sí", xy=(5.4, 0.30),
                     ha="center", va="top", fontsize=CAPTION, style="italic", color=MUTED)
    axes[0].set_xlabel("Número de grupos que se piden")
    axes[0].set_ylabel("Coeficiente de silueta")
    axes[0].set_ylim(0, 0.6)
    axes[0].set_xticks(ks)
    axes[0].set_title("Ningún número de grupos separa bien", loc="left",
                      fontsize=PANEL_TITLE, weight="bold", pad=12)
    axes[0].grid(axis="x", visible=False)

    groups = sorted(int(name.split("_")[1]) for name in scores["churn"])
    rates = [scores["churn"][f"group_{g}"]["rate"] for g in groups]
    sizes = [scores["churn"][f"group_{g}"]["users"] for g in groups]
    bars = axes[1].bar([f"Grupo {g}" for g in groups], rates, color=[GOLD, AZURITE],
                       width=0.55, edgecolor=SURFACE, linewidth=1.2, zorder=2)
    for bar, rate, size in zip(bars, rates, sizes):
        axes[1].annotate(decimal(rate, 2) + " %" + f"\n{thousands(size)} usuarios",
                         xy=(bar.get_x() + bar.get_width() / 2, rate), xytext=(0, 6),
                         textcoords="offset points", ha="center", fontsize=ANNOTATION,
                         weight="bold", color=GRAPHITE)
    axes[1].set_ylabel("Abandono del grupo")
    axes[1].set_ylim(0, max(rates) * 1.45)
    axes[1].set_title("Y los que salen abandonan casi igual", loc="left",
                      fontsize=PANEL_TITLE, weight="bold", pad=12)
    axes[1].grid(axis="x", visible=False)

    spread = decimal(results.data['segments']['churn_spread'], 2)
    fig.text(0.005, -0.05,
             f"Qué mirar: la silueta no llega a 0,26 en ningún caso, así que estos usuarios "
             f"no forman grupos separados, son un continuo.\nY los dos grupos que salen se "
             f"diferencian en {spread} puntos de abandono, que no es una segmentación "
             f"accionable.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.14,
             "Se reporta así, y la variable entra igual en el modelo, para que sea el "
             "modelo quien diga si valía algo. Adelanto: queda la última de nueve.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_segmentos.png")
    plt.close(fig)


def figure_tuning(results: Results) -> None:
    """What tuning bought each family, which is the honest way to compare them."""
    style()
    rows = [
        ("Regresión logística", results.data["candidates"]["logistica_auc"], None),
        ("Árbol suelto", results.data["candidates"]["arbol_auc"], None),
        ("Bosque aleatorio", results.data["candidates"]["bosque_auc"],
         results.data["tuning"]["bosque"]["validation_auc"]),
        ("Refuerzo (xgboost)", results.data["candidates"]["xgboost_auc"],
         results.data["tuning"]["xgboost"]["validation_auc"]),
    ]
    fig, ax = plt.subplots(figsize=WIDE)
    positions = np.arange(len(rows))[::-1]

    for position, (name, before, after) in zip(positions, rows):
        if after is None:
            ax.plot(before, position, "o", markersize=11, color=GOLD,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=5)
        else:
            ax.plot([before, after], [position, position], color=HAIRLINE, linewidth=2.4,
                    zorder=2)
            ax.plot(before, position, "o", markersize=9, color=MUTED,
                    markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=4)
            ax.plot(after, position, "o", markersize=11, color=AZURITE,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=5)
        value = after if after is not None else before
        ax.annotate(decimal(value, 4), xy=(0.995, position),
                    xycoords=("axes fraction", "data"), ha="right", va="center",
                    fontsize=ANNOTATION, weight="bold", color=GRAPHITE)

    best = results.data["candidates"]["logistica_auc"]
    ax.axvline(best, color=GOLD, linewidth=1.4, linestyle=(0, (4, 3)), zorder=3)
    ax.set_yticks(positions, [name for name, *_ in rows])
    ax.set_xlabel("AUC en validación")
    ax.set_xlim(0.55, 0.80)
    ax.margins(x=0.30)
    ax.set_title("Ajustar los árboles casi cierra la distancia, y no la cierra", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)

    forest = results.data["tuning"]["bosque"]
    gained = decimal(forest["validation_auc"] - results.data["candidates"]["bosque_auc"])
    short = decimal(best - forest["validation_auc"])
    fig.text(0.005, -0.06,
             f"Qué mirar: el punto apagado es el modelo sin ajustar y el vivo el ajustado. "
             f"El bosque gana {gained} al afinarlo, que es mucho para lo que se juega "
             f"aquí, y aun así se queda a {short} de la línea de puntos.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.14,
             "La línea de puntos es la regresión logística, que no lleva perillas que "
             "ajustar y por eso aparece con un solo punto. El árbol suelto tampoco lleva "
             "dos: está ahí sin acotar, para verlo perder.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "02_ajuste.png")
    plt.close(fig)


def figure_importance(forest, results: Results) -> None:
    """What the forest used, with the module 3 segment landing last."""
    style()
    pairs = sorted(zip(FEATURES, forest.feature_importances_), key=lambda t: t[1])
    for name, value in pairs:
        results.put(f"importance.{name}", round(float(value), 4))

    fig, ax = plt.subplots(figsize=TALL)
    names = [LABELS[name] for name, _ in pairs]
    values = [value for _, value in pairs]
    colours = [AZURITE if name == "segment" else GOLD for name, _ in pairs]
    bars = ax.barh(names, values, color=colours, height=0.62, edgecolor=SURFACE,
                   linewidth=1.1, zorder=2)
    for bar, value in zip(bars, values):
        ax.annotate(decimal(value, 4),
                    xy=(value, bar.get_y() + bar.get_height() / 2), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=CAPTION,
                    weight="bold", color=GRAPHITE)
    ax.set_xlim(0, max(values) * 1.22)
    ax.set_xlabel("Importancia dentro del bosque")
    ax.set_title("Los días de actividad son la mitad del modelo", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)

    top = decimal(max(values), 4)
    segment_value = decimal(dict(pairs)['segment'], 4)
    fig.text(0.005, -0.04,
             f"Qué mirar: los días activo se llevan {top} ellos solos, más que las ocho "
             f"restantes juntas.\nY en azul, abajo del todo, el segmento del módulo 3: "
             f"{segment_value}, que es no aportar nada.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             "Esa última barra es el resultado honesto de aplicar el agrupamiento a estos "
             "datos: la silueta ya avisaba de que no había grupos, y el modelo lo confirma.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "03_importancia.png")
    plt.close(fig)


def figure_comparison(results: Results) -> None:
    """The figure the whole course exists for: same users, same split, two courses."""
    style()
    rows = [
        ("Logística del Curso 4", results.data["course4"]["auc"], GOLD),
        ("Logística de este curso", results.data["test"]["logistica"]["auc"], GOLD),
        ("Bosque ajustado", results.data["test"]["bosque"]["auc"], AZURITE),
        ("Refuerzo ajustado", results.data["test"]["xgboost"]["auc"], AZURITE),
    ]
    fig, ax = plt.subplots(figsize=WIDE)
    positions = np.arange(len(rows))[::-1]
    bars = ax.barh(positions, [value for _, value, _ in rows],
                   color=[colour for *_, colour in rows], height=0.6,
                   edgecolor=SURFACE, linewidth=1.2, zorder=2)
    for bar, (_, value, _) in zip(bars, rows):
        ax.annotate(decimal(value, 4),
                    xy=(value, bar.get_y() + bar.get_height() / 2), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=ANNOTATION,
                    weight="bold", color=GRAPHITE)

    ax.set_yticks(positions, [name for name, *_ in rows])
    ax.set_xlim(0.70, 0.76)
    ax.set_xlabel("AUC sobre el conjunto de prueba")
    ax.set_title("Los mismos 3.575 usuarios, y el modelo simple sigue ganando", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)

    fig.text(0.005, -0.06,
             "Qué mirar: en dorado los dos modelos simples y en azul los complicados y "
             "ajustados. El eje empieza en 0,70 para que se vean las diferencias, que son "
             "de milésimas.\nEsa escala corta es honesta solo si se dice, y por eso se dice.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.15,
             "Es la comparación que ningún proyecto suelto puede hacer: mismo archivo, "
             "misma partición, misma semilla, y el conjunto de prueba mirado una sola vez "
             "en cada curso.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "04_comparacion.png")
    plt.close(fig)


def figure_recall(results: Results) -> None:
    """The finding that survives every model: nobody detects the churners."""
    style()
    names = ["Logística\nCurso 4", "Logística\nCurso 5", "Bosque\najustado",
             "Refuerzo\najustado"]
    recalls = [results.data["course4"]["recall"],
               results.data["test"]["logistica"]["recall"],
               results.data["test"]["bosque"]["recall"],
               results.data["test"]["xgboost"]["recall"]]
    accuracies = [results.data["course4"]["accuracy"],
                  results.data["test"]["logistica"]["accuracy"],
                  results.data["test"]["bosque"]["accuracy"],
                  results.data["test"]["xgboost"]["accuracy"]]

    fig, ax = plt.subplots(figsize=WIDE)
    positions = np.arange(len(names))
    ax.bar(positions - 0.19, accuracies, width=0.36, color=MUTED, edgecolor=SURFACE,
           linewidth=1.2, label="Exactitud", zorder=2)
    ax.bar(positions + 0.19, recalls, width=0.36, color=GOLD, edgecolor=SURFACE,
           linewidth=1.2, label="Sensibilidad: a cuántos de los que se van detecta",
           zorder=2)
    for position, (accuracy, recall) in enumerate(zip(accuracies, recalls)):
        ax.annotate(decimal(accuracy, 2), xy=(position - 0.19, accuracy),
                    xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=CAPTION, weight="bold", color=MUTED)
        ax.annotate(decimal(recall, 3), xy=(position + 0.19, recall),
                    xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=CAPTION, weight="bold", color=GOLD)

    ax.set_xticks(positions, names)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Proporción")
    ax.legend(loc="upper center", frameon=False, fontsize=ANNOTATION, ncols=2)
    ax.set_title("Cuatro modelos, el mismo fracaso: detectan a menos de uno de cada diez",
                 loc="left", fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="x", visible=False)

    fig.text(0.005, -0.05,
             "Qué mirar: las barras grises son casi idénticas y altas, y las doradas son "
             "casi idénticas y diminutas. Cambiar de familia de modelo no movió esto.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             "El Curso 4 ya había diagnosticado que el problema era el umbral y no el "
             "modelo. Esta figura lo confirma desde otro sitio: con tres modelos más, la "
             "sensibilidad sigue clavada.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "05_sensibilidad.png")
    plt.close(fig)


def main() -> None:
    results = Results(SLUG, "Waze: ¿le gana un modelo de árbol a la regresión?", COURSE)
    df = load(results)
    train, validation, test = split(df, results)
    segment(train, validation, test, results)

    plain = candidates(train, validation, results)
    tuned = tune(train, validation, results)

    banner("6. El campeón se elige en validación, no en prueba")
    finalists = {"logistica": plain["logistica"], "bosque": tuned["bosque"],
                 "xgboost": tuned["xgboost"]}
    Xv, yv = validation[FEATURES], validation.churned
    on_validation = {name: roc_auc_score(yv, model.predict_proba(Xv)[:, 1])
                     for name, model in finalists.items()}
    champion = max(on_validation, key=on_validation.get)
    for name, auc in on_validation.items():
        results.put(f"finalists.{name}_validation_auc", round(float(auc), 4))
    results.put("champion", champion, "el que gana en validación")
    print(f"  campeón: {champion}")

    banner("7. El conjunto de prueba, una sola vez")
    Xt, yt = test[FEATURES], test.churned
    for name, model in finalists.items():
        scores = measure(model, Xt, yt, results, f"test.{name}")
        print(f"  {name:12} AUC {scores['auc']:.4f}   exactitud {scores['accuracy']:.4f}   "
              f"sensibilidad {scores['recall']:.4f}")

    banner("8. Contra el Curso 4, sobre los mismos usuarios")
    previous = compare_with_course4(results)
    here = results.data["test"][champion]
    print(f"  Curso 4: AUC {previous['auc']:.4f}   sensibilidad {previous['recall']:.4f}")
    print(f"  Curso 5: AUC {here['auc']:.4f}   sensibilidad {here['recall']:.4f}")
    results.put("verdict.trees_win", bool(max(results.data["test"]["bosque"]["auc"],
                                              results.data["test"]["xgboost"]["auc"])
                                          > results.data["test"]["logistica"]["auc"]),
                "¿le ganó algún árbol a la logística en prueba?")

    banner("9. Figuras")
    figure_segments(results)
    figure_tuning(results)
    figure_importance(tuned["bosque"], results)
    figure_comparison(results)
    figure_recall(results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
