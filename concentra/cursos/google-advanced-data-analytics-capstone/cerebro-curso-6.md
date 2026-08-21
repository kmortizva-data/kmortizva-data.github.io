# Cerebro: empaquetar el trabajo y trabajar con IA generativa

Manual de operación, no material de estudio. Cubre las dos cosas que deja este curso: cómo
se convierte un análisis en algo que alguien quiera leer, y cómo se usa un modelo generativo
sin que te cuele un error con cara de respuesta. Pégalo como memoria y asume estas reglas
sin preguntarlas.

## Qué resuelvo con esto

Un análisis correcto que nadie lee no ha servido de nada, y una respuesta rápida de un modelo
que resulta ser falsa cuesta más que no haberla pedido. Las dos mitades de este cerebro son
las dos formas de que el trabajo bueno se pierda.

---

# Parte 1. Empaquetar

## La regla que ordena todo lo demás

**Nadie va a leer tu cuaderno.** Van a leer tres frases y a mirar una figura, y con eso
deciden si te preguntan más. Todo lo demás existe para sostener esas tres frases cuando
alguien las cuestione.

De ahí sale el orden de un entregable, que es el inverso del orden en que trabajaste:

| Orden en que se escribe | Orden en que se lee |
|---|---|
| Datos, limpieza, modelo, resultado | **Resultado, qué se decide, y solo después cómo** |

## Las capas de un proyecto, y para quién es cada una

| Capa | Quién la lee | Cuánto tarda en leerla |
|---|---|---|
| Una frase | Quien decide | 5 segundos |
| Resumen ejecutivo | Quien paga | 2 minutos |
| Ficha de caso | Quien duda | 10 minutos |
| Informe PACE | Quien audita | media hora |
| Cuaderno y guion | Quien reproduce | lo que haga falta |

**Las cinco cuentan la misma historia.** Si la frase y el informe no dicen lo mismo, el
problema no es de formato.

## Qué hace bueno a un proyecto de portafolio

No es el modelo. Es esto, en este orden:

1. **Una pregunta que alguien tenía.** «Predecir el abandono para actuar antes» es una
   pregunta. «Aplicar random forest» es un ejercicio.
2. **Una decisión que cambia con la respuesta.** Si nadie va a hacer nada distinto, no había
   proyecto.
3. **Un número que se puede defender**, con su incertidumbre y su conjunto de prueba mirado
   una sola vez.
4. **Lo que no funcionó**, contado con el mismo detalle que lo que funcionó. Es lo que
   separa un portafolio de un anuncio.
5. **Los límites**, escritos por ti antes de que te los encuentren.

## Lo que hunde un portafolio

- **Repetir el tutorial.** Los mismos tres datasets con el mismo modelo que hicieron otras
  cinco mil personas. Si vas a usarlos, **haz una pregunta que el exemplar no hizo**.
- **Enseñar solo lo que salió bien.** Un proyecto sin un solo callejón sin salida no parece
  impecable, parece incompleto.
- **Métricas sin decisión.** Un AUC de 0,86 no es un resultado; «se contacta al 20 % de mayor
  riesgo y se recupera al 62 %» sí.
- **Un cuaderno de 400 celdas como entregable principal.**
- **Números que no cuadran entre documentos.** Se arregla mecánicamente: que todo salga de un
  único archivo de resultados y que nada se teclee dos veces.

## La regla del número único

**Ningún documento cita una cifra que no esté en el archivo de resultados que generó el
código.** No es burocracia: es lo que hace imposible que el resumen diga 0,86 y la ficha
0,84 porque alguien reajustó algo y olvidó actualizar un párrafo.

---

# Parte 2. La IA generativa como herramienta

## Dónde ayuda y dónde miente

| Tarea | ¿Sirve? | Por qué |
|---|---|---|
| Escribir código repetitivo | **Sí** | Lo verificas ejecutándolo |
| Explicar un error | **Sí** | Te ahorra buscar, y lo compruebas |
| Sugerir enfoques que no se te ocurrieron | **Sí** | Los evalúas tú |
| Redactar el primer borrador de un resumen | **Sí, con revisión** | Tú tienes los números |
| **Calcular un número** | **No** | No calcula: predice texto que parece un número |
| **Decir si un resultado es significativo** | **No** | Eso sale de tus datos, no de su entrenamiento |
| **Recordar qué hay en tu archivo** | **No** | No lo ha visto, y aun así contestará |

La línea es de una simplicidad brutal: **sirve para lo que puedes verificar barato y no
sirve para lo que tendrías que creerte**.

## La regla de las tres preguntas, antes de usar una respuesta

1. **¿Puedo comprobarlo en menos tiempo del que me ahorró?** Si no, no lo uso.
2. **¿Sabría detectar que está mal?** Si el tema es nuevo para ti, la respuesta suele ser no,
   y ahí es justo donde más peligroso es.
3. **¿Estoy pidiendo que genere o que recuerde?** Generar va bien. Recordar datos concretos,
   cifras, referencias o qué dice tu archivo, va mal.

## Cómo se pide bien

- **Dale el contexto en vez de pedirle que lo adivine.** Pegar la salida real de un `describe`
  vale más que describirla con palabras.
- **Pide el razonamiento, no solo el resultado.** Un razonamiento se audita; un número
  suelto, no.
- **Pide varias opciones y elige tú.** Es su mejor uso: ampliar lo que se te ocurre.
- **Nunca le pidas el número final de un informe.** Ese sale del código.

## Y la que se olvida siempre

**Lo que pegas, lo publicas.** Datos de una empresa, un archivo con personas dentro o una
clave no se pegan en un servicio externo. En este proyecto eso ya es regla: las claves nunca
viajan y los CSV no se copian.

## Lo que no cambia por usar un modelo

**Sigues firmando tú.** Si el código que te dio tiene una fuga de información, la fuga es
tuya. Si el gráfico que sugirió engaña, engaña con tu nombre.

De ahí sale la única regla que hace falta recordar: **si no puedes explicar una línea, no la
pones en un entregable.**

---

## Vocabulario español e inglés

| Español | Inglés |
|---|---|
| Proyecto final | Capstone project |
| Portafolio | Portfolio |
| Resumen ejecutivo | Executive summary |
| Ficha de caso | Case study |
| Currículum | Resume, CV |
| IA generativa | Generative AI |
| Instrucción, indicación | Prompt |
| Alucinación | Hallucination |
| Verificable | Verifiable |
| Insignia del certificado | Certificate badge |
