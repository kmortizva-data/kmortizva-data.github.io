# Cerebro: explorar, limpiar y contar

Manual de operación, no material de estudio. Describe cómo abro un archivo que no he visto
nunca, qué decido sobre lo que falta y lo que sobra, y cómo presento el resultado. Pégalo
como memoria y asume estas reglas sin preguntarlas.

Va antes que los otros dos cerebros: comparar grupos o ajustar un modelo sobre un dato que
no se ha mirado es construir sobre arena.

## Lo primero, siempre: las cinco líneas

Antes de opinar nada sobre un archivo:

| Línea | Qué contesta |
|---|---|
| `df.shape` | El tamaño del problema. ¿500 filas o 700.000? |
| `df.info()` | Los tipos y los no nulos de golpe. Aquí salen las fechas leídas como texto |
| `df.describe()` | Mínimos y máximos. La pregunta no es qué números salen, sino **cuáles son imposibles** |
| `df.head(10)` | Cómo es una fila de verdad. Esto no lo sustituye ningún resumen |
| `df.isna().sum()` | Dónde están los huecos y cuántos son |

Un mínimo negativo en una tarifa, un máximo de 999,99 en una columna acotada o una fecha de
1970 son hallazgos, no ruido.

## Las seis prácticas del análisis exploratorio

Son iterativas y no lineales: se vuelve a la anterior todas las veces que haga falta.

| Práctica | Qué es |
|---|---|
| **Descubrir** | Conocer forma, tamaño y contenido |
| **Estructurar** | Ordenar, agrupar, pivotar, separar columnas |
| **Limpiar** | Ausentes, duplicados, atípicos, tipos mal leídos |
| **Unir** | Traer datos de otra fuente para completar el cuadro |
| **Validar** | Comprobar que lo que acabas de hacer no rompió nada |
| **Presentar** | Entregarlo a alguien que va a decidir |

**Validar no es opcional y es la que más se salta.** Después de cada transformación:
¿siguen siendo las mismas filas? ¿los totales cuadran? ¿algún valor se volvió nulo?

## Qué hacer con lo que falta

Primero la pregunta que casi nadie hace: **¿por qué falta?** No es lo mismo un sensor que se
apagó que una respuesta que la gente evita contestar.

| Situación | Qué hago |
|---|---|
| Faltan al azar y son pocos | Eliminar esas filas, diciendo cuántas |
| Faltan al azar y son muchos | Imputar, y decir con qué y por qué |
| **No faltan al azar** | Ni eliminar ni imputar sin avisar: la ausencia **es** información |
| Falta una columna entera casi siempre | Quitar la columna, no las filas |

**Antes de eliminar un grupo con datos ausentes, compáralo con el resto.** Si se parece, se
puede quitar. Si no, quitarlo cambia a quién describe el análisis, y hay que decirlo.

## Qué hacer con un atípico

Un valor extremo no es un error hasta que se demuestra. Tres respuestas legítimas, y
ninguna es "borrarlo porque afea el gráfico":

1. **Mantenerlo.** Si es real, es el dato más informativo que tienes.
2. **Recortarlo** al percentil alto. Conserva la fila y le quita el dominio.
3. **Eliminarlo**, solo si es imposible: una tarifa negativa, un viaje que acaba antes de
   empezar, una edad de 200 años.

La regla del rango intercuartílico marca candidatos: fuera de `Q1 − 1,5 × IQR` o
`Q3 + 1,5 × IQR`. **Marca candidatos, no culpables.**

Y un detalle que confunde: hay varias convenciones para calcular los cuartiles. `numpy`
interpola y otra escuela usa la mediana de cada mitad, así que Q1 y Q3 pueden salir
distintos con los mismos datos. Rara vez cambia el veredicto, pero conviene decir cuál se
usó.

## Reglas de limpieza que no se negocian

- **Nunca se sobrescribe el archivo original.** La limpieza produce un archivo nuevo.
- **Cada decisión se escribe**, con su conteo: cuántas filas, por qué motivo.
- **Los duplicados se investigan antes de borrarse.** Una fila repetida puede ser un error
  de carga o dos hechos idénticos legítimos.
- **Codificación de categorías:** una columna de unos y ceros por nivel menos uno. Nunca
  1, 2, 3, que le impone al modelo un orden que no existe.
- **Validación de entrada:** rangos, tipos y valores permitidos, comprobados al leer, no
  cuando el resultado sale raro.
- **Datos personales:** si el archivo identifica a personas, se anonimiza antes de nada.
  Nombre, correo, teléfono y coordenadas exactas son identificables.

## Reglas de un gráfico que se sostiene

- **Dibuja antes de resumir.** El cuarteto de Anscombe son cuatro conjuntos con la misma
  media, la misma desviación, la misma correlación y la misma recta, y cuatro formas
  completamente distintas. El resumen no vio ninguna.
