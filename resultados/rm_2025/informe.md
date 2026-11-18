# Concentración de revisiones: Región Metropolitana, clase B, 2025

Cobertura importada: **12/12 meses**. Plantas con registros: **33**.

Fuente: [descargas oficiales PRT](https://www.prt.cl/Descargas/index.html).

## Día de mayor volumen de cada mes, total RM

| Mes | Fecha | Día de la semana | Revisiones | Total mensual | % del mes |
|---|---|---|---:|---:|---:|
| 2025-01 | 2025-01-31 | viernes | 10,523 | 192,129 | 5.48% |
| 2025-02 | 2025-02-28 | viernes | 10,723 | 201,152 | 5.33% |
| 2025-03 | 2025-03-31 | lunes | 10,774 | 211,114 | 5.10% |
| 2025-04 | 2025-04-30 | miércoles | 10,923 | 176,377 | 6.19% |
| 2025-05 | 2025-05-30 | viernes | 10,918 | 187,196 | 5.83% |
| 2025-06 | 2025-06-30 | lunes | 10,874 | 171,181 | 6.35% |
| 2025-07 | 2025-07-01 | martes | 9,936 | 205,961 | 4.82% |
| 2025-08 | 2025-08-30 | sábado | 10,611 | 198,213 | 5.35% |
| 2025-09 | 2025-09-30 | martes | 12,182 | 204,199 | 5.97% |
| 2025-10 | 2025-10-30 | jueves | 12,068 | 233,003 | 5.18% |
| 2025-11 | 2025-11-03 | lunes | 11,209 | 207,327 | 5.41% |
| 2025-12 | 2025-12-01 | lunes | 10,280 | 132,472 | 7.76% |

Todos los empates se conservan. Los resultados por planta están en la hoja `peaks_por_planta` del [Excel](concentracion_rm_2025.xlsx) y en [CSV](peaks_por_planta.csv).

Las hojas `matriz_dias_rm` y `matriz_porcentaje_rm` muestran los días 1–31 de cada mes con una escala de color, en cantidad de revisiones y porcentaje del mes, respectivamente. `diario_por_planta` contiene todos los conteos, no solo el peak.

## Interpretación y límites

- Se cuentan registros publicados distintos después de eliminar filas completamente idénticas. Se incluyen reingresos; no son reservas, vehículos únicos ni tiempos de espera.
- Un día sin registros no demuestra que la planta estuviera cerrada. Los meses pendientes no se reemplazan por ceros.
- Se incluyen exclusivamente los archivos SGPRT RB. No se incluyen las categorías A1/A2.
- Si el archivo RB contiene un código de planta clase A, se conserva en la hoja `otras_clases_en_rb` y en la base, pero se excluye de los totales de plantas B/AB.
- El peak es la mayor cantidad en una fecha concreta, sin ajuste por feriados u horario de apertura. No se interpreta como un efecto puro del número del día del mes.
- El catálogo consultado en noviembre de 2026 puede describir cierres posteriores a 2025. La cobertura observada en los archivos se informa por separado.

## Archivos de origen

| Mes | Registros RM distintos | Plantas observadas | Duplicados exactos eliminados | Archivo oficial |
|---|---:|---:|---:|---|
| 2025-01 | 192,129 | 33 | 6,305 | [ZIP](https://www.prt.cl/Descargas/docs/2025/1.Enero/SGPRT_RB_ene-2025.zip) |
| 2025-02 | 201,152 | 33 | 3,485 | [ZIP](https://www.prt.cl/Descargas/docs/2025/2.Febrero/SGPRT_RB_feb-2025.zip) |
| 2025-03 | 211,114 | 33 | 853 | [ZIP](https://www.prt.cl/Descargas/docs/2025/3.Marzo/SGPRT_RB_mar-2025.zip) |
| 2025-04 | 176,377 | 33 | 773 | [ZIP](https://www.prt.cl/Descargas/docs/2025/4.Abril/SGPRT_RB_abr-2025.zip) |
| 2025-05 | 187,196 | 33 | 831 | [ZIP](https://www.prt.cl/Descargas/docs/2025/5.Mayo/SGPRT_RB_may-2025.zip) |
| 2025-06 | 171,181 | 33 | 426 | [ZIP](https://www.prt.cl/Descargas/docs/2025/6.Junio/SGPRT_RB_jun-2025.zip) |
| 2025-07 | 205,961 | 33 | 582 | [ZIP](https://www.prt.cl/Descargas/docs/2025/7.Julio/SGPRT_RB_jul-2025.zip) |
| 2025-08 | 198,213 | 33 | 632 | [ZIP](https://www.prt.cl/Descargas/docs/2025/8.Agosto/SGPRT_RB_ago-2025.zip) |
| 2025-09 | 204,199 | 33 | 910 | [ZIP](https://www.prt.cl/Descargas/docs/2025/9.Septiembre/SGPRT_RB_sep-2025.zip) |
| 2025-10 | 233,003 | 33 | 1,636 | [ZIP](https://www.prt.cl/Descargas/docs/2025/10.Octubre/SGPRT_RB_oct-2025.zip) |
| 2025-11 | 207,327 | 33 | 1,793 | [ZIP](https://www.prt.cl/Descargas/docs/2025/11.Noviembre/SGPRT_RB_nov-2025.zip) |
| 2025-12 | 132,472 | 33 | 2,286 | [ZIP](https://www.prt.cl/Descargas/docs/2025/12.Diciembre/SGPRT_RB-dic-2025.zip) |
