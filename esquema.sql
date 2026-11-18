PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS plantas (
    codigo TEXT PRIMARY KEY,
    region INTEGER,
    comuna TEXT,
    concesionario TEXT,
    sistema TEXT
);
CREATE TABLE IF NOT EXISTS archivos (
    url TEXT PRIMARY KEY,
    periodo TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    descargado_utc TEXT NOT NULL,
    filas_leidas INTEGER NOT NULL,
    filas_planta INTEGER NOT NULL,
    filas_invalidas INTEGER NOT NULL,
    revisiones_unicas INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS revisiones (
    id TEXT PRIMARY KEY,
    planta TEXT NOT NULL REFERENCES plantas(codigo),
    fecha TEXT NOT NULL CHECK(date(fecha) IS NOT NULL),
    hora_inicio TEXT,
    hora_fin TEXT,
    resultado TEXT,
    tipo_vehiculo TEXT,
    archivo_url TEXT NOT NULL REFERENCES archivos(url),
    CHECK (resultado IN ('A','R') OR resultado IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_revisiones_fecha ON revisiones(planta, fecha);
CREATE VIEW IF NOT EXISTS flujo_diario AS
SELECT planta, fecha, count(*) AS revisiones,
       sum(resultado = 'A') AS aprobadas, sum(resultado = 'R') AS rechazadas
FROM revisiones GROUP BY planta, fecha;
CREATE VIEW IF NOT EXISTS flujo_mensual AS
SELECT planta, substr(fecha,1,7) AS mes, count(*) AS revisiones,
       count(DISTINCT fecha) AS dias_con_registros,
       round(1.0*count(*)/count(DISTINCT fecha),2) AS promedio_por_dia_con_registros
FROM revisiones GROUP BY planta, mes;
CREATE VIEW IF NOT EXISTS flujo_anual AS
SELECT planta, substr(fecha,1,4) AS anio, count(*) AS revisiones,
       count(DISTINCT substr(fecha,1,7)) AS meses_con_registros
FROM revisiones GROUP BY planta, anio;
-- Bloques comparables dentro del mes: 1–7, 8–14, 15–21, 22–28, 29–fin.
-- El promedio usa días CON registros; no demuestra días abiertos ni cobertura completa.
CREATE VIEW IF NOT EXISTS flujo_semana_mes AS
SELECT planta, substr(fecha,1,7) AS mes,
       (cast(strftime('%d',fecha) AS INTEGER)-1)/7+1 AS semana_mes,
       count(*) AS revisiones, count(DISTINCT fecha) AS dias_con_registros,
       round(1.0*count(*)/count(DISTINCT fecha),2) AS promedio_por_dia_con_registros
FROM revisiones GROUP BY planta, mes, semana_mes;
CREATE VIEW IF NOT EXISTS flujo_semanal_calendario AS
SELECT planta, date(fecha, '-' || ((cast(strftime('%w',fecha) AS INTEGER)+6)%7) || ' days') AS lunes,
       count(*) AS revisiones, count(DISTINCT fecha) AS dias_con_registros
FROM revisiones GROUP BY planta, lunes;
CREATE VIEW IF NOT EXISTS flujo_horario AS
SELECT planta, fecha, substr(hora_inicio,1,2) AS hora, count(*) AS revisiones
FROM revisiones WHERE hora_inicio IS NOT NULL GROUP BY planta, fecha, hora;
