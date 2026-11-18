# Patrón mensual y viabilidad de la clasificación · RM 2025

En promedio, los últimos siete días concentran el 26.8% de las revisiones del mes, un 33% más que una ventana de siete días a mitad de mes.

| Ventana de 7 días | Participación mensual promedio |
|---|---:|
| Inicio: días 1–7 | 25.41% |
| Mitad: días 12–18 | 20.19% |
| Cierre: últimos 7 días reales de cada mes | 26.83% |

El cierre supera al inicio en 9 de 12 meses, y su promedio es 5.6% mayor. La U es aproximada, no una regla para todos los meses.

## Campos comprobados

Se conciliaron 2,320,324 registros de las 33 plantas B/AB contra la base diaria. 2,320,324 tienen PPU con formato reconocido y último dígito extraíble. En 0 de los 12 archivos aparece un campo explícito identificado como reingreso/reinspección/tipo de revisión.

- **PPU**: patente completa. El último dígito se deriva de ella; no se necesita publicarla.
- **COD_PRT, FEC_REVISION, HORA_INI, RESULTADO_CRT y RESULTADO_CRT_GASES**: permiten enlazar visitas y rechazos observados.
- **FEC_VENCIMIENTO**: vencimiento asociado al registro; no es por sí solo el vencimiento previo a la llegada.
- **COD_VEHICULO, COD_SERVICIO, COD_COMBUSTIBLE y ANO_FABRICACION**: ayudan a separar cohortes y excepciones.

Fuente primaria: [diccionario SGPRT RB](https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx). La hoja `campos_archivos` conserva los campos efectivamente observados en cada ZIP.

## Línea base observable para B

En la cohorte definida, 32,409 de 878,247 intentos iniciales observados ocurrieron en el mes precedente al del dígito: **3.69%**.

**Es una aproximación de uso del mes precedente, no una tasa confirmada de adelantos efectivos.** El numerador puede contener certificados vencidos de ciclos anteriores. No es la proporción del parque elegible ni incluye vehículos que nunca acudieron.

Cohorte: automóviles y station wagon de uso privado-particular, combustibles gasolina/diésel/eléctrico, fabricación 1993–2025 y PPU reconocida. No se incluyen taxis, transporte escolar ni todos los tipos B. Se excluyen órdenes temporales ambiguos y nuevas visitas dentro de 15 días de un rechazo anterior observado. Es una cohorte compatible con el calendario, no una certificación de periodicidad individual; puede incluir primeras revisiones con vigencia bienal.

Las sensibilidades de 30 días y la exclusión de la primera quincena de enero están en `linea_base_observada`. El límite de enero reconoce la falta de visitas de diciembre de 2024.

Dentro de las visitas del mes precedente, el 34.6% ocurre en sus últimos siete días y el 20.3% en los días 12–18. Mover una visita al mes anterior no asegura moverla fuera de su cierre: para evaluar B se deben medir ambos desplazamientos.

## Reingresos: inferidos, no marcados

Hay 465,415 registros compatibles con una revisita a la misma planta en los 15 días siguientes a un rechazo observado. Contando cambios de planta: 491,053. 6,133 registros comparten vehículo, fecha y hora y no permiten ordenar visitas con seguridad.

La regla requiere misma PPU, una visita estrictamente posterior y rechazo RT o gases en la visita previa. No verifica gratuidad, la condición oficial de reinspección ni visitas fuera de la RM o anteriores a 2025. Una cadena de rechazos puede producir varias revisitas; no son vehículos únicos.

Las tasas por ventana están en `revisitas_por_ventana`, sobre todos los registros B/AB. Permiten separar una posible contribución de revisitas al pico de inicio, además de las hipótesis de plazo y liquidez.

La figura `curva_sin_revisitas` compara el patrón de todos los registros B/AB con el mismo universo al excluir revisitas recientes inferidas y órdenes ambiguos; no es una identificación perfecta de primeras visitas.

## Lo que no decide el dígito

Una patente terminada en 9 revisada en diciembre puede estar anticipando enero siguiente o llegar tarde al ciclo de enero anterior. Incluso coincidir con el mes del dígito no acredita que el certificado anterior siguiera vigente.

Por eso se usan las etiquetas «mes correspondiente», «mes precedente» y «otros meses: atraso no determinado». No se renombran los otros meses como atrasos.

La hoja `mes_recien_terminado` separa los casos cuyo dígito corresponde al mes inmediatamente anterior al de la visita. Es una proximidad al calendario compatible con la hipótesis de plazo, no prueba de vencimiento ni de motivo.

El vencimiento previo se busca solo en aprobaciones anteriores observadas del mismo vehículo, nunca en el certificado emitido en la visita actual. Si falta, queda desconocido; una aprobación con fecha u orden ambiguo invalida ese antecedente. Aun cuando se encuentra, el historial RM 2025 puede omitir aprobaciones en otras regiones. La etiqueta «posterior al vencimiento previo observado» no confirma por sí sola atraso efectivo.

Para clasificar vigencia al llegar se necesita historial nacional anterior: al menos 2024 y también 2023 para ciclos bienales, manteniendo desconocido cuando falte antecedente suficiente. Las prórrogas/excepciones también deben verificarse.

**Liquidez no está observada:** un patrón al inicio del mes, aun con certificado previo vigente, no prueba que el conductor esperó el sueldo. Se necesitan fechas de pago/ingresos, encuesta o un diseño experimental para separar ese motivo de otros.

Plazo y liquidez pueden coexistir: un conductor con certificado vencido también puede haber esperado un pago. Reconstruir la vigencia identifica un estado frente al plazo, no el motivo de la decisión.

## Norma y visualización

El [artículo 7 del Decreto 156](https://www.bcn.cl/leychile/navegar?i=10183) permite efectuar la revisión en el mes precedente sin afectar su vigencia y contiene excepciones de periodicidad. Su artículo 10 describe la revisión posterior a un rechazo; aquí la ventana de 15 días es una regla de inferencia, no una marca oficial.

La curva usa la participación de cada fecha en su mes y promedia por número de día. El día 31 tiene siete meses disponibles; 29 y 30 tienen once. Se preservan los puntos reales y se añade un promedio móvil centrado de cinco días. No se ajusta una parábola para obtener una U. La comparación de tres ventanas usa siete días en todos los casos, incluyendo los últimos siete días de febrero.

Las tres ventanas no son tercios del mes y no cubren todas las fechas; su suma no tiene por qué ser 100%.

Se incluyen fechas existentes con cero registros publicados; no se afirma que estuvieran abiertas. No se ajusta por feriados ni por día de semana. La composición de cohortes se agrega por registros, mientras la curva promedia meses con igual peso.

Archivos: `curva_concentracion.png/.svg`, `curva_interactiva.html`, `composicion_inicio_cierre.png/.svg` y `calendario_y_revisitas_2025.xlsx`. No se exportan patentes ni identificadores de vehículo.
