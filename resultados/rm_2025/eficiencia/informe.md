# Rapidez registrada y días peak · RM 2025

**Cobertura: 12/12 meses; 2,320,324 registros; 95.94% con duración positiva.**

| Comparación ajustada | Día habitual | Día peak | Diferencia peak − habitual |
|---|---:|---:|---:|
| Mediana | 17.0 min | 20.0 min | +3.0 min |
| P90 | 42.0 min | 58.0 min | +16.0 min |

Soporte común: 86.6% de tiempos positivos peak y 33.0% de habituales; 33 plantas comparadas.

## Días de semana con mezcla comparable

| Día | Mediana ajustada | P90 ajustado |
|---|---:|---:|
| Lunes | 17.0 min | 43.0 min |
| Martes | 17.0 min | 43.0 min |
| Miércoles | 17.0 min | 43.0 min |
| Jueves | 17.0 min | 43.0 min |
| Viernes | 17.0 min | 45.0 min |
| Sábado | 19.0 min | 55.0 min |

## Disponibilidad de tiempos por tipo de día

| Tipo | Registros publicados | Duraciones positivas | Cobertura |
|---|---:|---:|---:|
| Habitual | 1,938,169 | 1,857,536 | 95.84% |
| Peak | 382,155 | 368,478 | 96.42% |

## Fechas de máximo volumen regional mensual

Comparación ajustada usando las mismas fechas peak regionales del informe anterior, en lugar de peaks por planta/mes.

| Tipo de fecha | Mediana | P90 | % de tiempos positivos comparables |
|---|---:|---:|---:|
| Otras fechas | 17.0 min | 43.0 min | 13.1% |
| Máximo regional del mes | 20.0 min | 61.0 min | 85.2% |

La sensibilidad por hora de inicio tiene soporte reducido y se considera exploratoria; no se interpreta como una estimación general de toda la RM.


## Qué se mide

Duración registrada = HORA_FIN − HORA_INI. Según el diccionario oficial, va de recepción en planta a término de revisión. Puede incluir esperas internas; no incluye necesariamente la fila exterior. No es tiempo puro de inspección ni productividad por trabajador/línea.

Se conservan solo diferencias positivas dentro del mismo día en las comparaciones de tiempo. Ceros, horas no interpretables y fin anterior al inicio se auditan por separado. Sin fecha de término no se inventa un cruce de medianoche. Se mantienen todos los tiempos positivos en el análisis principal; las sensibilidades limitan a cuatro horas y a plantas/meses con al menos 95% de duraciones positivas.

## Cómo se definen y comparan los peaks

Un día peak supera el percentil 90 del volumen de su propia planta y mes, entre fechas con registros. Se requieren al menos 15 fechas por planta/mes. El volumen incluye todos los registros distintos, aunque carezcan de duración utilizable. Por eso no se confunden plantas grandes con plantas congestionadas.

La comparación ajustada usa grupos de misma planta, mes, día de semana, resultado y tipo de vehículo. Cada grupo necesita al menos 20 tiempos positivos tanto en peaks como en días habituales. Dentro de cada planta, ambas categorías se reponderan a la mezcla de casos de sus peaks. Cada planta tiene el mismo peso regional. Los cuantiles provienen de la distribución estandarizada de tiempos, no del promedio de medianas. Se informa la cobertura del soporte común. El ajuste por hora se muestra como sensibilidad separada, porque cambia la población comparable y la hora puede formar parte del mecanismo de congestión.

La hoja `peaks_regionales_ajustados` repite el ajuste para las fechas de mayor volumen regional de cada mes (las mismas del informe anterior), en lugar de definir el peak dentro de cada planta. Ambas definiciones se mantienen identificadas y no se intercambian.

La comparación por día de semana usa una misma mezcla de planta/mes/resultado/tipo en lunes a sábado, con al menos 20 casos por grupo en cada uno de los seis días. Cada planta pesa lo mismo. Se conservan los empates en los rankings.

El calendario por número de día es una vista descriptiva diferente: mediana de índices de duración diaria / mediana de su propia planta y mes × 100. Incluye fechas/planta con al menos 30 duraciones positivas y 80% de cobertura. Un índice menor de 100 indica menor duración relativa. No ajusta tipo de vehículo, resultado ni día de semana y no sirve para atribuir un efecto al número de día.

## Interpretación

Son asociaciones observadas en 2025. El resultado no demuestra que la congestión cause un cambio de duración ni que una revisión más corta tenga la misma calidad. Se incluyen reingresos y el ajuste no identifica su efecto ni controla complejidad mecánica o dotación. Faltan líneas abiertas y recursos para medir productividad. Los vehículos que abandonan la fila y la espera antes de recepción no están representados. Una mediana menor y un P90 mayor pueden coexistir: el servicio típico puede ser rápido y la cola de demoras larga.

Fuente: [PRT/MTT, archivos SGPRT RB 2025](https://www.prt.cl/Descargas/index.html) y [diccionario de campos](https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx). Se conserva la misma deduplicación y alcance de 33 plantas B/AB de la RM del análisis anterior. Los conteos por planta/fecha se concilian antes de incorporar cada mes.
