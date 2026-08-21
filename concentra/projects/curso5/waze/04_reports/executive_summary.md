# Waze, Curso 5: resumen ejecutivo

## La respuesta

**No. El modelo complicado no gana.** Sobre los mismos 3.575 usuarios que el Curso 4 apartó,
con la misma semilla y la misma partición:

| Modelo | AUC | Exactitud | Sensibilidad | Precisión |
|---|---|---|---|---|
| Logística del Curso 4 | 0,7368 | 0,8229 | 0,0820 | 0,5049 |
| **Logística de este curso** | **0,7379** | 0,8249 | **0,0962** | 0,5351 |
| Bosque aleatorio ajustado | 0,7318 | 0,8243 | 0,0710 | 0,5357 |
| Refuerzo ajustado (xgboost) | 0,7348 | 0,8246 | 0,0489 | 0,5636 |

El campeón se eligió **en validación**, antes de tocar la prueba, y también ahí ganó la
logística: 0,7424 contra 0,7405 del bosque y 0,7401 del refuerzo.

## Lo que hizo falta para poder decir eso

Ajustar los árboles en serio, porque un árbol sin acotar pierde por goleada y compararse con
él no demuestra nada:

| Modelo | Sin ajustar | Ajustado | Lo que ganó |
|---|---|---|---|
| Árbol suelto | 0,5717 | — | — |
| Bosque aleatorio | 0,7129 | **0,7405** | **+0,0276** |
| Refuerzo (xgboost) | 0,7273 | **0,7401** | +0,0128 |

**Ajustar el bosque le dio 0,0276 de AUC**, que es una mejora grande para lo que se juega
aquí. Y se quedó a **0,0019** de la logística, que no lleva ninguna perilla que ajustar.

Ese es el resultado del proyecto: **afinar el modelo complicado casi cierra la distancia, y
no la cierra.** La búsqueda probó 40 combinaciones para el bosque en 61 segundos y 48 para
el refuerzo en 14.

## Lo que no funcionó, con el mismo detalle

**La segmentación del módulo 3 no encontró grupos.** El mejor coeficiente de silueta fue
**0,2588**, con dos grupos, y ningún otro número de grupos mejoró. Por debajo de 0,35 los
grupos se tocan entre sí: estos usuarios no forman familias separadas, son un continuo.

Los dos grupos que salieron abandonan al **17,29 %** y al **19,05 %**, o sea **1,75 puntos**
de diferencia. Eso no es una segmentación accionable.

Y el modelo lo confirmó por su cuenta: de las nueve variables, **el segmento quedó última,
con 0,0026 de importancia**. Se metió en el modelo precisamente para que el modelo pudiera
decir esto.

## Lo que sí manda

| Variable | Importancia |
|---|---|
| **Días activo** | **0,5163** |
| Días desde el alta | 0,1687 |
| Km por día conducido | 0,1594 |
| Trayectos | 0,0497 |
| Minutos al volante | 0,0445 |
| Sesiones totales | 0,0343 |
| Conductor profesional | 0,0216 |
| iPhone | 0,0030 |
| Segmento (módulo 3) | 0,0026 |

**Los días de actividad son más de la mitad del modelo**, más que las otras ocho juntas. Es
coherente con lo que el Curso 4 ya había encontrado por otro camino.

## El fallo que ningún modelo arregló

Los cuatro modelos aciertan alrededor del 82 % y **detectan a menos de uno de cada diez de
los que se van**. El mejor en sensibilidad es la logística de este curso con 0,0962, y el
peor el refuerzo ajustado con 0,0489.

Eso confirma desde otro sitio lo que el Curso 4 ya había diagnosticado: **el problema no era
el modelo, era el umbral**. Cambiar de familia no lo toca, porque no es una limitación del
algoritmo sino de dónde se pone el corte.

## Qué se decide con esto

1. **Desplegar la regresión logística**, que gana y además se explica, se defiende ante quien
   la sufra y se arregla sin reentrenar trescientos árboles.
2. **Bajar el umbral**, que es lo único que mueve la sensibilidad, aceptando más falsas
   alarmas. Cuánto se baja depende de lo que cueste contactar a un usuario que no se iba.
3. **No usar la segmentación** para dirigir campañas. Los grupos que salen no están
   separados y apenas difieren en abandono.
4. **Conservar el bosque como diagnóstico**, no como modelo de producción: su tabla de
   importancia es la que dice dónde mirar.

## Limitaciones

- **Las diferencias son de milésimas.** Con 3.575 usuarios de prueba, 0,7379 contra 0,7348
  no es una diferencia que aguante un cambio de semilla. Lo que sí aguanta es la conclusión
  cualitativa: los árboles **no** despegan.
- **El archivo no dice por qué se fue nadie.** Ningún modelo puede predecir bien una causa
  que no está en los datos, y ahí está el techo de este 0,74.
- La comparación con el Curso 4 usa su modelo entrenado con 10.724 usuarios y este con
  8.579, porque aquí hay validación. Aun con menos datos, la logística de este curso salió
  ligeramente mejor, lo que confirma que la diferencia está dentro del ruido.
- **La prueba se miró una sola vez**, después de elegir campeón. Todo lo demás se decidió
  contra validación.
