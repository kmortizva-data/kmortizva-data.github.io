# Cerebro: aprendizaje automático, árboles y agrupamiento

Manual de operación, no material de estudio. Describe cómo trabajo la pregunta "¿puedo
predecir esto sobre datos que nunca he visto?": cómo parto los datos, qué modelo pruebo,
qué perillas toco, qué reporto y qué trampas conozco. Pégalo como memoria y asume estas
reglas sin preguntarlas.

Complementa al cerebro del curso anterior, que cubre modelos que **explican**. Este cubre
modelos que **aciertan**, y la disciplina que hace falta cuando dejas de exigir que el
modelo se explique.

## Qué resuelvo con esto

Predecir una etiqueta o un número sobre casos nuevos, y saber con qué margen. La salida
siempre es: el modelo elegido **entre varios candidatos**, su rendimiento medido sobre datos
apartados desde el principio, y la comparación contra algo simple.

**Si el modelo complicado no le gana al simple, gana el simple.** No es humildad: un modelo
simple se explica, se defiende y se arregla; uno complicado hay que mantenerlo.

## Cómo se parten los datos, y por qué en tres

| Parte | Para qué | Cuándo se toca |
|---|---|---|
| Entrenamiento | Que el modelo aprenda | Todo el rato |
| Validación | Elegir entre candidatos y afinar perillas | Muchas veces, y por eso se gasta |
| **Prueba** | Decir cuánto acierta de verdad | **Una vez, al final** |

La razón de que sean tres y no dos: cada vez que miras un resultado y cambias algo, le
filtras información a ese conjunto. Después de veinte pruebas, tu conjunto de validación ya
no es una medida independiente; es parte del ajuste. **La prueba es la única cifra que se
publica**, y solo vale mientras no la hayas mirado antes.

La validación cruzada de *k* pliegues hace lo mismo sin apartar un trozo fijo: parte el
entrenamiento en *k* partes, entrena *k* veces dejando una fuera cada vez, y promedia. Se
usa cuando hay pocos datos, y su desviación importa tanto como su media.

## Qué modelo usar

| La pregunta | El modelo |
|---|---|
| ¿Sí o no, y quiero entender por qué? | Regresión logística *(Curso 4)* |
| ¿Sí o no, con muchas variables y sin exigir explicación? | Árbol, bosque aleatorio o refuerzo por gradiente |
| ¿Sí o no, con variables casi independientes y pocos datos? | Naive Bayes |
| ¿Cuánto vale este número? | Regresión lineal *(Curso 4)*, o un bosque de regresión |
| ¿Qué grupos hay aquí, si nadie los ha marcado? | K-medias |

**Empieza siempre por el simple.** Es la referencia contra la que se mide todo lo demás, y a
veces gana.

## Las perillas de cada familia

| Modelo | Perillas que importan | Qué controlan |
|---|---|---|
| Árbol | `max_depth`, `min_samples_leaf`, `min_samples_split` | Cuánto puede complicarse antes de memorizar |
| Bosque aleatorio | Las del árbol, más `n_estimators` y `max_features` | Cuántos árboles y cuánta variedad entre ellos |
| Refuerzo por gradiente | `learning_rate`, `n_estimators`, `max_depth` | Cuánto corrige cada árbol y cuántas correcciones |

**Un bosque aleatorio y un refuerzo por gradiente no son lo mismo aunque los dos sean muchos
árboles.** El bosque entrena árboles independientes sobre muestras distintas y promedia: cada
uno se equivoca por su lado y los errores se cancelan. El refuerzo entrena en cadena, y cada
árbol se dedica a lo que el anterior falló. Por eso el refuerzo suele acertar más y se
sobreajusta más fácil.

## Ojo con los valores por defecto

Dos casos comprobados en este proyecto, y los dos cambian el resultado entero:

- El `HistGradientBoostingClassifier` de scikit-learn trae `min_samples_leaf=20`. Sobre pocas
  filas **no parte nada** y contesta la clase mayoritaria. Sobre el ejemplo de diez lotes del
  módulo 4, xgboost acierta 9 y él 6; bajando la hoja a 5, los dos aciertan 9.
- `CategoricalNB` trae suavizado `alpha=1`. Sobre el ejemplo de ocho lotes del módulo 2, la
  probabilidad a mano es 0,9 exacta y con el suavizado sale 0,8.

Ninguno de los dos es un error de la librería: son decisiones razonables para miles de filas.
**Un valor por defecto es una decisión que alguien tomó sin conocer tus datos.**

## K-medias, y la pregunta difícil

El algoritmo es simple: elige *k* centros, asigna cada punto al más cercano, mueve cada
centro al promedio de los suyos, repite hasta que no se muevan. Lo difícil es *k*.

| Medida | Qué mide | Cómo se lee |
|---|---|---|
| Inercia | Suma de distancias al cuadrado a su centro | Siempre baja al subir *k*: se busca **el codo**, donde deja de bajar rápido |
| Coeficiente de silueta | Cuánto mejor encaja cada punto en su grupo que en el vecino | Va de −1 a 1; **se busca el máximo** |

**La inercia sola no elige *k***, porque con *k* igual al número de puntos vale cero. Se
miran las dos, y si discrepan se dice.

Tres cosas que k-medias exige y que se olvidan: **escalar las variables** (si no, la que
tenga números grandes manda), que los grupos son esféricos y de tamaño parecido, y que el
resultado depende del arranque, así que se repite varias veces.

