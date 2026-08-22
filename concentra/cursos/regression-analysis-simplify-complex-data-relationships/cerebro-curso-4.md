# Cerebro: regresión y modelos de relación

Manual de operación, no material de estudio. Describe cómo trabajo la pregunta "¿cuánto
cambia esto cuando cambia aquello?": qué modelo elegir, qué supuestos comprobar, qué
reportar y qué trampas conozco. Pégalo como memoria y asume estas reglas sin preguntarlas.

Complementa al cerebro del curso anterior, que cubre comparar dos grupos. Este cubre
cuantificar relaciones.

## Qué resuelvo con esto

Poner número a una relación. No "el turno de día recupera más", sino "por cada gramo por
tonelada de colector la recuperación sube 0,4 puntos, con un intervalo de tanto a tanto".
La salida siempre es un coeficiente con su incertidumbre y una recomendación.

## Qué modelo usar

| La pregunta | El modelo |
|---|---|
| ¿Cuánto cambia Y cuando cambia una X numérica? | Regresión lineal simple |
| ¿Y cuando cambian varias X a la vez? | Regresión lineal múltiple |
| ¿Difieren las medias de tres grupos o más? | ANOVA de un factor |
| ¿Y con dos factores de agrupación? | ANOVA de dos factores |
| ¿Están relacionadas dos variables categóricas? | Chi cuadrado de independencia |
| ¿Coincide un reparto con el esperado? | Chi cuadrado de bondad de ajuste |
| ¿Cuál es la probabilidad de un sí o un no? | Regresión logística binomial |

**Nunca encadenes pruebas t para comparar tres grupos.** Cada prueba tiene su propio riesgo
de falso positivo y se acumulan: con tres comparaciones al 5 % el riesgo real ronda el
14 %. Para eso existe ANOVA.

## El procedimiento, en este orden

1. **Dibujar los datos antes de modelar.** Un diagrama de dispersión enseña si la relación
   es siquiera aproximadamente recta. Ajustar una recta a algo curvo no da error.
2. **Ajustar el modelo** y leer los coeficientes, no solo el R².
3. **Comprobar los supuestos** con la lista de abajo. Este paso es el que casi todo el
   mundo se salta.
4. **Mirar los residuos dibujados**, que es donde aparecen los problemas.
5. **Reportar** el bloque completo.
6. **Traducir a una recomendación** con unidades reales.

## Los supuestos, y cómo se comprueba cada uno

| Supuesto | Qué significa | Cómo se comprueba |
|---|---|---|
| Linealidad | La relación es aproximadamente una recta | Dispersión de X contra Y |
| Independencia | Cada observación es su propio caso | Cómo se recogieron los datos, no una prueba |
| Normalidad de los residuos | Los errores se reparten en campana | Histograma o gráfico cuantil de los residuos |
| Varianza constante | El error no crece con la predicción | Residuos contra valores predichos: no debe verse un embudo |
| Sin multicolinealidad | Las X no se explican entre sí | Correlación entre variables, o el factor de inflación de varianza |

**La normalidad se exige de los residuos, no de los datos.** Es el malentendido más común
del tema.

## Lo que siempre se reporta

| Elemento | Por qué |
|---|---|
| El coeficiente de cada variable, **con sus unidades** | Es el resultado: cuánto sube Y por unidad de X |
| Su intervalo de confianza | Si cruza el cero, esa variable no está demostrada |
| R², y R² ajustado en modelos múltiples | Cuánta variación explica el modelo |
| Número de observaciones | Determina cuánto vale todo lo anterior |
| Los supuestos comprobados, uno por uno | Sin esto el modelo no es defendible |
| Limitaciones | El rango de validez y los factores no medidos |

## Trampas que ya conozco

- **Un R² alto no significa modelo bueno.** Puede venir de una relación curva mal ajustada,
  de valores extremos que tiran de la recta, o de meter variables sin sentido.
- **El R² siempre sube al añadir variables**, aunque sean ruido. Por eso en modelos
  múltiples se mira el **R² ajustado**, que penaliza las variables de más.
- **Extrapolar fuera del rango medido no vale.** Si dosificaste entre 10 y 50 g/t, el
  modelo no dice nada sobre 200 g/t, y la recta seguirá dándote un número igualmente.
- **La paradoja de Simpson.** Una relación puede invertir su signo al mirar los grupos por
  separado. Si hay una variable de agrupación conocida, hay que meterla en el modelo.
- **Variables muy correlacionadas entre sí** vuelven los coeficientes inestables y sin
  interpretación individual, aunque el modelo prediga bien.
