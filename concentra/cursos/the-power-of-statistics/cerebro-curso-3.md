# Cerebro: inferencia estadística para decisiones de negocio

Manual de operación, no material de estudio. Describe cómo trabajo una pregunta del tipo
"¿esta diferencia es real?": el orden, los umbrales, lo que siempre reporto y lo que nunca
hago. Pégalo como memoria y asume estas reglas sin volver a preguntarlas.

## Qué resuelvo con esto

Comparar dos grupos y decidir si la diferencia observada justifica actuar. Tasas de
conversión, tiempos, importes, métricas de uso, recuperación de un proceso. La respuesta
siempre es una decisión de negocio, nunca un número suelto.

## El procedimiento, en este orden

1. **Escribir H₀ y Hₐ en lenguaje de negocio, antes de mirar los datos.** Si se formulan
   después de ver el resultado, la prueba no vale.
2. **Fijar α antes también.** Por defecto 0,05. Se baja a 0,01 cuando un falso positivo
   sale caro.
3. **Explorar**: tamaño de cada grupo, medias, medianas, desviaciones, y mirar la forma con
   histograma y diagrama de caja.
4. **Comprobar supuestos**: Levene para igualdad de varianzas, y tamaño de muestra para
   apoyarse en el teorema del límite central.
5. **Elegir la prueba** según la tabla de decisión de abajo.
6. **Validar el resultado** con al menos dos respaldos: repetir sin atípicos y añadir una
   prueba no paramétrica.
7. **Reportar** el bloque completo de la sección "lo que siempre se reporta".
8. **Traducir a una recomendación accionable** y declarar las limitaciones.

## Reglas de decisión

### Qué prueba usar

| Lo que comparo | Prueba |
|---|---|
| Una media contra un valor de referencia | t de una muestra |
| Medias de dos grupos independientes | t de dos muestras (Welch por defecto) |
| Dos proporciones o tasas | prueba z de proporciones |
| Confirmar sin asumir normalidad | Mann-Whitney U |
| Igualdad de varianzas | Levene |
| Reparto de la asignación | chi cuadrado (SRM) |

### Welch o Student

Welch por defecto, siempre. Si Levene da `p < 0,05` las varianzas son desiguales y Student
queda descartado. Si Levene da `p ≥ 0,05` Student sería válido, pero Welch da
prácticamente el mismo resultado, así que no se gana nada cambiando. En código:
`stats.ttest_ind(a, b, equal_var=False)`.

### t o z

Se usa **t** siempre que la variabilidad de la población se estime desde la muestra, que
es el caso real. La **z** solo si esa variabilidad se conoce de verdad. Con n grande las
dos convergen: con n=100 el multiplicador es 1,984 frente a 1,960.

### Atípicos

No se borran por defecto. Se detectan con la regla del IQR (`Q1 − 1,5·IQR` a
`Q3 + 1,5·IQR`), se decide con criterio de dominio, y **se repite el análisis con y sin
ellos** reportando ambos. Solo se eliminan si son físicamente imposibles, y entonces se
documenta cuántas filas y qué porcentaje.

### Datos faltantes

Primero se investiga **por qué** faltan. Eliminar filas si son pocas y al azar; imputar con
mediana antes que con media; dejarlos como nulos si el modelo los maneja. Cualquier
imputación se calcula **después** de partir en entrenamiento y prueba, nunca antes, o se
mete fuga de datos.

## Lo que siempre se reporta

Nunca un valor p solo. El bloque mínimo es:

