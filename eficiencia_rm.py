"""Comparaciones descriptivas de duración registrada; no estima productividad causal."""
import argparse
import json
import os
from pathlib import Path
import sqlite3

os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parent/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rm_2025 import DB,OUT

DEST=OUT/'eficiencia'
WEEKDAYS=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado']
MIN_CELL=20


def stats(seconds,weights):
    seconds=np.asarray(seconds,dtype=float)
    weights=np.asarray(weights,dtype=float)
    valid=(weights>0)&np.isfinite(seconds)&np.isfinite(weights)
    seconds,weights=seconds[valid],weights[valid]
    if not len(seconds):
        return dict(mediana_min=np.nan,p90_min=np.nan,media_min=np.nan)
    order=np.argsort(seconds)
    values,w=seconds[order],weights[order]
    cumulative=np.cumsum(w)
    # Cuantil de la distribución empírica ponderada, sin interpolar tiempos.
    median=values[min(np.searchsorted(cumulative,cumulative[-1]*.5),len(values)-1)]
    p90=values[min(np.searchsorted(cumulative,cumulative[-1]*.9),len(values)-1)]
    return dict(mediana_min=float(median/60),p90_min=float(p90/60),
                media_min=float(np.dot(values,w)/w.sum()/60))


def summarize(df,keys,weight='revisiones'):
    records=[]
    for key,group in df.groupby(keys,observed=True,sort=True):
        key=key if isinstance(key,tuple) else (key,)
        records.append(dict(zip(keys,key))|stats(group.segundos,group[weight])|
                       {'registros':int(group.revisiones.sum())})
    return pd.DataFrame(records)


def standardized(df,keys,category,levels,reference_peak=False):
    """Misma mezcla de casos para cada categoría y el mismo peso para cada planta."""
    totals=df.groupby(keys+[category],observed=True).revisiones.sum().unstack(category).reindex(columns=levels).fillna(0)
    eligible=totals[totals.ge(MIN_CELL).all(axis=1)].copy()
    if eligible.empty:
        raise ValueError(f'No hay soporte común suficiente: {category}, {keys}')
    eligible['referencia']=eligible[True] if reference_peak else eligible.reindex(columns=levels).sum(axis=1)
    meta=eligible[['referencia']].reset_index()
    plant_reference=meta.groupby('planta',observed=True).referencia.transform('sum')
    plants=meta.planta.nunique()
    meta['peso_celda']=meta.referencia/plant_reference/plants
    denominators=eligible.reindex(columns=levels).stack().rename('n_celda_categoria').reset_index()
    # Pandas conserva el nombre de category en la columna apilada.
    matched=df.merge(denominators,on=keys+[category],how='inner',validate='many_to_one')
    matched=matched.merge(meta[keys+['peso_celda']],on=keys,how='left',validate='many_to_one')
    matched['peso']=matched.revisiones/matched.n_celda_categoria*matched.peso_celda
    summary=summarize(matched,[category],weight='peso')
    by_plant=summarize(matched,['planta',category],weight='peso')
    coverage=(matched.groupby(category,observed=True).revisiones.sum()/df.groupby(category,observed=True).revisiones.sum()*100)
    summary['cobertura_soporte_pct']=summary[category].map(coverage)
    summary['plantas_comparadas']=int(plants)
    summary['celdas_comparables']=len(eligible)
    weight_sums=matched.groupby(category,observed=True).peso.sum()
    assert np.allclose(weight_sums.reindex(levels),1),weight_sums
    return summary,by_plant


