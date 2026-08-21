"""Automatidata, Course 5: who leaves a generous tip, and can it be predicted at all?

The third flavour of the course. Waze had a weak signal and TikTok an enormous one; this
one has **none**, and finding that out properly is the whole exercise.

Run it:
    python projects/curso5/automatidata/02_scripts/automatidata_trees.py

Reads Kevin's CSV read-only, writes figures to 03_figures/ and every publishable number to
04_reports/model_results.json.

Two decisions taken before any model, both forced by the data and both departures from the
official exemplar:

  1. **Card payments only.** The 7,434 trips paid any other way record a tip of zero in
     100 % of cases, because the meter does not capture cash tips. Training on the whole
     file teaches the model "cash, therefore no tip", which is a property of the machine
     dressed up as a finding.

  2. **Generous means above the default button, not above zero.** The median tip on card is
     19.97 %, and 4,377 trips leave exactly 20.00 %, which is the preset the machine offers.
     Someone who presses the default did not decide to be generous. The threshold is read
     off that distribution rather than picked.

And one leak checked rather than assumed: `total_amount` includes `tip_amount`, verified on
22,656 of 22,699 rows, so it can never be a predictor. The pre-tip cost is rebuilt as
`total_amount - tip_amount` and that is what the passenger sees when the prompt appears.
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # projects/, for common.py
from common import (  # noqa: E402
    ANNOTATION, AZURITE, CAPTION, GOLD, GRAPHITE, HAIRLINE, MUTED, PANEL_TITLE, SURFACE,
    TALL, TITLE, WIDE, Results, banner, dataset, decimal, figures_dir, save_figure, style,
    thousands,
)

import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SLUG = "automatidata"
COURSE = "curso5"
FIGURES = figures_dir(COURSE, SLUG)
SEED = 42
STAMP = "%m/%d/%Y %I:%M:%S %p"
CARD = 1                      # payment_type 1 is the only one that records a tip
DEFAULT_BUTTON = 0.20         # read off the distribution, not chosen

FEATURES = ["trip_distance", "duration", "passenger_count", "fare_amount", "extra",
            "tolls_amount", "base", "hour", "weekend", "rush_hour", "airport_flat",
            "speed"]

LABELS = {
    "trip_distance": "Distancia", "duration": "Duración", "passenger_count": "Pasajeros",
    "fare_amount": "Tarifa", "extra": "Suplementos", "tolls_amount": "Peajes",
    "base": "Coste antes de propina", "hour": "Hora del día", "weekend": "Fin de semana",
    "rush_hour": "Hora punta", "airport_flat": "Tarifa plana de aeropuerto",
    "speed": "Velocidad media",
}


def check_leak(df: pd.DataFrame, results: Results) -> None:
    """Prove that total_amount contains the tip, instead of assuming it."""
    banner("1. La fuga que hay que descartar antes de nada")
    parts = ["fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
             "improvement_surcharge"]
    matches = int(((df[parts].sum(axis=1) - df.total_amount).abs() < 0.01).sum())
    results.put("leak.rows_where_total_equals_parts", matches,
                "filas donde el importe total es la suma de las partes, propina incluida")
    results.put("leak.rows", len(df))
    print(f"  el importe total contiene la propina en {matches} de {len(df)} viajes")
    print(f"  así que total_amount NO puede ser variable predictora")


def load(results: Results) -> tuple[pd.DataFrame, pd.DataFrame]:
    banner("2. El efectivo, y por qué el proyecto se queda solo con la tarjeta")
    df = pd.read_csv(dataset(SLUG), index_col=0)
    df["pickup"] = pd.to_datetime(df.tpep_pickup_datetime, format=STAMP)
    df["dropoff"] = pd.to_datetime(df.tpep_dropoff_datetime, format=STAMP)
    df["duration"] = (df.dropoff - df.pickup).dt.total_seconds() / 60
    check_leak(df, results)

    results.put("data.rows_raw", len(df), "viajes en el CSV")
    for kind, group in df.groupby("payment_type"):
        results.put(f"payment.type_{kind}.trips", len(group))
        results.put(f"payment.type_{kind}.zero_tip_pct",
                    round(100 * float(group.tip_amount.eq(0).mean()), 1),
                    f"  % con propina cero en el tipo de pago {kind}")
    not_card = df[~df.payment_type.eq(CARD)]
    results.put("payment.non_card_trips", len(not_card), "viajes que no se pagan con tarjeta")
    results.put("payment.non_card_zero_tip_pct",
                round(100 * float(not_card.tip_amount.eq(0).mean()), 1),
                "  y su porcentaje de propina cero")

    card = df[df.payment_type.eq(CARD)].copy()
    card["base"] = card.total_amount - card.tip_amount
    card = card[(card.base > 0) & (card.duration > 0) & (card.trip_distance > 0)].copy()
    card["rate"] = card.tip_amount / card.base
    results.put("data.card_trips", len(card), "viajes con tarjeta utilizables")
    return df, card


def build_target(card: pd.DataFrame, results: Results) -> pd.DataFrame:
    """The threshold comes off the distribution: above the machine's default button."""
    banner("3. Qué es «generoso», leído de los datos y no elegido")
    results.put("target.median_rate", round(100 * float(card.rate.median()), 2),
                "mediana de la propina, en porcentaje")
    exact = int(card.rate.round(4).eq(DEFAULT_BUTTON).sum())
    results.put("target.exactly_20pct", exact,
                "viajes que dejan exactamente el 20,00 %, que es el botón por defecto")
    results.put("target.exactly_20pct_share", round(100 * exact / len(card), 1),
                "  en porcentaje")
    buttons = int(card.rate.round(4).isin([0.20, 0.25, 0.30]).sum())
    results.put("target.on_a_button", buttons,
                "viajes en uno de los tres botones de la máquina")
    results.put("target.on_a_button_share", round(100 * buttons / len(card), 1),
                "  en porcentaje")

    card = card.copy()
    card["generous"] = card.rate.gt(DEFAULT_BUTTON).astype(int)
    results.put("target.threshold", DEFAULT_BUTTON,
                "generoso es pasar del botón por defecto, no dejar algo")
    results.put("target.generous_pct", round(100 * float(card.generous.mean()), 2),
                "  y sale este porcentaje de generosos")

    card["hour"] = card.pickup.dt.hour
    card["weekend"] = card.pickup.dt.dayofweek.ge(5).astype(int)
    card["rush_hour"] = ((~card.weekend.astype(bool))
                         & (card.hour.between(6, 9) | card.hour.between(16, 19))).astype(int)
    card["airport_flat"] = card.RatecodeID.eq(2).astype(int)
    card["speed"] = card.trip_distance / (card.duration / 60)
    print(f"  mediana {100 * card.rate.median():.2f} %, y {exact} viajes en el botón "
          f"exacto del 20 %")
    print(f"  generosos: {100 * card.generous.mean():.2f} %")
    return card


