# Automatidata: qué hay en el archivo de viajes

**Resumen ejecutivo · Curso 2, proyecto de exploración · 2026-08-13**

---

## El taxi de Nueva York es un negocio de tarde y noche

Es la pregunta que este archivo nunca había respondido, y la contesta solo:

| | |
|---|---|
| Hora punta | Las **19**, con 1.454 viajes |
| Hora más floja | Las **4**, con 233 |
| Diferencia | **6,2 veces** |
| De 17 a 21 h | **6.695 viajes, el 29,5 %** del día |

Casi un tercio del negocio ocurre en cuatro horas. Cualquier decisión sobre flota, turnos o
precios sale de este reparto y no de la media diaria.

Y tiene una consecuencia concreta para el trabajo posterior: el modelo de tarifas del Curso 4
usa una variable de hora punta, y **sus horas salen de aquí**, no de una convención.

## 197 viajes no pudieron ocurrir

Son el 0,87 % del archivo. Pocos, y hay que quitarlos igual, porque no describen viajes:

| Problema | Viajes |
|---|---|
| Distancia cero | 148 |
| Cero pasajeros | 33 |
| Termina antes de empezar | 27 |
| Tarifa cero o negativa | 20 |
| Importe total negativo | 14 |

Una tarifa negativa **no es un valor extremo, es una devolución**. Un viaje que termina antes
de empezar es un error de reloj. La diferencia entre esto y un atípico es que aquí no hay
nada que decidir: no son viajes.

## El pico de los 52 dólares no es un atípico

**514 viajes cuestan exactamente 52,00 $**, el 2,26 % del archivo, y **513 de ellos llevan
el código de tarifa 2**, que es la tarifa plana del aeropuerto.

Es el ejemplo perfecto de por qué se mira la columna que explica antes de tocar la que
molesta: sin el código de tarifa, ese pico parece un montón de carreras caras sospechosas.
Con él, es un precio fijo y **hay que conservarlo tal cual**.

## Lo demás del archivo

| | |
|---|---|
| Filas y columnas | 22.699 y 17 |
| Duplicados y ausentes | **Ninguno** |
| Periodo cubierto | Del 2017-01-01 al 2017-12-31, 364 días |
| Fechas | Llegan como texto, en formato `MM/DD/YYYY hh:mm:ss AM/PM` |

Las fechas son el trabajo obligatorio de este archivo: hasta convertirlas, no se puede
ordenar por tiempo, ni restar para sacar la duración, ni agrupar por hora. **La duración del
viaje no existe como columna**: hay que construirla.

Y los candidatos a atípico, contados sin borrar nada: 2.064 en la tarifa (9,09 %), 2.527 en
la distancia (11,13 %) y 1.228 en la duración (5,41 %). Son carreras largas de verdad, no
errores, y por eso se recortan en vez de eliminarse cuando estorban.

## Qué hacer

1. **Convertir las dos marcas de tiempo antes que nada**, indicando el formato, y construir
   la duración.
2. **Eliminar los 197 viajes imposibles**, con su conteo escrito.
3. **Conservar los 514 de tarifa plana** y marcarlos con una variable, porque su precio no
   depende de la distancia.
4. **Usar el reparto por hora** para cualquier decisión operativa, en vez del promedio.

## Límites declarados

- Un solo año y una sola ciudad.
- El archivo es una muestra de los viajes de 2017, no todos.
- No se ha corregido nada aquí: este informe cuenta y describe, y las decisiones quedan
  escritas para que las aplique quien limpie.

---

*Los números salen de `model_results.json`, generado por `02_scripts/automatidata_eda.py`,
que lee el CSV original en modo lectura.*