def load(c):
    daily=pd.read_sql_query("SELECT planta,fecha,revisiones AS volumen_total FROM flujo_diario WHERE planta LIKE 'B-%' OR planta LIKE 'AB%'",c)
    periods={p for p, in c.execute('SELECT periodo FROM duraciones_importadas')}
    daily=daily[daily.fecha.str[:7].isin(periods)].copy()
    dates=pd.to_datetime(daily.fecha)
    daily['mes']=dates.dt.month.astype('int8')
    daily['dia']=dates.dt.day.astype('int8')
    daily['dia_semana']=dates.dt.dayofweek.astype('int8')
    grouping=daily.groupby(['planta','mes'],observed=True).volumen_total
    daily['umbral_p90_volumen']=grouping.transform(lambda s:s.quantile(.9))
    daily['fechas_con_registros_mes']=grouping.transform('size')
    daily['pico']=(daily.volumen_total>daily.umbral_p90_volumen)&(daily.fechas_con_registros_mes>=15)
    regional_dates={r[0] for r in c.execute('SELECT fecha FROM concentracion_rm WHERE ranking=1')}
    daily['pico_regional']=daily.fecha.isin(regional_dates)
    data=pd.read_sql_query("SELECT planta,fecha,hora,resultado,tipo_vehiculo,segundos,revisiones FROM duraciones_rm WHERE estado='positiva'",c)
    for col in ['planta','resultado','tipo_vehiculo']:
        data[col]=data[col].astype('category')
    for col in ['segundos','revisiones']:
        data[col]=data[col].astype('int32')
    data['hora']=data.hora.astype('int8')
    data=data.merge(daily,on=['planta','fecha'],validate='many_to_one')
    return daily,data


