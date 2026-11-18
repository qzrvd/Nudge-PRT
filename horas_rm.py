"""Agrega HORA_INI, conciliando exactamente contra los conteos diarios RM."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import sqlite3
import time
from urllib.parse import urlparse,unquote

from prt import RAW,normalize,clean_date,clean_time,rows_from_zip
from rm_2025 import DB,OUT


def main():
    c=sqlite3.connect(DB)
    c.executescript('''
    CREATE TABLE IF NOT EXISTS horas_importadas (
      periodo TEXT PRIMARY KEY,sha256 TEXT NOT NULL,registros INTEGER NOT NULL,
      sin_hora INTEGER NOT NULL,importado_utc TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS flujo_horario_rm (
      planta TEXT NOT NULL,fecha TEXT NOT NULL,hora INTEGER NOT NULL,
      revisiones INTEGER NOT NULL,PRIMARY KEY(planta,fecha,hora),
      CHECK(hora BETWEEN -1 AND 23),CHECK(revisiones>0));
    ''')
    plants={normalize(p):p for p, in c.execute("SELECT codigo FROM plantas WHERE codigo LIKE 'B-%' OR codigo LIKE 'AB%'")}
    for period,url,expected_sha in c.execute('SELECT periodo,url,sha256 FROM archivos ORDER BY periodo').fetchall():
        if c.execute('SELECT 1 FROM horas_importadas WHERE periodo=?',(period,)).fetchone():
            continue
        path=RAW/unquote(urlparse(url).path.rsplit('/',1)[-1])
        with path.open('rb') as f:
            assert hashlib.file_digest(f,'sha256').hexdigest()==expected_sha
        seen=set()
        counts=Counter()
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
            hour=clean_time(row.get('HORAINI'))
            hour=int(hour[:2]) if hour else -1
            counts[(plants[code],day,hour)]+=1
            if time.monotonic()-last>30:
                print(f'{period}: {len(seen):,} registros únicos con hora revisada',flush=True)
                last=time.monotonic()
        daily=Counter()
        for (plant,day,hour),n in counts.items():
            daily[(plant,day)]+=n
        expected=Counter({(p,d):n for p,d,n in c.execute(
            "SELECT planta,fecha,revisiones FROM flujo_diario WHERE periodo=? AND (planta LIKE 'B-%' OR planta LIKE 'AB%')",(period,))})
        assert daily==expected, f'No coincide con la base diaria: {period}'
        missing=sum(n for (p,d,h),n in counts.items() if h==-1)
        with c:
            c.executemany('INSERT INTO flujo_horario_rm VALUES (?,?,?,?)',[(p,d,h,n) for (p,d,h),n in counts.items()])
            c.execute('INSERT INTO horas_importadas VALUES (?,?,?,?,?)',
                      (period,expected_sha,sum(counts.values()),missing,datetime.now(timezone.utc).isoformat()))
        print(f'{period}: horas importadas; {sum(counts.values()):,} registros, {missing} sin hora; {time.monotonic()-started:.0f}s',flush=True)
    print('LISTO: cobertura horaria',c.execute('SELECT count(*) FROM horas_importadas').fetchone()[0],'/12',flush=True)


if __name__=='__main__':
    main()
