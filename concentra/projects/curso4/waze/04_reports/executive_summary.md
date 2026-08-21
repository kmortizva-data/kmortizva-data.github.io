# Waze: predecir qué usuario abandona la aplicación

**Resumen ejecutivo · Curso 4, proyecto de regresión logística · 2026-08-13**

---

## El modelo funciona, pero el umbral por defecto lo inutiliza

Con 14.299 usuarios se construyó una regresión logística que estima el riesgo de que
alguien abandone Waze. Tal y como sale de fábrica, **acierta el 82,3 % y detecta al 8,2 %
de los que se van**: deja escapar a 582 de los 634 usuarios que abandonaron.

Ese 82,3 % de acierto es casi exactamente lo que se conseguiría contestando siempre "se
queda", que acertaría el 82,26 %. **La exactitud, aquí, no mide nada.**

## Y sin embargo el modelo sí sabe algo

Su AUC es de **0,737**, así que ordena a los usuarios por riesgo bastante mejor que el azar.
El problema no es el modelo, es dónde se pone el corte:

| | Umbral 0,50 | **Umbral 0,20** |
|---|---|---|
| Detecta a los que se van | 8,2 % | **62,3 %** |
| Alarmas que resultan ciertas | 50,5 % | 31,3 % |
| F1 | 0,141 | **0,417** |

Bajando el umbral se pasa de detectar a 52 usuarios en riesgo a detectar a 395, al precio de
que dos de cada tres avisos sean falsos. **Si una campaña de retención cuesta poco por
usuario, ese cambio se paga solo**, y es una decisión de negocio, no del modelo.

## Qué protege de verdad contra el abandono

| Variable | Momios de abandonar |
|---|---|
| **Cada año más de antigüedad** | **×0,864** |
| **Cada día de actividad más en el mes** | **×0,901** |
| Cada 10 trayectos más | ×1,016 |
| Cada hora más al volante | ×1,004 |

Los dos primeros son los que mandan, y apuntan al mismo sitio: **el riesgo está en el
usuario nuevo y poco activo**. Quien abandona lleva una mediana de **8 días de actividad**
en el último mes; quien se queda, **17**.

## Dos cosas que parecían importar y no importan

**El conductor profesional.** En crudo abandona al 7,56 % frente al 19,88 % del resto, así
que parece el mejor predictor del archivo. Dentro del modelo su efecto es **0,993 con un p
de 0,952**, es decir nada. Los días de actividad ya recogían ese efecto: era una variable de
confusión, no un hallazgo.

**El dispositivo.** iPhone frente a Android da un p de 0,773. Es la misma conclusión que el
proyecto de Waze del Curso 3, que no encontró diferencia entre dispositivos con una prueba
t. Aquí se confirma controlando por otras siete variables a la vez.

## Qué hacer

1. **Bajar el umbral a 0,20** y medir el coste real de una alarma falsa antes de fijarlo del
   todo.
2. **Dirigir la retención a los usuarios nuevos con pocos días de uso**, que es donde están
   los dos efectos demostrados.
3. **No usar "conductor profesional" como criterio de segmentación.** Su ventaja aparente se
   explica por los días de actividad, que ya se están midiendo.
4. **Empezar a registrar por qué se va la gente.** Es la limitación de fondo, y ningún
   modelo la arregla desde dentro.

## Límites declarados

- El pseudo R² es de **0,1348**: el modelo explica una parte pequeña de lo que ocurre.
- El archivo **no contiene ninguna causa de abandono**, solo comportamiento. Con estos datos
  se detecta a quién se está desenganchando, no por qué.
- Se excluyeron 700 usuarios sin etiqueta, el 4,7 %. Se comprobó antes que se parecen al
  resto: la mayor diferencia de medianas es del 6,2 % y el reparto de dispositivo es
  idéntico. Si no hubiera sido así, excluirlos habría cambiado a quién describe el modelo.
- 983 usuarios condujeron cero días, y su ratio de kilómetros por día se fijó en cero en vez
  de en infinito. Es una decisión defendible y conviene saber que se tomó.
- Los datos son sintéticos, creados por Waze para el certificado.

---

*Los números de este informe salen de `model_results.json`, generado por
`02_scripts/waze_logistic.py`. El script lee el CSV original en modo lectura y no modifica
ningún archivo del curso.*