def analyze(c):
    daily,data=load(c)
    ds=summarize(data,['planta','fecha'])
    daily=daily.merge(ds,on=['planta','fecha'],how='left',validate='one_to_one')
    daily=daily.rename(columns={'registros':'duraciones_positivas'})
    daily['cobertura_duracion_pct']=daily.duraciones_positivas.fillna(0)/daily.volumen_total*100
    baseline=summarize(data,['planta','mes'])[['planta','mes','mediana_min']].rename(columns={'mediana_min':'mediana_planta_mes_min'})
    daily=daily.merge(baseline,on=['planta','mes'],how='left',validate='many_to_one')
    daily['indice_duracion']=100*daily.mediana_min/daily.mediana_planta_mes_min
    raw=summarize(data,['pico'])
    raw['tipo_comparacion']='Sin ajuste; ponderación por registros'
    keys=['planta','mes','dia_semana','resultado','tipo_vehiculo']
    adjusted,by_plant=standardized(data,keys,'pico',[False,True],reference_peak=True)
    adjusted['tipo_comparacion']='Ajustada; mismo peso por planta'
    regional,_=standardized(data,keys,'pico_regional',[False,True],reference_peak=True)
    by_result=summarize(data,['resultado','pico'])
    qm=daily.groupby(['planta','mes'],observed=True).agg(n=('duraciones_positivas','sum'),total=('volumen_total','sum')).reset_index()
    reliable=qm[qm.n/qm.total>=.95][['planta','mes']]
    high_quality=data.merge(reliable,on=['planta','mes'],how='inner',validate='many_to_one')
    sensitivity=[]
    for label,subset,extra in [
        ('Positivas hasta 4 horas',data[data.segundos<=14400],[]),
        ('Planta/mes con al menos 95% de tiempos positivos',high_quality,[]),
        ('Ajuste adicional por hora de inicio',data,['hora'])]:
        try:
            result,_=standardized(subset,keys+extra,'pico',[False,True],reference_peak=True)
            result['escenario']=label
            sensitivity.append(result)
        except ValueError:
            pass
    sensitivity=pd.concat(sensitivity,ignore_index=True) if sensitivity else pd.DataFrame()
    weekdays,week_by_plant=standardized(data[data.dia_semana<6],
        ['planta','mes','resultado','tipo_vehiculo'],'dia_semana',list(range(6)))
    weekdays['nombre_dia']=weekdays.dia_semana.map(dict(enumerate(WEEKDAYS)))
    weekdays['ranking_mediana']=weekdays.mediana_min.rank(method='min').astype(int)
    weekdays['ranking_p90']=weekdays.p90_min.rank(method='min').astype(int)
    week_by_plant['nombre_dia']=week_by_plant.dia_semana.map(dict(enumerate(WEEKDAYS)))
    week_by_plant['ranking_mediana_planta']=week_by_plant.groupby('planta',observed=True).mediana_min.rank(method='min').astype(int)
    week_by_plant['ranking_p90_planta']=week_by_plant.groupby('planta',observed=True).p90_min.rank(method='min').astype(int)
    # Índice por número de día: descriptivo, normalizado solo por planta y mes.
    eligible=daily[(daily.duraciones_positivas>=30)&(daily.cobertura_duracion_pct>=80)].copy()
    calendar=eligible.groupby('dia').agg(indice_mediano=('indice_duracion','median'),
        indice_p25=('indice_duracion',lambda s:s.quantile(.25)),
        indice_p75=('indice_duracion',lambda s:s.quantile(.75)),
        mediana_de_medianas_min=('mediana_min','median'),
        fechas_planta=('fecha','size'),plantas=('planta','nunique')).reset_index()
    missing=c.execute("SELECT sum(revisiones) FROM duraciones_rm WHERE estado!='positiva'").fetchone()[0]
    total=c.execute('SELECT sum(registros) FROM duraciones_importadas').fetchone()[0]
    quality=pd.read_sql_query('SELECT estado,sum(revisiones) AS registros FROM duraciones_rm GROUP BY estado',c)
    quality['porcentaje']=quality.registros/total*100
    quality_plant=pd.read_sql_query('''SELECT planta,estado,sum(revisiones) AS registros
                FROM duraciones_rm GROUP BY planta,estado''',c)
    quality_peak=daily.groupby('pico').agg(total_registros=('volumen_total','sum'),
                duraciones_positivas=('duraciones_positivas','sum'),fechas_planta=('fecha','size')).reset_index()
    quality_peak['cobertura_pct']=quality_peak.duraciones_positivas/quality_peak.total_registros*100
    wide=by_plant.pivot(index='planta',columns='pico',values=['mediana_min','p90_min','registros'])
    plant_comparison=pd.DataFrame(index=wide.index)
    for field in ['mediana_min','p90_min','registros']:
        plant_comparison[field+'_habitual']=wide[(field,False)]
        plant_comparison[field+'_pico']=wide[(field,True)]
    plant_comparison['diferencia_mediana_min']=plant_comparison.mediana_min_pico-plant_comparison.mediana_min_habitual
    plant_comparison['diferencia_p90_min']=plant_comparison.p90_min_pico-plant_comparison.p90_min_habitual
    plant_comparison=plant_comparison.reset_index()
    frames={'comparacion_sin_ajuste':raw,'comparacion_ajustada':adjusted,
        'peaks_regionales_ajustados':regional,
        'comparacion_por_resultado':by_result,'sensibilidades':sensitivity,
        'picos_por_planta':plant_comparison,'dias_semana_ajustados':weekdays,
        'dias_semana_por_planta':week_by_plant,'calendario_rapidez':calendar,
        'duracion_por_fecha_y_planta':daily,'calidad_datos':quality,
        'calidad_por_planta':quality_plant,'calidad_pico_habitual':quality_peak,
        'cobertura':pd.read_sql_query('SELECT * FROM duraciones_importadas ORDER BY periodo',c)}
    for name,frame in frames.items():
        frame.to_csv(DEST/f'{name}.csv',index=False,encoding='utf-8-sig')
    with pd.ExcelWriter(DEST/'eficiencia_rm_2025.xlsx',engine='openpyxl') as writer:
        for name,frame in frames.items():
            frame.to_excel(writer,sheet_name=name[:31],index=False)
            sheet=writer.sheets[name[:31]];sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
            for col in sheet.columns:
                sheet.column_dimensions[col[0].column_letter].width=min(42,max(15,len(str(col[0].value))+2))
    a=adjusted.set_index('pico')
    summary=dict(meses=int(len(frames['cobertura'])),registros=int(total),
        duraciones_positivas=int(total-missing),registros_sin_duracion_positiva=int(missing),
        cobertura_positiva_pct=float(100*(total-missing)/total),
        mediana_habitual_ajustada=float(a.loc[False,'mediana_min']),
        mediana_pico_ajustada=float(a.loc[True,'mediana_min']),
        p90_habitual_ajustado=float(a.loc[False,'p90_min']),
        p90_pico_ajustado=float(a.loc[True,'p90_min']),
        diferencia_mediana_min=float(a.loc[True,'mediana_min']-a.loc[False,'mediana_min']),
        diferencia_p90_min=float(a.loc[True,'p90_min']-a.loc[False,'p90_min']),
        plantas_comparadas=int(a.loc[True,'plantas_comparadas']),
        cobertura_soporte_pico_pct=float(a.loc[True,'cobertura_soporte_pct']),
        cobertura_soporte_habitual_pct=float(a.loc[False,'cobertura_soporte_pct']),
        comparacion_peaks_regionales=regional.to_dict('records'),
        plantas_pico_mas_lento_mediana=int((plant_comparison.diferencia_mediana_min>0).sum()),
        plantas_pico_igual_mediana=int((plant_comparison.diferencia_mediana_min==0).sum()),
        plantas_pico_mas_rapido_mediana=int((plant_comparison.diferencia_mediana_min<0).sum()),
        dias_semana=weekdays.to_dict('records'),
        mas_de_4_horas=int(data.loc[data.segundos>14400,'revisiones'].sum()))
    summary['duraciones_en_minutos_enteros_pct']=float(100*data.loc[data.segundos%60==0,'revisiones'].sum()/data.revisiones.sum())
    (DEST/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return frames,summary


def save(fig,name):
    fig.savefig(DEST/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(DEST/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)


def charts(frames,summary):
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'#fafcfb','axes.facecolor':'#fafcfb','axes.titleweight':'bold'})
    a=frames['comparacion_ajustada'].sort_values('pico')
    colors=['#087f8c','#dc6428']
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,metric,title in zip(axes,['mediana_min','p90_min'],['Mediana','Percentil 90']):
        ax.bar(['Habitual','Peak'],a[metric],color=colors)
        for i,val in enumerate(a[metric]): ax.text(i,val+.5,f'{val:.1f} min',ha='center')
        ax.set_ylim(0,a[metric].max()*1.2);ax.set_ylabel('Minutos registrados');ax.set_title(title)
    fig.suptitle('Días peak frente a días habituales · comparación ajustada',fontsize=16,y=1.02)
    fig.text(.02,-.06,'Misma planta, mes, día de semana, resultado y tipo de vehículo; cada planta pesa lo mismo.\n'
             'Solo duraciones positivas y casos con soporte comparable. Asociación descriptiva; no mide fila exterior.',fontsize=9)
    save(fig,'peak_vs_habitual')
    w=frames['dias_semana_ajustados'].sort_values('dia_semana')
    fig,ax=plt.subplots(figsize=(11.5,5))
    x=np.arange(6);ax.bar(x-.18,w.mediana_min,.36,label='Mediana',color=colors[0]);ax.bar(x+.18,w.p90_min,.36,label='P90',color=colors[1])
    ax.set_xticks(x,w.nombre_dia);ax.set_ylabel('Minutos registrados');ax.legend()
    ax.set_title('Rapidez registrada por día de la semana · mezcla comparable')
    fig.text(.03,-.04,'Misma planta, mes, resultado y tipo; soporte común en los seis días, mínimo 20 casos por grupo.\n'
             'Ponderación igual por planta. Menor duración no equivale por sí sola a mayor productividad o calidad.',fontsize=9)
    save(fig,'rapidez_dia_semana')
    cal=frames['calendario_rapidez'].set_index('dia')
    fig,ax=plt.subplots(figsize=(12.5,8))
    spread=max(abs(cal.indice_mediano-100).max(),1)
    norm=TwoSlopeNorm(vmin=100-spread,vcenter=100,vmax=100+spread)
    cmap=plt.get_cmap('RdYlGn_r')
    for day,row in cal.iterrows():
        y,x=divmod(int(day)-1,7);val=row.indice_mediano;color=cmap(norm(val))
        luminance=.2126*color[0]+.7152*color[1]+.0722*color[2]
        ink='white' if luminance<.4 else '#142b30'
        ax.add_patch(FancyBboxPatch((x+.05,y+.05),.9,.9,boxstyle='round,pad=.01',facecolor=color,edgecolor='white'))
        ax.text(x+.17,y+.28,str(day),fontsize=18,weight='bold',color=ink)
        ax.text(x+.5,y+.57,f'{val:.0f}',fontsize=22,ha='center',weight='bold',color=ink)
        ax.text(x+.5,y+.8,f'{int(row.fechas_planta)} observaciones',ha='center',fontsize=8,color=ink)
    ax.set(xlim=(0,7),ylim=(5,0));ax.set_aspect('equal');ax.axis('off')
    fig.suptitle('¿Qué días muestran menor duración relativa?',fontsize=20,x=.08,ha='left')
    ax.set_title('Índice descriptivo · 100 = mediana de su propia planta y mes',loc='left',pad=18)
    fig.text(.05,.035,'Verde: menor duración relativa. Rojo: mayor. Una observación = planta en una fecha; mínimo 30 tiempos positivos y 80% de cobertura.\n'
             'Mes sintético, sin columnas lunes–domingo. No ajusta mezcla de casos ni feriados; no es un efecto causal del número de día.',fontsize=9)
    save(fig,'calendario_rapidez')
    p=frames['picos_por_planta'].sort_values('diferencia_mediana_min')
    fig,ax=plt.subplots(figsize=(10,10))
    ax.barh(p.planta,p.diferencia_mediana_min,color=np.where(p.diferencia_mediana_min>0,colors[1],colors[0]))
    ax.axvline(0,color='black',linewidth=.8);ax.set_xlabel('Mediana peak − mediana habitual (minutos ajustados)')
    ax.set_title('El efecto observado cambia entre plantas')
    fig.text(.1,.02,'Negativo: menor duración registrada en peaks. Positivo: mayor. Asociación, no causalidad.',fontsize=9)
    save(fig,'diferencia_por_planta')
    scatter=frames['duracion_por_fecha_y_planta'].query('duraciones_positivas >= 30')
    p1=make_subplots(rows=1,cols=2,subplot_titles=['Mediana','P90'])
    for i,metric in enumerate(['mediana_min','p90_min'],1):
        p1.add_trace(go.Bar(x=['Habitual','Peak'],y=a[metric],marker_color=colors,name=metric),row=1,col=i)
    p1.update_layout(title='Comparación ajustada: recepción a término',template='plotly_white',showlegend=False)
    p2=go.Figure()
    for metric in ['mediana_min','p90_min']:
        p2.add_trace(go.Bar(x=w.nombre_dia,y=w[metric],name=metric))
    p2.update_layout(title='Día de semana · tiempos ajustados',barmode='group',template='plotly_white',yaxis_title='Minutos')
    p3=go.Figure()
    for peak,label,color in [(False,'Habitual',colors[0]),(True,'Peak',colors[1])]:
        rows=scatter[scatter.pico==peak]
        p3.add_trace(go.Scattergl(x=rows.volumen_total,y=rows.mediana_min,mode='markers',name=label,
             marker=dict(color=color,opacity=.4,size=5),text=rows.planta+' · '+rows.fecha,
             hovertemplate='%{text}<br>Volumen: %{x}<br>Mediana: %{y} min<extra></extra>'))
    p3.update_layout(title='Cada punto es una planta en una fecha · comparación sin ajustar',template='plotly_white',
                    xaxis_title='Registros de la fecha',yaxis_title='Mediana registrada (minutos)')
    return [p1,p2,p3]


