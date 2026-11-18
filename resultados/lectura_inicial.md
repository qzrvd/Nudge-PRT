# B-1348: resultado parcial, enero de 2025

Fuente: archivo oficial [SGPRT_RB_ene-2025.zip](https://www.prt.cl/Descargas/docs/2025/1.Enero/SGPRT_RB_ene-2025.zip), descargado el 2 de noviembre de 2026. Base: `datos/prt.sqlite`. **Cobertura actual: 1 de los 12 meses de 2025. No permite determinar el peak anual.**

Se leyeron 522.816 filas del archivo nacional. Se seleccionaron 7.422 filas de la B-1348 y se obtuvieron 7.410 registros distintos, eliminando únicamente doce filas completamente idénticas. La auditoría detectó reutilización de claves planta/fecha/certificado con diferencias en otros campos, incluidos datos vehiculares; por eso se conservan las filas distintas y se corrigió la deduplicación inicial. Hubo cero fechas inválidas o fuera de enero entre las filas seleccionadas.

| Días de enero | Revisiones únicas | Días con registros | Promedio por día con registros |
|---|---:|---:|---:|
| 1–7 | 1.106 | 5 | 221,20 |
| 8–14 | 1.492 | 6 | 248,67 |
| 15–21 | 1.781 | 6 | 296,83 |
| 22–28 | 1.912 | 6 | 318,67 |
| 29–31 | 1.119 | 3 | 373,00 |

En enero, el mayor volumen por bloque semanal se concentra entre los días 22 y 28. El final del mes muestra la mayor intensidad por día con registros. La hora 11:00–11:59 concentra 980 revisiones, el mayor volumen horario acumulado del mes.

Estas cifras cuentan atenciones realizadas, incluidos reingresos con otro certificado; no cuentan reservas, personas esperando ni vehículos únicos. Los días con registros no equivalen automáticamente a días hábiles ni a todos los días abiertos.

El manifiesto `fuentes/manifiesto_2025.json` contiene los enlaces oficiales de los doce meses. Las descargas restantes no se completaron por lentitud de la transferencia; no se reemplazan por valores estimados ni por ceros. La hoja `cobertura` del Excel y la tabla `archivos` son la referencia de los meses efectivamente importados.