def split(card: pd.DataFrame, results: Results) -> tuple[pd.DataFrame, ...]:
    banner("4. Partición en tres")
    rest, test = train_test_split(card, test_size=0.20, random_state=SEED,
                                  stratify=card.generous)
    train, validation = train_test_split(rest, test_size=0.25, random_state=SEED,
                                         stratify=rest.generous)
    for name, part in [("train", train), ("validation", validation), ("test", test)]:
        results.put(f"split.{name}_rows", len(part))
    print(f"  entrenamiento {len(train)}   validación {len(validation)}   prueba {len(test)}")
    return train, validation, test


def lazy_baseline(validation: pd.DataFrame, results: Results) -> None:
    """The model that always answers no, which is the bar everything has to clear."""
    banner("5. El control: contestar siempre «no generoso»")
    accuracy = 1 - float(validation.generous.mean())
    results.put("lazy.validation_accuracy", round(accuracy, 4))
    results.put("lazy.recall", 0.0)
    results.put("lazy.auc", 0.5)
    print(f"  exactitud {accuracy:.4f}, sensibilidad 0,0000, AUC 0,5000")
    print(f"  cualquier modelo que no supere esto no ha aportado nada")


def candidates(train, validation, results: Results) -> dict:
    banner("6. Los candidatos, en validación")
    X, y = train[FEATURES], train.generous
    Xv, yv = validation[FEATURES], validation.generous
    models = {
        "logistica": LogisticRegression(max_iter=3000),
        "arbol": DecisionTreeClassifier(random_state=SEED),
        "bosque": RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
        "xgboost": XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1,
                                 eval_metric="logloss", random_state=SEED, n_jobs=1),
    }
    for name, model in models.items():
        model.fit(X, y)
        probability = model.predict_proba(Xv)[:, 1]
        decision = (probability >= 0.5).astype(int)
        results.put(f"candidates.{name}_auc", round(float(roc_auc_score(yv, probability)), 4))
        results.put(f"candidates.{name}_accuracy",
                    round(float(accuracy_score(yv, decision)), 4))
        results.put(f"candidates.{name}_recall", round(float(recall_score(yv, decision)), 4))
        print(f"  {name:11} AUC {roc_auc_score(yv, probability):.4f}   "
              f"exactitud {accuracy_score(yv, decision):.4f}   "
              f"sensibilidad {recall_score(yv, decision):.4f}")
    return models


