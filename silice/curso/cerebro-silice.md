# Cerebro: predicción de SiO2 en flotación de hierro

Manual de operación del proyecto. No es un resumen de las lecciones: son las cifras, los
umbrales y las decisiones que cambian cómo se trabaja sobre estos datos. Pensado para
pegarse en la memoria de un asistente.

## El problema

Predecir el `% Silica Concentrate` (sílice en el concentrado) de una planta de flotación
inversa de hierro, en tiempo real, antes de que llegue el análisis de laboratorio.

Dataset: "Quality Prediction in a Mining Process" (Kaggle). 737.453 filas x 24 columnas,
marzo a septiembre de 2017. Archivo en `data/MiningProcess_Flotation_Plant_Database.csv`,
183 MB, fuera de git.

## El veredicto

Con estos datos, ningún modelo supera de forma significativa al baseline de persistencia.
Recomendación: **no desplegar** machine learning para esta tarea.

| Horizonte | Persistencia (R²) | Aporte del modelo |
|---|---|---|
| 1 h | 0,632 | +0,009 |
| 3 h | 0,271 | menos de +0,02 |
| 5 h y más | negativo | ninguno |
| 12 h | negativo | el modelo del nivel llega a −0,85 |

Única señal propia del modelo: predecir el **cambio** en vez del nivel da R² +0,175 a 12 h.

## Tres intentos de tumbar el veredicto, y qué midió cada uno

Medidos en `src/experiment_verdict.py`. El veredicto sobrevive a los tres.

| Sospecha | Resultado |
|---|---|
| El modelo estaba congelado dos meses, sin reentrenar | Reentrenar cada 1, 3, 7, 14 o 28 días deja el aporte entre −0,001 y +0,009. No cambia nada |
| Entrenar solo con lo reciente (ventana móvil) | **Empeora**: de −0,012 a −0,040 según la ventana |
| Un modelo por estado operativo, ya que la planta cambió de régimen | **Empeora**: R² 0,601 contra 0,641 del modelo único. Partir el entrenamiento cuesta más de lo que arregla |

**Y una corrección al módulo 6.** El clasificador de fuera de especificación se comparó contra
"siempre en spec", que no atrapa nada. Contra el baseline correcto:

| Aviso | Acierto | Precisión | Atrapa | Falsas alarmas | Se escapan |
|---|---|---|---|---|---|
| Siempre en spec | 0,810 | - | 0 de 182 | 0 | 182 |
| **Persistencia** | **0,912** | 0,769 | **140** | 42 | 42 |
| Clasificador | 0,901 | 0,813 | 113 | 26 | 69 |

La persistencia atrapa 27 problemas más y levanta 16 falsas alarmas más. Para una planta,
mandar concentrado fuera de especificación suele costar más que una comprobación de más, así
que la persistencia también gana aquí.

## Reglas de trabajo sobre estos datos

1. **Separación temporal siempre.** Corte el 1 de agosto de 2017: entrenamiento 563.482
   filas (77 %, marzo a julio), prueba 172.800 (23 %, agosto y septiembre). Una separación
   aleatoria da R² alrededor de 0,9 y es fuga, no habilidad.
2. **Excluir `% Iron Concentrate`.** Es complementaria de la sílice (r = −0,80) y sale del
   mismo análisis de laboratorio, una hora después. Usarla es fuga de la respuesta.
3. **El baseline se mide antes de celebrar nada.** Persistencia a 1 h ya vale 0,632. Toda
   métrica se reporta como diferencia contra ella.
4. **Conservar las dos columnas de alimentación** (`% Iron Feed`, `% Silica Feed`): su
   importancia es casi cero, pero no dañan y su ausencia se notaría en la interpretación.
5. **Validación cruzada temporal, no k-fold aleatorio.** El corte único era optimista: la
   validación cruzada honesta dio R² −0,13 donde el corte único daba 0,04.

## Cicatrices del archivo, medidas

