# Waze: qué hay en el archivo antes de modelar nada

**Resumen ejecutivo · Curso 2, proyecto de exploración · 2026-08-13**

---

## Hay 461 usuarios que conducen más de 24 horas en un día

El archivo registra, por usuario y por mes, cuántos días condujo y cuántos kilómetros y
minutos acumuló. Dividiendo una cosa entre la otra aparece algo que ningún análisis
posterior detectó:

| Comprobación | Usuarios |
|---|---|
| Más de 1.000 km en un solo día conducido | **1.994** |
| **Más de 24 horas al volante en un solo día conducido** | **461** |
| Máximo de kilómetros en un día | **15.420 km** |
| Máximo de horas en un día | **172 horas** |

La mediana son 297 km por día conducido, así que el grueso del archivo es plausible. Pero
172 horas dentro de un día de 24 no es un valor extremo: **es aritméticamente imposible**, y
significa que la columna de días conduciendo o la de minutos no miden lo que dicen medir.

## Por qué importa, y no es una curiosidad

Los cursos siguientes usan este archivo para dos cosas serias: una prueba de hipótesis sobre
el uso por dispositivo y un modelo de abandono. **Ninguno de los dos miró esta variable**,
porque ninguno de los dos la construyó: aparece al dividir kilómetros entre días.

No invalida aquellos resultados, que no la usaban. Sí dice que **el archivo tiene un defecto
estructural en dos de sus columnas** y que cualquier análisis que las combine hereda ese
defecto.

## Lo demás del archivo

| | |
|---|---|
| Filas y columnas | 14.999 y 13 |
| Filas duplicadas | 0 |
| Columnas con ausentes | 1, solo la etiqueta |
| Usuarios sin etiqueta | **700**, el 4,67 % |
| Tasa de abandono entre los etiquetados | 17,74 % |
| Usuarios con cero días conduciendo | 1.024 |

**Los 700 sin etiqueta se pueden excluir.** Comparados con el resto, la mayor diferencia de
medianas es del 6,2 % en días de actividad, y menor en todo lo demás. Si no se parecieran,
excluirlos habría cambiado a quién describe cualquier modelo construido después.

**Los 1.024 con cero días conduciendo** son la causa de que la división por días falle. No
son un error del dato: son usuarios que abrieron la aplicación y no condujeron. Lo que hay
que decidir es qué vale su ratio, y la respuesta defendible es cero, no infinito.

## Qué hacer

1. **Preguntar al equipo que genera el archivo** qué mide exactamente "días conduciendo".
   La hipótesis más probable es que sea un conteo de días con actividad de conducción dentro
   de una ventana mayor que un mes, y entonces el ratio por día no significa lo que parece.
2. **No usar kilómetros ni minutos por día conducido** en ningún modelo hasta que eso se
   aclare.
3. **Mantener los 1.024 de cero días con ratio cero**, no eliminarlos: son usuarios reales
   con un comportamiento real.
4. **Excluir los 700 sin etiqueta** para cualquier trabajo supervisado, dejándolo escrito.

## Límites declarados

- No se ha corregido nada: este informe cuenta y describe, no limpia.
- El umbral de 1.000 km al día es un criterio propio y discutible; lo que no es discutible
  son los 461 casos por encima de 24 horas diarias.
- Los datos son sintéticos, creados por Waze para el certificado, así que el defecto puede
  ser del generador y no de un sistema real. La forma de detectarlo es la misma.

---

*Los números salen de `model_results.json`, generado por `02_scripts/waze_eda.py`, que lee
el CSV original en modo lectura.*