## Qué reportar siempre

1. El reparto de los datos, con los tamaños de las tres partes.
2. **La tabla de todos los candidatos**, no solo del ganador.
3. Las perillas probadas y la elegida, con cuánto mejoró respecto a no ajustar nada.
4. Sobre la prueba: exactitud, precisión, sensibilidad, F1 y AUC. **Nunca la exactitud
   sola** si las clases están desbalanceadas.
5. La importancia de las variables.
6. **La comparación contra el modelo simple.**

## Las trampas

- **Fuga de información.** Una variable que no existiría en el momento de predecir, o una
  transformación calculada sobre el conjunto entero antes de partir. Infla el resultado y
  solo se descubre en producción.
- **Mirar la prueba antes de tiempo.** En cuanto la miras y cambias algo, deja de medir.
- **Exactitud con clases desbalanceadas.** Con un 95 % de una clase, contestar siempre esa
  acierta el 95 % y no detecta a nadie.
- **Equilibrar antes de partir.** Si duplicas filas de la clase minoritaria y luego partes,
  la misma fila acaba en entrenamiento y en prueba. Se parte primero.
- **Casi perfecto.** Un AUC por encima de 0,99 es una fuga hasta que se demuestre lo
  contrario, o una señal enorme que ya conocías.
- **Confundir importancia con causa.** Que una variable pese mucho en el bosque no dice que
  moverla cambie el resultado.
- **Sobreajustar por ajustar.** Probar mil combinaciones y quedarte con la mejor sobre
  validación es elegir el ruido. Por eso la prueba se aparta.

## Sesgo y equidad, que no es un apéndice

Un modelo aprende del pasado, así que **repite el pasado**. Si los datos históricos recogen
una decisión sesgada, el modelo la aprende y la aplica más rápido y a más gente.

Tres preguntas antes de desplegar cualquier modelo que decida sobre personas: **de quién son
los datos y quién falta**; **qué cuesta cada tipo de error y a quién le cuesta**; y **si el
afectado puede saber por qué se decidió eso**. Un modelo que no puede contestar la tercera
no debería decidir solo.

## Casos de referencia, con números reales

Tres proyectos propios sobre los mismos archivos de los cursos anteriores, y los tres
enseñan lo mismo desde ángulos distintos: **la comparación contra algo simple decide el
proyecto**. Todos los números salen de `projects/curso5/<caso>/04_reports/model_results.json`,
y la prueba se miró una sola vez.

| Caso | El control, fijado antes | El campeón sobre la prueba | Veredicto |
|---|---|---|---|
| **Automatidata**, ¿quién deja propina generosa? | Contestar siempre «no generoso»: exactitud 0,7688, sensibilidad 0, AUC 0,5. Generosos = 23,11 % | Refuerzo ajustado (36 combinaciones): exactitud 0,7708, **sensibilidad 0,0128**, AUC 0,6104. La logística y el bosque decidieron **exactamente como el perezoso** | No hay señal: el archivo describe el viaje y la propina es una decisión personal. Decirlo con pruebas fue el entregable |
| **TikTok**, ¿reclamación u opinión? | Un árbol de **una pregunta sobre una columna** (más de 10.031 vistas): exactitud 0,9961 en validación | Bosque ajustado de 300 árboles con nueve variables: exactitud **0,9958**, la misma, AUC 0,9986 frente a 0,9958 | Nueve variables y trescientos árboles aportaron **+0,0000** de exactitud. La opinión más vista tiene 9.998 visualizaciones y la reclamación menos vista 1.049: las clases están separadas por una línea, y eso es una marca de datos sintéticos |
| **Waze**, ¿le gana un árbol a la logística? | El modelo del Curso 4 sobre los mismos 3.575 usuarios de prueba: AUC 0,7368, sensibilidad 0,0820 | Logística 0,7379; bosque ajustado 0,7318; refuerzo 0,7348. 88 combinaciones en total. Ajustar el bosque le dio +0,0276 en validación y se quedó a 0,0019 de la logística | Los árboles no ganan. Y k-medias sobre los mismos usuarios dio la mejor silueta en 0,2588 con dos grupos que abandonan al 17,29 % y al 19,05 %: un continuo, no segmentos |

Las tres particiones fueron 60/20/20 estratificadas, con la prueba apartada desde el
principio y las perillas elegidas solo contra validación.

## Vocabulario español e inglés

| Español | Inglés |
|---|---|
| Aprendizaje supervisado / no supervisado | Supervised / unsupervised learning |
| Variable construida | Engineered feature |
| Clases desbalanceadas | Imbalanced classes |
| Validación cruzada de *k* pliegues | *k*-fold cross-validation |
| Perilla, hiperparámetro | Hyperparameter |
| Búsqueda en rejilla | Grid search |
| Árbol de decisión | Decision tree |
| Impureza de Gini | Gini impurity |
| Bosque aleatorio | Random forest |
| Agregación por remuestreo | Bootstrap aggregation, bagging |
| Refuerzo por gradiente | Gradient boosting |
| Importancia de variables | Feature importance |
| Agrupamiento | Clustering |
| Inercia | Inertia |
| Coeficiente de silueta | Silhouette coefficient |
| Sobreajuste | Overfitting |
| Fuga de información | Data leakage |
