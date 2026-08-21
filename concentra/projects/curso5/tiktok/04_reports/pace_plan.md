# TikTok, Curso 5: documento de estrategia PACE

**Escenario.** TikTok quiere reducir la cola de reclamaciones que esperan revisión humana.
El objetivo final, anunciado desde el Curso 2, es clasificar automáticamente si un vídeo
contiene una reclamación o una opinión. Este es ese modelo.

**Datos.** `tiktok_dataset_raw.csv`, 19.382 vídeos. Las mismas 298 filas incompletas que
encontró el Curso 2, eliminadas por la misma razón: les faltan las siete columnas a la vez.

---

## Plan

**La pregunta:**

> ¿Se puede decidir automáticamente si un vídeo es una reclamación?

**Y la pregunta que este proyecto añade, que es la que de verdad importa:**

> Si sale bien, ¿lo hizo el modelo o ya estaba hecho?

**Lo que se espera, dicho antes de ajustar nada.** El Curso 2 ya midió que una reclamación
se ve **101 veces más** que una opinión, con los dos repartos casi sin solaparse. Con esa
señal, cualquier modelo va a salir casi perfecto. **Un resultado por encima del 99 % no será
un éxito: será una confirmación de lo que el Curso 2 ya sabía.**

Por eso este proyecto se diseña con un control.

## Analyze

**El control, fijado antes de tocar los modelos de verdad:** un árbol de **una sola pregunta
sobre una sola columna**, las visualizaciones. Es el modelo más tonto que se puede escribir,
y todo lo demás tiene que ganarle para justificar su existencia.

Decidir después qué cuenta como buena referencia es cómo un proyecto se convence a sí mismo
de que su resultado es impresionante. Se decide antes.

**Y una diferencia con el Curso 4 que conviene mirar.** Aquel proyecto predecía si la cuenta
estaba verificada, con un reparto de 93,6 % contra 6,4 %, y tuvo que submuestrear. Aquí el
objetivo está al **50,3 % contra 49,7 %**, así que no hay que equilibrar nada. Mismos datos,
problema opuesto: el desbalance no es una propiedad del archivo, es una propiedad de la
pregunta.

## Construct

**Partición en tres**, 60/20/20 estratificado, con la prueba apartada desde el principio.

**Cuatro familias medidas en validación**: logística, árbol suelto, bosque aleatorio y
refuerzo por gradiente. Luego **búsqueda en rejilla con validación cruzada de 4 pliegues**
para las dos familias de árboles.

**Y el control corriendo al lado en todo momento**, sobre las mismas particiones.

## Execute

El campeón se elige en validación. La prueba se mira una vez, **y en esa medición entra
también el control**, que es lo que convierte el informe en algo defendible.

Se reporta la importancia de variables, los vídeos que la regla de una línea no acierta, y
la comparación explícita entre lo que aporta el modelo completo y lo que aportaba una
pregunta.

---

## Riesgos declarados antes de empezar

- **Que salga casi perfecto y se cuente como un logro.** Es el riesgo principal y la razón
  del control. Un AUC por encima de 0,99 es una fuga de información o una señal enorme hasta
  que se demuestre lo contrario.
- **Que la señal sea un artefacto de los datos.** Son sintéticos, generados para el
  certificado. Si el modelo encuentra un umbral demasiado limpio, hay que comprobar si ese
  umbral podría existir en la realidad, y decirlo.
- **Que los cinco contadores se repartan la importancia** y parezcan cinco señales cuando
  son una. El Curso 4 ya midió que correlacionan entre sí por encima de 0,55.
- **Que la exactitud tape lo que pasa en los casos difíciles.** Con las clases equilibradas
  la exactitud no miente por desbalance, pero sigue promediando: hay que mirar aparte los
  vídeos que la regla simple no acierta.