- **1.171 filas duplicadas** en 15 marcas de tiempo.
- **Hueco de 13 días**, del 16 al 29 de marzo de 2017.
- **Ensayo de hierro en alimentación congelado** del 13 de mayo al 15 de junio (792 horas)
  clavado en 64,03. El laboratorio no actualizó el valor; no es señal física. Afecta al
  19,4 % de las filas, pero solo a 2 columnas de alimentación: proceso y objetivo siguen
  vivos, así que esas filas **no se tiran**.
- **Frecuencias distintas por columna.** Alimentación: 1 valor único por hora. Proceso
  (pH, flujos, aire, niveles): 150 a 180 por hora, sensor cada 20 s. Objetivo
  (`% Silica Concentrate`): unos 14 por hora. La creencia de que el objetivo se repite 180
  veces por hora es falsa y se comprobó.
- **Almidón por debajo de 100** en 3.976 filas.
- 0 valores faltantes, lo cual es sospechoso en datos de planta: el archivo viene
  preprocesado.

## Resultados por técnica, en orden

| Módulo | Técnica | Resultado |
|---|---|---|
| 2 | Árbol de decisión, profundidad 3 | RMSE 1,11 · R² 0,04 (baseline tonto: RMSE 1,14) |
| 2 | Random forest podado | empata al árbol, R² alrededor de 0,04 |
| 3 | Regresión lineal | R² 0,01 |
| 3 | Lineal regularizada (Ridge/Lasso) | R² 0,06 |
| 4 | Validación cruzada honesta | R² −0,13, el corte único era optimista |
| 5 | Variables con memoria (retardos, medias móviles) | R² 0,12 a 0,49 |
| 5 | Gradient boosting sobre esas variables | R² 0,64, el mejor del proyecto |
| 6 | Clasificación fuera de especificación (umbral 3,5 %) | acierto 0,90 frente a 0,81 del baseline · precisión 0,81 · exhaustividad 0,62 |
| 7 | Persistencia bien medida | 0,632, de donde el aporte real del ML es +0,009 |
| 8 | Modelo contra persistencia a 1, 3, 6 y 12 h | el ML no gana en ningún horizonte |
| 9 | k-medias, k = 3 por el codo | 3 estados operativos |
| 9 | PCA | 46 % de varianza en 2 ejes. CP1 = aireación (31 %), CP2 = niveles (15 %) |
| 10 | Red neuronal (MLPRegressor) | R² 0,165, la peor de todo el proyecto |
| 10 | PyTorch en la RTX 5060 | R² 0,190. La GPU acelera 32 veces (541 ms a 17 ms), no mejora. El apunte viejo decía 34 veces con 580 ms; al volver a medirlo salen 541 ms |

## Los tres estados de la planta (k-medias)

| Estado | Carácter | SiO2 medio |
|---|---|---|
| 0 | aireación alta, marcha buena | 1,85 |
| 1 | aireación baja | 2,60 |
| 2 | peleando: alimentación sucia, reactivo al máximo | 2,46 |

**El estado 1 domina marzo y abril y después desaparece.** La planta cambió de forma de
operar en abril, y eso explica la deriva que arrastran los módulos 2 a 8.

## Deriva medida (módulo 10)

RMSE mensual del modelo en producción simulada: 0,44 en junio, 0,65 en agosto, 0,76 en
septiembre. Cruza el umbral de +30 % sobre la referencia en septiembre, que es cuándo habría
que reentrenar.

## Señal real, dónde está

Consistente en correlación, árbol y bosque: **aire de las columnas 3 y 4** y **amina**. La
amina sale con signo invertido (r = +0,16) por el lazo de control: cuando la sílice sube, el
operador dosifica más. Correlación no es causa, y aquí el control la invierte.

`% Silica Feed` frente al objetivo: r = +0,07. El control de la planta borra la relación que
la fisicoquímica haría esperar.

## Entorno

- `.venv` (Python 3.14): pandas, numpy, matplotlib, scikit-learn 1.9.0, shap 0.52.
- `.venv-gpu` (Python 3.12 + PyTorch nightly cu128) solo para el apunte de GPU.
- Los ejecutables sueltos de `.venv/Scripts` quedaron con rutas viejas tras un traslado:
  usar `.venv\Scripts\python.exe -m pip`, no `pip.exe`.
- Consola cp1252: forzar UTF-8 en las salidas de Python.