- **El número de barras de un histograma cambia la historia.** Pocas barras aplanan dos
  grupos en uno. Prueba varios cortes antes de concluir.
- **Un panel por grupo**, y si se comparan, con los mismos ejes. Escalas distintas hacen que
  cosas distintas parezcan iguales.
- **El eje vertical empieza en cero** en un gráfico de barras. Recortarlo exagera
  diferencias.
- **Escala logarítmica** cuando el dato abarca órdenes de magnitud, con marcas legibles.
- **Escribe en el gráfico qué hay que mirar.** Si hace falta un párrafo aparte para
  entenderlo, el gráfico no está terminado.
- **Accesibilidad:** que se entienda en blanco y negro y con daltonismo. El color no puede
  ser el único portador del significado.

## Cómo se presenta un hallazgo

1. **El hallazgo primero**, en una frase con su número y sus unidades.
2. **Qué decisión cambia.** Si no cambia ninguna, no es un hallazgo, es un dato.
3. **Qué no permite afirmar todavía.** Las limitaciones que declaras tú son parte del
   resultado; las que descubre otro después son un problema de credibilidad.
4. **Y solo entonces**, cómo se hizo.

## Trampas que ya conozco

- **Un promedio puede esconder una tendencia.** Seis meses que promedian 85,5 pueden ser
  una caída constante de un punto al mes.
- **Media y mediana pueden coincidir y no describir a nadie**, si los datos están en dos o
  tres grupos separados.
- **Una fecha leída como texto se ordena alfabéticamente**, así que noviembre va antes que
  septiembre y nadie avisa.
- **`df.describe()` solo mira las columnas numéricas** por defecto. Las de texto, con sus
  categorías inesperadas, hay que pedirlas aparte.
- **Eliminar filas cambia el denominador de todos los porcentajes** que calcules después.
- **El dato agregado ya perdió información.** Si te dan medias por grupo, no puedes
  recuperar la dispersión que había dentro.

## Casos de referencia, con números reales

Sirven para calibrar qué es normal, qué es extremo y qué es imposible. Son exploraciones
propias sobre los mismos tres archivos que usan los cursos siguientes, y todos los números
salen de `projects/curso2/<caso>/04_reports/model_results.json`.

| Caso | El archivo | Lo que encontró la exploración | Lección |
|---|---|---|---|
| **Waze** | 14.999 usuarios, 13 columnas, 700 sin etiqueta (4,67 %) | **461 usuarios conducen más de 24 horas en un solo día**, hasta 172 horas; 1.994 pasan de 1.000 km por día conducido; 1.024 condujeron cero días | Lo imposible no lo encuentra ninguna regla estadística: el archivo pasa las comprobaciones de rutina y aun así una columna no mide lo que dice medir |
| **TikTok** | 19.382 vídeos, 298 incompletos (1,54 %) con las siete columnas ausentes a la vez | Una reclamación se ve **101,1 veces** más que una opinión: 501.029,5 vistas medias frente a 4.956,4, y las dos montañas no se solapan en escala logarítmica | El hallazgo estaba en el reparto, sin prueba estadística; y la regla del IQR no marcó ni un candidato en la columna más extrema del archivo |
| **Automatidata** | 22.699 viajes, sin ausentes ni duplicados, fechas leídas como texto | **197 viajes imposibles** (148 de distancia cero, 33 sin pasajeros, 27 que acaban antes de empezar, 20 de tarifa cero o negativa); el **29,5 % del día** ocurre entre las 17 y las 21 (6.695 viajes), con 6,2 veces más carreras a las 19 que a las 4 | Los 514 viajes de 52,00 $ exactos no eran atípicos: 513 llevan el código de tarifa plana del aeropuerto. Un filtro automático los habría borrado por caros |

Los tres se exploraron con las mismas seis pasadas: forma, ausentes, tipos, categorías,
candidatos a atípico e imposibles, que los declara quien conoce el dominio.

## Vocabulario, español e inglés

| Español | Inglés |
|---|---|
| Análisis exploratorio | exploratory data analysis (EDA) |
| Descubrir, estructurar, limpiar, unir, validar, presentar | discovering, structuring, cleaning, joining, validating, presenting |
| Valor ausente | missing value |
| Imputar | to impute |
| Valor atípico | outlier |
| Rango intercuartílico | interquartile range (IQR) |
| Duplicado | duplicate |
| Codificación one-hot | one-hot encoding |
| Validación de entrada | input validation |
| Datos personales identificables | personally identifiable information (PII) |
| Ciclo de vida de la visualización | visualization life cycle |
| Panel de control | dashboard |
| Relato con datos | data storytelling |
