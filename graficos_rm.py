"""Gráficos exportables e informe interactivo de concentración RM 2025."""
import calendar
import json
import os
from pathlib import Path
import sqlite3

os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parent/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rm_2025 import ROOT,DB,OUT

DEST=OUT/'graficos'
MONTHS=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
WEEKDAYS=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
TEAL='#087f8c'
ORANGE='#dc6428'
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,
                     'axes.titleweight':'bold','axes.labelcolor':'#344454','text.color':'#172f42',
                     'figure.facecolor':'#fafcfb','axes.facecolor':'#fafcfb','savefig.facecolor':'#fafcfb'})


def save(fig,name):
    fig.savefig(DEST/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(DEST/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)


def fmt(n):
    return f'{int(n):,}'.replace(',','.')


def calendar_matrix(values):
    matrix=np.full((5,7),np.nan)
    labels=[['']*7 for _ in range(5)]
    for d in range(1,32):
        row,col=divmod(d-1,7)
        matrix[row,col]=values[d]
        labels[row][col]=f'{d}<br>{values[d]:.2f}%'
    return matrix,labels


def base_data(c):
    raw=pd.read_sql_query("SELECT planta,fecha,revisiones FROM flujo_diario WHERE planta LIKE 'B-%' OR planta LIKE 'AB%'",c)
    raw['fecha']=pd.to_datetime(raw.fecha)
    raw['mes']=raw.fecha.dt.month
    scopes={'Toda la RM':raw.groupby('fecha',as_index=False).revisiones.sum()}
    for plant,frame in raw.groupby('planta'):
        scopes[plant]=frame[['fecha','revisiones']]
    grids={}
    averages={}
    for name,frame in scopes.items():
        grid=pd.DataFrame({'fecha':pd.date_range('2025-01-01','2025-12-31')}).merge(frame,on='fecha',how='left')
        grid['revisiones']=grid.revisiones.fillna(0).astype(int)
        grid['mes']=grid.fecha.dt.month
        grid['dia']=grid.fecha.dt.day
        grid['dia_semana']=grid.fecha.dt.dayofweek
        grid['porcentaje_mes']=100*grid.revisiones/grid.groupby('mes').revisiones.transform('sum')
        grids[name]=grid
        averages[name]=grid.groupby('dia').agg(
            porcentaje_mensual_promedio=('porcentaje_mes','mean'),
            promedio_revisiones=('revisiones','mean'),
            meses_disponibles=('mes','count'),
            minimo_porcentaje=('porcentaje_mes','min'),maximo_porcentaje=('porcentaje_mes','max'))
    return grids,averages


def calendar_charts(grids,averages):
    pooled=averages['Toda la RM']
    fig,ax=plt.subplots(figsize=(12.8,8.2))
    cmap=plt.get_cmap('YlOrRd')
    norm=Normalize(vmin=pooled.porcentaje_mensual_promedio.min(),vmax=pooled.porcentaje_mensual_promedio.max())
    for day,row in pooled.iterrows():
        y,x=divmod(day-1,7)
        val=row.porcentaje_mensual_promedio
        color=cmap(norm(val))
        ax.add_patch(FancyBboxPatch((x+.05,y+.05),.9,.9,boxstyle='round,pad=0.012,rounding_size=0.07',facecolor=color,edgecolor='white',linewidth=2))
        ink='white' if norm(val)>.62 else '#3c2420'
        ax.text(x+.15,y+.26,str(day),fontsize=18,weight='bold',color=ink)
        ax.text(x+.5,y+.55,f'{val:.2f}%'.replace('.',','),ha='center',fontsize=18,color=ink,weight='bold')
        ax.text(x+.5,y+.78,f'{int(row.meses_disponibles)} meses',ha='center',fontsize=9,color=ink)
    ax.set(xlim=(0,7),ylim=(5,0)); ax.set_aspect('equal'); ax.axis('off')
    fig.suptitle('¿Qué días concentran más revisiones?',fontsize=23,x=.08,ha='left',y=.98)
    ax.set_title('RM · 33 plantas B/AB · promedio de participación mensual en 2025',fontsize=12,loc='left',pad=18)
    fig.text(.08,.05,'Mes sintético: las columnas NO son días de la semana. Cada casilla promedia el % de su mes.\n'
             'Días 29–31: solo meses donde existen. Incluye fines de semana y fechas con 0 registros publicados.\n'
             'Los 31 promedios usan denominadores distintos y no tienen por qué sumar 100%. Fuente: PRT/MTT.',fontsize=9)
    save(fig,'calendario_promedio')

    pfig=go.Figure()
    names=list(averages)
    for i,name in enumerate(names):
        frame=averages[name]
        matrix,labels=calendar_matrix(frame.porcentaje_mensual_promedio)
        custom=np.zeros((5,7,2))
        for d,r in frame.iterrows():
            a,b=divmod(d-1,7)
            custom[a,b]=[r.meses_disponibles,r.promedio_revisiones]
        pfig.add_trace(go.Heatmap(z=matrix,text=labels,texttemplate='%{text}',customdata=custom,
            colorscale='YlOrRd',visible=i==0,colorbar_title='% del mes',xgap=6,ygap=6,
            hovertemplate='%{text}<br>Meses disponibles: %{customdata[0]:.0f}<br>Promedio de registros: %{customdata[1]:.1f}<extra></extra>'))
    pfig.update_layout(title='Calendario promedio · seleccionar planta',height=570,
        updatemenus=[dict(buttons=[dict(label=n,method='update',args=[{'visible':[j==i for j in range(len(names))]}]) for i,n in enumerate(names)],x=0,y=1.16)],
        margin=dict(t=100,b=40),template='plotly_white')
    pfig.update_xaxes(visible=False);pfig.update_yaxes(visible=False,autorange='reversed')

    # Calendarios reales de cada mes, con sus días de semana.
    grid=grids['Toda la RM']
    fig,axes=plt.subplots(3,4,figsize=(18,12.2))
    max_pct=grid.porcentaje_mes.max()
    for month,ax in enumerate(axes.flat,1):
        frame=grid[grid.mes==month].set_index('dia')
        weeks=calendar.monthcalendar(2025,month)
        for r,week in enumerate(weeks):
            for col,d in enumerate(week):
                if not d: continue
                v=frame.loc[d,'porcentaje_mes']
                color=cmap(v/max_pct)
                ax.add_patch(plt.Rectangle((col,r),.95,.95,color=color))
                ink='white' if v/max_pct>.6 else '#3c2420'
                ax.text(col+.47,r+.3,str(d),ha='center',va='center',fontsize=10,color=ink,weight='bold')
                label='0%' if v==0 else ('<0,1%' if v<.05 else f'{v:.1f}%'.replace('.',','))
                ax.text(col+.47,r+.7,label,ha='center',va='center',fontsize=8,color=ink)
        ax.set(xlim=(0,7),ylim=(6,0),xticks=np.arange(7)+.47,xticklabels=['L','M','X','J','V','S','D'],yticks=[])
        ax.xaxis.tick_top();ax.tick_params(length=0)
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.set_title(MONTHS[month-1],pad=25)
    fig.suptitle('2025 · Calendarios reales de concentración en la RM',fontsize=22,y=1.015)
    fig.text(.08,.015,'Cada casilla muestra el % del total de su mes. Misma escala en los 12 calendarios.\n'
             '0% = sin registros publicados; no demuestra cierre. Incluye reingresos. Fuente: PRT/MTT.',fontsize=10)
    fig.subplots_adjust(hspace=.4,wspace=.15,bottom=.08)
    save(fig,'calendarios_2025')
    return pfig


def month_charts(grid):
    q90=float(grid.revisiones.quantile(.9))
    monthly=grid.groupby('mes').agg(total=('revisiones','sum'),promedio_por_fecha=('revisiones','mean'),
        maximo_diario=('revisiones','max'),dias_calendario=('fecha','size'))
    monthly['dias_sobre_p90']=grid.assign(alto=grid.revisiones>q90).groupby('mes').alto.sum()
    monthly['ranking_total']=monthly.total.rank(ascending=False,method='min').astype(int)
    monthly['ranking_promedio']=monthly.promedio_por_fecha.rank(ascending=False,method='min').astype(int)
    monthly.to_csv(DEST/'comparacion_meses.csv',encoding='utf-8-sig')
    colors=[ORANGE if i==3 else TEAL for i in monthly.index]
    fig,axes=plt.subplots(3,1,figsize=(12.8,10.5),sharex=True)
    panels=[('total','Revisiones totales'),('promedio_por_fecha','Promedio por fecha del calendario'),('dias_sobre_p90','Días de alta actividad (sobre el percentil 90 anual)')]
    for ax,(field,title) in zip(axes,panels):
        ax.bar(np.arange(12),monthly[field],color=colors)
        ax.set_title(title,loc='left',fontsize=12)
        ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
        for i,val in enumerate(monthly[field]):
            ax.text(i,val+monthly[field].max()*.018,fmt(round(val)),ha='center',fontsize=9)
        ax.set_ylim(0,monthly[field].max()*1.17)
    axes[-1].set_xticks(range(12),[m[:3] for m in MONTHS])
    fig.suptitle('Marzo frente al resto del año',fontsize=22,x=.08,ha='left',y=.98)
    fig.text(.08,.02,'Naranja: marzo. Comparación descriptiva de 2025; no estima un efecto causal del permiso.\n'
             'Promedio por fecha: incluye sábados, domingos y feriados. P90: umbral común de todo el año. Fuente: PRT/MTT.',fontsize=9)
    fig.subplots_adjust(hspace=.35,top=.91,bottom=.09)
    save(fig,'comparacion_meses')
    p=make_subplots(rows=3,cols=1,subplot_titles=[t for f,t in panels],vertical_spacing=.12)
    for i,(field,title) in enumerate(panels,1):
        p.add_trace(go.Bar(x=MONTHS,y=monthly[field],marker_color=colors,name=title),row=i,col=1)
    p.update_layout(height=850,showlegend=False,template='plotly_white',title='Volumen, intensidad media y días de alta actividad')
    # Distribución diaria por mes: permite distinguir un peak aislado de un mes cargado.
    fig,ax=plt.subplots(figsize=(12.8,5.5))
    ax.boxplot([grid[grid.mes==m].revisiones for m in range(1,13)],tick_labels=[m[:3] for m in MONTHS],showmeans=True)
    ax.set_title('Distribución de revisiones por fecha, en cada mes',loc='left')
    ax.set_ylabel('Registros diarios');ax.grid(axis='y',alpha=.2)
    fig.text(.1,.015,'Caja: mitad central de las fechas. Línea: mediana. Triángulo: media. Puntos: valores extremos. Incluye fechas con 0 registros.',fontsize=8)
    save(fig,'distribucion_por_mes')
    return p,monthly,q90


def hourly_charts(c):
    coverage=pd.read_sql_query('SELECT * FROM horas_importadas ORDER BY periodo',c)
    if len(coverage)!=12:
        return [],dict(meses_horarios=len(coverage))
    data=pd.read_sql_query('SELECT * FROM flujo_horario_rm',c)
    assert int(data.revisiones.sum())==2320324
    data['fecha']=pd.to_datetime(data.fecha)
    data['dia']=data.fecha.dt.day;data['dia_semana']=data.fecha.dt.dayofweek;data['mes']=data.fecha.dt.month
    valid=data[data.hora>=0].copy()
    hist=valid.groupby('hora').revisiones.sum().reindex(range(24),fill_value=0)
    annual=hist.rename('revisiones').to_frame();annual['porcentaje']=hist/hist.sum()*100
    annual.to_csv(DEST/'distribucion_horaria.csv',encoding='utf-8-sig')
    coverage.to_csv(DEST/'cobertura_horaria.csv',index=False,encoding='utf-8-sig')
    data.to_csv(DEST/'horas_por_planta_y_fecha.csv',index=False,encoding='utf-8-sig')
    fig,ax=plt.subplots(figsize=(12.8,5.5))
    ax.bar(range(24),annual.porcentaje,color=[ORANGE if n==hist.idxmax() else TEAL for n in range(24)])
    ax.set_xticks(range(24),[f'{h:02d}' for h in range(24)]);ax.set_xlabel('Hora de inicio registrada');ax.set_ylabel('% de registros con hora válida')
    ax.set_title('¿A qué hora se concentran las revisiones?',loc='left',fontsize=18)
    fig.text(.08,.015,'RM · 2025 · HORA_INI (recepción en planta). No mide la espera fuera de la planta. Fuente: PRT/MTT.',fontsize=9)
    save(fig,'concentracion_horaria')
    plots=[go.Figure(go.Bar(x=[f'{h:02d}:00' for h in range(24)],y=annual.porcentaje))]
    plots[0].update_layout(title='Distribución por hora de inicio · RM 2025',yaxis_title='% con hora válida',template='plotly_white',height=420)
    summaries={}
    for group,title,name,index in [('dia_semana','Día de la semana × hora','semana_hora',range(7)),
                                   ('dia','Día del mes × hora','dia_mes_hora',range(1,32))]:
        pivot=valid.pivot_table(index=group,columns='hora',values='revisiones',aggfunc='sum',fill_value=0).reindex(index=index,columns=range(24),fill_value=0)
        pct=pivot.div(pivot.sum(axis=1).replace(0,np.nan),axis=0)*100
        labels=WEEKDAYS if group=='dia_semana' else [str(x) for x in index]
        pct.to_csv(DEST/f'{name}_porcentaje.csv',encoding='utf-8-sig')
        fig,ax=plt.subplots(figsize=(13,5.2 if group=='dia_semana' else 12))
        im=ax.imshow(pct.to_numpy(),aspect='auto',cmap='YlOrRd')
        ax.set_xticks(range(24),[f'{h:02d}' for h in range(24)]);ax.set_yticks(range(len(index)),labels)
        ax.set_xlabel('Hora de inicio registrada');ax.set_title(title+' · % dentro de cada fila',loc='left')
        fig.colorbar(im,ax=ax,label='% de registros con hora válida')
        fig.text(.08,.01,'Cada fila suma 100% si tiene registros. Filas vacías: sin registros con hora. No ajusta por horarios de apertura.',fontsize=9)
        save(fig,name)
        pp=go.Figure(go.Heatmap(z=pct.to_numpy(),x=[f'{h:02d}:00' for h in range(24)],y=labels,colorscale='YlOrRd',colorbar_title='% de la fila'))
        pp.update_layout(title=title,height=430 if group=='dia_semana' else 820,template='plotly_white')
        pp.update_yaxes(autorange='reversed');plots.append(pp)
        if group=='dia_semana':
            for i,label in enumerate(labels):
                if pivot.loc[i].sum()>0:
                    summaries[label]={'hora':int(pivot.loc[i].idxmax()),'porcentaje':float(pct.loc[i].max())}
    per_day=valid.groupby(['fecha','hora'],as_index=False).revisiones.sum()
    per_day['total_dia_con_hora']=per_day.groupby('fecha').revisiones.transform('sum')
    per_day['porcentaje_dia']=100*per_day.revisiones/per_day.total_dia_con_hora
    per_day['ranking']=per_day.groupby('fecha').revisiones.rank(ascending=False,method='min')
    per_day[per_day.ranking==1].to_csv(DEST/'hora_peak_por_fecha.csv',index=False,encoding='utf-8-sig')
    per_plant=valid.groupby(['planta','hora'],as_index=False).revisiones.sum()
    per_plant['porcentaje_planta']=per_plant.revisiones/per_plant.groupby('planta').revisiones.transform('sum')*100
    per_plant.to_csv(DEST/'horario_por_planta.csv',index=False,encoding='utf-8-sig')
    return plots,dict(meses_horarios=12,registros_con_hora=int(hist.sum()),registros_sin_hora=int(data[data.hora<0].revisiones.sum()),
        hora_peak=int(hist.idxmax()),porcentaje_hora_peak=float(annual.loc[hist.idxmax(),'porcentaje']),peak_por_dia_semana=summaries,
        registros_hora_00=int(hist.loc[0]))


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB)
    grids,averages=base_data(c)
    averages['Toda la RM'].to_csv(DEST/'calendario_promedio.csv',encoding='utf-8-sig')
    for name,frame in averages.items():
        frame.assign(planta=name).reset_index().to_csv(DEST/f'calendario_{name.replace(" ","_")}.csv',index=False,encoding='utf-8-sig')
    cal=calendar_charts(grids,averages)
    months,monthly,q90=month_charts(grids['Toda la RM'])
    hourly,summary=hourly_charts(c)
    summary.update(total_registros=2320324,marzo_total=int(monthly.loc[3,'total']),marzo_ranking_total=int(monthly.loc[3,'ranking_total']),
                   marzo_promedio_fecha=float(monthly.loc[3,'promedio_por_fecha']),marzo_ranking_promedio=int(monthly.loc[3,'ranking_promedio']),
                   umbral_p90=q90,dias_promedio_mayor_concentracion=averages['Toda la RM'].sort_values('porcentaje_mensual_promedio',ascending=False).head(5).reset_index().to_dict('records'))
    (DEST/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    parts=['''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Concentración de revisiones · RM 2025</title><style>body{margin:0;background:#f3f6f6;color:#183344;font:16px system-ui}
    main{max-width:1200px;margin:auto;padding:32px}section{background:white;border-radius:18px;padding:24px;margin:24px 0;box-shadow:0 3px 18px #1231}
    h1{font-size:36px}p{line-height:1.6}a{color:#087f8c}.note{color:#526570;font-size:14px}.plotly-graph-div{max-width:100%}</style><main>
    <h1>Cuándo se concentran las revisiones</h1><p>Región Metropolitana · 2025 · 33 plantas B/AB · 2.320.324 registros distintos</p>
    <p><a href="https://www.prt.cl/Descargas/index.html">Fuente: archivos públicos PRT/MTT</a> · <a href="contexto_y_fuentes.md">Parque vehicular, permisos y límites de la evidencia</a></p>
    <section><h2>Un mes promedio</h2><p>Selecciona toda la RM o una planta. Cada casilla muestra la participación mensual promedio de ese número de día.</p>
    <p class="note">Es un mes sintético: las columnas no representan lunes a domingo. Los días 29–31 usan solo meses donde existen.
    Incluye fechas con cero registros publicados, fines de semana y feriados. No permite separar la preferencia por una fecha del efecto del día de semana.
    Los 31 promedios no tienen por qué sumar 100%, porque no todos usan los mismos meses.</p>''']
    figures=[cal,months]+hourly
    for i,figure in enumerate(figures):
        if i:
            parts.append('</section><section>')
        parts.append(figure.to_html(full_html=False,include_plotlyjs=True if i==0 else False,config={'responsive':True,'displaylogo':False}))
    if not hourly:
        parts.append('<p>La lectura de horas todavía está en proceso. Consulta resumen.json para verificar su cobertura.</p>')
    parts.append('''</section><section><h2>Calendarios reales y otras vistas</h2>
    <p><a href="calendarios_2025.png">Ver los doce calendarios de 2025</a> · <a href="distribucion_por_mes.png">Distribuciones por mes</a></p>
    <h2>Cómo leer los resultados</h2><p>Se cuentan registros distintos publicados, incluidos reingresos. Se eliminaron filas completamente idénticas.
    La hora corresponde a HORA_INI; no representa espera en la fila exterior. Las comparaciones de meses describen 2025 y no prueban causalidad del permiso de circulación.
    Las cifras de permisos INE y las revisiones PRT corresponden a universos, regiones de registro y años diferentes; su resta no mide incumplimiento.</p>
    <h2>Parque vehicular y documentos vencidos</h2><p>El INE registra <strong>2.442.537 vehículos motorizados en la RM durante 2024</strong>,
    según su estadística de permisos de circulación.
    <a href="https://www.ine.gob.cl/docs/default-source/variables-basicas-ambientales/publicaciones-y-anuarios/informe-anual-de-medio-ambiente/informe-anual-de-estadisticas-del-medio-ambiente-2025.pdf?sfvrsn=62fcb728_4">Ver tabla 11.2.2 del informe ambiental 2025</a>.</p>
    <p>El total más amplio es de <strong>2.476.153 permisos emitidos en la RM durante 2024</strong>,
    incluidos vehículos motorizados y no motorizados, cifra provisional.
    <a href="https://regiones.ine.cl/documentos/default-source/region-iii/estadisticas/parque-de-veh%C3%ADiulos/publicaciones-y-anuarios/documentos/permisos-de-circulaci%C3%B3n---per%C3%ADodo-2024.pdf?sfvrsn=59b9aaab_4">Ver tabla oficial, página 4</a>.</p>
    <p>No se encontró una cifra regional consolidada, actual y verificable de vehículos con revisión vencida o permiso impago.
    Los permisos emitidos no cuentan directamente a quienes no pagaron. Para medirlo se necesitan el universo de vehículos obligados y los registros de vigencia/pagos conciliados.</p>
    <p>Marzo fue segundo en volumen de revisiones y cuarto por promedio por fecha calendario. Un solo año no permite atribuir ese patrón al permiso de circulación.
    <a href="https://www.bcn.cl/api-leyfacil/servicio/ObtenerGuiaPublicadaHTML?uri=permiso-de-circulacion">Ver plazos y requisitos en BCN</a>.</p></section></main></html>''')
    (DEST/'informe_interactivo.html').write_text('\n'.join(parts),encoding='utf-8')
    exports={'calendario_promedio':'calendario_promedio.csv','comparacion_meses':'comparacion_meses.csv',
             'horas':'distribucion_horaria.csv','semana_hora':'semana_hora_porcentaje.csv',
             'dia_mes_hora':'dia_mes_hora_porcentaje.csv','hora_peak_por_fecha':'hora_peak_por_fecha.csv',
             'horario_por_planta':'horario_por_planta.csv','cobertura_horaria':'cobertura_horaria.csv'}
    with pd.ExcelWriter(DEST/'datos_graficos.xlsx',engine='openpyxl') as writer:
        for name,file in exports.items():
            if not (DEST/file).exists(): continue
            pd.read_csv(DEST/file).to_excel(writer,sheet_name=name,index=False)
            writer.sheets[name].freeze_panes='A2'
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
