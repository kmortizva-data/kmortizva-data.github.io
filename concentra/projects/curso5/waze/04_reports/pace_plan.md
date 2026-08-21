# Waze, Curso 5: documento de estrategia PACE

**Escenario.** El mismo del Curso 4: Waze quiere saber quién está a punto de abandonar la
aplicación para poder actuar antes. Lo que cambia no es la pregunta, es el arsenal.

**Datos.** `waze_dataset.csv`, 14.999 usuarios y 13 columnas. 700 sin etiqueta, que se
excluyen igual que en el Curso 4 y por la misma comprobación.

---

## Plan

**La pregunta de este curso, que es distinta de la del Curso 4:**

> ¿Le gana un modelo de árbol a la regresión logística sobre este mismo problema?

Esta es la única pregunta de todo el proyecto que se puede contestar **de verdad**, porque
el Curso 4 predijo lo mismo sobre el mismo archivo y dejó sus números escritos.

**Cómo se hace válida la comparación.** El primer corte de los datos es idéntico al del
Curso 4: 25 % de prueba, semilla 42, estratificado por abandono. Eso significa que **los
3.575 usuarios apartados son literalmente los mismos**, y los 10.724 restantes son los que
el Curso 4 usó enteros para entrenar. Aquí se subdividen:

| Parte | Usuarios | Abandono | Cuándo se toca |
|---|---|---|---|
| Entrenamiento | 8.579 | 17,74 % | Todo el rato |
| Validación | 2.145 | 17,72 % | Para elegir modelo y perillas |
| **Prueba** | **3.575** | 17,73 % | **Una vez, al final** |

**Lo que se espera, dicho antes de ajustar nada.** Una comparación sin ajustar ya sugería
que los árboles no ganan. Este proyecto los ajusta en serio, con búsqueda en rejilla, para
que la respuesta signifique algo en las dos direcciones. **Si ganan, se reporta que ganan**,
y la moraleja del curso cambia sin que cambie el método.

## Analyze

**La segmentación del módulo 3, aplicada a los usuarios.** Se agrupan por comportamiento,
sin etiqueta, sobre cinco variables escaladas, y **el número de grupos se elige con la
silueta y no a dedo**. Se prueba de 2 a 7.

Esa segmentación entra en el modelo como una variable más, para que sea el modelo quien
diga si valía algo. La alternativa, decidirlo nosotros, es la que produce análisis que se
defienden solos.

**Las mismas variables construidas que el Curso 4**, a propósito: kilómetros por día
conducido, conductor profesional y el dispositivo como unos y ceros. Cambiar cualquiera de
ellas invalidaría la comparación, que es lo que el proyecto viene a hacer.

## Construct

**Cuatro familias, medidas en validación**: regresión logística, un árbol suelto, bosque
aleatorio y refuerzo por gradiente con xgboost.

**Ajuste de perillas por búsqueda en rejilla, con validación cruzada de 4 pliegues**, para
las dos familias de árboles. La logística no lleva perillas que ajustar, así que compite
tal cual, y eso es parte de su ventaja: **es el modelo que no hay que afinar**.

Se reportan las dos cifras de cada búsqueda, la de validación cruzada y la de validación, y
la diferencia entre ellas se explica en vez de esconderse: la primera sale optimista porque
es sobre la que se eligió al ganador.

## Execute

**El campeón se elige en validación. El conjunto de prueba se mira una vez.**

Se reporta la tabla de todos los candidatos y no solo del ganador, la importancia de las
variables del bosque, y la comparación contra el Curso 4 sobre los mismos usuarios.

Y se reporta lo que no funcionó con el mismo detalle que lo que funcionó.

---

## Riesgos declarados antes de empezar

- **Que la segmentación no encuentre nada.** K-medias siempre devuelve grupos, también donde
  no los hay. Si la silueta sale baja, se dice, y la variable se queda en el modelo para que
  el modelo también opine.
- **Que el ajuste dé la vuelta al resultado.** Es el motivo de ajustar en serio.
- **Que la sensibilidad siga siendo mala.** El Curso 4 detectaba al 8,2 % de los que se van.
  Cambiar de familia de modelo no ataca la causa de eso, que es el umbral, así que lo
  probable es que siga igual. Se mide y se reporta.
- **Que las diferencias sean tan pequeñas que no signifiquen nada.** Con 3.575 usuarios de
  prueba, una diferencia de milésimas de AUC no es una diferencia. Si pasa, se dice.
