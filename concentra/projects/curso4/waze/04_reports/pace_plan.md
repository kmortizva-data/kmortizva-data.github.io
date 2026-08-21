# Waze, Curso 4: documento de estrategia PACE

**Escenario.** Waze quiere crecer, y para eso necesita que la gente no se vaya. Se pide un
modelo que prediga qué usuario está a punto de abandonar la aplicación, para poder actuar
antes.

**Datos.** `waze_dataset.csv`, 14.999 usuarios y 13 columnas.

---

## Plan

**La pregunta:**

> ¿Se puede saber quién va a abandonar la aplicación mirando cómo la usa?

**Lo que se espera, dicho antes de ajustar nada para que no se pueda ajustar después.**
Solo el 17,74 % de los usuarios abandona, las variables disponibles describen
comportamiento y no causas, y en el archivo no hay ni un dato sobre **por qué** se fue
nadie. Con eso, lo probable es que el modelo se deje escapar a la mayoría de los que se
van. Si ocurre, se reporta como resultado, igual que el Curso 3 reportó que en Waze no
había diferencia entre dispositivos.

## Analyze

**Las 700 etiquetas ausentes, que son el 4,7 %.** No se tiran sin mirarlas: excluir a un
grupo solo es inocuo si ese grupo se parece al resto. Comparando medianas, que no se mueven
con los valores extremos de los que este archivo está lleno:

| Variable | Diferencia de la mediana |
|---|---|
| Sesiones | 0,0 % |
| Días conduciendo | 0,0 % |
| Trayectos | −1,0 % |
| Kilómetros | −2,2 % |
| Días activo | −6,2 % |

La mayor diferencia es del 6,2 %, y el reparto de dispositivo es prácticamente idéntico:
**63,9 % de iPhone entre los que no tienen etiqueta y 64,5 % entre el resto**. Se pueden
excluir. Quedan 14.299 usuarios, de los que **2.536 abandonan**.

**La división por cero que había escondida.** 983 usuarios condujeron cero días. Calcular
kilómetros por día conducido sobre ellos da infinito, que entra en el modelo sin avisar y
rompe el ajuste. Como no condujeron nada, su tasa es cero.

**Multicolinealidad, y aquí sí es grave.** Sesiones y trayectos correlacionan a **0,997**, y
días activo con días conduciendo a **0,948**. Sus factores de inflación de la varianza son
de **159,3 y 159,1**, muy por encima del umbral de 10. No pueden estar las dos parejas
dentro. Se quedan trayectos y días activo; salen sesiones, días conduciendo y kilómetros
totales. En el modelo final ninguna variable pasa de 1,8.

## Construct

**Variables construidas:** kilómetros por día conducido, conductor profesional (60 o más
trayectos en 15 o más días, la definición del propio curso) y el dispositivo como columna
de unos y ceros.

Un dato de la exploración que luego resulta ser una trampa: los 2.488 conductores
profesionales abandonan al **7,56 %** frente al **19,88 %** del resto. Parece un predictor
potente. No lo es, y por qué no lo es está en el resultado.

**Ajuste.** Regresión logística binomial sobre 10.724 usuarios de entrenamiento, con 3.575
reservados y el reparto de clases mantenido en las dos partes.

## Execute

**Los coeficientes, escalados a unidades que se puedan imaginar.** Por unidad suelta casi
todos salen 1,000 y no dicen nada, aunque su valor p sea de 3e-48: el problema es la
unidad, no el efecto.

| Variable | Razón de momios | p |
|---|---|---|
| **Cada año más de antigüedad** | **0,864** | 3,09e-48 |
| **Cada día de actividad más** | **0,901** | 5,03e-139 |
| Cada 10 trayectos más | 1,016 | 0,00132 |
| Cada hora más al volante | 1,004 | 9,46e-05 |
| Cada 10 sesiones históricas | 1,003 | 0,247 |
| Cada 100 km por día conducido | 1,002 | 0,497 |
| Usar iPhone | 1,017 | 0,773 |
| Ser conductor profesional | 0,993 | 0,952 |

**Dos lecturas que valen el proyecto entero:**

**El conductor profesional desaparece.** En crudo abandonaba menos de la mitad que el resto;
dentro del modelo su razón de momios es 0,993 con un p de 0,952, o sea nada. La explicación
está en el módulo 3: los días de actividad ya recogen ese efecto, y ser profesional no
añadía nada propio. Era una variable de confusión disfrazada de hallazgo.

**El dispositivo tampoco importa**, con un p de 0,773. Es la misma conclusión a la que llegó
el proyecto del Curso 3 con una prueba t, ahora controlando por otras siete variables.

**Clasificación, sobre 3.575 usuarios de prueba:**

| Métrica | Umbral 0,50 | Umbral 0,20 |
|---|---|---|
| Exactitud | 0,823 | 0,691 |
| Precisión | 0,505 | 0,313 |
| **Sensibilidad** | **0,082** | **0,623** |
| F1 | 0,141 | 0,417 |
| AUC | 0,737 | 0,737 |

**El resultado incómodo, que es el que importa.** Con el umbral por defecto el modelo
acierta el 82,3 % y **se le escapan 582 de los 634 usuarios que se van**. Ese 82,3 % es casi
lo mismo que se conseguiría contestando siempre "se queda", que acertaría el 82,26 %.

**Recomendación.** El modelo **no sirve tal cual**, pero no porque sea inútil: su AUC de
0,737 dice que sí ordena a los usuarios por riesgo. Lo que está mal es el umbral. Bajándolo
a 0,20 se pasa a detectar al **62,3 %** de los que se van, al precio de que dos de cada tres
avisos sean falsos. Si una campaña de retención cuesta poco por usuario, ese cambio es
rentable y es la decisión que hay que llevar al negocio, no al modelo.
