"""Publica todas las visualizaciones existentes en un HTML autónomo."""
import base64
import json
from html import escape
from pathlib import Path

from lxml import html
from plotly.offline import get_plotlyjs

BASE = Path(__file__).resolve().parent / 'resultados/rm_2025'


def plots(path):
    doc = html.fromstring((BASE / path).read_text(encoding='utf-8'))
    result = []
    for graph in doc.xpath('//div[contains(@class,"plotly-graph-div")]'):
        scripts = graph.getparent().xpath('./script[contains(text(),"Plotly.newPlot")]')
        assert len(scripts) == 1
        result.append(html.tostring(graph, encoding='unicode') + html.tostring(scripts[0], encoding='unicode'))
    return result


def main():
    general = plots('graficos/informe_interactivo.html')
    efficiency = plots('eficiencia/informe_interactivo.html')
    curve = plots('patron_calendario/curva_interactiva.html')
    assert (len(general), len(efficiency), len(curve)) == (5, 3, 1)
    groups = [
        ('patron', 'Concentración dentro del mes', [
            ('patron_calendario/curva_u_presentacion.png', 'Una U aproximada: más revisiones al inicio y al cierre', 'Los últimos siete días reúnen, en promedio, el 26,8% del mes: un 33% más que los días 12–18. El inicio reúne el 25,4%. Son ventanas de siete días; no son tercios del mes.', curve[0]),
            ('patron_calendario/curva_concentracion.png', 'Inicio, mitad y cierre: comparación entre meses', 'El cierre supera al inicio en nueve de los doce meses. La forma de U es una descripción aproximada de 2025. La línea usa suavizado de cinco días, sin imponer una curva cuadrática.', None),
            ('graficos/calendario_promedio.png', 'Calendario de concentración promedio', 'Cada casilla muestra la participación mensual promedio de ese número de día. Es un mes sintético: las columnas no representan días de semana. Los días 29–31 usan solamente meses donde existen; las 31 casillas no necesariamente suman 100%. En la versión interactiva puedes seleccionar toda la RM o una planta.', general[0]),
            ('graficos/calendarios_2025.png', 'Los doce calendarios reales de 2025', 'Permiten distinguir el número de día del efecto del día de semana. Se incluyen fechas sin registros publicados; esto no demuestra que la planta estuviera abierta ni que la demanda fuera cero.', None),
        ]),
        ('meses', 'Diferencias entre meses', [
            ('graficos/comparacion_meses.png', 'Volumen, promedio diario y días de alta actividad', 'Octubre tiene el mayor volumen. Marzo ocupa el segundo lugar por total y el cuarto por promedio por fecha calendario. Alta actividad usa el P90 anual del volumen diario regional (9.640,6 registros); no es la misma definición de peak usada para comparar duraciones.', general[1]),
            ('graficos/distribucion_por_mes.png', 'Distribución del volumen diario de cada mes', 'Muestra la variación entre fechas, además del promedio. Las comparaciones incluyen domingos y feriados; un solo año no permite atribuir el patrón al permiso de circulación.', None),
        ]),
        ('horas', 'Horarios de concentración', [
            ('graficos/concentracion_horaria.png', 'Revisiones por hora de inicio', 'La franja 11:00–11:59 concentra el 12,1% de los registros del año. HORA_INI corresponde al inicio registrado del servicio; no mide la llegada a la fila exterior.', general[2]),
            ('graficos/semana_hora.png', 'Día de semana y hora', 'Cada fila muestra cómo se distribuyen las revisiones de ese día de semana entre las horas. Los porcentajes se interpretan dentro de cada fila.', general[3]),
            ('graficos/dia_mes_hora.png', 'Número de día del mes y hora', 'Permite observar si el perfil horario cambia al inicio o al cierre del mes. Cada fila se normaliza por su propio volumen.', general[4]),
        ]),
        ('duracion', 'Duración registrada y días peak', [
            ('eficiencia/peak_vs_habitual.png', '¿Demoran más las revisiones en días peak?', 'La mediana ajustada pasa de 17 a 20 minutos; el P90, de 42 a 58. Peak significa volumen superior al P90 de su planta y mes. Se ajusta por planta, mes, día de semana, resultado y tipo de vehículo, con igual ponderación por planta. Es una asociación, no un efecto causal.', efficiency[0]),
            ('eficiencia/rapidez_dia_semana.png', 'Duración según día de semana', 'La mediana ajustada es de 17 minutos de lunes a viernes y 19 los sábados. De lunes a jueves también coincide el P90 en 43 minutos; no hay un único día ganador.', efficiency[1]),
            ('eficiencia/diferencia_por_planta.png', 'Diferencia de duración en cada planta', 'Treinta plantas tienen una mediana ajustada mayor en días peak; tres empatan. Una menor duración no demuestra mejor calidad ni mayor productividad por trabajador.', None),
            ('eficiencia/calendario_rapidez.png', 'Calendario de duración relativa', 'Índice 100 = mediana de su planta y mes. Esta vista descriptiva no ajusta por mezcla de casos ni por día de semana; no permite recomendar un número de día universal.', None),
        ]),
        ('calendario', 'Dígito, mes correspondiente y revisitas', [
            ('patron_calendario/composicion_inicio_cierre.png', 'Composición del inicio y cierre según el calendario del dígito', 'En la primera semana, el 44% de los intentos iniciales observados de la cohorte tiene el dígito del mes recién terminado. Esto no confirma atraso: falta un vencimiento previo suficiente para el 94,4% de esa primera semana. Cohorte: autos y station wagon particulares, gasolina/diésel/eléctricos, fabricación 1993–2025; excluye revisitas recientes inferidas y órdenes ambiguos.', None),
            ('patron_calendario/curva_sin_revisitas.png', '¿Persiste la U al excluir revisitas recientes inferidas?', 'Se comparan todos los registros B/AB con los que quedan al excluir órdenes ambiguos y visitas dentro de 15 días de un rechazo anterior observado, incluso al cambiar de planta. No hay una marca oficial de reingreso; faltan visitas fuera de la RM o anteriores a 2025.', None),
        ]),
    ]
    parts = ['''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Todos los gráficos · PRT RM 2025</title><style>
:root{color-scheme:light;--ink:#19373c;--teal:#096e70}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f2f5f4;color:var(--ink);font:16px/1.65 system-ui,sans-serif}header,main,footer{max-width:1250px;margin:auto;padding:28px}header{padding-top:48px}h1{font-size:clamp(30px,4vw,48px);line-height:1.15;margin:12px 0}h2{margin-top:42px;scroll-margin-top:90px}h3{font-size:22px;line-height:1.4}a{color:var(--teal)}nav{position:sticky;top:0;z-index:5;background:#fffffff2;backdrop-filter:blur(8px);border-bottom:1px solid #d8e5e0;padding:12px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}nav a{text-decoration:none;padding:4px 12px;border-radius:20px;background:#e8f1ee;font-size:14px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:28px 0}.card{padding:20px;background:#fff;border:1px solid #dce8e2;border-radius:14px}.card strong{display:block;font-size:30px;color:var(--teal)}article,.note{background:white;border:1px solid #dce8e2;border-radius:18px;padding:clamp(16px,3vw,30px);margin:22px 0}article img{display:block;width:100%;height:auto;cursor:zoom-in}figure{margin:18px 0}figcaption,.small{font-size:14px;color:#52676a}details{margin-top:20px;border-top:1px solid #dce8e2;padding-top:14px}summary{cursor:pointer;color:var(--teal);font-weight:600}.interactive{overflow-x:auto;min-height:450px}.plotly-graph-div{min-width:550px}dialog{border:0;border-radius:12px;max-width:98vw;width:1450px;max-height:95vh;padding:16px}dialog::backdrop{background:#102c35d9}dialog img{width:100%;height:auto}button{cursor:pointer;padding:9px 18px;border:0;border-radius:20px;background:var(--teal);color:#fff}dialog button{position:sticky;top:0;float:right}table{border-collapse:collapse;width:100%}td,th{text-align:left;border-bottom:1px solid #dce8e2;padding:10px}footer{font-size:14px}@media print{nav,details,dialog,.zoom-note{display:none}body{background:#fff}article{break-inside:avoid}header,main{padding:0}}
</style></head><body><header><p>REGIÓN METROPOLITANA · ENERO–DICIEMBRE 2025</p><h1>Cuándo se concentran las revisiones técnicas</h1><p>Calendarios, tendencia mensual, horarios y duración del servicio en 33 plantas B/AB.</p>
<div class="cards"><div class="card"><strong>2.320.324</strong>registros distintos publicados</div><div class="card"><strong>26,8%</strong>del mes en sus últimos siete días, en promedio</div><div class="card"><strong>11:00–11:59</strong>franja con más inicios registrados</div><div class="card"><strong>+3 minutos</strong>de mediana ajustada en días peak</div></div>
<p class="small zoom-note">Haz clic en cualquier imagen para ampliarla. Abre «Explorar gráfico interactivo» para consultar valores y las opciones disponibles. Este archivo funciona sin conexión; los enlaces a fuentes requieren internet.</p></header><nav>''']
    parts.extend(f'<a href="#{key}">{escape(title)}</a>' for key, title, _ in groups)
    parts.append('<a href="#fuentes">Fuentes y método</a></nav><main>')
    expected = set()
    for key, title, items in groups:
        parts.append(f'<section id="{key}"><h2>{escape(title)}</h2>')
        for file, subtitle, caption, interactive in items:
            expected.add(file)
            encoded = base64.b64encode((BASE / file).read_bytes()).decode('ascii')
            parts.append(f'<article><h3>{escape(subtitle)}</h3><p>{escape(caption)}</p><figure><img loading="lazy" tabindex="0" src="data:image/png;base64,{encoded}" alt="{escape(subtitle)}"><figcaption>{escape(caption)}</figcaption></figure>')
            if interactive:
                parts.append(f'<details><summary>Explorar gráfico interactivo</summary><div class="interactive">{interactive}</div></details>')
            parts.append('</article>')
        if key == 'duracion':
            parts.append('<article><h3>Volumen y duración: cada planta en cada fecha</h3><p>Vista exploratoria sin ajustar: cada punto representa una planta en una fecha. La dispersión no identifica por sí sola el efecto del volumen.</p><details><summary>Explorar gráfico interactivo</summary><div class="interactive">' + efficiency[2] + '</div></details></article>')
        parts.append('</section>')
    actual = {str(p.relative_to(BASE)).replace('\\', '/') for folder in ['graficos', 'eficiencia', 'patron_calendario'] for p in (BASE / folder).glob('*.png')}
    assert actual == expected, (actual - expected, expected - actual)
    parts.append('''<section id="fuentes"><h2>Fuentes y método</h2><div class="note"><h3>Qué cuenta este informe</h3>
<p>Registros publicados de revisión en 2025 de 33 plantas B/AB de la RM, con cobertura de los doce meses. No son vehículos únicos ni solicitudes de reserva. Se eliminaron 20.512 filas completamente idénticas. Las fechas sin registros se incluyen como cero registros publicados.</p>
<p>La curva asigna a cada fecha su porcentaje dentro del mes y promedia ese porcentaje para cada número de día. Los días 29 y 30 tienen once meses disponibles; el 31, siete. No se ha ajustado esta curva por días de semana ni feriados.</p>
<h3>Duración y comparabilidad</h3><p>Se usan 2.226.014 duraciones positivas (95,94% de los registros), calculadas entre HORA_INI y HORA_FIN dentro de la misma fecha. Se excluyen ceros y fin anterior al inicio; no se inventan cruces de medianoche. No se mide la espera exterior ni los recursos por planta. El P90 es el tiempo que no supera el 90% de los casos ponderados.</p>
<p>El ajuste principal requiere al menos veinte casos por categoría y grupo, compara mezclas comunes y da igual peso a cada planta. Su soporte representa el 86,6% de los tiempos positivos peak y el 33,0% de los habituales. Las asociaciones observadas no prueban causalidad ni calidad del servicio.</p>
<h3>Calendario y línea base</h3><p>La patente está disponible en los archivos fuente, pero no se publica en este informe. El 3,69% de los 878.247 intentos iniciales observados de la cohorte ocurrió en el mes precedente al del dígito (32.409 registros). Es una aproximación de uso de ese mes, no una tasa confirmada de adelantos: puede incluir atrasos de ciclos anteriores. La periodicidad individual y las primeras revisiones bienales requieren historia adicional.</p>
<p>Ni el dígito ni la concentración al inicio prueban que una revisión estuviera vencida o que el conductor esperara el sueldo. Los archivos no tienen un campo explícito de reingreso. Las revisitas se infieren de un rechazo anterior observado y pueden omitir historia fuera de la RM o anterior a 2025.</p>
<h3>Parque vehicular y permisos</h3><p>El INE registra 2.442.537 vehículos motorizados en la RM en 2024 en su tabla 11.2.2 del informe ambiental 2025. No se encontró una cifra regional consolidada y verificable de revisión vencida o permiso impago. Restar los permisos de 2024 de las visitas PRT de 2025 no permite estimar incumplimiento.</p>
<p><a href="https://www.ine.gob.cl/docs/default-source/variables-basicas-ambientales/publicaciones-y-anuarios/informe-anual-de-medio-ambiente/informe-anual-de-estadisticas-del-medio-ambiente-2025.pdf?sfvrsn=62fcb728_4">INE: informe ambiental 2025, tabla 11.2.2</a>. La cifra se verificó en el extracto indexado de esa tabla.</p>
<h3>Fuentes primarias</h3><p><a href="https://www.prt.cl/Descargas/index.html">PRT: índice oficial de descargas</a> · <a href="https://www.prt.cl/Descargas/docs/Codigos_Plantas.xlsx">Catálogo de plantas</a> · <a href="https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx">Diccionario de campos</a> · <a href="https://www.bcn.cl/leychile/navegar?i=10183">Decreto 156: calendario y excepciones</a>.</p><table><thead><tr><th>Período</th><th>Archivo original nacional</th></tr></thead><tbody>''')
    manifest = json.loads((BASE.parents[1] / 'fuentes/manifiesto_2025.json').read_text(encoding='utf-8'))
    for source in manifest:
        parts.append(f'<tr><td>{escape(source["periodo"])}</td><td><a href="{escape(source["url"], quote=True)}">Descargar ZIP SGPRT RB</a></td></tr>')
    parts.append('''</tbody></table></div></section></main><footer>Informe consolidado · RM 2025 · Elaborado el 2 de noviembre de 2026. Imágenes y gráficos interactivos incorporados en este archivo.</footer>
<dialog id="zoom"><button type="button" id="cerrar">Cerrar ×</button><img alt="Gráfico ampliado"></dialog><script>''')
    # One shared offline runtime; chart initializers are deferred until after it.
    runtime = get_plotlyjs()
    prefix = '<script type="text/javascript">'
    # The imported chart initializers are wrapped to run after the complete DOM/runtime.
    content = ''.join(parts)
    doc = html.fromstring(content + '</script></body></html>')
    for script in doc.xpath('//script[contains(text(),"Plotly.newPlot")]'):
        script.text = 'window.addEventListener("load",function(){' + script.text + '\n});'
    # Serialize without the intentionally empty final placeholder script.
    content = '<!doctype html>\n' + html.tostring(doc, encoding='unicode', method='html')
    behavior = '''document.querySelectorAll('article img').forEach(img=>{const open=()=>{document.querySelector('#zoom img').src=img.src;document.querySelector('#zoom img').alt=img.alt;document.querySelector('#zoom').showModal()};img.addEventListener('click',open);img.addEventListener('keydown',e=>{if(e.key==='Enter')open()})});document.querySelector('#cerrar').onclick=()=>document.querySelector('#zoom').close();document.querySelectorAll('details').forEach(d=>d.addEventListener('toggle',()=>{if(d.open)requestAnimationFrame(()=>d.querySelectorAll('.plotly-graph-div').forEach(g=>Plotly.Plots.resize(g)))}));'''
    content = content.replace('</body>', prefix + runtime + '</script><script>' + behavior + '</script></body>')
    out = BASE / 'PRT_RM_2025_todos_los_graficos.html'
    out.write_text(content, encoding='utf-8')
    check = html.fromstring(out.read_text(encoding='utf-8'))
    assert len(check.xpath('//article//img')) == 15
    assert len(check.xpath('//div[contains(@class,"plotly-graph-div")]')) == 9
    assert not check.xpath('//*[@src and not(starts-with(@src,"data:"))]')
    assert len(check.xpath('//*[@id="fuentes"]//tbody/tr')) == 12
    ids = check.xpath('//*[@id]/@id')
    assert len(ids) == len(set(ids))
    print(f'{out}\n15 imágenes y 9 vistas interactivas; {out.stat().st_size:,} bytes; validación correcta.')


if __name__ == '__main__':
    main()
