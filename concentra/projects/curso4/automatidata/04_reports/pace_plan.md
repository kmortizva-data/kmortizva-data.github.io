# Automatidata, Curso 4: documento de estrategia PACE

**Escenario.** Automatidata trabaja para la Comisión de Taxis y Limusinas de Nueva York.
La comisión quiere que el pasajero vea **una tarifa estimada antes de subirse**, y ha
pedido un modelo de regresión que la calcule.

**Datos.** `C2_2017_Yellow_Taxi_Trip_Data.csv`, 22.699 viajes y 17 columnas, sin
duplicados y sin celdas vacías.

---

## Plan

**La pregunta, escrita con precisión, porque de aquí sale todo lo demás:**

> ¿Cuánto va a costar este viaje, **sabiéndolo antes de que empiece**?

Esa última condición es la que decide el proyecto entero. El dataset contiene la distancia
recorrida y la duración del viaje, que son con diferencia los dos mejores predictores de la
tarifa, y **ninguno de los dos existe en el momento en que hay que dar el precio**. Un
modelo que los use predice muy bien y no se puede desplegar.

Así que las variables se separan desde el principio en dos grupos:

| Se sabe al reservar | Solo se sabe al terminar |
|---|---|
| Origen y destino | Distancia recorrida |
| Hora y día de la semana | Duración real |
| Tipo de tarifa (taxímetro o plana de aeropuerto) | Peajes, propina, total |
| Histórico de viajes anteriores por esa ruta | |

**Qué se entrega:** un modelo con su ecuación, el error esperado en dólares, y una
declaración honesta de cuándo falla.

**Riesgos identificados antes de empezar:** que el modelo se evalúe sobre información que
no tendrá en producción, y que el error medio esconda un grupo de viajes donde se equivoca
mucho más. Los dos se materializaron, y los dos están medidos.

## Analyze

**Limpieza.** Se descartan 165 viajes físicamente imposibles: 20 con tarifa cero o
negativa, 27 que terminan antes de empezar y 148 con distancia cero. Quedan 22.534.

**Valores extremos.** En vez de borrarlos, se recortan al percentil 99,5: la tarifa a
55,67 $, la duración a 73,18 minutos y la distancia a 20,55 millas. Son 113 viajes en cada
variable. Borrarlos habría cambiado en silencio la población que el modelo dice describir.

**El hallazgo que condiciona el modelo.** Hay **514 viajes que cuestan exactamente
52,00 $**, y 513 de ellos tienen el código de tarifa 2, la tarifa plana del aeropuerto. Ahí
el precio está fijado y la distancia no lo mueve: la pendiente medida en ese grupo es de
**0,00 $ por milla**, frente a 2,86 $ por milla en los viajes con taxímetro. Sin una
variable que marque ese caso, se le pide al modelo que explique con la distancia algo que
la distancia no gobierna.

**El reparto del negocio.** El 52,5 % de los viajes cuesta menos de 10 $ y solo el 7,4 %
pasa de 30 $. La tarifa mediana es 9,50 $ y la media 12,85 $.

## Construct

**Variables construidas.** Distancia media y duración media de cada pareja
origen-destino, hora punta (días laborables de 6 a 9 y de 16 a 19), y tarifa plana de
aeropuerto.

**La decisión metodológica del proyecto.** Las medias por ruta se calculan **solo con los
datos de entrenamiento** y se aplican al conjunto de prueba. Calcularlas sobre el dataset
completo, que es el atajo habitual, mete información de los viajes de prueba dentro del
entrenamiento.

**Multicolinealidad.** Con todas las variables dentro, la distancia real y la media de la
ruta dan factores de inflación de la varianza de 32,17 y 28,68: miden lo mismo. En el
modelo final, que ya no lleva la distancia real, ningún factor pasa de 5,50.

**Tres modelos, y solo uno se puede entregar:**

| Modelo | R² en prueba | RMSE | ¿Se puede desplegar? |
|---|---|---|---|
| A. Con la distancia y la duración reales | 0,9461 | 2,41 $ | **No.** Esos datos no existen al reservar |
| B. Medias de ruta de todo el dataset | 0,8847 | 3,53 $ | **No.** Evaluado con información que no tendrá |
| C. Medias de ruta solo del entrenamiento | 0,6746 | 5,93 $ | **Sí** |

## Execute

**El modelo entregado:**

```
tarifa = 2,65
       + 1,87 × distancia media de la ruta (millas)
       + 0,32 × duración media de la ruta (minutos)
       + 0,27 × (1 si es hora punta)
       + 3,30 × (1 si es tarifa plana de aeropuerto)
```

Los cuatro coeficientes son significativos y sus intervalos del 95 % no tocan el cero.

**Rendimiento sobre 5.634 viajes que el modelo no vio:** R² de 0,6746, RMSE de 5,93 $ y
error absoluto medio de 3,21 $.

**Los supuestos, honestamente:**

| Supuesto | Estado |
|---|---|
| Linealidad | Se cumple en los viajes con taxímetro |
| Independencia | Razonable: viajes distintos, coches distintos |
| Normalidad de los residuos | **No se cumple.** Asimetría 3,49 y curtosis 18,07 |
| Varianza constante | **No se cumple.** p de 1,74e-06 |

Las dos violaciones tienen la misma causa, y es identificable en la figura de residuos: el
grupo de rutas nuevas y el grupo de tarifa plana forman estructuras propias en vez de
repartirse como ruido.

**Recomendación.** El modelo sirve para las rutas que la ciudad ya conoce, que son el
90,9 % de los viajes, con un error medio de 2,42 $. **No sirve tal cual para una ruta que
no ha visto nunca**, donde el error medio es de 11,11 $. La mejora con más recorrido no es
cambiar de modelo, sino sustituir el respaldo actual, que predice 12,68 $ para cualquier
ruta desconocida, por una estimación basada en la distancia geográfica entre las dos zonas.
