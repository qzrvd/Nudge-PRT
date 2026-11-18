"""Curva de concentración mensual y auditoría de calendario/revisitas."""
import argparse
import json
import os
from pathlib import Path
import sqlite3

os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parent/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from rm_2025 import DB,OUT

DEST=OUT/'patron_calendario'
DIGIT_MONTH={9:1,0:2,1:4,2:5,3:6,4:7,5:8,6:9,7:10,8:11}
TEAL='#087f8c';ORANGE='#dc6428'


def save(fig,name):
    fig.savefig(DEST/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(DEST/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)


def curves(c):
    observed=pd.read_sql_query('SELECT fecha,revisiones FROM diario_rm ORDER BY fecha',c)
    grid=pd.DataFrame({'fecha':pd.date_range('2025-01-01','2025-12-31')})
    observed['fecha']=pd.to_datetime(observed.fecha)
    grid=grid.merge(observed,on='fecha',how='left')
    grid['revisiones']=grid.revisiones.fillna(0).astype(int)
    grid['mes']=grid.fecha.dt.month;grid['dia']=grid.fecha.dt.day
    grid['dias_mes']=grid.fecha.dt.days_in_month
    grid['porcentaje_mes']=100*grid.revisiones/grid.groupby('mes').revisiones.transform('sum')
    curve=grid.groupby('dia').agg(porcentaje_promedio=('porcentaje_mes','mean'),
        meses=('mes','size'),minimo=('porcentaje_mes','min'),maximo=('porcentaje_mes','max')).reset_index()
    curve['suavizado_5_dias']=curve.porcentaje_promedio.rolling(5,center=True,min_periods=3).mean()
    windows=[]
    for month,rows in grid.groupby('mes'):
        for label,mask in [('Inicio: días 1–7',rows.dia<=7),('Mitad: días 12–18',rows.dia.between(12,18)),
                           ('Cierre: últimos 7 días',rows.dia>rows.dias_mes-7)]:
            chosen=rows[mask]
            assert len(chosen)==7
            windows.append(dict(mes=month,ventana=label,porcentaje_del_mes=chosen.porcentaje_mes.sum(),
                promedio_por_fecha=chosen.revisiones.mean()))
    windows=pd.DataFrame(windows)
    labels=['Inicio: días 1–7','Mitad: días 12–18','Cierre: últimos 7 días']
    mean=windows.groupby('ventana').porcentaje_del_mes.mean().reindex(labels)
    curve.to_csv(DEST/'curva_dias.csv',index=False,encoding='utf-8-sig')
    windows.to_csv(DEST/'ventanas_7_dias.csv',index=False,encoding='utf-8-sig')
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,
        'figure.facecolor':'#fafcfb','axes.facecolor':'#fafcfb'})
    fig,axes=plt.subplots(1,2,figsize=(15,5.8),gridspec_kw={'width_ratios':[1.65,1]})
    ax=axes[0]
    ax.scatter(curve.dia,curve.porcentaje_promedio,color='#8c9ba3',s=28,label='Promedio observado',zorder=3)
    ax.plot(curve.dia,curve.suavizado_5_dias,color=TEAL,linewidth=3,label='Promedio móvil de 5 días')
    ax.fill_between(curve.dia,curve.suavizado_5_dias,alpha=.10,color=TEAL)
    ax.axvspan(25,31,color=ORANGE,alpha=.09)
    ax.set(xlim=(1,31),ylim=(0,5.2),xlabel='Día del mes',ylabel='% del total mensual, en promedio')
    ax.set_xticks([1,5,10,15,20,25,31]);ax.legend(loc='lower right',frameon=False,fontsize=9)
    ax.set_title('Curva observada: un valle a mitad de mes',loc='left',weight='bold')
    ax=axes[1]
    for month,rows in windows.groupby('mes'):
        values=rows.set_index('ventana').porcentaje_del_mes.reindex(labels)
        ax.plot(range(3),values,color='#ccd4d7',alpha=.55,linewidth=1)
    ax.plot(range(3),mean,color=ORANGE,linewidth=3,marker='o',markersize=8)
    for x,val in enumerate(mean):
        ax.annotate(f'{val:.1f}%'.replace('.',','),(x,val),xytext=(0,9),textcoords='offset points',ha='center',weight='bold',fontsize=13)
    ax.set_xticks(range(3),['Inicio','Mitad','Cierre'])
    ax.set(ylabel='% del mes en una ventana de 7 días',ylim=(0,max(windows.porcentaje_del_mes)*1.15))
    ax.set_title('Tres ventanas de igual duración',loc='left',weight='bold')
    fig.suptitle('Las revisiones aumentan hacia el cierre del mes',fontsize=22,x=.075,ha='left',y=1.01)
    fig.text(.07,-.025,'RM · 33 plantas B/AB · 2025. Panel derecho: gris = cada mes; naranja = promedio de los 12 meses.\n'
        'Se incluyen fechas existentes con 0 registros publicados. Día 31: 7 meses; días 29–30: 11. No se impone una parábola ni se ajusta por feriados.',fontsize=9)
    fig.tight_layout();save(fig,'curva_concentracion')
    fig,ax=plt.subplots(figsize=(11.5,5.5))
    ax.scatter(curve.dia,curve.porcentaje_promedio,color='#99a6ad',s=22,label='Promedio observado',zorder=3)
    ax.plot(curve.dia,curve.suavizado_5_dias,color=TEAL,linewidth=3.5,label='Tendencia: promedio móvil de 5 días')
    ax.fill_between(curve.dia,curve.suavizado_5_dias,color=TEAL,alpha=.08)
    ax.set(xlim=(1,31),ylim=(0,5.2),xlabel='Día del mes',ylabel='% mensual promedio por fecha')
    ax.set_xticks([1,5,10,15,20,25,31])
    ax.set_title('Más revisiones al inicio y al cierre del mes',loc='left',weight='bold',fontsize=20,pad=18)
    ax.text(2,4.65,'Inicio',color=TEAL,weight='bold',fontsize=12)
    ax.text(14,1.85,'Valle central',color=TEAL,weight='bold',fontsize=12)
    ax.text(27,4.65,'Cierre',color=TEAL,weight='bold',fontsize=12)
    ax.legend(loc='lower right',frameon=False,fontsize=9)
    fig.text(.08,-.025,'RM · 33 plantas B/AB · 2025 · Fuente: PRT/MTT. No se impone una parábola.\n'
        'Día 31: 7 meses; días 29–30: 11. Incluye fechas sin registros y no ajusta por feriados o día de semana.',fontsize=9)
    save(fig,'curva_u_presentacion')
    interactive=go.Figure()
    interactive.add_trace(go.Scatter(x=curve.dia,y=curve.porcentaje_promedio,mode='markers',name='Promedio observado',
        customdata=curve.meses,hovertemplate='Día %{x}: %{y:.2f}%<br>%{customdata} meses<extra></extra>'))
    interactive.add_trace(go.Scatter(x=curve.dia,y=curve.suavizado_5_dias,mode='lines',line=dict(color=TEAL,width=3),name='Promedio móvil 5 días'))
    interactive.update_layout(title='Patrón mensual observado · RM 2025',xaxis_title='Día del mes',
        yaxis_title='% mensual promedio por fecha',template='plotly_white',yaxis_range=[0,5.2])
    interactive.write_html(DEST/'curva_interactiva.html',include_plotlyjs=True,config={'responsive':True,'displaylogo':False})
    summary=dict(inicio_pct=float(mean.iloc[0]),mitad_pct=float(mean.iloc[1]),cierre_pct=float(mean.iloc[2]),
        cierre_vs_mitad_pct=float(100*(mean.iloc[2]/mean.iloc[1]-1)),
        cierre_vs_inicio_pct=float(100*(mean.iloc[2]/mean.iloc[0]-1)),
        meses_cierre_supera_inicio=int((windows.pivot(index='mes',columns='ventana',values='porcentaje_del_mes')[labels[2]]>
                                      windows.pivot(index='mes',columns='ventana',values='porcentaje_del_mes')[labels[0]]).sum()))
    (DEST/'resumen_curva.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return curve,windows,summary


def annotate(data):
    data['vehiculo']=pd.factorize(data.vehiculo)[0]
    for field in ['planta','resultado','resultado_gases']:
        data[field]=data[field].astype('category')
    data['fecha']=pd.to_datetime(data.fecha)
    data['vencimiento']=pd.to_datetime(data.vencimiento,errors='coerce')
    data=data.sort_values(['vehiculo','fecha','inicio_seg','planta'],kind='stable').reset_index(drop=True)
    data['mes']=data.fecha.dt.month;data['dia']=data.fecha.dt.day
    group=data.groupby('vehiculo',sort=False)
    data['orden_ambiguo']=data.duplicated(['vehiculo','fecha','inicio_seg'],keep=False)
    previous_date=group.fecha.shift()
    previous_start=group.inicio_seg.shift()
    gap=(data.fecha-previous_date).dt.days
    strict_later=(data.fecha>previous_date)|((data.fecha==previous_date)&(data.inicio_seg>previous_start))
    prev_amb=group.orden_ambiguo.shift().fillna(True).astype(bool)
    previous_reject=(group.resultado.shift()=='R')|(group.resultado_gases.shift()=='R')
    reliable=data.ppu_reconocida.eq(1)&~data.orden_ambiguo&~prev_amb&strict_later
    data['revisita_15']=reliable&previous_reject&gap.between(0,15)
    data['revisita_30']=reliable&previous_reject&gap.between(0,30)
    data['misma_planta_previa']=data.planta.eq(group.planta.shift())
    data['reingreso_compatible_15']=data.revisita_15&data.misma_planta_previa
    data['mes_calendario']=data.digito.map(DIGIT_MONTH)
    previous_month=((data.mes_calendario-2)%12)+1
    data['relacion_calendario']=np.select([
        data.ppu_reconocida.ne(1),data.mes.eq(data.mes_calendario),data.mes.eq(previous_month)],
        ['PPU no clasificable','Mes correspondiente','Mes precedente'],default='Otros meses: atraso no determinado')
    data['mes_posterior_inmediato']=data.mes.eq((data.mes_calendario%12)+1)
    data['cohorte_compatible']=data.ppu_reconocida.eq(1)&data.tipo_vehiculo.isin([1,4])&data.servicio.eq(3)&\
        data.combustible.isin([1,2,4])&data.anio_fabricacion.between(1993,2025)
    data['inicio_observado_15']=data.cohorte_compatible&~data.orden_ambiguo&~data.revisita_15
    data['inicio_observado_30']=data.cohorte_compatible&~data.orden_ambiguo&~data.revisita_30
    # No usar el certificado emitido hoy como si fuera el vencimiento anterior.
    # El marcador -2 invalida también la ausencia de fecha en una aprobación observada.
    due_days=(data.vencimiento-pd.Timestamp('1970-01-01')).dt.days
    today=(data.fecha-pd.Timestamp('1970-01-01')).dt.days
    approved=data.resultado.eq('A')
    marker=due_days.where(approved,np.nan)
    marker=marker.where(~approved|(due_days.notna()&due_days.ge(today)&~data.orden_ambiguo),-2)
    filled=marker.groupby(data.vehiculo,sort=False).ffill()
    prev_due=filled.groupby(data.vehiculo,sort=False).shift()
    known=prev_due.ge(0)&~data.orden_ambiguo&data.ppu_reconocida.eq(1)
    data['estado_vencimiento_previo']=np.select([known&today.le(prev_due),known&today.gt(prev_due)],
        ['Fecha no posterior al vencimiento previo observado','Fecha posterior al vencimiento previo observado'],
        default='Sin vencimiento previo suficiente')
    return data


def classify(c):
    coverage=pd.read_sql_query('SELECT * FROM calendario_importado ORDER BY periodo',c)
    if len(coverage)!=12:
        raise ValueError(f'Extracción de patente aún incompleta: {len(coverage)}/12')
    data=pd.read_sql_query('''SELECT vehiculo,ppu_reconocida,digito,planta,fecha,inicio_seg,
        resultado,resultado_gases,vencimiento,tipo_vehiculo,servicio,combustible,anio_fabricacion
        FROM calendario_eventos''',c)
    data=annotate(data)
    data['ventana']=np.select([data.dia<=7,data.dia.between(12,18),data.dia>data.fecha.dt.days_in_month-7],
        ['Inicio: 1–7','Mitad: 12–18','Cierre: últimos 7'],default='Resto del mes')
    def count(keys,rows=None):
        rows=data if rows is None else rows
        return rows.groupby(keys,observed=True).size().rename('registros').reset_index()
    baseline=data[data.inicio_observado_15]
    previous_month_visits=baseline[baseline.relacion_calendario.eq('Mes precedente')]
    frames={
        'relacion_todos_registros':count(['relacion_calendario']),
        'relacion_cohorte':count(['relacion_calendario'],baseline),
        'cohorte_por_mes':count(['mes','relacion_calendario'],baseline),
        'cohorte_por_digito':count(['digito','relacion_calendario'],baseline),
        'cohorte_por_dia':count(['dia','relacion_calendario'],baseline),
        'cohorte_por_ventana':count(['ventana','relacion_calendario'],baseline),
        'cohorte_por_planta':count(['planta','relacion_calendario'],baseline),
        'mes_precedente_por_dia':count(['dia'],previous_month_visits),
        'mes_precedente_por_ventana':count(['ventana'],previous_month_visits),
        'revisitas_por_mes':count(['mes','reingreso_compatible_15','revisita_15']),
        'vencimiento_previo_observado':count(['ventana','estado_vencimiento_previo'],baseline),
        'campos_archivos':coverage,
    }
    revisit_windows=data.groupby('ventana',observed=True).agg(registros=('vehiculo','size'),
        compatibles_misma_planta_15=('reingreso_compatible_15','sum'),revisitas_cualquier_planta_15=('revisita_15','sum')).reset_index()
    revisit_windows['porcentaje_compatible_misma_planta']=100*revisit_windows.compatibles_misma_planta_15/revisit_windows.registros
    frames['revisitas_por_ventana']=revisit_windows
    proximity=baseline.groupby('ventana',observed=True).agg(registros=('vehiculo','size'),
        del_mes_recien_terminado=('mes_posterior_inmediato','sum')).reset_index()
    proximity['porcentaje_del_mes_recien_terminado']=100*proximity.del_mes_recien_terminado/proximity.registros
    frames['mes_recien_terminado']=proximity
    detail=baseline[['ventana','relacion_calendario','mes_posterior_inmediato']].copy()
    detail['categoria']=np.where(detail.mes_posterior_inmediato,'Dígito del mes recién terminado',detail.relacion_calendario)
    frames['cohorte_ventana_detalle']=detail.groupby(['ventana','categoria'],observed=True).size().rename('registros').reset_index()
    initial=data[data.ppu_reconocida.eq(1)&~data.orden_ambiguo&~data.revisita_15]
    initial_daily=initial.groupby('fecha').size().rename('n').reset_index()
    initial_grid=pd.DataFrame({'fecha':pd.date_range('2025-01-01','2025-12-31')}).merge(initial_daily,on='fecha',how='left')
    initial_grid['n']=initial_grid.n.fillna(0)
    initial_grid['mes']=initial_grid.fecha.dt.month;initial_grid['dia']=initial_grid.fecha.dt.day
    initial_grid['porcentaje']=100*initial_grid.n/initial_grid.groupby('mes').n.transform('sum')
    initial_curve=initial_grid.groupby('dia').porcentaje.mean().rename('sin_revisita_reciente_pct').reset_index()
    frames['curva_sin_revisitas']=initial_curve
    rows=[]
    for label,mask in [('Todos los registros',pd.Series(True,index=data.index)),
                       ('Cohorte compatible',data.cohorte_compatible),
                       ('Sin revisita reciente 15d ni orden ambiguo',data.inicio_observado_15),
                       ('Sin revisita reciente 30d ni orden ambiguo',data.inicio_observado_30),
                       ('Sensibilidad: excluir primera quincena de enero',data.inicio_observado_15&~((data.mes==1)&(data.dia<=15)))]:
        subset=data[mask]
        numerator=int(subset.relacion_calendario.eq('Mes precedente').sum())
        rows.append(dict(poblacion=label,registros=len(subset),mes_precedente=numerator,
            porcentaje_mes_precedente=100*numerator/len(subset) if len(subset) else np.nan))
    frames['linea_base_observada']=pd.DataFrame(rows)
    for name,frame in frames.items():
        frame.to_csv(DEST/f'{name}.csv',index=False,encoding='utf-8-sig')
    with pd.ExcelWriter(DEST/'calendario_y_revisitas_2025.xlsx',engine='openpyxl') as writer:
        for name,frame in frames.items():
            frame.to_excel(writer,sheet_name=name[:31],index=False)
            writer.sheets[name[:31]].freeze_panes='A2'
    summary=dict(registros=len(data),ppu_reconocida=int(data.ppu_reconocida.sum()),
        campo_reingreso_explicito_archivos=int(coverage.campo_reingreso_explicito.sum()),
        reingreso_compatible_15=int(data.reingreso_compatible_15.sum()),
        revisita_cualquier_planta_15=int(data.revisita_15.sum()),
        registros_orden_ambiguo=int(data.orden_ambiguo.sum()),cohorte_compatible=int(data.cohorte_compatible.sum()),
        linea_base_observada=rows[2],sensibilidades=rows[3:],
        mes_precedente_cierre_pct=float(100*previous_month_visits.ventana.eq('Cierre: últimos 7').mean()),
        mes_precedente_mitad_pct=float(100*previous_month_visits.ventana.eq('Mitad: 12–18').mean()),
        revisitas_por_ventana=revisit_windows.to_dict('records'),
        proximidad_calendario_por_ventana=proximity.to_dict('records'),
        inicio_mes_estado_vencimiento=count(['estado_vencimiento_previo'],baseline[baseline.dia<=7]).to_dict('records'),
        limites='Historial limitado a RM 2025. No confirma atraso efectivo ni causa de liquidez; revisitas inferidas, no marcadas oficialmente.')
    (DEST/'resumen_calendario.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    categories=['Mes correspondiente','Dígito del mes recién terminado','Mes precedente','Otros meses: atraso no determinado']
    pivot=frames['cohorte_ventana_detalle'].pivot(index='ventana',columns='categoria',values='registros').reindex(columns=categories,fill_value=0)
    pct=pivot.div(pivot.sum(axis=1),axis=0)*100
    pct.to_csv(DEST/'composicion_ventanas_pct.csv',encoding='utf-8-sig')
    fig,ax=plt.subplots(figsize=(12,6.4))
    labels=['Inicio: 1–7','Mitad: 12–18','Cierre: últimos 7']
    bottom=np.zeros(3)
    for category,color in zip(categories,[TEAL,ORANGE,'#6cad55','#b1b8bd']):
        values=pct.reindex(labels)[category].fillna(0)
        ax.bar(labels,values,bottom=bottom,label=category,color=color)
        for i,v in enumerate(values):
            if v>=5: ax.text(i,bottom[i]+v/2,f'{v:.1f}%',ha='center',va='center',color='white' if category in categories[:2] else '#142b30')
        bottom+=values.to_numpy()
    ax.set(ylabel='% de intentos iniciales observados',ylim=(0,100));ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),frameon=False,fontsize=9,ncol=2)
    ax.set_title('¿Quiénes llegan al inicio y al cierre del mes?',loc='left',weight='bold')
    fig.subplots_adjust(bottom=.29)
    fig.text(.03,.015,'Cohorte de automóviles/station wagon particulares. Se excluyen revisitas recientes inferidas y orden ambiguo.\n'
        'Las categorías de calendario no prueban vigencia ni atraso. Los motivos de liquidez no están observados.',fontsize=9)
    save(fig,'composicion_inicio_cierre')
    original=pd.read_csv(DEST/'curva_dias.csv')
    fig,ax=plt.subplots(figsize=(11.5,5))
    ax.plot(original.dia,original.suavizado_5_dias,color='#7d8e98',linewidth=2,label='Todos los registros B/AB')
    ax.plot(initial_curve.dia,initial_curve.sin_revisita_reciente_pct.rolling(5,center=True,min_periods=3).mean(),
        color=TEAL,linewidth=3,label='Sin revisita reciente inferida ni orden ambiguo')
    ax.set(xlim=(1,31),ylim=(0,5.5),xlabel='Día del mes',ylabel='% mensual promedio por fecha')
    ax.set_title('Patrón mensual al separar las revisitas observables',loc='left',weight='bold');ax.legend(frameon=False)
    fig.text(.03,-.04,'Ambas series: universo B/AB, promedio móvil 5 días. Retorno tras rechazo a cualquier planta en hasta 15 días.\n'
        'No identifica todos los reingresos: faltan visitas de otras regiones y anteriores a 2025.',fontsize=9)
    save(fig,'curva_sin_revisitas')
    return summary


