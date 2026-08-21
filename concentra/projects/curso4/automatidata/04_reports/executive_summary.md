# Automatidata: estimar la tarifa antes del viaje

**Resumen ejecutivo · Curso 4, proyecto de regresión · 2026-08-13**

---

## Se puede dar un precio por adelantado, con un margen de unos 2,42 dólares

Con 22.534 viajes de taxi de Nueva York se construyó un modelo que estima la tarifa
**usando solo lo que se conoce en el momento de reservar**: el origen, el destino, la hora
y el tipo de tarifa.

En las rutas que la ciudad ya conoce, que son el **90,9 %** de los viajes, el modelo se
equivoca **2,42 $ de media**. Esa cifra es la que se puede prometer.

## Lo que mueve la tarifa

```
tarifa = 2,65 + 1,87 × distancia media de la ruta + 0,32 × duración media
              + 0,27 × hora punta + 3,30 × tarifa plana de aeropuerto
```

| Variable | Efecto | Intervalo del 95 % |
|---|---|---|
| Cada milla de la ruta habitual | **+1,87 $** | 1,84 a 1,90 |
| Cada minuto de la ruta habitual | **+0,32 $** | 0,31 a 0,33 |
| Viajar en hora punta | **+0,27 $** | 0,15 a 0,38 |
| Trayecto con tarifa plana de aeropuerto | **+3,30 $** | 2,86 a 3,74 |

Los cuatro efectos están demostrados: ningún intervalo toca el cero.

## Los dos hallazgos que importan para la decisión

**1. El modelo no vale para una ruta que no ha visto antes.** En las rutas conocidas se
equivoca 2,42 $; en las nuevas, **11,11 $, cuatro veces y media más**. Hoy el sistema
responde 12,68 $ a cualquier ruta desconocida, que es simplemente el precio medio de la
ciudad. Son el 9,1 % de los viajes y concentran casi todo el error.

**2. Hay un precio que no depende de la distancia.** 514 viajes cuestan exactamente
52,00 $, y 513 son la tarifa plana del aeropuerto. En ese grupo la tarifa sube **0,00 $ por
milla**, frente a 2,86 $ por milla en el resto. El modelo tiene que saber cuándo se aplica,
y por eso lleva esa variable.

## Una advertencia sobre el número que se reporta

El mismo modelo, evaluado con el atajo habitual de calcular los promedios por ruta sobre
todos los datos en vez de solo sobre los de entrenamiento, presenta un **R² de 0,8847 en
lugar de 0,6746**.

Esos 21 puntos no son una mejora: son información de los viajes de prueba filtrada dentro
del entrenamiento. Un modelo presentado así **parece 2,40 $ más preciso de lo que va a ser
en producción**. La cifra que aparece en este informe es la que se sostendrá el primer día
de funcionamiento.

## Qué hacer ahora

1. **Desplegar el modelo para rutas conocidas**, anunciando un margen de unos 2,42 $.
2. **Arreglar el caso de la ruta nueva antes de ampliar la cobertura.** No hace falta otro
   modelo: basta con estimar la distancia entre las dos zonas en vez de responder con la
   media de la ciudad.
3. **No prometer precisión uniforme.** El error depende de si la ruta es conocida, y el
   pasajero debería ver un rango, no una cifra exacta.

## Límites declarados

- Los datos son de 2017 y de una sola ciudad. Las tarifas cambian.
- El modelo no incluye tráfico ni meteorología en tiempo real, que son la causa más
  probable de las desviaciones grandes en rutas conocidas.
- Dos supuestos de la regresión lineal no se cumplen: los residuos no son normales
  (asimetría 3,49) y su varianza no es constante (p de 1,74e-06). Los coeficientes siguen
  siendo utilizables, pero **sus intervalos son algo más optimistas de lo que deberían**.
- Solo el 53,2 % de los viajes se predice con menos de 2 $ de error, así que la media de
  2,42 $ describe al conjunto y no a cada viaje.

---

*Los números de este informe salen de `model_results.json`, generado por
`02_scripts/automatidata_regression.py`. El script lee el CSV original en modo lectura y no
modifica ningún archivo del curso.*
