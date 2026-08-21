# TikTok, Curso 4: documento de estrategia PACE

**Escenario.** TikTok quiere reducir la cola de reclamaciones de usuarios que esperan
revisión. El objetivo final, que es el Curso 5, es clasificar automáticamente si un vídeo
contiene una reclamación o una opinión. Este proyecto es el paso previo: construir una
regresión logística sobre una variable binaria conocida, `verified_status`, y aprender qué
se puede y qué no se puede esperar de ella.

**Datos.** `tiktok_dataset_raw.csv`, 19.382 vídeos y 12 columnas.

---

## Plan

**La pregunta:**

> ¿Se puede saber si una cuenta está verificada mirando el vídeo que publicó?

**El aviso que hay que dar antes de empezar**, porque decide cómo se mide todo:

De los 19.084 vídeos completos, **17.884 son de cuentas sin verificar y 1.200 de cuentas
verificadas**. Es un 93,7 % contra un 6,3 %. Un modelo que conteste siempre "no está
verificada" acierta el **93,7 % de las veces y no detecta ni una sola cuenta verificada**.
Con ese reparto, la exactitud deja de ser una métrica y pasa a ser una trampa.

**Qué se entrega:** un modelo con sus razones de momios, la matriz de confusión, y la
lectura honesta de para qué sirve y para qué no.

## Analyze

**Limpieza.** 298 filas tienen datos ausentes, siempre en el mismo bloque de siete
columnas. Se eliminan y quedan 19.084. No hay duplicados.

**Dónde está la señal, que no es donde suele decirse.** El material del curso apunta a la
duración del vídeo. En estos datos la duración media es de **31,77 segundos en las cuentas
verificadas y 32,47 en las no verificadas**: siete décimas de segundo de diferencia sobre
vídeos de medio minuto.

La señal de verdad es qué publica cada tipo de cuenta:

| | Reclamaciones | Opiniones |
|---|---|---|
| Cuentas no verificadas | 52,6 % | 47,4 % |
| Cuentas verificadas | 17,4 % | **82,6 %** |

La proporción se da la vuelta. Las cuentas verificadas publican opiniones cuatro de cada
cinco veces.

**Correlación entre los contadores.** Las cinco medidas de interacción (visualizaciones,
me gusta, compartidos, descargas y comentarios) están correlacionadas entre sí por encima
de 0,55, y las de me gusta con descargas llegan a 0,82. Sus factores de inflación de la
varianza van de 3,8 a 7,8. **Ninguno pasa de 10**, así que quedarse con uno solo fue un
criterio y no una obligación del umbral.

## Construct

**Equilibrar.** La clase mayoritaria se submuestrea hasta igualar a la minoritaria: 1.200 y
1.200, o sea 2.400 filas, descartando 16.684. Es la forma de impedir que el modelo gane
diciendo siempre que no. **Como consecuencia, la exactitud que se reporta se compara contra
el 50 % de una moneda, no contra el 93,7 % del dataset original.**

**Codificación.** Una columna de unos y ceros por categoría menos una: `is_claim` con la
opinión como referencia, y `banned` y `under_review` con la cuenta activa como referencia.

**Variables del modelo:** duración del vídeo, si es reclamación, las dos de estado del
autor, y las visualizaciones.

**Ajuste.** Regresión logística binomial por máxima verosimilitud, sobre 1.800 filas de
entrenamiento, con 600 reservadas para la prueba y el reparto de clases mantenido en las
dos partes.

## Execute

**De las cinco variables, una sola tiene efecto demostrado:**

| Variable | Razón de momios | Intervalo del 95 % | p |
|---|---|---|---|
| **El vídeo es una reclamación** | **0,20** | 0,13 a 0,29 | 1,9e-16 |
| Autor en revisión | 0,78 | 0,54 a 1,13 | 0,196 |
| Autor expulsado | 0,76 | 0,48 a 1,20 | 0,234 |
| Cada segundo de vídeo | 1,00 | 0,99 a 1,00 | 0,63 |
| Cada visualización | 1,00 | 1,00 a 1,00 | 0,886 |

Los cuatro últimos intervalos cruzan el 1, que es la línea de no efecto cuando se habla de
momios. **Solo la primera fila dice algo:** publicar una reclamación multiplica por 0,20
los momios de ser una cuenta verificada, o sea que una cuenta verificada tiene la quinta
parte de momios de estar publicando una reclamación.

**Clasificación, sobre las 600 cuentas de prueba:**

| Métrica | Valor |
|---|---|
| Exactitud | 0,682 |
| Precisión | 0,641 |
| Sensibilidad | 0,827 |
| F1 | 0,722 |
| AUC | 0,697 |

**El hallazgo del proyecto.** El umbral de clasificación, que el módulo 5 presenta como una
decisión de negocio, **aquí no decide nada**. Las probabilidades que predice el modelo van
de 0,204 a 0,651 y caen en dos grupos, uno alrededor de 0,25 y otro alrededor de 0,64, con
**cero casos entre 0,28 y 0,56**. Mover el corte dentro de esa banda produce exactamente
las mismas 387 cuentas marcadas y los mismos 248 aciertos.

La razón es que el modelo descansa en una sola variable binaria, así que en la práctica se
ha convertido en la regla "¿el vídeo es una reclamación?" con dos pasos intermedios.

**Recomendación.** Con un pseudo R² de 0,1046 y un AUC de 0,697, esto **no es un
clasificador que se pueda poner a decidir solo**. Sirve para dos cosas, y las dos son
reales: confirma que el tipo de contenido, y no la actividad de la cuenta, es lo que separa
a los dos grupos, y deja montada la tubería completa para el Curso 5, donde el objetivo
pasa a ser la variable que aquí resultó ser la única que importa.