def tune(train, validation, results: Results) -> dict:
    banner("7. Ajuste de perillas")
    X, y = train[FEATURES], train.generous
    Xv, yv = validation[FEATURES], validation.generous
    tuned = {}
    grids = {
        "bosque": (RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1),
                   {"max_depth": [3, 5, 8, None], "min_samples_leaf": [1, 20, 50],
                    "max_features": ["sqrt", 0.5]}),
        "xgboost": (XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=1),
                    {"max_depth": [2, 3, 5], "learning_rate": [0.02, 0.05, 0.1],
                     "n_estimators": [200, 500], "subsample": [0.8, 1.0]}),
    }
    for name, (estimator, grid) in grids.items():
        combinations = int(np.prod([len(v) for v in grid.values()]))
        started = time.perf_counter()
        search = GridSearchCV(estimator, grid, cv=4, scoring="roc_auc", n_jobs=-1).fit(X, y)
        elapsed = time.perf_counter() - started
        auc = roc_auc_score(yv, search.best_estimator_.predict_proba(Xv)[:, 1])
        results.put(f"tuning.{name}.combinations", combinations)
        results.put(f"tuning.{name}.seconds", round(elapsed, 1))
        results.put(f"tuning.{name}.best_params",
                    {k: str(v) for k, v in search.best_params_.items()})
        results.put(f"tuning.{name}.cv_auc", round(float(search.best_score_), 4))
        results.put(f"tuning.{name}.validation_auc", round(float(auc), 4))
        print(f"  {name:8} {combinations} combinaciones en {elapsed:4.0f} s   AUC {auc:.4f}")
        tuned[name] = search.best_estimator_
    return tuned


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


# ------------------------------------------------------------------------- figures

def figure_cash(df: pd.DataFrame, results: Results) -> None:
    """The trap: the meter never records a cash tip, so the whole file cannot be used."""
    style()
    names = {1: "Tarjeta", 2: "Efectivo", 3: "Sin cargo", 4: "Disputa"}
    kinds = sorted(names)
    zero = [results.data["payment"][f"type_{k}"]["zero_tip_pct"] for k in kinds]
    trips = [results.data["payment"][f"type_{k}"]["trips"] for k in kinds]

    fig, ax = plt.subplots(figsize=WIDE)
    bars = ax.bar([names[k] for k in kinds], zero,
                  color=[AZURITE if k == CARD else GOLD for k in kinds], width=0.55,
                  edgecolor=SURFACE, linewidth=1.2, zorder=2)
    for bar, value, count in zip(bars, zero, trips):
        ax.annotate(f"{decimal(value, 1)} %\n{thousands(count)} viajes",
                    xy=(bar.get_x() + bar.get_width() / 2, value), xytext=(0, 6),
                    textcoords="offset points", ha="center", fontsize=ANNOTATION,
                    weight="bold", color=GRAPHITE)
    ax.set_ylabel("Viajes con propina cero")
    ax.set_ylim(0, 122)
    ax.set_title("La propina en efectivo no se registra nunca", loc="left", fontsize=TITLE,
                 weight="bold", pad=16)
    ax.grid(axis="x", visible=False)

    excluded = results.data["payment"]["non_card_trips"]
    fig.text(0.005, -0.05,
             f"Qué mirar: las tres barras doradas están clavadas en el 100 %. No es que esa "
             f"gente no deje propina: es que el taxímetro solo apunta la de la tarjeta.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             f"Entrenar con el archivo entero le enseñaría al modelo «efectivo, luego no hay "
             f"propina», que es una propiedad de la máquina disfrazada de hallazgo. Se "
             f"apartan {thousands(excluded)} viajes y se dice por qué.",
             fontsize=CAPTION, color=MUTED)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_figure(fig, FIGURES, "01_efectivo.png")
    plt.close(fig)


