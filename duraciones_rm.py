"""Duración registrada de recepción a término, sin identificadores vehiculares."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import sqlite3
import time
from urllib.parse import unquote,urlparse

from prt import RAW,normalize,clean_date,clean_time,rows_from_zip
from rm_2025 import DB

SCHEMA='''
CREATE TABLE IF NOT EXISTS duraciones_importadas (
 periodo TEXT PRIMARY KEY,sha256 TEXT NOT NULL,registros INTEGER NOT NULL,
 validas_positivas INTEGER NOT NULL,cero INTEGER NOT NULL,
 fin_anterior INTEGER NOT NULL,hora_invalida INTEGER NOT NULL,importado_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS duraciones_rm (
 planta TEXT NOT NULL,fecha TEXT NOT NULL,hora INTEGER NOT NULL,
 resultado TEXT NOT NULL,tipo_vehiculo TEXT NOT NULL,segundos INTEGER NOT NULL,
 estado TEXT NOT NULL,revisiones INTEGER NOT NULL,
 PRIMARY KEY(planta,fecha,hora,resultado,tipo_vehiculo,segundos,estado),
 CHECK(revisiones>0),CHECK(estado IN ('positiva','cero','fin_anterior','hora_invalida')));
CREATE INDEX IF NOT EXISTS idx_duraciones_fecha ON duraciones_rm(fecha,planta);
'''


def seconds(value):
    text=clean_time(value)
    if text is None:
        return None
    h,m,s=map(int,text.split(':'))
    return h*3600+m*60+s


def duration(start,end):
    a,b=seconds(start),seconds(end)
    hour=a//3600 if a is not None else -1
    if a is None or b is None:
        return hour,-1,'hora_invalida'
    if b<a:
        # Sin fecha de término no se distingue cruce de medianoche de un error.
        return hour,-1,'fin_anterior'
    if a==b:
        return hour,0,'cero'
    return hour,b-a,'positiva'


def vehicle_code(value):
    if isinstance(value,(float,int)):
        return str(int(value)) if float(value).is_integer() else str(value)
    return str(value or 'desconocido').strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--months',nargs='*',type=int)
    args=parser.parse_args()
    c=sqlite3.connect(DB)
    c.executescript(SCHEMA)
    plants={normalize(p):p for p, in c.execute("SELECT codigo FROM plantas WHERE codigo LIKE 'B-%' OR codigo LIKE 'AB%'")}
    files=c.execute('SELECT periodo,url,sha256 FROM archivos ORDER BY periodo').fetchall()
    for period,url,sha in files:
        if args.months and int(period[-2:]) not in args.months:
            continue
        done=c.execute('SELECT sha256 FROM duraciones_importadas WHERE periodo=?',(period,)).fetchone()
        if done:
            assert done[0]==sha
            continue
        path=RAW/unquote(urlparse(url).path.rsplit('/',1)[-1])
        with path.open('rb') as f:
            assert hashlib.file_digest(f,'sha256').hexdigest()==sha
        seen=set();hist=Counter();states=Counter()
        started=last=time.monotonic()
        for row in rows_from_zip(path,set(plants)):
            code=normalize(row.get('CODPRT'))
            if code not in plants:
                continue
            key=hashlib.sha256(json.dumps(row,sort_keys=True,default=str).encode()).digest()
            if key in seen:
                continue
            seen.add(key)
            day=clean_date(row.get('FECREVISION'))
            assert day[:7]==period
            hour,elapsed,status=duration(row.get('HORAINI'),row.get('HORAFIN'))
            result=str(row.get('RESULTADOCRT') or '').strip().upper()
            result=result if result in ('A','R') else 'otro'
            hist[(plants[code],day,hour,result,vehicle_code(row.get('CODVEHICULO')),elapsed,status)]+=1
            states[status]+=1
            if time.monotonic()-last>30:
                print(f'{period}: {len(seen):,} registros revisados; {dict(states)}',flush=True)
                last=time.monotonic()
        daily=Counter()
        for (plant,day,h,r,t,s,status),n in hist.items():
            daily[(plant,day)]+=n
        expected=Counter({(p,d):n for p,d,n in c.execute(
            "SELECT planta,fecha,revisiones FROM flujo_diario WHERE periodo=? AND (planta LIKE 'B-%' OR planta LIKE 'AB%')",(period,))})
        assert daily==expected, f'Diferencia frente a la base diaria: {period}'
        with c:
            c.executemany('INSERT INTO duraciones_rm VALUES (?,?,?,?,?,?,?,?)',
                          [(*key,n) for key,n in hist.items()])
            c.execute('INSERT INTO duraciones_importadas VALUES (?,?,?,?,?,?,?,?)',
                      (period,sha,len(seen),states['positiva'],states['cero'],states['fin_anterior'],states['hora_invalida'],datetime.now(timezone.utc).isoformat()))
        print(f'{period}: DURACIONES IMPORTADAS, {len(seen):,} registros, {dict(states)}, {time.monotonic()-started:.0f}s',flush=True)
    print('Cobertura:',c.execute('SELECT count(*),sum(registros),sum(validas_positivas) FROM duraciones_importadas').fetchone(),flush=True)


if __name__=='__main__':
    main()
