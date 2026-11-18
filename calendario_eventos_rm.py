"""Campos de calendario y vínculos anónimos de visitas observadas en RM 2025."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from urllib.parse import unquote,urlparse

from prt import RAW,normalize,clean_date,clean_time,rows_from_zip
from rm_2025 import DB,ROOT

SCHEMA='''
CREATE TABLE IF NOT EXISTS calendario_importado (
 periodo TEXT PRIMARY KEY,sha256 TEXT NOT NULL,registros INTEGER NOT NULL,
 ppu_formato_reconocido INTEGER NOT NULL,campos_json TEXT NOT NULL,
 campo_reingreso_explicito INTEGER NOT NULL,importado_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS calendario_eventos (
 id BLOB PRIMARY KEY,vehiculo BLOB NOT NULL,ppu_reconocida INTEGER NOT NULL,
 digito INTEGER,planta TEXT NOT NULL,fecha TEXT NOT NULL,inicio_seg INTEGER NOT NULL,
 resultado TEXT NOT NULL,resultado_gases TEXT NOT NULL,vencimiento TEXT,
 tipo_vehiculo INTEGER,servicio INTEGER,combustible INTEGER,anio_fabricacion INTEGER);
'''


def code(value):
    try:
        n=float(value)
        return int(n) if n.is_integer() else None
    except (ValueError,TypeError,OverflowError):
        return None


def plate(value):
    p=normalize(value)
    valid=bool(re.fullmatch(r'(?:[A-Z]{2}\d{4}|[A-Z]{4}\d{2}|[A-Z]{3}\d{2,3})',p))
    return p,valid,int(p[-1]) if valid else None


def safe_date(value):
    try:
        result=clean_date(value)
        return result if '1901-01-01'<=result<='2100-12-31' else None
    except (ValueError,TypeError,OverflowError):
        return None


def main():
    key_path=ROOT/'datos/.clave_calendario'
    if not key_path.exists():
        with key_path.open('xb') as f:
            f.write(os.urandom(32))
    secret=key_path.read_bytes()
    assert len(secret)==32
    c=sqlite3.connect(DB)
    c.execute('PRAGMA cache_size=-262144')
    c.executescript(SCHEMA)
    plants={normalize(p):p for p, in c.execute("SELECT codigo FROM plantas WHERE codigo LIKE 'B-%' OR codigo LIKE 'AB%'")}
    for period,url,sha in c.execute('SELECT periodo,url,sha256 FROM archivos ORDER BY periodo').fetchall():
        done=c.execute('SELECT sha256 FROM calendario_importado WHERE periodo=?',(period,)).fetchone()
        if done:
            assert done[0]==sha
            continue
        path=RAW/unquote(urlparse(url).path.rsplit('/',1)[-1])
        with path.open('rb') as f:
            assert hashlib.file_digest(f,'sha256').hexdigest()==sha
        seen=set();records=[];daily=Counter();fields=set();recognized=0
        started=last=time.monotonic()
        for row in rows_from_zip(path,set(plants)):
            plant=plants.get(normalize(row.get('CODPRT')))
            if plant is None:
                continue
            fields.update(row)
            event=hashlib.sha256(json.dumps(row,sort_keys=True,default=str).encode()).digest()
            if event in seen:
                continue
            seen.add(event)
            p,valid,digit=plate(row.get('PPU'))
            recognized+=int(valid)
            vehicle=hmac.new(secret,p.encode(),hashlib.sha256).digest() if valid else event
            day=clean_date(row.get('FECREVISION'))
            assert day[:7]==period
            start=clean_time(row.get('HORAINI'))
            sec=sum(int(n)*m for n,m in zip(start.split(':'),(3600,60,1))) if start else -1
            result=str(row.get('RESULTADOCRT') or '').strip().upper()
            gas=str(row.get('RESULTADOCRTGASES') or '').strip().upper()
            records.append((event,vehicle,int(valid),digit,plant,day,sec,
                result if result in ('A','R') else 'otro',gas if gas in ('A','R') else 'otro',
                safe_date(row.get('FECVENCIMIENTO')),code(row.get('CODVEHICULO')),
                code(row.get('CODSERVICIO')),code(row.get('CODCOMBUSTIBLE')),code(row.get('ANOFABRICACION'))))
            daily[(plant,day)]+=1
            if time.monotonic()-last>30:
                print(f'{period}: {len(records):,} registros, {recognized:,} PPU con formato reconocido',flush=True)
                last=time.monotonic()
        expected=Counter({(p,d):n for p,d,n in c.execute(
            "SELECT planta,fecha,revisiones FROM flujo_diario WHERE periodo=? AND (planta LIKE 'B-%' OR planta LIKE 'AB%')",(period,))})
        assert daily==expected
        explicit=any('REINGRES' in f or 'REINSPEC' in f or 'TIPOREVISION' in f for f in fields)
        with c:
            c.executemany('INSERT INTO calendario_eventos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',records)
            c.execute('INSERT INTO calendario_importado VALUES (?,?,?,?,?,?,?)',
                (period,sha,len(records),recognized,json.dumps(sorted(fields)),int(explicit),datetime.now(timezone.utc).isoformat()))
        print(f'{period}: CALENDARIO IMPORTADO {len(records):,} registros; campo reingreso explícito={explicit}; {time.monotonic()-started:.0f}s',flush=True)
    c.execute('CREATE INDEX IF NOT EXISTS idx_calendario_vehiculo ON calendario_eventos(vehiculo,fecha,inicio_seg)')
    c.commit()
    print('LISTO:',c.execute('SELECT count(*),sum(registros),sum(ppu_formato_reconocido),sum(campo_reingreso_explicito) FROM calendario_importado').fetchone(),flush=True)


if __name__=='__main__':
    main()