def figure_buttons(card: pd.DataFrame, results: Results) -> None:
    """What is really being predicted: which preset the passenger pressed."""
    style()
    fig, ax = plt.subplots(figsize=WIDE)
    percentage = (100 * card.rate).clip(upper=40)
    ax.hist(percentage, bins=np.arange(0, 40.5, 0.5), color=GOLD, alpha=0.95,
            edgecolor=SURFACE, linewidth=0.6, zorder=2)
    ax.axvline(100 * DEFAULT_BUTTON, color=GRAPHITE, linewidth=1.8, zorder=5)
    ax.annotate("el corte: por encima\ndel botón por defecto",
                xy=(100 * DEFAULT_BUTTON, 0.93), xycoords=("data", "axes fraction"),
                xytext=(10, 0), textcoords="offset points", va="top", fontsize=ANNOTATION,
                weight="bold", color=GRAPHITE)
    for button in (25, 30):
        ax.axvline(button, color=HAIRLINE, linewidth=1.2, linestyle=(0, (4, 3)), zorder=3)
        ax.annotate(f"{button} %", xy=(button, 0.55), xycoords=("data", "axes fraction"),
                    xytext=(5, 0), textcoords="offset points", fontsize=CAPTION,
                    color=MUTED)
    ax.set_xlabel("Propina, en porcentaje de lo que costó el viaje")
    ax.set_ylabel("Número de viajes")
    ax.set_title("Lo que se predice no es cuánto da alguien: es qué botón pulsó", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="x", visible=False)

    target = results.data["target"]
    fig.text(0.005, -0.05,
             f"Qué mirar: las tres torres son los tres botones que ofrece la máquina. "
             f"{thousands(target['exactly_20pct'])} viajes dejan exactamente el 20,00 %, el "
             f"{decimal(target['exactly_20pct_share'], 1)} % de los pagos con tarjeta.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             f"Por eso el umbral es «pasar del 20 %» y no «dejar algo»: quien pulsa el botón "
             f"por defecto no decidió ser generoso. Y la mediana cae en "
             f"{decimal(target['median_rate'], 2)} %, o sea justo en ese botón: la mitad "
             f"de los pasajeros no elige, acepta.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "02_el_boton.png")
    plt.close(fig)


def figure_nothing_works(results: Results) -> None:
    """The result: every model decides exactly what the lazy one decides."""
    style()
    rows = [
        ("Contestar siempre\n«no generoso»", results.data["lazy"]["auc"],
         results.data["test"]["lazy"]["accuracy"], MUTED),
        ("Regresión logística", results.data["test"]["logistica"]["auc"],
         results.data["test"]["logistica"]["accuracy"], GOLD),
        ("Bosque ajustado", results.data["test"]["bosque"]["auc"],
         results.data["test"]["bosque"]["accuracy"], AZURITE),
        ("Refuerzo ajustado", results.data["test"]["xgboost"]["auc"],
         results.data["test"]["xgboost"]["accuracy"], AZURITE),
    ]
    fig, axes = plt.subplots(1, 2, figsize=WIDE)
    positions = np.arange(len(rows))[::-1]

    for ax, index, title, limits in [(axes[0], 1, "Aciertan todos lo mismo", (0.74, 0.79)),
                                     (axes[1], 2, "Y ordenan distinto", (0.48, 0.65))]:
        values = [row[index] for row in rows]
        bars = ax.barh(positions, values, color=[row[3] for row in rows], height=0.6,
                       edgecolor=SURFACE, linewidth=1.2, zorder=2)
        for bar, value in zip(bars, values):
            ax.annotate(decimal(value), xy=(value, bar.get_y() + bar.get_height() / 2),
                        xytext=(6, 0), textcoords="offset points", va="center",
                        fontsize=CAPTION, weight="bold", color=GRAPHITE)
        ax.set_xlim(*limits)
        ax.set_yticks(positions, [row[0] for row in rows] if ax is axes[0] else [])
        ax.set_title(title, loc="left", fontsize=PANEL_TITLE, weight="bold", pad=12)
        ax.grid(axis="y", visible=False)
    axes[0].set_xlabel("Exactitud en prueba")
    axes[1].set_xlabel("AUC en prueba")

    lazy = results.data["test"]["lazy"]["accuracy"]
    fig.text(0.005, -0.05,
             f"Qué mirar: en el panel izquierdo las cuatro barras miden lo mismo, "
             f"{decimal(lazy)}, porque **los cuatro modelos toman exactamente las mismas "
             f"decisiones** que contestar siempre que no.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.13,
             "En el derecho sí hay diferencias, y aquí los árboles por fin le ganan a la "
             "logística. Ordenan mejor los casos, y aun así ninguno señala a nadie con el "
             "umbral por defecto: es ganar una carrera que pierden todos.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "03_no_hay_senal.png")
    plt.close(fig)


def figure_importance(forest, results: Results) -> None:
    style()
    pairs = sorted(zip(FEATURES, forest.feature_importances_), key=lambda t: t[1])
    for name, value in pairs:
        results.put(f"importance.{name}", round(float(value), 4))

    fig, ax = plt.subplots(figsize=TALL)
    bars = ax.barh([LABELS[name] for name, _ in pairs], [value for _, value in pairs],
                   color=GOLD, height=0.62, edgecolor=SURFACE, linewidth=1.1, zorder=2)
    for bar, (_, value) in zip(bars, pairs):
        ax.annotate(decimal(value), xy=(value, bar.get_y() + bar.get_height() / 2),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=CAPTION, weight="bold", color=GRAPHITE)
    ax.set_xlim(0, max(value for _, value in pairs) * 1.22)
    ax.set_xlabel("Importancia dentro del bosque")
    ax.set_title("Un reparto de importancia sobre un modelo que no funciona", loc="left",
                 fontsize=TITLE, weight="bold", pad=16)
    ax.grid(axis="y", visible=False)

    top_name, top_value = pairs[-1]
    fig.text(0.005, -0.04,
             f"Qué mirar: {LABELS[top_name].lower()} se lleva {decimal(top_value)}, y es la "
             f"variable más importante de un modelo con un AUC de "
             f"{decimal(results.data['test']['bosque']['auc'])}.",
             fontsize=CAPTION, color=GRAPHITE, style="italic")
    fig.text(0.005, -0.12,
             "Ese es el aviso de la figura. La importancia siempre reparte el total entre "
             "las variables que hay, funcione el modelo o no, así que leerla sin mirar "
             "antes si el modelo acierta produce conclusiones sobre nada.",
             fontsize=CAPTION, color=MUTED)
    save_figure(fig, FIGURES, "04_importancia.png")
    plt.close(fig)


def main() -> None:
    results = Results(SLUG, "Automatidata: quién deja propina generosa, y si se puede saber",
                      COURSE)
    df, card = load(results)
    card = build_target(card, results)
    train, validation, test = split(card, results)
    lazy_baseline(validation, results)

    plain = candidates(train, validation, results)
    tuned = tune(train, validation, results)

    banner("8. El campeón, elegido en validación")
    Xv, yv = validation[FEATURES], validation.generous
    finalists = {"logistica": plain["logistica"], "bosque": tuned["bosque"],
                 "xgboost": tuned["xgboost"]}
    on_validation = {name: roc_auc_score(yv, model.predict_proba(Xv)[:, 1])
                     for name, model in finalists.items()}
    champion = max(on_validation, key=on_validation.get)
    for name, auc in on_validation.items():
        results.put(f"finalists.{name}_validation_auc", round(float(auc), 4))
    results.put("champion", champion)
    print(f"  campeón: {champion}")

    banner("9. La prueba, una sola vez")
    lazy_accuracy = 1 - float(test.generous.mean())
    results.put("test.lazy.accuracy", round(lazy_accuracy, 4))
    results.put("test.lazy.recall", 0.0)
    results.put("test.lazy.auc", 0.5)
    print(f"  {'siempre no':12} exactitud {lazy_accuracy:.4f}   sensibilidad 0.0000   "
          f"AUC 0.5000")
    for name, model in finalists.items():
        scores = measure(model, test[FEATURES], test.generous, results, f"test.{name}")
        print(f"  {name:12} exactitud {scores['accuracy']:.4f}   "
              f"sensibilidad {scores['recall']:.4f}   AUC {scores['auc']:.4f}")

    banner("10. El veredicto")
    # A model decides exactly like the lazy one when it never says yes, which is what a
    # recall of zero means. Comparing accuracies would be fragile: they are stored rounded
    # to four places and the lazy one is not, so an equality test on them silently fails.
    same = [name for name in finalists if results.data["test"][name]["recall"] == 0.0]
    results.put("verdict.models_deciding_like_the_lazy_one", same,
                "modelos que no señalan a nadie, o sea que deciden igual que contestar «no»")
    results.put("verdict.best_auc",
                round(max(results.data["test"][n]["auc"] for n in finalists), 4))
    results.put("verdict.signal_found", False,
                "¿hay señal utilizable en los datos del viaje?")
    print(f"  toman las mismas decisiones que el control: {', '.join(same)}")
    print(f"  el mejor AUC de todos: {results.data['verdict']['best_auc']}")

    banner("11. Figuras")
    figure_cash(df, results)
    figure_buttons(card, results)
    figure_nothing_works(results)
    figure_importance(tuned["bosque"], results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"  {figure.name}")

    results.write()


if __name__ == "__main__":
    main()
