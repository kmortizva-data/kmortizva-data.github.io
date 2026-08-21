# Automatidata, Curso 5: resumen ejecutivo

## La respuesta

**No se puede.** Los datos del viaje no dicen quién va a dejar una propina generosa.

| Modelo | Exactitud | Sensibilidad | AUC |
|---|---|---|---|
| Contestar siempre «no generoso» | 0,7688 | 0,0000 | 0,5000 |
| Regresión logística | 0,7688 | **0,0000** | 0,5395 |
| Bosque ajustado | 0,7688 | **0,0000** | 0,6073 |
| Refuerzo ajustado (xgboost) | 0,7708 | 0,0128 | 0,6104 |

**La logística y el bosque no señalan absolutamente a nadie.** Toman exactamente las mismas
decisiones que un modelo que contesta siempre que no, y por eso su exactitud es idéntica a
la de ese modelo hasta el cuarto decimal.

El refuerzo señala a alguien: detecta al **1,28 %** de los generosos.

## Un matiz que este proyecto sí tiene y los otros dos no

**Aquí los árboles le ganan a la logística.** 0,6073 y 0,6104 de AUC contra 0,5395, que es
la primera vez en todo el curso.

Y no significa lo que parece. Ordenan mejor los casos, sí, pero **con el umbral por defecto
ninguno señala a nadie**. Es ganar una carrera que pierden todos.

Ese matiz vale la pena guardarlo: **un AUC mejor no es un modelo utilizable.** El AUC mide
si sabes ordenar; la sensibilidad mide si sirves para decidir.

## Dos decisiones que se tomaron antes de modelar, y por qué

### 1. Solo pagos con tarjeta

| Tipo de pago | Viajes | Con propina cero |
|---|---|---|
| Tarjeta | 15.265 | 4,1 % |
| Efectivo | 7.267 | **100 %** |
| Sin cargo | 121 | **100 %** |
| Disputa | 46 | **100 %** |

**El taxímetro no registra la propina en efectivo.** No es que esa gente no dé propina: es
que el aparato solo apunta la de la tarjeta.

Entrenar con el archivo entero le enseñaría al modelo *«efectivo, luego no hay propina»*, que
es una propiedad de la máquina disfrazada de hallazgo, y produciría un modelo excelente por
la razón equivocada. **El exemplar oficial hace exactamente eso.** Aquí se apartan 7.434
viajes y se dice por qué.

### 2. Generoso es pasar del botón, no dejar algo

| | |
|---|---|
| Mediana de la propina con tarjeta | **19,97 %** |
| Viajes que dejan **exactamente** el 20,00 % | 4.363, el **28,7 %** |
| Viajes en uno de los tres botones (20, 25, 30) | el **43,1 %** |

La distribución tiene tres torres, y son los tres botones que ofrece la máquina. **Quien
pulsa el botón por defecto no decidió ser generoso: aceptó.** Y la mediana cae justo en ese
botón, o sea que la mitad de los pasajeros no elige.

Por eso el umbral es **por encima del 20 %**, leído de la distribución y no elegido. Con él,
los generosos son el **23,11 %**.

## Y una fuga comprobada, no supuesta

`total_amount` **incluye** `tip_amount`. Verificado: la suma de las partes coincide con el
total en **22.656 de 22.699** viajes.

Así que esa columna no puede ser una variable predictora, porque contiene la respuesta. El
coste antes de propina se reconstruye como `total_amount − tip_amount`, que es lo que el
pasajero ve en la pantalla cuando le sale el aviso.

## Lo que sí se puede decir

**Dar propina generosa es una decisión de la persona, no del viaje.** Ni la distancia, ni la
duración, ni la hora, ni lo que costó predicen quién pasa del botón por defecto.

La variable más importante del bosque es el coste antes de propina, con 0,3757, y es la
variable más importante de un modelo con un AUC de 0,6073. **Un reparto de importancia sobre
un modelo que no funciona sigue sumando 1**, y leerlo sin comprobar antes si el modelo
acierta produce conclusiones sobre nada.

## Qué se decide con esto

1. **No construir esto.** El encargo no se puede cumplir con los datos disponibles, y decirlo
   es el entregable.
2. **Si de verdad hiciera falta**, lo que hay que conseguir es información del pasajero, no
   más variables del viaje: historial de propinas, si es habitual, la app por la que pidió.
   Nada de eso está en el archivo.
3. **Mirar el botón por defecto**, que es la palanca de verdad. El 28,7 % de los pasajeros
   deja exactamente lo que la máquina propone. **Mover ese botón mueve más dinero que
   cualquier modelo**, y eso sí se puede probar con un experimento A/B como los del Curso 3.

## Limitaciones

- Un año, una ciudad, y el archivo es **una muestra** de los viajes de 2017.
- **Se descartan 7.434 viajes** por no tener propina registrada. Si quien paga en efectivo
  se comporta distinto, esta conclusión no se le aplica.
- El umbral del 20 % es defendible pero no es el único. Con «pasar del 15 %» los generosos
  serían el 77 % y el problema cambiaría de forma.
- **La prueba se miró una vez.** El campeón se eligió en validación, y fue el refuerzo.