METHODS='''
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
'''


def report(frames,summary,figures):
    coverage=f"**Cobertura: {summary['meses']}/12 meses; {summary['registros']:,} registros; {summary['cobertura_positiva_pct']:.2f}% con duración positiva.**"
    a=frames['comparacion_ajustada'].set_index('pico')
    text=['# Rapidez registrada y días peak · RM 2025','',coverage,'',
          '| Comparación ajustada | Día habitual | Día peak | Diferencia peak − habitual |',
          '|---|---:|---:|---:|',
          f"| Mediana | {a.loc[False,'mediana_min']:.1f} min | {a.loc[True,'mediana_min']:.1f} min | {summary['diferencia_mediana_min']:+.1f} min |",
          f"| P90 | {a.loc[False,'p90_min']:.1f} min | {a.loc[True,'p90_min']:.1f} min | {summary['diferencia_p90_min']:+.1f} min |",'',
          f"Soporte común: {summary['cobertura_soporte_pico_pct']:.1f}% de tiempos positivos peak y {summary['cobertura_soporte_habitual_pct']:.1f}% de habituales; {summary['plantas_comparadas']} plantas comparadas.",
          '', '## Días de semana con mezcla comparable','',
          '| Día | Mediana ajustada | P90 ajustado |','|---|---:|---:|']
    for row in frames['dias_semana_ajustados'].itertuples():
        text.append(f'| {row.nombre_dia} | {row.mediana_min:.1f} min | {row.p90_min:.1f} min |')
    text += ['', '## Disponibilidad de tiempos por tipo de día','',
             '| Tipo | Registros publicados | Duraciones positivas | Cobertura |',
             '|---|---:|---:|---:|']
    for row in frames['calidad_pico_habitual'].itertuples():
        label='Peak' if row.pico else 'Habitual'
        text.append(f'| {label} | {row.total_registros:,} | {row.duraciones_positivas:,.0f} | {row.cobertura_pct:.2f}% |')
    text += ['', '## Fechas de máximo volumen regional mensual','',
             'Comparación ajustada usando las mismas fechas peak regionales del informe anterior, en lugar de peaks por planta/mes.', '',
             '| Tipo de fecha | Mediana | P90 | % de tiempos positivos comparables |',
             '|---|---:|---:|---:|']
    for row in frames['peaks_regionales_ajustados'].itertuples():
        label='Máximo regional del mes' if row.pico_regional else 'Otras fechas'
        text.append(f'| {label} | {row.mediana_min:.1f} min | {row.p90_min:.1f} min | {row.cobertura_soporte_pct:.1f}% |')
    text += ['', 'La sensibilidad por hora de inicio tiene soporte reducido y se considera exploratoria; no se interpreta como una estimación general de toda la RM.']
    text += ['',METHODS]
    (DEST/'informe.md').write_text('\n'.join(text),encoding='utf-8')
    (DEST/'metodologia.md').write_text(METHODS,encoding='utf-8')
    html=['''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Rapidez y peaks · RM 2025</title><style>body{font:16px system-ui;background:#f3f6f6;color:#183344;margin:0}
    main{max-width:1150px;margin:auto;padding:30px}section{background:white;margin:20px 0;padding:24px;border-radius:16px}
    p{line-height:1.65}a{color:#087f8c}</style><main><h1>Rapidez registrada y días peak</h1>''',
    f"<p>{coverage.replace('**','')}</p>",
    f"<p>La comparación ajustada de peaks utiliza {summary['plantas_comparadas']} plantas y casos comparables que representan "
    f"el {summary['cobertura_soporte_pico_pct']:.1f}% de los tiempos positivos peak y el {summary['cobertura_soporte_habitual_pct']:.1f}% de los habituales.</p>",
    '<p>Duración de recepción a término. No mide la fila exterior ni la productividad por trabajador. Comparaciones descriptivas de 2025.</p>',
    '<p><a href="eficiencia_rm_2025.xlsx">Descargar datos en Excel</a> · <a href="metodologia.md">Metodología y cobertura</a> · <a href="informe.md">Informe con tablas</a></p>']
    for i,figure in enumerate(figures):
        html.append('<section>'+figure.to_html(full_html=False,include_plotlyjs=i==0,config={'responsive':True,'displaylogo':False})+'</section>')
    html.append('''<section><h2>Calendario de duración relativa</h2><img src="calendario_rapidez.png" style="width:100%">
    <p>Índice 100 = mediana de su planta y mes. Esta vista no ajusta mezcla de casos ni día de semana; los días no tienen siempre la misma composición.</p>
    <h2>Diferencias entre plantas</h2><img src="diferencia_por_planta.png" style="width:100%">
    <p>Peak = volumen sobre el P90 de su planta y mes. Ajuste por planta, mes, día de semana, resultado y tipo de vehículo; mínimo 20 casos por categoría y grupo.
    Se reponderan ambos grupos a la mezcla de los peaks de cada planta, con ponderación igual por planta. Se excluyen de los tiempos los registros cero o inconsistentes y se informa su cobertura.
    Una menor duración no demuestra mayor calidad ni un efecto causal del volumen. Las hojas de sensibilidades muestran los cambios al ajustar por hora o limitar duraciones largas.</p></section></main></html>''')
    (DEST/'informe_interactivo.html').write_text('\n'.join(html),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB)
    n=c.execute('SELECT count(*) FROM duraciones_importadas').fetchone()[0]
    if n!=12 and not args.allow_partial:
        raise SystemExit(f'Faltan meses: {n}/12. Ejecute duraciones_rm.py primero.')
    frames,summary=analyze(c)
    figures=charts(frames,summary)
    report(frames,summary,figures)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
