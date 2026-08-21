# TikTok: predecir si una cuenta está verificada

**Resumen ejecutivo · Curso 4, proyecto de regresión logística · 2026-08-13**

---

## Lo que separa a una cuenta verificada no es cómo publica, es qué publica

Con 19.084 vídeos se construyó una regresión logística que estima si la cuenta que publicó
un vídeo está verificada. De las cinco variables candidatas, **solo una tiene efecto
demostrado**: si el vídeo es una reclamación o una opinión.

| | Reclamaciones | Opiniones |
|---|---|---|
| Cuentas no verificadas | 52,6 % | 47,4 % |
| Cuentas verificadas | 17,4 % | **82,6 %** |

Publicar una reclamación multiplica por **0,20** los momios de que la cuenta esté
verificada, con un intervalo del 95 % de 0,13 a 0,29.

## Lo que no importa, y conviene decirlo

Tres variables que parecían candidatas **no muestran ningún efecto**: la duración del
vídeo (razón de momios 1,00, p de 0,63), las visualizaciones (1,00, p de 0,886) y el estado
del autor, expulsado o en revisión, cuyos intervalos cruzan el 1.

Sobre la duración vale la pena insistir, porque es la variable que suele presentarse como
la interesante: la media es de **31,77 segundos en las verificadas y 32,47 en las no
verificadas**. Siete décimas de segundo sobre vídeos de medio minuto.

## Rendimiento, con la advertencia por delante

**El 93,7 % de las cuentas no están verificadas.** Un modelo que conteste siempre "no"
acierta el 93,7 % y no detecta a nadie. Por eso el modelo se entrenó con las dos clases
igualadas y **la exactitud que sigue se compara contra el 50 % de una moneda**:

| Métrica | Valor | Qué significa |
|---|---|---|
| Sensibilidad | **0,827** | De cada 100 cuentas verificadas, pilla 83 |
| Precisión | **0,641** | De cada 100 alarmas, 64 son ciertas |
| F1 | 0,722 | |
| AUC | 0,697 | 0,5 sería azar |

## El hallazgo: aquí el umbral no sirve para nada

El manual dice que el umbral de clasificación es una decisión de negocio, y normalmente lo
es. **En este modelo no decide nada.**

Las probabilidades que predice caen en dos montones, uno alrededor de 0,25 y otro alrededor
de 0,64, y **no hay ni un solo caso entre 0,28 y 0,56**. Cortar en 0,30, en 0,40 o en 0,55
produce exactamente las mismas 387 cuentas marcadas y los mismos 248 aciertos.

La causa es que el modelo se apoya en una sola variable binaria, así que se ha convertido
en la regla "¿es una reclamación?" con dos pasos de aritmética por el medio.

## Qué hacer con esto

1. **No usarlo como clasificador automático.** Un AUC de 0,697 y una de cada tres alarmas
   falsas no sostienen una decisión sin persona delante.
2. **Sí usar el hallazgo.** Lo que distingue a los dos grupos es el tipo de contenido, no
   la actividad de la cuenta. Eso reorienta dónde buscar señal.
3. **Pasar al problema real.** La variable que aquí resultó ser la única que importa,
   reclamación contra opinión, es justo la que hay que predecir en el proyecto siguiente, y
   la tubería completa ya está montada.

## Límites declarados

- Al equilibrar las clases se descartaron 16.684 vídeos de la clase mayoritaria. El modelo
  aprende de una muestra que no se parece al reparto real de la plataforma.
- El pseudo R² es de 0,1046: el modelo explica poco, y eso es un resultado, no un fallo del
  procedimiento.
- Los datos son sintéticos, creados por TikTok para el certificado. Las conclusiones valen
  como ejercicio y no describen la plataforma real.
- `claim_status` es la variable que el Curso 5 tiene que predecir. Usarla aquí como
  predictora es correcto para este ejercicio, pero **los dos proyectos no son
  independientes**, y conviene recordarlo al comparar resultados.

---

*Los números de este informe salen de `model_results.json`, generado por
`02_scripts/tiktok_logistic.py`. El script lee el CSV original en modo lectura y no modifica
ningún archivo del curso.*
