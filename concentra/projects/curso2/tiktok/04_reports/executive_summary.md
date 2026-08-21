# TikTok: qué hay en el archivo antes de analizar nada

**Resumen ejecutivo · Curso 2, proyecto de exploración · 2026-08-13**

---

## Un vídeo con reclamación se ve 101 veces más que uno de opinión

No hizo falta ninguna prueba estadística para verlo: está en el reparto.

| | Vídeos | Vistas medias | Mediana |
|---|---|---|---|
| **Con reclamación** | 9.608 | **501.029,5** | 501.555 |
| **De opinión** | 9.476 | **4.956,4** | 4.953 |

Dibujados en escala logarítmica, los dos repartos **no se solapan**: son dos poblaciones
distintas de vídeos, no una con una cola.

Es la variable que los cursos siguientes van a intentar predecir, y este archivo dice de
entrada que la señal es enorme.

## Los huecos entran de golpe, no sueltos

Hay **298 filas incompletas**, el 1,54 % del archivo. Y no están repartidas:

- Afectan a **siete columnas**, siempre las mismas.
- Y a las 298 filas **les faltan las siete a la vez**.

Eso descarta el error de medición columna a columna y apunta a un registro que se creó vacío
o a una carga que se interrumpió. Al ser el 1,5 % y comportarse igual entre sí, **se pueden
eliminar**, dejándolo escrito. Quedan 19.084 filas completas.

## Lo que la regla del rango intercuartílico no ve

Aplicada columna a columna sobre las cinco medidas de interacción:

| Columna | Candidatos a atípico | % |
|---|---|---|
| Visualizaciones | **0** | 0,00 |
| Me gusta | 1.726 | 9,04 |
| Compartidos | 2.508 | 13,14 |
| Descargas | 2.450 | 12,84 |
| Comentarios | 2.789 | 14,61 |

**La columna con los valores más extremos del archivo no tiene ni un solo candidato.** Su
cuartil superior está en 504.327, así que la valla se va a 1.253.403, por encima del máximo
real. Cuando la mitad central de los datos es enorme, la regla no marca nada.

Es un buen recordatorio de que el criterio del IQR describe una distribución concentrada, y
que **en datos así de dispersos hay que mirar el dibujo, no la regla**.

## Lo que sí está limpio

- **Sin duplicados.**
- **Sin valores imposibles**: ninguna vista negativa, ningún vídeo con más me gusta que
  visualizaciones, ninguna duración fuera del rango de 1 a 60 segundos.
- **Las categorías están escritas de una sola manera**: dos valores en estado de
  reclamación, dos en verificación y tres en estado del autor, sin variantes de mayúsculas.

## Qué hacer

1. **Eliminar las 298 filas incompletas**, declarando que son el 1,54 % y que les faltaban
   las siete columnas a la vez.
2. **Trabajar la variable de reclamación como la señal principal.** El archivo la señala
   solo.
3. **No usar la regla del IQR sobre las visualizaciones.** Con esa dispersión no marca nada,
   y el criterio útil es por tramos o en escala logarítmica.

## Límites declarados

- Los datos son sintéticos, creados por TikTok para el certificado.
- La diferencia de 101 veces es descriptiva: aquí no se ha contrastado nada ni se ha
  descartado que otra variable la explique.
- No se ha corregido nada. Este informe cuenta y describe.

---

*Los números salen de `model_results.json`, generado por `02_scripts/tiktok_eda.py`, que lee
el CSV original en modo lectura.*
