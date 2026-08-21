# Automatidata, Curso 5: documento de estrategia PACE

**Escenario.** La Comisión de Taxis y Limusinas de Nueva York quiere saber **quién deja
propina generosa**, para que el conductor lo sepa antes de aceptar la carrera.

**Datos.** `C2_2017_Yellow_Taxi_Trip_Data.csv`, 22.699 viajes de 2017. Los mismos del Curso
2 y del Curso 4, con una pregunta completamente distinta.

---

## Plan

**La pregunta:**

> ¿Se puede saber, antes de que acabe el viaje, si el pasajero va a dejar propina generosa?

**Y la pregunta ética que va pegada, y que el módulo 1 obliga a hacer.** Un modelo que dice
al conductor quién va a dar propina es un modelo que puede acabar decidiendo **a quién se le
para el taxi**. Eso es discriminación con apariencia de eficiencia, y hay que decirlo aunque
el modelo funcione. Aquí resulta que además no funciona, pero el orden importa: la pregunta
se hace antes de conocer el resultado.

**Lo que se espera, dicho antes de ajustar nada.** Dar propina es una decisión personal.
Distancia, duración, hora y tarifa describen el viaje, no al pasajero. Lo probable es que no
se pueda predecir. Si es así, **el entregable es decirlo con pruebas**, no un modelo flojo
presentado como si fuera algo.

## Analyze

**Primero, una fuga que hay que descartar en vez de suponer.** `total_amount` podría incluir
la propina. Se comprueba sumando las partes y comparando con el total, viaje a viaje. Si la
incluye, esa columna queda prohibida como variable, porque contiene la respuesta.

**Segundo, el efectivo.** Hay que mirar el porcentaje de propina cero **por tipo de pago**
antes de nada. Si un tipo de pago tiene el 100 %, no es conducta: es el aparato.

**Tercero, el umbral.** No se elige: se lee de la distribución de la propina. Si hay picos,
son los botones que ofrece la máquina, y eso cambia qué significa «generoso».

## Construct

**Partición en tres**, 60/20/20 estratificada.

**El control primero:** contestar siempre «no generoso». Con clases desbalanceadas ese modelo
saca una exactitud alta sin hacer nada, y es la barra que todo lo demás tiene que superar.

**Cuatro familias** medidas en validación, y **búsqueda en rejilla** con validación cruzada
de 4 pliegues para las dos de árboles.

**Y la métrica que decide no es la exactitud.** Con un 23 % de positivos, la exactitud premia
al que no señala a nadie. Se mira sensibilidad y AUC, y se reportan las dos.

## Execute

Campeón elegido en validación, prueba mirada una vez, y **el control dentro de la tabla
final**, que es lo que permite ver si algún modelo decidió algo distinto.

Si la respuesta es que no se puede predecir, el informe explica **qué haría falta** para
poder, y qué palanca real existe mientras tanto.

---

## Riesgos declarados antes de empezar

- **Que el modelo salga bien por el efectivo.** Es el riesgo principal y el que se ataca en
  la fase de análisis, mirando la propina cero por tipo de pago antes de modelar.
- **Que la exactitud engañe.** Con clases desbalanceadas, un modelo que no señala a nadie
  saca buena nota. Por eso el control entra en la tabla.
- **Que se lea la importancia de variables de un modelo que no funciona.** La importancia
  reparte el total entre las variables que hay, acierte el modelo o no. Se mira después de
  comprobar si el modelo sirve, nunca antes.
- **Que el resultado negativo se presente como un fracaso.** No lo es. Saber que un encargo
  no se puede cumplir con los datos disponibles ahorra construir algo inútil, y es
  exactamente lo que un análisis honesto entrega cuando esa es la verdad.