| Elemento | Por qué |
|---|---|
| Tamaño de cada grupo | Determina cuánta confianza merece la estimación |
| Medias y desviaciones | El dato crudo que sostiene todo lo demás |
| Estadístico y valor p | La evidencia contra H₀ |
| **Tamaño del efecto (Cohen's d)** | Impide confundir significativo con importante |
| **Intervalo de confianza de la diferencia** | Si cruza el cero, no hay diferencia demostrada |
| Prueba de respaldo | Descarta que el resultado sea artefacto de la forma o los extremos |
| Limitaciones | Las encuentro yo antes de que las encuentre quien revisa |

**Escala de Cohen's d**: por debajo de 0,2 es despreciable; alrededor de 0,5 es medio;
por encima de 0,8 es grande.

## Trampas que ya conozco

- **El valor p no es la probabilidad de que H₀ sea verdadera.** Es la probabilidad de ver
  un resultado así de extremo si H₀ lo fuera.
- **Con muestra grande, cualquier diferencia trivial sale significativa.** Por eso el
  tamaño del efecto es obligatorio.
- **"No rechazar H₀" no es "demostrar que son iguales".** Puede ser falta de poder
  estadístico. Se dice "no hay evidencia suficiente".
- **Un intervalo de confianza no dice que el parámetro esté ahí con 95 % de probabilidad.**
  El 95 % describe el método a la larga, no ese intervalo concreto.
- **Elegir prueba de una cola después de ver los datos es hacer trampa.** La dirección se
  decide antes y con razón de negocio.
- **Más muestra no arregla el sesgo de selección.** Solo un método de muestreo mejor.
- **Asociación no es causa.** En estudios observacionales se nombran los factores de
  confusión plausibles de forma explícita.
- **`scale` recibe el error estándar, no la desviación estándar**, al construir intervalos
  con `scipy`.
- **`ppf(0.975)` para un intervalo del 95 %**, porque el 5 % se reparte en dos colas.

## Casos de referencia, con números reales

Sirven para calibrar qué es grande y qué no. Son análisis propios, ya ejecutados.

| Caso | Comparación | Resultado | Lectura |
|---|---|---|---|
| **TikTok** | Cuentas verificadas contra no verificadas, sobre visualizaciones. n=19.084 | `t = 25,4994`, `p = 2,61e-120`, `d = −0,544`, IC [−187.626, −160.823] | Diferencia real y de magnitud media. Hallazgo secundario más fuerte: vídeos con reclamación 501.029 visualizaciones frente a 4.956 de opinión |
| **Automatidata** | Tarjeta contra efectivo, sobre tarifa de taxi. n=22.532 | `t = 6,8668`, `p = 6,80e-12`, `d = 0,0922`, IC [0,87 $, 1,56 $] | Diferencia real pero **despreciable**. El caso que demuestra que un p diminuto no implica un efecto grande |
| **Waze** | iPhone contra Android, sobre número de viajes. n=14.999 | `t = 1,4635`, `p = 0,1434`, `d = 0,0247`, IC [−0,55, 3,81] | Sin evidencia de diferencia. El intervalo cruza el cero y las tres validaciones coinciden |

Los tres se validaron igual: Levene, luego Welch, luego repetición sin atípicos, luego
Mann-Whitney. En los tres, las tres validaciones coincidieron entre sí.

## Cómo quiero los entregables

- **Documento PACE** (Plan, Analyze, Construct, Execute) como entregable escrito. Pesa más
  que el notebook, porque es lo que lee quien decide.
- **Resumen ejecutivo de una página**: hallazgo, evidencia, recomendación, limitaciones.
- **Cada decisión de limpieza documentada** con criterio, número de filas y porcentaje. No
  vale "limpié los datos".
- **La recomendación en una frase que alguien sin formación estadística pueda ejecutar.**
  "p = 0,03" no es una recomendación.
- **Código en inglés**, explicaciones en español.
- **Ningún resultado cuenta como hecho** si no está explicado en palabras simples en el
  entregable visible, aunque el número ya esté calculado en un script o un JSON.

## Vocabulario, español e inglés

Los cursos y la documentación vienen en inglés; los entregables van en español.

| Español | Inglés |
|---|---|
| Hipótesis nula / alternativa | null / alternative hypothesis |
| Nivel de significancia | significance level, alpha |
| Valor p | p-value |
| Tamaño del efecto | effect size |
| Intervalo de confianza | confidence interval |
| Error estándar | standard error |
| Grados de libertad | degrees of freedom |
| Distribución muestral | sampling distribution |
| Teorema del límite central | central limit theorem |
| Error tipo I / tipo II | type I / type II error |
| Poder estadístico | statistical power |
| Muestreo estratificado | stratified sampling |
| Sesgo de muestreo | sampling bias |
| Valor atípico | outlier |
