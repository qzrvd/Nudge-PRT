# Flujo de revisiones técnicas: B-1348, Maipú, 2025

## Archivos grandes y GitHub

El repositorio conserva código, fuentes documentadas y resultados agregados
(CSV, Excel, gráficos e informes HTML). Las bases SQLite de `datos/`, los ZIP
originales de `fuentes/`, el entorno virtual y la clave local de enlace están
excluidos mediante `.gitignore`; permanecen en el computador donde se generan.

Los enlaces oficiales de los doce archivos originales están en
[`fuentes/manifiesto_2025.json`](fuentes/manifiesto_2025.json). Las instrucciones
de este documento permiten descargar y procesar nuevamente esos archivos.
Conservar una copia aparte de `datos/.clave_calendario` si se necesita enlazar
futuros años con los identificadores de la base local existente.

GitHub bloquea archivos mayores de 100 MiB en Git normal. Si una base grande ya
entró en un commit, eliminarla en un commit posterior no la quita del historial.
Para un único commit inicial todavía no publicado, se puede retirar del índice
con `git rm --cached -- datos/rm_2025.sqlite datos/prt.sqlite` y corregir ese
commit con `git commit --amend --no-edit`, incluyendo antes `.gitignore`.
`--cached` conserva las bases en el disco. Este procedimiento se aplica al
commit inicial no publicado; un historial compartido requiere otro tratamiento.