- **Correlación no es causa**, y una regresión sobre datos observacionales tampoco lo es.
  Lo que se afirma es asociación, salvo que haya asignación aleatoria.
- **En logística el coeficiente no es una probabilidad.** Está en escala de log-odds, y hay
  que exponenciarlo para leerlo como razón de momios.
- **Chi cuadrado necesita frecuencias esperadas suficientes.** Con esperados por debajo de
  5 en muchas casillas el resultado deja de ser fiable.

## Cómo se lee un coeficiente

Para una recta `recuperación = 66 + 0,4 × dosis`:

- El **66** es el intercepto: lo que predice el modelo con dosis cero. Solo tiene sentido
  si el cero está dentro del rango medido, y muchas veces no lo está.
- El **0,4** es la pendiente: por cada gramo por tonelada más de colector, la recuperación
  sube 0,4 puntos. **Esa frase, con sus unidades, es el resultado del análisis.**

En logística, un coeficiente de 0,7 significa que la razón de momios se multiplica por
`e^0,7`, o sea por 2, cada vez que la variable sube una unidad.

## Lo que aprendí haciendo los tres proyectos

Números reales, de mis propios modelos, para calibrar expectativas en vez de citar reglas
generales.

- **Comprueba si la variable existirá cuando haya que predecir.** En el modelo de tarifas de
  taxi, la distancia recorrida explicaba casi todo y no existe al reservar. Quitarla bajó el
  R² de 0,95 a 0,67, y ese 0,67 es el número real: sobre la prueba, **RMSE de 5,93 $** y
  error absoluto medio de 3,21 $, con cuatro variables (distancia y duración medias de la
  ruta, hora punta y tarifa plana de aeropuerto).
- **La fuga de información se mide, no se discute.** Calcular medias por grupo sobre todos
  los datos en vez de solo sobre el entrenamiento infló el R² en **0,2101** y escondió 2,40
  dólares de error.
- **Un error medio puede esconder dos poblaciones.** El mismo modelo se equivocaba 2,42
  dólares en rutas conocidas y 11,11 en rutas nuevas. Siempre parto el error por algún
  criterio antes de reportarlo.
- **Con clases desbalanceadas, la exactitud es ruido.** Un modelo de abandono con 82,3 % de
  acierto y 8,2 % de detección: contestar siempre "se queda" acertaba el 82,26 %.
- **Un modelo mal calibrado se parece a un modelo malo.** Ese mismo tenía AUC de 0,737. El
  fallo era el umbral: bajarlo a 0,20 llevó la detección al 62,3 %.
- **Comprueba que el umbral hace algo.** En un caso las probabilidades predichas cayeron en
  dos montones sin nada entre 0,28 y 0,56, así que cualquier corte intermedio daba el mismo
  resultado. El modelo se había reducido a una regla binaria.
- **Un predictor fuerte en crudo puede evaporarse dentro del modelo.** Un grupo que abandonaba
  al 7,56 % frente al 19,88 % acabó con un p de 0,952, porque otra variable ya recogía ese
  efecto.
- **Escala los coeficientes a unidades imaginables.** Razones de momios de 1,000 con
  intervalos de 1,000 a 1,000 y valores p de 3e-48: el efecto era real y la unidad, absurda.
  Por año en vez de por día, la razón pasó a 0,864.
- **Antes de tirar filas sin etiqueta, compara ese grupo con el resto.** Con 700 ausentes, la
  mayor diferencia de medianas era del 6,2 % y el reparto por dispositivo idéntico, así que
  excluirlos era inocuo. Si no lo hubiera sido, habría cambiado a quién describe el modelo.
- **Busca divisiones por cero en las variables derivadas.** 983 usuarios con cero días
  conduciendo habrían metido infinitos en el ajuste sin un solo aviso.

## Vocabulario, español e inglés

| Español | Inglés |
|---|---|
| Regresión lineal simple / múltiple | simple / multiple linear regression |
| Pendiente e intercepto | slope and intercept |
| Residuo | residual |
| Mínimos cuadrados | ordinary least squares (OLS) |
| Bondad de ajuste | goodness of fit |
| R² ajustado | adjusted R-squared |
| Varianza constante | homoscedasticity |
| Multicolinealidad | multicollinearity |
| Variable de confusión | confounder |
| Razón de momios | odds ratio |
| Análisis de varianza | analysis of variance (ANOVA) |
| Chi cuadrado de independencia | chi-squared test of independence |
