# TikTok, Curso 5: resumen ejecutivo

## El resultado, y por qué no hay que celebrarlo

El modelo clasifica reclamación contra opinión con un **99,58 % de acierto** sobre 3.817
vídeos que no había visto. En un portafolio eso se lee como un éxito.

**No lo es, y este informe existe para explicar por qué.**

## El control que lo destapa

Antes de ajustar nada se dejó fijado un modelo de comparación deliberadamente ridículo: **un
árbol de una sola pregunta sobre una sola columna**, las visualizaciones. La regla entera que
aprendió cabe en una línea:

> Si el vídeo pasa de **10.031 visualizaciones**, es una reclamación.

| Modelo | Variables | Exactitud en prueba | AUC |
|---|---|---|---|
| **Una pregunta, una columna** | **1** | **0,9958** | 0,9958 |
| Regresión logística | 9 | 0,9940 | 0,9973 |
| Refuerzo ajustado (xgboost) | 9 | 0,9948 | 0,9979 |
| **Bosque ajustado, 300 árboles** | **9** | **0,9958** | 0,9986 |

**Nueve variables y trescientos árboles aportan exactamente 0,0000 de exactitud sobre una
sola pregunta.** La regresión logística, con las nueve, saca menos.

El AUC sí mejora, de 0,9958 a 0,9986, y eso es real: el bosque ordena mejor los casos dudosos.
Pero a la hora de decidir, que es lo que se despliega, no mejora nada.

## De dónde salía la señal

El Curso 2, que solo miraba los datos, ya lo había encontrado: **una reclamación se ve 101,1
veces más que una opinión**. Este proyecto añade el número que lo cierra:

| | |
|---|---|
| La opinión **más vista** de todo el archivo | **9.998** visualizaciones |
| El corte que eligió el modelo | **10.031** visualizaciones |
| La reclamación **menos vista** | 1.049 visualizaciones |

Las dos clases están separadas por una línea, y por eso cualquier algoritmo la encuentra. No
hizo falta aprendizaje automático: hacía falta ordenar una columna.

## Y aquí está la parte incómoda

**Un hueco así no existe en datos de una plataforma real.** Ningún vídeo de opinión de
TikTok tiene un techo de diez mil visualizaciones.

Aparece cuando alguien genera dos poblaciones sacándolas de rangos distintos, y **estos datos
son sintéticos**, creados por TikTok para el certificado. El proyecto del Curso 2 ya lo
declaraba como limitación; aquí se ve la consecuencia:

> Un modelo con 99,58 % sobre este archivo ha medido **cómo se generó el archivo**, no cómo
> se comporta la plataforma.

Eso no invalida el ejercicio, que es el que el curso pide y el que enseña el método. Invalida
la conclusión de negocio, y por eso se dice antes que el número.

## Los únicos vídeos difíciles

La regla de una línea se equivoca con **65 vídeos** del entrenamiento, y los 65 son del mismo
tipo: **reclamaciones que casi nadie vio**, por debajo del corte.

Son los únicos casos con algo que aprender, y la distancia entre 0,9958 y 0,9986 de AUC se
juega entera ahí dentro. Ningún modelo de los cuatro los resuelve.

## Lo que sí cambió respecto al Curso 4

Aquel proyecto predecía si la cuenta estaba verificada, con un reparto de 93,6 % contra
6,4 %, así que tuvo que equilibrar las clases y no podía fiarse de la exactitud.

**Aquí no hace falta nada de eso**: reclamación y opinión están al 50,3 % y 49,7 %. Es la
misma tabla y el problema opuesto, y sirve para ver que el desbalance no es una propiedad de
los datos, es una propiedad de la pregunta que les haces.

## Qué se decide con esto

1. **No desplegar esto como clasificador de contenido.** Lo que aprendió es un umbral de
   visualizaciones que solo existe en el archivo de prácticas.
2. **Usar la regla de una pregunta como referencia obligatoria** en cualquier proyecto
   futuro sobre estos datos. Si un modelo nuevo no le gana, no ha aportado nada.
3. **Reservar el ejercicio para lo que sí enseña:** cómo se compara un modelo contra un
   control, cómo se ajusta con validación cruzada y cómo se lee la importancia de variables.
4. **Si esto fuera un encargo real, pedir datos reales** antes de cualquier otra cosa.

## Limitaciones

- **Los datos son sintéticos.** Es la limitación principal y contamina la conclusión, no los
  métodos.
- Los cinco contadores de interacción suman el grueso de la importancia y **están
  correlacionados entre sí por encima de 0,55**, según se midió en el Curso 4. No son cinco
  señales: son una repartida.
- **La prueba se miró una vez**, después de elegir campeón en validación. El campeón fue el
  bosque ajustado, con 0,9979 de AUC en validación.
- El ajuste costó 41 segundos para 24 combinaciones del bosque y 4 para 12 del refuerzo.
