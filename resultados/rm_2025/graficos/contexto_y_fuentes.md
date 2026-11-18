# Parque vehicular, revisión vigente y permiso de circulación

Consulta de fuentes públicas: **2 de noviembre de 2026**. El análisis de revisiones corresponde a **2025, plantas B/AB de la RM**.

## Cifra oficial verificada

Para el parque **motorizado**, el INE registra **2.442.537 vehículos en la RM en 2024**, en su tabla 11.2.2 «Vehículos motorizados en circulación, según tipo de motor y región, 2024». Su fuente es la estadística de permisos 2024.

Fuente primaria: [INE, Informe anual de estadísticas del medio ambiente 2025, tabla 11.2.2](https://www.ine.gob.cl/docs/default-source/variables-basicas-ambientales/publicaciones-y-anuarios/informe-anual-de-medio-ambiente/informe-anual-de-estadisticas-del-medio-ambiente-2025.pdf?sfvrsn=62fcb728_4). El desglose y el total se verificaron en el extracto indexado de esa tabla; el visor web rechazó abrir el PDF completo por superar su límite de tamaño.

Para el conjunto **motorizado y no motorizado**, el INE publica **2.476.153 permisos de circulación emitidos en la Región Metropolitana durante 2024**, frente a 2.400.417 en 2023: crecimiento de **3,2%**. El boletín identifica 2024 como provisional. No debe presentarse como un conteo de automóviles particulares domiciliados en la RM.

Fuente primaria: [INE, boletín de permisos 2024, tabla nacional y regional, página 4](https://regiones.ine.cl/documentos/default-source/region-iii/estadisticas/parque-de-veh%C3%ADiulos/publicaciones-y-anuarios/documentos/permisos-de-circulaci%C3%B3n---per%C3%ADodo-2024.pdf?sfvrsn=59b9aaab_4).

El [portal temático del INE](https://www.ine.gob.cl/estadisticas-por-tema/comercio-y-servicios/permisos-de-circulacion) describe estos datos como registros administrativos de permisos otorgados por las municipalidades. El [glosario de CONASET](https://www.conaset.cl/biblioteca-observatorio/glosario/) también define su parque vehicular a partir de permisos otorgados.

## Cuántos tienen la revisión vencida o no pagan el permiso

**No se encontró una cifra regional consolidada, actual y verificable para esos dos indicadores en las fuentes consultadas.** Esto no demuestra que el dato no exista en registros administrativos. No se asignó un porcentaje estimado.

El conteo INE se construye a partir de permisos emitidos: no es por sí mismo un censo de deudores. La [BCN confirma que se puede pagar en una comuna diferente a la de residencia](https://www.bcn.cl/api-leyfacil/servicio/ObtenerGuiaPublicadaHTML?uri=permiso-de-circulacion), de modo que la región emisora no identifica necesariamente el domicilio del vehículo. Nuestra base PRT cuenta revisiones realizadas, incluidos reingresos, no vehículos únicos residentes. Además, sus años y alcances son distintos. Por tanto, **restar 2.320.324 revisiones de 2025 a los 2.476.153 permisos de 2024 no mide ni revisiones vencidas ni permisos impagos**.

Tampoco una infracción detectada equivale a un vehículo distinto incumplidor, ni una tasa de incumplimiento en controles de fiscalización representa automáticamente al parque regional. No se extrapolaron controles en calle, cifras de buses interurbanos ni datos de otros países.

Para medir estos indicadores se necesita un corte temporal y un universo compatible:

- Revisión vencida: parque activo domiciliado en la RM, último certificado válido de cada vehículo, vencimiento a la fecha de corte y vehículos con homologación/exención. Las revisiones en otras regiones también deben incorporarse.
- Permiso impago: universo de vehículos obligados, pagos del año y sus cuotas, deduplicación entre municipios, exenciones y vehículos fuera de circulación. Se requieren registros municipales o un consolidado nacional conciliado.

## Marzo y el permiso de circulación

La fuente oficial [Gob.cl sobre el permiso](https://www.gob.cl/noticias/hasta-cuando-hay-plazo-para-pagar-permiso-de-circulacion/) indica que se requiere revisión vigente y describe el proceso de renovación. La [guía de BCN](https://www.bcn.cl/api-leyfacil/servicio/ObtenerGuiaPublicadaHTML?uri=permiso-de-circulacion) permite verificar las condiciones y plazos según categoría. Estas reglas hacen razonable investigar una asociación temporal; no demuestran causalidad en nuestros datos.

En la RM, marzo de 2025 tuvo **211.114 registros**, segundo en volumen anual; fue cuarto por promedio por fecha calendario (**6.810,1**). Octubre tuvo **233.003**, el mayor total y promedio diario (**7.516,2**). Marzo tuvo dos fechas sobre el percentil 90 anual; octubre, seis. El umbral común es **9.640,6 registros por fecha**.

El promedio por fecha incluye sábados, domingos y feriados. No equivale a productividad por jornada abierta. Separar un efecto del permiso requeriría varios años, calendario de operación y control de feriados y otros cambios; este informe describe un año.

## Cómo se construyen los gráficos

- **Calendario promedio:** para cada fecha se divide su conteo por el total de su mes. Se promedian esos porcentajes por número de día. Los días 29 y 30 tienen 11 observaciones y el 31 tiene 7; los demás, 12. Los 31 promedios no tienen por qué sumar 100% porque sus denominadores difieren. Se incluyen fechas existentes sin registros como cero registros publicados; esto no afirma cierre ni cero demanda.
- **Calendarios reales:** mantienen la ubicación lunes–domingo de cada mes de 2025 y muestran la participación de cada fecha en su mes. Ayudan a reconocer efectos de composición del calendario.
- **Comparación mensual:** total, promedio por fecha y cantidad de fechas sobre un mismo umbral anual P90. Distingue volumen, intensidad media y frecuencia de días de mucha actividad.
- **Distribución mensual:** cajas con mediana, media y dispersión diaria. Permiten reconocer si el mes completo está cargado o si sobresalen pocas fechas.
- **Horas:** usa HORA_INI del archivo original, la recepción del vehículo según el diccionario. No mide la fila exterior ni duración de espera. La extracción se concilia contra la base diaria antes de incorporarse.
- La extracción horaria cubre los doce meses y reproduce los **2.320.324 registros** de la base diaria. No hubo horas sin interpretar. Se conservaron cinco registros con hora 00; una hora interpretable no garantiza que su registro de origen sea exacto ni demuestra apertura a medianoche.
- **Mapas de día × hora:** cada fila muestra la distribución porcentual dentro de ese día de semana o número de día del mes, usando solo horas válidas. Una fila sin registros queda vacía.

Fuentes de revisiones: [descargas PRT/MTT](https://www.prt.cl/Descargas/index.html) y [diccionario SGPRT RB](https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx). Se mantienen el alcance de 33 plantas B/AB, la eliminación de duplicados exactos y la exclusión auditada de dos registros con código de planta clase A.