def report(curve_summary,calendar_summary):
    baseline=calendar_summary['linea_base_observada']
    total=calendar_summary['registros']
    statement=(f"En promedio, los últimos siete días concentran el {curve_summary['cierre_pct']:.1f}% de las revisiones del mes, "
        f"un {curve_summary['cierre_vs_mitad_pct']:.0f}% más que una ventana de siete días a mitad de mes.")
    text=['# Patrón mensual y viabilidad de la clasificación · RM 2025','',statement,'',
        '| Ventana de 7 días | Participación mensual promedio |','|---|---:|',
        f"| Inicio: días 1–7 | {curve_summary['inicio_pct']:.2f}% |",
        f"| Mitad: días 12–18 | {curve_summary['mitad_pct']:.2f}% |",
        f"| Cierre: últimos 7 días reales de cada mes | {curve_summary['cierre_pct']:.2f}% |",'',
        f"El cierre supera al inicio en {curve_summary['meses_cierre_supera_inicio']} de 12 meses, "
        f"y su promedio es {curve_summary['cierre_vs_inicio_pct']:.1f}% mayor. La U es aproximada, no una regla para todos los meses.", '',
        '## Campos comprobados','',
        f"Se conciliaron {total:,} registros de las 33 plantas B/AB contra la base diaria. "
        f"{calendar_summary['ppu_reconocida']:,} tienen PPU con formato reconocido y último dígito extraíble. "
        f"En {calendar_summary['campo_reingreso_explicito_archivos']} de los 12 archivos aparece un campo explícito identificado como reingreso/reinspección/tipo de revisión.", '',
        '- **PPU**: patente completa. El último dígito se deriva de ella; no se necesita publicarla.',
        '- **COD_PRT, FEC_REVISION, HORA_INI, RESULTADO_CRT y RESULTADO_CRT_GASES**: permiten enlazar visitas y rechazos observados.',
        '- **FEC_VENCIMIENTO**: vencimiento asociado al registro; no es por sí solo el vencimiento previo a la llegada.',
        '- **COD_VEHICULO, COD_SERVICIO, COD_COMBUSTIBLE y ANO_FABRICACION**: ayudan a separar cohortes y excepciones.', '',
        'Fuente primaria: [diccionario SGPRT RB](https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx). '
        'La hoja `campos_archivos` conserva los campos efectivamente observados en cada ZIP.', '',
        '## Línea base observable para B','',
        f"En la cohorte definida, {baseline['mes_precedente']:,} de {baseline['registros']:,} "
        f"intentos iniciales observados ocurrieron en el mes precedente al del dígito: **{baseline['porcentaje_mes_precedente']:.2f}%**.", '',
        '**Es una aproximación de uso del mes precedente, no una tasa confirmada de adelantos efectivos.** '
        'El numerador puede contener certificados vencidos de ciclos anteriores. No es la proporción del parque elegible ni incluye vehículos que nunca acudieron.', '',
        'Cohorte: automóviles y station wagon de uso privado-particular, combustibles gasolina/diésel/eléctrico, '
        'fabricación 1993–2025 y PPU reconocida. No se incluyen taxis, transporte escolar ni todos los tipos B. '
        'Se excluyen órdenes temporales ambiguos y nuevas visitas dentro de 15 días de un rechazo anterior observado. '
        'Es una cohorte compatible con el calendario, no una certificación de periodicidad individual; puede incluir primeras revisiones con vigencia bienal.', '',
        'Las sensibilidades de 30 días y la exclusión de la primera quincena de enero están en `linea_base_observada`. '
        'El límite de enero reconoce la falta de visitas de diciembre de 2024.', '',
        f"Dentro de las visitas del mes precedente, el {calendar_summary['mes_precedente_cierre_pct']:.1f}% ocurre en sus últimos siete días "
        f"y el {calendar_summary['mes_precedente_mitad_pct']:.1f}% en los días 12–18. "
        'Mover una visita al mes anterior no asegura moverla fuera de su cierre: para evaluar B se deben medir ambos desplazamientos.', '',
        '## Reingresos: inferidos, no marcados','',
        f"Hay {calendar_summary['reingreso_compatible_15']:,} registros compatibles con una revisita a la misma planta "
        f"en los 15 días siguientes a un rechazo observado. Contando cambios de planta: {calendar_summary['revisita_cualquier_planta_15']:,}. "
        f"{calendar_summary['registros_orden_ambiguo']:,} registros comparten vehículo, fecha y hora y no permiten ordenar visitas con seguridad.", '',
        'La regla requiere misma PPU, una visita estrictamente posterior y rechazo RT o gases en la visita previa. '
        'No verifica gratuidad, la condición oficial de reinspección ni visitas fuera de la RM o anteriores a 2025. '
        'Una cadena de rechazos puede producir varias revisitas; no son vehículos únicos.', '',
        'Las tasas por ventana están en `revisitas_por_ventana`, sobre todos los registros B/AB. '
        'Permiten separar una posible contribución de revisitas al pico de inicio, además de las hipótesis de plazo y liquidez.', '',
        'La figura `curva_sin_revisitas` compara el patrón de todos los registros B/AB con el mismo universo al excluir revisitas recientes inferidas y órdenes ambiguos; no es una identificación perfecta de primeras visitas.', '',
        '## Lo que no decide el dígito','',
        'Una patente terminada en 9 revisada en diciembre puede estar anticipando enero siguiente o llegar tarde al ciclo de enero anterior. '
        'Incluso coincidir con el mes del dígito no acredita que el certificado anterior siguiera vigente.', '',
        'Por eso se usan las etiquetas «mes correspondiente», «mes precedente» y «otros meses: atraso no determinado». '
        'No se renombran los otros meses como atrasos.', '',
        'La hoja `mes_recien_terminado` separa los casos cuyo dígito corresponde al mes inmediatamente anterior al de la visita. '
        'Es una proximidad al calendario compatible con la hipótesis de plazo, no prueba de vencimiento ni de motivo.', '',
        'El vencimiento previo se busca solo en aprobaciones anteriores observadas del mismo vehículo, nunca en el certificado emitido en la visita actual. '
        'Si falta, queda desconocido; una aprobación con fecha u orden ambiguo invalida ese antecedente. '
        'Aun cuando se encuentra, el historial RM 2025 puede omitir aprobaciones en otras regiones. '
        'La etiqueta «posterior al vencimiento previo observado» no confirma por sí sola atraso efectivo.', '',
        'Para clasificar vigencia al llegar se necesita historial nacional anterior: al menos 2024 y también 2023 para ciclos bienales, '
        'manteniendo desconocido cuando falte antecedente suficiente. Las prórrogas/excepciones también deben verificarse.', '',
        '**Liquidez no está observada:** un patrón al inicio del mes, aun con certificado previo vigente, '
        'no prueba que el conductor esperó el sueldo. Se necesitan fechas de pago/ingresos, encuesta o un diseño experimental para separar ese motivo de otros.', '',
        'Plazo y liquidez pueden coexistir: un conductor con certificado vencido también puede haber esperado un pago. '
        'Reconstruir la vigencia identifica un estado frente al plazo, no el motivo de la decisión.', '',
        '## Norma y visualización','',
        'El [artículo 7 del Decreto 156](https://www.bcn.cl/leychile/navegar?i=10183) '
        'permite efectuar la revisión en el mes precedente sin afectar su vigencia y contiene excepciones de periodicidad. '
        'Su artículo 10 describe la revisión posterior a un rechazo; aquí la ventana de 15 días es una regla de inferencia, no una marca oficial.', '',
        'La curva usa la participación de cada fecha en su mes y promedia por número de día. '
        'El día 31 tiene siete meses disponibles; 29 y 30 tienen once. Se preservan los puntos reales y se añade un promedio móvil centrado de cinco días. '
        'No se ajusta una parábola para obtener una U. La comparación de tres ventanas usa siete días en todos los casos, incluyendo los últimos siete días de febrero.', '',
        'Las tres ventanas no son tercios del mes y no cubren todas las fechas; su suma no tiene por qué ser 100%.', '',
        'Se incluyen fechas existentes con cero registros publicados; no se afirma que estuvieran abiertas. '
        'No se ajusta por feriados ni por día de semana. La composición de cohortes se agrega por registros, mientras la curva promedia meses con igual peso.', '',
        'Archivos: `curva_concentracion.png/.svg`, `curva_interactiva.html`, `composicion_inicio_cierre.png/.svg` '
        'y `calendario_y_revisitas_2025.xlsx`. No se exportan patentes ni identificadores de vehículo.'
    ]
    (DEST/'informe.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    html=f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Patrón mensual y calendario · RM 2025</title><style>body{{background:#f3f6f6;color:#183344;font:16px system-ui;margin:0}}
    main{{max-width:1200px;margin:auto;padding:32px}}section{{background:white;border-radius:18px;padding:24px;margin:22px 0}}
    img{{width:100%}}p{{line-height:1.6}}a{{color:#087f8c}}</style><main><h1>Dos extremos cargados y un valle central</h1>
    <p>{statement}</p><section><img src="curva_concentracion.png"><p><a href="curva_interactiva.html">Explorar la curva</a> ·
    <a href="curva_u_presentacion.png">Versión simple para diapositiva</a> ·
    <a href="curva_concentracion.svg">Gráfico vectorial para presentación</a></p></section>
    <section><h2>Qué permiten los archivos</h2><p>Se verificó PPU en {calendar_summary['ppu_reconocida']:,} registros.
    No se encontró una marca explícita de reingreso en los 12 archivos. Las revisitas se infieren del historial observado.</p>
    <h2>Uso observado del mes precedente</h2><p><strong>{baseline['porcentaje_mes_precedente']:.2f}%</strong> de los intentos iniciales observados de la cohorte
    ocurrieron en el mes anterior al del dígito ({baseline['mes_precedente']:,} de {baseline['registros']:,}).
    Es una aproximación observable, no un porcentaje confirmado de adelantos efectivos.</p>
    <img src="composicion_inicio_cierre.png"><p>«Otros meses» no significa atraso comprobado.
    Para saber si el vehículo llegó con revisión vencida se necesita su certificado anterior e historial suficiente.
    Los archivos no contienen ingresos ni fechas de sueldo y no identifican por sí solos liquidez.</p>
    <p><a href="calendario_y_revisitas_2025.xlsx">Datos y auditoría en Excel</a> · <a href="informe.md">Metodología, denominadores y límites</a> ·
    <a href="https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx">Diccionario oficial</a></p></section></main></html>'''
    (DEST/'informe.html').write_text(html,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--curves-only',action='store_true')
    args=parser.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB)
    _,_,summary=curves(c)
    print('CURVA:',json.dumps(summary,ensure_ascii=False),flush=True)
    if not args.curves_only:
        calendar_summary=classify(c)
        report(summary,calendar_summary)
        print('CALENDARIO:',json.dumps(calendar_summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