Referencia: [GitHub: archivos grandes y commits no publicados](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## Análisis regional ampliado de 2025

### Curva mensual, patentes y revisitas observadas

```powershell
python -u calendario_eventos_rm.py
.\.venv\Scripts\python.exe patron_mensual.py
.\.venv\Scripts\python.exe -m unittest test_patron_mensual -v
```

La extracción verifica los campos reales de los doce ZIP, conserva el último dígito y usa un identificador HMAC para enlazar visitas. La clave local `datos/.clave_calendario` no se exporta y debe conservarse para poder enlazar futuros años con el mismo identificador. Los informes no contienen patentes ni identificadores de vehículo.

`resultados/rm_2025/patron_calendario/` contiene una curva simple para presentación, ventanas comparables de siete días, composición por calendario, auditoría de revisitas y Excel. Las revisitas son inferidas a partir de rechazos recientes; no existe una marca oficial en los campos publicados verificados. La línea base de uso del mes precedente es una aproximación observable, no adelanto efectivo confirmado. No se convierte «otros meses» en «atrasos». El historial nacional anterior y las excepciones de vigencia son necesarios para clasificar atraso real; el motivo de liquidez requiere información adicional.

### Duración y días peak

```powershell
python -u duraciones_rm.py
.\.venv\Scripts\python.exe eficiencia_rm.py
.\.venv\Scripts\python.exe -m unittest test_duraciones_rm test_eficiencia_rm -v
```

El extractor conserva histogramas anónimos de duración de recepción a término, junto con hora de inicio, resultado y tipo de vehículo. Concilia los registros por planta/fecha y el SHA-256 de cada ZIP. No conserva patentes ni certificados. Ceros y términos anteriores al inicio se auditan y no se convierten en tiempos artificiales.

El análisis principal define peaks por el P90 del volumen dentro de cada planta y mes. Compara distribuciones estandarizadas de tiempos en grupos de misma planta, mes, día de semana, resultado y tipo, con mínimo 20 casos positivos en ambos grupos. Cada planta pesa lo mismo. La cobertura del soporte común se publica; también se compara usando las fechas peak regionales del informe previo. El ranking por día de semana conserva empates y usa un mismo soporte para los seis días.

Las salidas quedan en `resultados/rm_2025/eficiencia/`: Excel, CSV, gráficos PNG/SVG e informe interactivo. Son medidas descriptivas de rapidez registrada. Faltan fila exterior, dotación y líneas abiertas para medir espera total o productividad; una menor duración no demuestra igual calidad.

### Calendarios y análisis por hora

`horas_rm.py` relee los ZIP ya descargados y agrega la hora de recepción sin guardar identificadores vehiculares. Cada mes se incorpora únicamente si sus conteos por planta y fecha coinciden exactamente con la base diaria existente. La cobertura se registra en `horas_importadas`.

```powershell
python -u horas_rm.py
python -m pip install -r requirements-graficos.txt
python graficos_rm.py
```

Los gráficos, PNG/SVG exportables, informe interactivo sin conexión, datos y fuentes quedan en `resultados/rm_2025/graficos/`. El calendario promedio usa participaciones mensuales y solo meses donde cada número de día existe. Los calendarios reales mantienen la ubicación lunes–domingo de 2025. El informe distingue el conteo de permisos INE de los registros de revisiones PRT y documenta qué datos faltan para medir vencimiento e impago.

La hora de inicio no equivale a espera fuera de planta. Los mapas por hora muestran porcentajes dentro de cada día de semana o número de día del mes. Los CSV y el Excel complementario permiten revisar los denominadores y las horas que no se pudieron interpretar.

El análisis regional usa todos los registros SGPRT RB de plantas de región 13, separados por planta. La base regional es `datos/rm_2025.sqlite` y no modifica la base de la B-1348.

```powershell
python -u rm_2025.py --workers 1
python rm_2025.py --export-only
```

El descargador reanuda archivos parciales mediante HTTP Range, valida tamaño y CRC del ZIP y registra el SHA-256 de cada archivo. Los resultados y la cobertura actual se guardan en `resultados/rm_2025/`. El Excel incluye peaks por mes de la RM y por planta, conteos diarios, matriz de días 1–31 y auditoría de cobertura. El porcentaje es la participación de esa fecha en su propio total mensual. Se conservan los empates.

La base regional guarda únicamente conteos por planta y fecha, sin identificadores de vehículos. El catálogo incluye plantas históricas y puede contener observaciones de cierre posteriores a 2025; el informe distingue las plantas efectivamente observadas. Meses pendientes y días sin registros no se interpretan como cero demanda.

La prueba `python -m unittest test_rm_2025 -v` verifica el filtro regional, certificados reutilizados, duplicados exactos, empates y el denominador regional. El lector optimizado reprodujo las 522.816 filas nacionales, 198.434 filas RM y 192.129 registros distintos de enero calculados por el lector original.

## Análisis inicial de una planta

Objetivo: identificar el mes de mayor volumen de 2025 y las semanas de mayor actividad dentro de cada mes en la planta UVT B-1348. La unidad es **una revisión técnica efectuada**, incluidos reingresos con otro certificado. No equivale a solicitudes de reserva ni a vehículos únicos.

## Fuente comprobada el 2 de noviembre de 2026

- [Descargas oficiales PRT / MTT](https://www.prt.cl/Descargas/index.html): archivos mensuales SGPRT, clase RB.
- [Diccionario de campos RB](https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx).
- [Catálogo de plantas](https://www.prt.cl/Descargas/docs/Codigos_Plantas.xlsx): B-1348, región 13, Maipú, Revisiones Técnicas UVT S.A., sistema SGPRT.
- [Referencia aportada: HistorialPRT](https://www.historialprt.cl/planta/B-1348). Sus acumulados abarcan otro período; no se usan para inferir el flujo de 2025.
- [Consulta oficial de estadísticas por planta](https://www.prt.cl/paginas/estadisticas.aspx): la interfaz publicada restringe la consulta de atenciones a cinco meses; para 2025 se necesitan los archivos históricos.

## Archivos

- `esquema.sql`: tablas de plantas, procedencia de archivos y revisiones; vistas por año, mes, día, semana y hora.
- `prt.py`: descubre los enlaces reales publicados, descarga los ZIP, filtra la planta, importa en SQLite y exporta CSV y Excel.
- `fuentes/`: página de descarga y diccionarios oficiales; manifiesto de los doce meses cuando se complete su descubrimiento.
- `datos/prt.sqlite`: base analítica local.
- `resultados/analisis_2025.xlsx`: exportación cuando haya datos importados. La hoja `cobertura` indica qué meses están realmente cargados.

## Uso

```powershell
python -m pip install -r requirements.txt
python -u prt.py --year 2025
```

La ejecución retoma meses ya importados. Conserva los ZIP para evitar repetir descargas. Un archivo incompleto queda como `.part` y no se importa. Requiere acceso de red a prt.cl; usa los certificados del sistema con `truststore`, sin desactivar la validación TLS.

```powershell
python -u prt.py --year 2025 --discover-only
python -u prt.py --year 2025 --months 1
python prt.py --year 2025 --export-only
```

El proyecto está configurado para una planta y un año por base. Para otra combinación debe usarse una copia del proyecto con una base nueva; no se deben mezclar ejecuciones con distintos parámetros sobre la misma base.

## Cómo interpretar las semanas y los peaks

`flujo_semana_mes` usa bloques 1–7, 8–14, 15–21, 22–28 y 29–fin. Se muestran el total y el promedio por día **con registros**. El quinto bloque es más corto, por lo que no debe compararse solo por total. `flujo_semanal_calendario` agrupa de lunes a domingo, incluso cuando una semana cruza el límite del mes.

El promedio por día con registros no es un promedio por día hábil ni por día abierto: falta verificar feriados, horarios y cierres. Un día ausente puede representar cierre o falta de datos. No se reemplazan ausencias por cero sin esa comprobación. Un mes descargado tampoco garantiza que el MTT tenga el 100% de las atenciones de la planta.

Para concluir sobre 2025 deben existir los doce meses en `archivos`, verificar fechas mínima/máxima, inspeccionar discontinuidades diarias y contrastar los totales. El script rechaza meses sin registros de la planta o con fechas inválidas/fuera de período. Registra filas originales, filas filtradas, revisiones únicas y SHA-256 del archivo. No debe afirmarse un peak anual con cobertura parcial.

`HORA_INI` corresponde, según el diccionario, a la recepción del vehículo en la planta, y `HORA_FIN` al término de su revisión. No permiten aislar el tiempo en la fila exterior. El volumen observado depende tanto de las llegadas como de la capacidad de atención; no demuestra demanda insatisfecha.

No se almacenan patentes, VIN, números de motor ni chasis en la base analítica. Los ZIP originales sí contienen campos vehiculares públicos. La deduplicación elimina únicamente filas completamente idénticas mediante una huella SHA-256. La auditoría de enero encontró certificados reutilizados para registros distintos, por lo que el certificado no se considera una clave única. Registros distintos se conservan, aunque podrían requerir revisión adicional para determinar si son correcciones del origen.

## Consultas

```sql
-- Mes con más revisiones: comprobar antes los doce meses de cobertura.
SELECT * FROM flujo_mensual ORDER BY revisiones DESC;

-- Semanas de cada mes, conservando empates.
SELECT *, dense_rank() OVER (PARTITION BY planta, mes ORDER BY revisiones DESC) AS ranking
FROM flujo_semana_mes ORDER BY mes, ranking;

-- Semanas según intensidad por día con registros.
SELECT * FROM flujo_semana_mes
ORDER BY mes, promedio_por_dia_con_registros DESC;

-- Auditoría de cobertura.
SELECT periodo, filas_leidas, filas_planta, revisiones_unicas FROM archivos ORDER BY periodo;
SELECT min(fecha), max(fecha), count(*) FROM revisiones;
```
