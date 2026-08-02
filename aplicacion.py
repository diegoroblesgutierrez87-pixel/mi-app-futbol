# --- FIX PYLANCE BUILTINS ---
import builtins as _b
str = _b.str
int = _b.int
float = _b.float
bool = _b.bool
list = _b.list
dict = _b.dict
set = _b.set
tuple = _b.tuple
len = _b.len
range = _b.range
enumerate = _b.enumerate
zip = _b.zip
map = _b.map
max = _b.max
min = _b.min
sorted = _b.sorted
round = _b.round
sum = _b.sum
open = _b.open
isinstance = _b.isinstance
globals = _b.globals
Exception = _b.Exception
# --- FIN FIX ---



import re
import unicodedata
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  # type: ignore
import os
from functools import lru_cache
import json
from datetime import datetime
import subprocess
import sys
import time
import streamlit.components.v1 as components  # <-- ESTA ES LA LÍNEA NUEVA

st.set_page_config(
    page_title="Filtro Jornada", 
    layout="wide",
    initial_sidebar_state="expanded"  # <-- ESTO FUERZA EL SIDEBAR ABIERTO
)
import time
st.caption(f"VERSION-MOVIL-FIX {int(time.time())}")
# CSS LIMPIO - fondo blanco papel - FIX MOVIL
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stToolbar"],
section[data-testid="stSidebar"] > div:first-child,
.block-container {
    background-color: #FFFFFF!important;
    color-scheme: light!important;
}
html, body { background: #FFFFFF!important; }
[data-testid="stDeployButton"],[data-testid="stToolbar"],#MainMenu,footer{display:none!important}
.block-container{padding:3rem .5rem .5rem .5rem!important; background:#FFFFFF!important}

div[data-testid="stExpanderDetails"]{
    padding:8px 4px!important;
    max-height: none!important;
    overflow: visible!important;
}
div[data-testid="stExpander"] div[data-testid="stHorizontalBlock"]{
    display:grid!important;
    grid-template-columns: 32% 32% 32%!important;
    gap:4px!important;
}
div[data-testid="stExpander"] div[data-testid="stHorizontalBlock"] > div{
    width:100%!important;
    min-width:0!important;
}
[data-testid="stWidgetLabel"] p{
    font-size:10px!important;margin:0!important;white-space:nowrap;color:#000!important;
}
table{border-collapse:collapse;width:100%;font-size:9px;font-family:'Source Code Pro',monospace;table-layout:fixed;margin:0; background:#FFFFFF}
thead{display:none}
td{padding:3px 5px!important;border-bottom:2px solid #000!important;border-left:1px solid #d1d5db;border-right:1px solid #d1d5db;vertical-align:middle;line-height:1.15; background:#FFFFFF}

/* FIX MOVIL - solo texto base en negro, respeta colores inline verde/rojo */
@media (max-width: 768px) {
  div[data-testid="stExpanderDetails"]{
    color: #000000!important;
  }
}
</style>
""", unsafe_allow_html=True)


# --- LIMPIEZA FORZADA DE CACHE VIEJO --- (ahora con botón)

def normaliza(nombre: str) -> str:
    # quita acentos, pasa a mayúsculas, limpia espacios
    n = unicodedata.normalize('NFKD', str(nombre))
    n = n.encode('ASCII', 'ignore').decode('ASCII')
    n = n.upper().strip()
    n = re.sub(r'\s+', ' ', n)
    return n
@lru_cache(maxsize=2048)
def abreviar_equipo(nombre):
    n = normaliza(nombre)

    # --- PARCHE DURO: Atlético de Madrid SIEMPRE ATM ---
    if 'ATLETICO' in n or n.startswith('ATLETI') or n in ('ATH MADRID','ATH. MADRID','AT MADRID','ATM'):
        return 'ATM'

    # --- PARCHE DURO: Athletic Club SIEMPRE ATH ---
    if 'ATHLETIC' in n or 'BILBAO' in n:
        return 'ATH'

    mapa = {
        # Holanda
        'HERACLES ALMELO': 'HER', 'HERACLES': 'HER',
        'GRONINGEN': 'GRO', 'FC GRONINGEN': 'GRO',
        'TELSTAR': 'TEL', 'PEC ZWOLLE': 'ZWO', 'ZWOLLE': 'ZWO',
        'VOLENDAM': 'VOL', 'FC VOLENDAM': 'VOL',
        'AJAX': 'AJA', 'AFC AJAX': 'AJA', 'AZ ALKMAAR': 'AZ',
        'FEYENOORD': 'FEY', 'PSV EINDHOVEN': 'PSV', 'PSV': 'PSV',
        'TWENTE': 'TWE', 'FC TWENTE': 'TWE', 'UTRECHT': 'UTR',
        'HEERENVEEN': 'HEE', 'EXCELSIOR': 'EXC',
        # España
        'ATLETICO MADRID': 'ATM', 'ATLETICO DE MADRID': 'ATM',
        'ATHLETIC BILBAO': 'ATH', 'ATHLETIC CLUB': 'ATH',
        'REAL MADRID': 'RMA', 'BARCELONA': 'FCB', 'FC BARCELONA': 'FCB',
        'BETIS': 'BET', 'REAL BETIS': 'BET', 'BETIS SEVILLA': 'BET',
        'SEVILLA': 'SEV', 'VALENCIA': 'VAL', 'VILLARREAL': 'VIL',
        'REAL SOCIEDAD': 'RSO', 'CELTA': 'CEL', 'CELTA VIGO': 'CEL',
        'OSASUNA': 'OSA', 'GETAFE': 'GET', 'ALAVES': 'ALA',
        'GIRONA': 'GIR', 'LAS PALMAS': 'LPA', 'MALLORCA': 'MAL',
        'RAYO VALLECANO': 'RAY', 'ESPANYOL': 'ESP', 'LEGANES': 'LEG',
        'VALLADOLID': 'VLL', 'LEVANTE': 'LEV', 'LEVANTE UD': 'LEV',
        'ELCHE': 'ELC', 'ELCHE CF': 'ELC',
        'REAL OVIEDO': 'OVI', 'OVIEDO': 'OVI',
        # Inglaterra
        'MANCHESTER UNITED': 'MUN', 'MANCHESTER CITY': 'MCI',
        'ARSENAL': 'ARS', 'CHELSEA': 'CHE', 'LIVERPOOL': 'LIV',
        'TOTTENHAM': 'TOT',
        # Otros
        'PARIS SAINT GERMAIN': 'PSG', 'BAYERN MUNICH': 'BAY', 'BAYERN MUNCHEN': 'BAY',
    }
    if n in mapa:
        return mapa[n]

    for pref in ['FC ', 'AFC ', 'SC ', 'AC ', 'AS ', 'CF ', 'REAL ', 'CLUB ', 'DE ', 'LA ', 'UD ', 'SD ']:
        if n.startswith(pref):
            n = n[len(pref):]
    return (n.split()[0][:3]).upper()


##################### H2H COMPACTO - UNICA DEFINICION #####################
@lru_cache(maxsize=8192)
def _formatear_h2h_compacto_cached(key_tuple):
    (lg3, fecha, jorn, ht, at, hg, ag, h1, a1, hpos, apos, hpts, apts, hperf, aperf,
     hs,hst,hf,hc,hy,hr, as_,ast2,af,ac,ay,ar, b365h,b365d,b365a, ftr, eq_norm, home_team, away_team) = key_tuple

    h2, a2 = hg - h1, ag - a1
    is_h = eq_norm == home_team if eq_norm else False
    is_a = eq_norm == away_team if eq_norm else False

    def nv(t,b=False,u=False):
        return f"<span style='font-weight:{900 if b else 600}{';text-decoration:underline;text-decoration-thickness:2px' if u else ''}'>{t}</span>"

    if eq_norm:
        won = (is_h and hg > ag) or (is_a and ag > hg)
        lost = (is_h and hg < ag) or (is_a and ag < hg)
        color_linea = "#0f8105" if won else "#f31818" if lost else "#f89007"
        color = color_linea
    else:
        color_linea = "#0A2342"
        color = "#444"

    try:
        s_win = "font-weight:900; color:#000"; s_norm = "color:#555"
        odds = f"<span style='{s_win if ftr=='H' else s_norm}'>{b365h:.2f}</span> <span style='{s_win if ftr=='D' else s_norm}'>{b365d:.2f}</span> <span style='{s_win if ftr=='A' else s_norm}'>{b365a:.2f}</span>"
    except:
        odds = ""

    ht_line = f"<span style='color:{color_linea}'>1ªP: {nv(ht,h1>a1,is_h)} {nv(h1,h1>a1,is_h)}-{nv(a1,a1>h1,is_a)} {nv(at,a1>h1,is_a)}</span>"
    st_line = f"<span style='color:{color_linea}'>2ªP: {nv(ht,h2>a2,is_h)} {nv(h2,h2>a2,is_h)}-{nv(a2,a2>h2,is_a)} {nv(at,a2>h2,is_a)}</span>"
    ft_line = f"<span style='color:{color_linea};font-weight:900'>FINAL: {nv(ht,hg>ag,is_h)} {nv(hg,hg>ag,is_h)}-{nv(ag,ag>hg,is_a)} {nv(at,ag>hg,is_a)}</span>"

    pos = f"{nv(str(hpos)+'º',False,is_h)} <span style='color:#000'>vs</span> {nv(str(apos)+'º',False,is_a)}"
    pts = f"{nv(hpts,False,is_h)}-<span style='color:#000'>pts</span> {nv(apts,False,is_a)}"

    ht_res = ht if h1>a1 else at if a1>h1 else 'E'
    ft_res = ht if hg>ag else at if ag>hg else 'E'
    res = f"<span style='color:{color};font-weight:700'>{ht_res}/{ft_res}</span>"

    lineas = [
        f"{lg3} {res}",
        f"{fecha} |{jorn}|",
        odds,
        ht_line,
        st_line,
        ft_line,
        pos,
        pts,
        f"<span style='color:#000'>Perf:</span>{nv(hperf,hg>ag,is_h)}-{nv(aperf,ag>hg,is_a)}",
        f"1p:{nv(str(h1)+'G',False,is_h)}",
        f"1p:{nv(str(a1)+'G',False,is_a)}",
        f"2p:{nv(str(h2)+'G',False,is_h)}",
        f"2p:{nv(str(a2)+'G',False,is_a)}",
        nv(f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R",hg>ag,is_h),
        nv(f"{as_}T {ast2}TP {af}F {ac}C {ay}A {ar}R",ag>hg,is_a)
    ]
    return f"<div style='font-family:monospace; font-size:11px; line-height:1.15; padding:3px 2px; border-bottom:1px solid #ddd; white-space:nowrap'>{ '<br>'.join(lineas) }</div>"

def formatear_h2h_compacto(row, equipo_ref=None):
    try:
        eq_norm = normaliza(equipo_ref) if equipo_ref else ""
        lg3 = str(row.get('League',''))[:3].upper()
        fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
        jorn = f"J{int(row['Jornada'])}"
        ht = row.get('HomeAbbr', abreviar_equipo(row['HomeTeam']))
        at = row.get('AwayAbbr', abreviar_equipo(row['AwayTeam']))
        key = (
            lg3, fecha, jorn, ht, at,
            int(row['FTHG']), int(row['FTAG']), int(row['HTHG']), int(row['HTAG']),
            int(row.get('HomePosPrev',0)), int(row.get('AwayPosPrev',0)),
            int(row.get('HomePtsPrev',0)), int(row.get('AwayPtsPrev',0)),
            round(float(row.get('HomePerf',0)),1), round(float(row.get('AwayPerf',0)),1),
            int(row.get('HS',0)), int(row.get('HST',0)), int(row.get('HF',0)), int(row.get('HC',0)), int(row.get('HY',0)), int(row.get('HR',0)),
            int(row.get('AS',0)), int(row.get('AST',0)), int(row.get('AF',0)), int(row.get('AC',0)), int(row.get('AY',0)), int(row.get('AR',0)),
            float(row.get('B365H',0) or 0), float(row.get('B365D',0) or 0), float(row.get('B365A',0) or 0),
            str(row.get('FTR','')),
            eq_norm, str(row.get('HomeTeam','')), str(row.get('AwayTeam',''))
        )
        return _formatear_h2h_compacto_cached(key)
    except Exception:
        return "<div style='font-size:10px'>-</div>"
##################### FIN H2H UNICO #####################

def jornadas_conteo(jornadas, df_ref=None, equipo=None, rival=None, parte="Todo"):
    from collections import Counter
    if df_ref is None or equipo is None:
        c = Counter(jornadas)
        return "|".join([f"J{int(j)}-{c[j]}#" if c[j]>1 else f"J{int(j)}" for j in sorted(c)])

    df_eq = df_ref[(df_ref['HomeTeam']==equipo) | (df_ref['AwayTeam']==equipo)] if len(df_ref) > 300 else df_ref
    if df_eq.empty:
        return ""

    is_home_s = (df_eq['HomeTeam']==equipo)
    final_gf_arr = np.where(is_home_s, df_eq['FTHG'].to_numpy(), df_eq['FTAG'].to_numpy())
    final_gc_arr = np.where(is_home_s, df_eq['FTAG'].to_numpy(), df_eq['FTHG'].to_numpy())
    win_s = pd.Series(final_gf_arr > final_gc_arr, index=df_eq.index)
    loss_s = pd.Series(final_gf_arr < final_gc_arr, index=df_eq.index)

    partes = []
    for (season, j), g in df_eq.groupby(['Season','Jornada'], sort=True):
        if g.empty:
            continue
        if win_s.loc[g.index].all():
            color = '#0f8105'
        elif loss_s.loc[g.index].all():
            color = '#f31818'
        else:
            color = '#0A2342'

        first_row = g.iloc[0]
        is_h_first = first_row['HomeTeam']==equipo
        if len(g)==1:
            sufijo_final = 'c' if is_h_first else 'f'
        else:
            all_home = (g['HomeTeam']==equipo).all()
            all_away = (g['AwayTeam']==equipo).all()
            sufijo_final = 'c' if all_home else 'f' if all_away else 'cf'

        real_home = int(first_row['FTHG'])
        real_away = int(first_row['FTAG'])
        home_short = str(first_row['HomeTeam'])[:3].upper()
        away_short = str(first_row['AwayTeam'])[:3].upper()
        h_pos = int(first_row.get('HomePosPrev', 0))
        a_pos = int(first_row.get('AwayPosPrev', 0))
        es_local = first_row['HomeTeam'] == equipo

        if es_local:
            htgf, htgc = int(first_row['HTHG']), int(first_row['HTAG'])
            ftgf, ftgc = real_home, real_away
        else:
            htgf, htgc = int(first_row['HTAG']), int(first_row['HTHG'])
            ftgf, ftgc = real_away, real_home

        res_ht = 'G' if htgf > htgc else 'P' if htgf < htgc else 'E'
        res_ft = 'G' if ftgf > ftgc else 'P' if ftgf < ftgc else 'E'
        am = " ▪" if real_home > 0 and real_away > 0 else ""

        if es_local:
            txt = f"J{int(j)}{sufijo_final}<u>{h_pos}º {home_short} {real_home}</u>-{real_away} {away_short} {a_pos}º {res_ht}/{res_ft}{am}"
        else:
            txt = f"J{int(j)}{sufijo_final}{h_pos}º {home_short} {real_home}-<u>{real_away} {away_short} {a_pos}º</u> {res_ht}/{res_ft}{am}"

        es_h2h = False
        if rival:
            es_h2h = ((g['HomeTeam']==equipo) & (g['AwayTeam']==rival)).any() or ((g['HomeTeam']==rival) & (g['AwayTeam']==equipo)).any()

        viñeta = "".join([formatear_h2h_compacto(r, equipo) for _, r in g.iterrows()])
        
                # ESTILO TEXTO SIMPLE, SIN BURBUJA NI BORDE tamaño J1f9º WES 1-0 BLA 10º P/P....
        estilos_summary = f"color:{color};font-weight:700;cursor:pointer;list-style:none;display:inline-block;background:transparent;border:none;padding:1px 3px;margin:0;white-space:nowrap;font-size:11px;font-family:monospace;letter-spacing:-0.4px;word-spacing:-1.2px;line-height:20px"
        if es_h2h:
            estilos_summary += ";text-decoration:underline;text-decoration-thickness:2px"

        jx_html = f"""<details style="display:inline-block;margin:1px 1px;padding:0;vertical-align:middle">
        <summary style="{estilos_summary}">{txt}</summary>
        <div style="position:absolute;z-index:9999;top:100%;left:0;background:#FFFFFF;border:2px solid #000;padding:4px;margin-top:4px;box-shadow:4px 4px 10px rgba(0,0,0,0.4);max-width:360px;min-width:320px;text-align:left;white-space:normal">{viñeta}</div>
    </details>"""
        partes.append(jx_html)

    # CON GAP JUSTO PARA DEDO
    separador = " <span style='color:#999;font-size:9px;font-weight:900;margin:0 1px'>|</span> "
    return f"<div style='display:flex;flex-wrap:wrap;gap:2px 2px;align-items:center;line-height:1.8;padding:2px 0'>{separador.join(partes)}</div>"





###########bloque rachas comprimidas "filtro actual"

def racha_comprimida_html(df_team, equipo):
    if df_team.empty:
        return ""
    df_team = df_team.sort_values('Date')
    res = []
    for _, r in df_team.iterrows():
        is_home = r['HomeTeam'] == equipo
        hg, ag = int(r['FTHG']), int(r['FTAG'])
        if is_home:
            res.append('G' if hg>ag else 'P' if hg<ag else 'E')
        else:
            res.append('G' if ag>hg else 'P' if ag<hg else 'E')
    comp = []
    cnt = 1
    for i in range(1, len(res)):
        if res[i]==res[i-1]: cnt+=1
        else: comp.append((cnt,res[i-1])); cnt=1
    comp.append((cnt,res[-1]))

    sep = "<span style='color:#bbb;font-size:11px;margin:0 1px'>|</span>"
    parts = []
    for c, letra in comp:
        col = "#0f8105" if letra=='G' else "#f31818" if letra=='P' else "#0A2342"
        parts.append(f"<span style='color:{col};font-weight:700;font-size:11px;line-height:1.1'>{c}{letra}</span>")
    return sep.join(parts)
############################################
def racha_ambos_marcan_html(df_team):
    if df_team.empty:
        return ""
    df_team = df_team.sort_values('Date')
    res = ['si' if int(r['FTHG'])>0 and int(r['FTAG'])>0 else 'no' for _,r in df_team.iterrows()]
    comp = []
    cnt=1
    for i in range(1,len(res)):
        if res[i]==res[i-1]: cnt+=1
        else: comp.append(f"{cnt}{res[i-1]}"); cnt=1
    comp.append(f"{cnt}{res[-1]}")

    sep = "<span style='color:#bbb;font-size:7px;margin:0 1px'>|</span>"
    return sep.join([f"<span style='font-size:11px;font-weight:700;color:#000;line-height:1.1'>{x}</span>" for x in comp])
    ##############
with st.expander("⚙ Opciones avanzadas"):
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧪 Borrar cache", width='stretch'):
            for f in ['ligas_2122_a_2526.parquet', 'ligas_2122_a_2526.parquet.lock']:
                if os.path.exists(f):
                    os.remove(f)
            st.cache_data.clear()
            st.rerun()

    with col_b:
        if st.button("🔄 Actualizar 25/26", type="primary", width='stretch'):
            with st.spinner("Descargando jornadas nuevas..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "actualizar_ligas.py"], 
                        capture_output=True, 
                        text=True, 
                        timeout=180
                    )
                    st.code(result.stdout)
                    if result.returncode == 0:
                        st.cache_data.clear()
                        for f in ['ligas_2122_a_2526.parquet', 'ligas_2122_a_2526.parquet.lock']:
                            if os.path.exists(f):
                                os.remove(f)
                        st.success("✅ Actualizado")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Falló")
                        st.code(result.stderr)
                except Exception as e:
                    st.error(f"Error: {e}")
# --- FIN BOTONES ---

# --- INICIALIZAR SESSION STATE ---
if 'rango_cuotas' not in st.session_state: 
    st.session_state.rango_cuotas = (1.5, 10.0)
if 'rango_minutos' not in st.session_state: 
    st.session_state.rango_minutos = (0, 120)
if 'pct_marcador' not in st.session_state: 
    st.session_state.pct_marcador = 1
if 'xx_filtro' not in st.session_state: st.session_state.xx_filtro = "Todo"

# anti-traductor
components.html("""<script>
const doc = window.parent.document;
doc.documentElement.setAttribute('translate','no');
</script>""", height=0)



@st.cache_data
def cargar_todo():
    import os, re
    # 1. Carga base
    if os.path.exists('ligas_2122_a_2526.parquet'):
        df = pd.read_parquet('ligas_2122_a_2526.parquet')
    else:
        df = pd.read_csv('ligas_2122_a_2526.csv', low_memory=False)

    # 2. ¿Necesitamos el parche de LaLiga 24/25?
    tiene_laliga_2425 = ((df['League'] == 'LaLiga') & (df['Season'] == '2024/2025')).any()

    if not tiene_laliga_2425:
        df2 = None
        if os.path.exists('laliga_2425_partidos.parquet'):
            df2 = pd.read_parquet('laliga_2425_partidos.parquet')
        elif os.path.exists('laliga_2425_partidos.csv'):
            df2 = pd.read_csv('laliga_2425_partidos.csv', low_memory=False)

        if df2 is not None and not df2.empty:
            df = pd.concat([
                df[~((df['League']=='LaLiga') & (df['Season']=='2024/2025'))],
                df2
            ], ignore_index=True)

    # 3. Resto igual (limpieza)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df[df['Date'].notna()]

    df['__tiene_cuota'] = df['B365H'].astype(str).str.strip().ne('') & df['B365H'].notna()
    df = df.sort_values('__tiene_cuota', ascending=False)
    df = df.drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League'], keep='first')
    df = df.drop(columns='__tiene_cuota')

    for col in ['League','Season','HomeTeam','AwayTeam']:
        df[col] = df[col].astype(str).str.strip().str.replace('"','').str.replace("'",'')
    for col in ['HomeTeam','AwayTeam']:
        df[col] = df[col].apply(normaliza)

    mapa_unifica = {
    'HERACLES ALMELO':'HERACLES','SC HERACLES ALMELO':'HERACLES','SC HERACLES':'HERACLES',
    'FC GRONINGEN':'GRONINGEN','PEC ZWOLLE':'ZWOLLE','FC ZWOLLE':'ZWOLLE',
    'FC VOLENDAM':'VOLENDAM','SC TELSTAR':'TELSTAR','AFC AJAX':'AJAX','AJAX AMSTERDAM':'AJAX',
    'AZ ALKMAAR':'AZ','PSV EINDHOVEN':'PSV','FC TWENTE':'TWENTE','FC TWENTE ENSCHEDE':'TWENTE',
    'FC UTRECHT':'UTRECHT','SC HEERENVEEN':'HEERENVEEN','SBV EXCELSIOR':'EXCELSIOR','EXCELSIOR ROTTERDAM':'EXCELSIOR',
    'ATLETICO DE MADRID':'ATLETICO MADRID',
    'ATH MADRID':'ATLETICO MADRID', 'ATH. MADRID':'ATLETICO MADRID', 'AT MADRID':'ATLETICO MADRID',
    'ATHLETIC CLUB':'ATHLETIC BILBAO',
    'VALLECANO':'RAYO VALLECANO','RAYO VALLECANO MADRID':'RAYO VALLECANO',
    'DEPORTIVO ALAVES':'ALAVES','LEVANTE UD':'LEVANTE',
    'ELCHE CF':'ELCHE', 'REAL OVIEDO':'OVIEDO',
}
    df['HomeTeam'] = df['HomeTeam'].replace(mapa_unifica)
    df['AwayTeam'] = df['AwayTeam'].replace(mapa_unifica)

    df = df.sort_values('Date')
    df['pair'] = df.apply(lambda r: tuple(sorted([r['HomeTeam'], r['AwayTeam']])), axis=1)
    df = df.sort_values('Date').groupby(['Season','League','pair'], as_index=False).head(2)
    df = df.drop(columns='pair')
    def norm_season(s):
        s = str(s)
        if re.match(r'^\d{4}/\d{4}$', s): return s
        if re.match(r'^\d{4}$', s): return f"20{s[:2]}/20{s[2:]}"
        return s
    df['Season'] = df['Season'].apply(norm_season)
    df = df[df['League'].notna() & (df['League']!='nan')]

    cols_num = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR']
    for col in cols_num:
        df[col] = pd.to_numeric(df.get(col,0), errors='coerce').fillna(0)
    if 'FTR' not in df.columns:
        df['FTR'] = np.where(df['FTHG']>df['FTAG'],'H',np.where(df['FTHG']<df['FTAG'],'A','D'))
    for col in ['B365H','B365D','B365A']:
        df[col] = pd.to_numeric(df.get(col,np.nan), errors='coerce')

    ##########LOGICA: COLUMNAS CALCULADAS GOLES/STATS

    df['GolesTotales'] = df['FTHG']+df['FTAG']
    df['GolesHT'] = df['HTHG']+df['HTAG']
    df['HomeAbbr'] = df['HomeTeam'].apply(abreviar_equipo)
    df['AwayAbbr'] = df['AwayTeam'].apply(abreviar_equipo)
    df['Goles2T'] = df['GolesTotales']-df['GolesHT']
    df['corneTot'] = df['HC']+df['AC']
    df['TargAmTot'] = df['HY']+df['AY']
    df['tirosTot'] = df['HS']+df['AS']
    df['tirosPuertaTot'] = df['HST']+df['AST']
    df['faltasTot'] = df['HF']+df['AF']
    df['TargRojTot'] = df['HR']+df['AR']
    return df.copy()

df = cargar_todo()
df_original = df.copy()  # <-- AÑADE ESTA LÍNEA

@st.cache_data
def cargar_eventos(league, season):
    import os
    if os.path.exists('laliga_2425_goles.parquet'):
        df_g = pd.read_parquet('laliga_2425_goles.parquet')
    elif os.path.exists('laliga_2425_goles.csv'):
        df_g = pd.read_csv('laliga_2425_goles.csv', low_memory=False)
        
        
    else:
        return {}

    # --- MAPEO INTELIGENTE DE COLUMNAS ---
    cols = {c.lower(): c for c in df_g.columns}
    def get(col_options):
        for opt in col_options:
            if opt.lower() in cols: return cols[opt.lower()]
        return None

    col_date = get(['Date','Fecha','fecha'])
    col_home = get(['HomeTeam','Local','Equipo_Local','local'])
    col_away = get(['AwayTeam','Visitante','Equipo_Visitante','visitante'])
    col_min = get(['minuto','Minuto','minute','Minute'])
    col_gol = get(['goleador','Goleador','jugador','Jugador','player'])
    col_ast = get(['asistente','Asistente','assist'])
    col_tipo = get(['tipo','Tipo','type'])
    col_eq = get(['equipo','Equipo','team'])

    # renombra a estándar
    rename_map = {}
    if col_date: rename_map[col_date] = 'Date'
    if col_home: rename_map[col_home] = 'HomeTeam'
    if col_away: rename_map[col_away] = 'AwayTeam'
    if col_min: rename_map[col_min] = 'minuto'
    if col_gol: rename_map[col_gol] = 'goleador'
    if col_ast: rename_map[col_ast] = 'asistente'
    if col_tipo: rename_map[col_tipo] = 'tipo'
    if col_eq: rename_map[col_eq] = 'equipo'
    df_g = df_g.rename(columns=rename_map)
    
    if 'asistente' not in df_g.columns:
        df_g['asistente'] = ''
    if 'tipo' not in df_g.columns:
        df_g['tipo'] = ''
    if 'equipo' not in df_g.columns:
        df_g['equipo'] = ''
    

    # si faltan columnas clave, salimos
    for req in ['Date','HomeTeam','AwayTeam','minuto','goleador']:
        if req not in df_g.columns:
            st.error(f"Tu CSV no tiene columna '{req}'. Columnas encontradas: {list(df_g.columns)}")
            return {}

    # normaliza nombres equipos
    for col in ['HomeTeam','AwayTeam','equipo']:
        if col in df_g.columns:
            df_g[col] = df_g[col].apply(normaliza)

    # filtro opcional
    if 'League' in df_g.columns and 'Season' in df_g.columns:
        df_g = df_g[(df_g['League']==league) & (df_g['Season']==season)]

    df_g['Date'] = pd.to_datetime(df_g['Date'], dayfirst=True, errors='coerce')
    df_g = df_g.dropna(subset=['Date'])
    df_g['Date'] = df_g['Date'].dt.strftime('%Y-%m-%d')



    eventos_dict = {}
    for (ht, at, fecha), grupo in df_g.groupby(['HomeTeam','AwayTeam','Date']):
        evs = []
        for _, r in grupo.sort_values('minuto').iterrows():
            tipo = str(r.get('tipo','')).lower()
            evs.append({
                "minute": int(r['minuto']),
                "player": str(r['goleador']),
                "assist": str(r.get('asistente','')) if pd.notna(r.get('asistente')) else "",
                "extra": None,
                "penalty": 'pen' in tipo,
                "missed": 'penx' in tipo or tipo == 'x',
                "team": normaliza(str(r.get('equipo','')))
            })
        key = (ht, at, fecha) # ht y at ya están normalizados
        eventos_dict[key] = evs
    return eventos_dict
     
##########LOGICA: GOLES POR MINUTO/JUGADOR
def buscar_goles_partido(row, eventos_dict, min_min=0, max_min=120, parte="Todo", equipo_filtro=None):
    if pd.isna(row['Date']):
        return ""
    key = (row['HomeTeam'], row['AwayTeam'], row['Date'].strftime('%Y-%m-%d'))
    evs = eventos_dict.get(key, [])
    if not evs:
        return ""

    hg = int(row['FTHG']); ag = int(row['FTAG'])
    ganador = row['HomeTeam'] if hg > ag else row['AwayTeam'] if ag > hg else None
    filtro_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro!= "Ninguno" else None

    txt = []
    for ev in evs:
        minuto = ev.get('minute', 0)
        if parte == "1T" and minuto > 45: continue
        if parte == "2T" and minuto <= 45: continue
        if not (min_min <= minuto <= max_min): continue

        team = ev.get('team','')
        if filtro_norm and team!= filtro_norm:
            continue

        if ev.get('penalty'):
            minuto_txt = f"{minuto}'(penX)" if ev.get('missed') else f"{minuto}'(pen)"
        else:
            minuto_txt = f"{minuto}'"

        gol_text = f"{minuto_txt} {ev.get('player','')}"
        if ev.get('assist') and not ev.get('missed'):
            gol_text += f" ({ev['assist']})"

        estilos = []
        if filtro_norm and team == filtro_norm:
            estilos.append("text-decoration:underline; text-decoration-thickness:2px")
        if ganador and team == ganador:
            estilos.append("font-weight:900")
        txt.append(f"<span style=\"{';'.join(estilos)}\">{gol_text}</span>" if estilos else gol_text)

    return " | ".join(txt)
###################def formatear_partido
def formatear_partido(row, equipo_filtro=None, cuota_tipo=None, goles_txt=""):
    ht, at = row['HomeTeam'], row['AwayTeam']
    ht_disp = row.get('HomeAbbr', abreviar_equipo(ht))
    at_disp = row.get('AwayAbbr', abreviar_equipo(at))
    league = row.get('League','')
    fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
    jornada = f"J{int(row['Jornada'])}" if pd.notna(row.get('Jornada')) else ''
    hg_num, ag_num = int(row['FTHG']), int(row['FTAG'])
    hpts, apts = int(row['HomePtsPrev']), int(row['AwayPtsPrev'])
    hpos, apos = int(row['HomePosPrev']), int(row['AwayPosPrev'])
    hy, ay = int(row['HY']), int(row['AY']); hr, ar = int(row['HR']), int(row['AR'])
    hc, ac = int(row['HC']), int(row['AC']); hs, as_ = int(row['HS']), int(row['AS'])
    hst, ast = int(row['HST']), int(row['AST']); hf, af = int(row['HF']), int(row['AF'])
    hthg, htag = int(row['HTHG']), int(row['HTAG'])
    h2tg = hg_num - hthg; a2tg = ag_num - htag

    NAVY = "#0A2342"
    style_base = f"color:{NAVY}; font-weight:600; font-size:9px; font-style:normal!important"
    style_ganador = f"color:{NAVY}; font-weight:900; font-size:9px; font-style:normal!important"
    style_subrayado = "text-decoration:underline; text-decoration-thickness:2px; font-style:normal!important"

    ht_res = ht_disp if hthg > htag else at_disp if hthg < htag else 'E'
    ft_res = ht_disp if hg_num > ag_num else at_disp if hg_num < ag_num else 'E'
    color_res = "#444"
    eq_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro!= "Ninguno" else None
    if eq_norm:
        won = (eq_norm == ht and hg_num > ag_num) or (eq_norm == at and ag_num > hg_num)
        lost = (eq_norm == ht and hg_num < ag_num) or (eq_norm == at and ag_num < hg_num)
        color_res = "#0f8105" if won else "#f31818" if lost else "#f89007"

    cuota_h = row.get('B365H'); cuota_d = row.get('B365D'); cuota_a = row.get('B365A')
    league_short = str(league)[:3].upper()
    home_perf = round(float(row.get('HomePerf',0)),1); away_perf = round(float(row.get('AwayPerf',0)),1)

    hg_txt = f"<span style='{style_base}'>{hg_num}</span>"; ag_txt = f"<span style='{style_base}'>{ag_num}</span>"
    hpts_txt = f"<span style='{style_base}'>{hpts}</span>"; apts_txt = f"<span style='{style_base}'>{apts}</span>"
    hpos_txt = f"<span style='{style_base}'>{hpos}º</span>"; apos_txt = f"<span style='{style_base}'>{apos}º</span>"
    ht_txt = ht_disp; at_txt = at_disp
    home_perf_txt = f"<span style='{style_base}'>{home_perf:.1f}</span>"
    away_perf_txt = f"<span style='{style_base}'>{away_perf:.1f}</span>"

    if hg_num > ag_num:
        ht_txt = f"<span style='{style_ganador}'>{ht_disp}</span>"; hg_txt = f"<span style='{style_ganador}'>{hg_num}</span>"
        hpts_txt = f"<span style='{style_ganador}'>{hpts}</span>"; hpos_txt = f"<span style='{style_ganador}'>{hpos}º</span>"
        home_perf_txt = f"<span style='{style_ganador}'>{home_perf:.1f}</span>"
    elif ag_num > hg_num:
        at_txt = f"<span style='{style_ganador}'>{at_disp}</span>"; ag_txt = f"<span style='{style_ganador}'>{ag_num}</span>"
        apts_txt = f"<span style='{style_ganador}'>{apts}</span>"; apos_txt = f"<span style='{style_ganador}'>{apos}º</span>"
        away_perf_txt = f"<span style='{style_ganador}'>{away_perf:.1f}</span>"

    if eq_norm == ht:
        sty = f"{style_ganador if hg_num>ag_num else style_base}; {style_subrayado}"
        ht_txt = f"<span style='{sty}'>{ht_disp}</span>"; hg_txt = f"<span style='{sty}'>{hg_num}</span>"
        hpts_txt = f"<span style='{sty}'>{hpts}</span>"; hpos_txt = f"<span style='{sty}'>{hpos}º</span>"
        home_perf_txt = f"<span style='{sty}'>{home_perf:.1f}</span>"
    if eq_norm == at:
        sty = f"{style_ganador if ag_num>hg_num else style_base}; {style_subrayado}"
        at_txt = f"<span style='{sty}'>{at_disp}</span>"; ag_txt = f"<span style='{sty}'>{ag_num}</span>"
        apts_txt = f"<span style='{sty}'>{apts}</span>"; apos_txt = f"<span style='{sty}'>{apos}º</span>"
        away_perf_txt = f"<span style='{sty}'>{away_perf:.1f}</span>"

    top_line = f"<div style='font-size:9px'>{league_short} <span style='color:{color_res};font-weight:700'>{ht_res}/{ft_res}</span></div>"
    jornada_html = f"<span style='color:#0A2342;font-weight:700'>{jornada}</span>" if jornada else ""
    date_line = f"<div style='font-size:9px'>{fecha} |{jornada_html}|</div>"

    odds_html = ""
    if pd.notna(cuota_h) and pd.notna(cuota_d) and pd.notna(cuota_a):
        try:
            ftr = row.get('FTR', '')
            h_o = f"{float(cuota_h):.2f}"; d_o = f"{float(cuota_d):.2f}"; a_o = f"{float(cuota_a):.2f}"
            h_s = "font-weight:900; color:#000" if ftr == 'H' else "font-weight:600; color:#555"
            d_s = "font-weight:900; color:#000" if ftr == 'D' else "font-weight:600; color:#555"
            a_s = "font-weight:900; color:#000" if ftr == 'A' else "font-weight:600; color:#555"
            odds_html = f"<div style='font-size:9px'><span style='{h_s}'>{h_o}</span> <span style='{d_s}'>{d_o}</span> <span style='{a_s}'>{a_o}</span></div>"
        except: pass

    color_linea = color_res if eq_norm else "#0A2342"
    ht_style = "font-weight:900" if hg_num > ag_num else "font-weight:600"
    at_style = "font-weight:900" if ag_num > hg_num else "font-weight:600"
    if eq_norm == ht:
        ht_style += ";text-decoration:underline;text-decoration-thickness:2px"
    if eq_norm == at:
        at_style += ";text-decoration:underline;text-decoration-thickness:2px"
    
    # --- NUEVO: calcular goles por parte ---#"cartas" de los partidos
    h1, a1 = int(row['HTHG']), int(row['HTAG'])
    h2, a2 = hg_num - h1, ag_num - a1
    ht_line = f"<div style='font-size:9px;color:{color_linea}'>1ªP: <span style='{ht_style}'>{ht_disp}</span> {h1}-{a1} <span style='{at_style}'>{at_disp}</span></div>"
    st_line = f"<div style='font-size:9px;color:{color_linea}'>2ªP: <span style='{ht_style}'>{ht_disp}</span> {h2}-{a2} <span style='{at_style}'>{at_disp}</span></div>"
    ft_line = f"<div style='font-size:9px;color:{color_linea};font-weight:900'>FINAL: <span style='{ht_style}'>{ht_disp}</span> {hg_num}-{ag_num} <span style='{at_style}'>{at_disp}</span></div>"
    pos_line = f"<div style='font-size:9px'>{hpos_txt} vs {apos_txt}</div>"
    pts_line = f"<div style='font-size:9px'>{hpts_txt}-pts {apts_txt}</div>"
    perf_line = f"<div style='font-size:9px'>Perf:{home_perf_txt}-{away_perf_txt}</div>"

    def wrap(v, win, fil):
        s = style_ganador if win else style_base
        if fil: s += f"; {style_subrayado}"
        return f"<span style='{s}'>{v}</span>"

    h1_g = f"1p:{wrap(f'{hthg}G', hg_num>ag_num, eq_norm==ht)}"
    a1_g = f"1p:{wrap(f'{htag}G', ag_num>hg_num, eq_norm==at)}"
    h2_g = f"2p:{wrap(f'{h2tg}G', hg_num>ag_num, eq_norm==ht)}"
    a2_g = f"2p:{wrap(f'{a2tg}G', ag_num>hg_num, eq_norm==at)}"
    sh = wrap(f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R", hg_num>ag_num, eq_norm==ht)
    sa = wrap(f"{as_}T {ast}TP {af}F {ac}C {ay}A {ar}R", ag_num>hg_num, eq_norm==at)

    stats_html = f"<div style='font-size:7.5px'>{h1_g}</div><div style='font-size:7.5px'>{a1_g}</div><div style='font-size:7.5px'>{h2_g}</div><div style='font-size:7.5px'>{a2_g}</div><div style='font-size:7px'>{sh}</div><div style='font-size:7px'>{sa}</div>"

    goles_html = f"<div style='font-size:9px;color:{NAVY}'>{goles_txt}</div>" if goles_txt else ""
    return f'<div translate="no" lang="zxx" style="border-bottom:2px solid #000; padding-bottom:4px; margin-bottom:6px">{top_line}{date_line}{odds_html}{ht_line}{st_line}{ft_line}{pos_line}{pts_line}{perf_line}{stats_html}{goles_html}</div>'
####def formatear_h2h_compacto



####def def calcular_htft




def calcular_htft(row, equipo):
    if equipo == row['HomeTeam']:
        gf, gc = row['FTHG'], row['FTAG']
        htgf, htgc = row['HTHG'], row['HTAG']
    elif equipo == row['AwayTeam']:
        gf, gc = row['FTAG'], row['FTHG']
        htgf, htgc = row['HTAG'], row['HTHG']
    else:
        return None

    if htgf > htgc:
        res_ht = 'G'
    elif htgf < htgc:
        res_ht = 'P'
    else:
        res_ht = 'E'

    if gf > gc:
        res_ft = 'G'
    elif gf < gc:
        res_ft = 'P'
    else:
        res_ft = 'E'

    return f"{res_ht}/{res_ft}"

def crear_columna_tarjetas_corners(row, equipo_filtro=None):
    ht, at = row['HomeTeam'], row['AwayTeam']
    hy, ay = int(row['HY']), int(row['AY']); hr, ar = int(row['HR']), int(row['AR']); hc, ac = int(row['HC']), int(row['AC'])
    hthg, htag = int(row['HTHG']), int(row['HTAG']); fthg, ftag = int(row['FTHG']), int(row['FTAG'])
    h2tg = fthg - hthg; a2tg = ftag - htag
    style_subrayado = "text-decoration:underline; text-decoration-thickness:2px"
    def balon_con_numero(parte, goles):
        if goles == 0: return ""
        return f"<span style='display:inline-flex; align-items:center; margin-right:6px'><span style='margin-right:3px; font-size:9px; color:#555; font-weight:600'>{parte}</span><span style='display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; background:#000; color:#fff; border-radius:50%; font-size:11px; font-weight:900; border:2px solid #000'>{goles}</span></span>"
    def badge_equipo(eq, amarillas, rojas, corners, gol_ht, gol_2t, subrayar=False):
        badges = []
        if amarillas > 0: badges.append(f"<span style='display:inline-block; background:#fbbf24; color:#000; font-weight:700; font-size:11px; padding:0px 4px; border-radius:2px; margin:0 2px; min-width:14px; text-align:center; line-height:1.4'>{amarillas}</span>")
        if rojas > 0: badges.append(f"<span style='display:inline-block; background:#dc2626; color:#fff; font-weight:700; font-size:11px; padding:0px 4px; border-radius:2px; margin:0 2px; min-width:14px; text-align:center; line-height:1.4'>{rojas}</span>")
        if corners > 0: badges.append(f"<span style='margin-left:4px; margin-right:4px; font-size:11px; font-weight:600'>{corners} ⛳</span>")
        badges.append(balon_con_numero('1P', gol_ht)); badges.append(balon_con_numero('2P', gol_2t))
        badges = [b for b in badges if b]
        if badges:
            nombre_eq = f"<span style='{style_subrayado}'>{eq}</span>" if subrayar else f"<b>{eq}</b>"
            return f"<span style='font-size:11px'>{nombre_eq}: {' '.join(badges)}</span>"
        return ""
    h_badge = badge_equipo(row.get('HomeAbbr', abreviar_equipo(ht)), hy, hr, hc, hthg, h2tg, equipo_filtro == ht)
    a_badge = badge_equipo(row.get('AwayAbbr', abreviar_equipo(at)), ay, ar, ac, htag, a2tg, equipo_filtro == at)
    if h_badge and a_badge: return f"<div style='text-align:left; line-height:1.8'>{h_badge}<br>{a_badge}</div>"
    elif h_badge: return f"<div style='text-align:left'>{h_badge}</div>"
    elif a_badge: return f"<div style='text-align:left'>{a_badge}</div>"
    return ""


################################# FIN RESULTADO_HT_FT#################################

@st.cache_data
def calcular_estado_jornada(df):
    df = df.sort_values(['League','Season','Date']).copy()
##########bloque para que las jornadas vallan de 1 en 1
# 1) Jornada - 1 jornada = todos los equipos juegan una vez
    for (l, s), g in df.groupby(['League','Season'], sort=False):
        g = g.sort_values('Date')
        teams = pd.unique(g[['HomeTeam','AwayTeam']].values.ravel())
        per_jor = max(1, len(teams) // 2)
        # asigna jornada secuencial: 0-9 → J1, 10-19 → J2, etc.
        jornadas = (np.arange(len(g)) // per_jor) + 1
        df.loc[g.index, 'Jornada'] = jornadas
    df['Jornada'] = df['Jornada'].astype(int)
    

    # 2) Puntos del partido
    df['HPts'] = np.where(df['FTR']=='H', 3, np.where(df['FTR']=='D', 1, 0))
    df['APts'] = np.where(df['FTR']=='A', 3, np.where(df['FTR']=='D', 1, 0))

    # 3) Puntos previos
    df['HomePtsPrev'] = df.groupby(['League','Season','HomeTeam'])['HPts']\
                        .transform(lambda x: x.cumsum().shift(fill_value=0))
    df['AwayPtsPrev'] = df.groupby(['League','Season','AwayTeam'])['APts']\
                        .transform(lambda x: x.cumsum().shift(fill_value=0))

    # 4) Posiciones previas con numpy
    home_pos = pd.Series(0, index=df.index, dtype=int)
    away_pos = pd.Series(0, index=df.index, dtype=int)
    tablas = []

    for (l, s), g in df.groupby(['League','Season'], sort=False):
        g = g.sort_values(['Jornada','Date'])
        teams = pd.unique(g[['HomeTeam','AwayTeam']].values.ravel())
        idx_map = {t:i for i, t in enumerate(teams)}
        n = len(teams)

        pts = np.zeros(n, dtype=int)
        gf = np.zeros(n, dtype=int)
        gc = np.zeros(n, dtype=int)
        pj = np.zeros(n, dtype=int)
        pg = np.zeros(n, dtype=int)
        pe = np.zeros(n, dtype=int)
        pp = np.zeros(n, dtype=int)

        last_jor = None

        for row in g.itertuples():
            hi = idx_map[row.HomeTeam]
            ai = idx_map[row.AwayTeam]

            if last_jor is not None and row.Jornada!= last_jor:
                snap = pd.DataFrame({
                    'Equipo': teams, 'Pts': pts, 'PJ': pj, 'PG': pg,
                    'PE': pe, 'PP': pp, 'GF': gf, 'GC': gc, 'DG': gf-gc
                })
                snap['Pos'] = snap['Pts'].rank(method='min', ascending=False).astype(int)
                snap = snap.sort_values(['Pts','DG','GF'], ascending=False)
                snap['Jornada'] = last_jor
                snap['League'] = l
                snap['Season'] = s
                tablas.append(snap)

            dg = gf - gc
            order = np.lexsort((-gf, -dg, -pts))
            ranks = np.empty(n, dtype=int)
            ranks[order] = np.arange(1, n+1)

            home_pos.at[row.Index] = ranks[hi]
            away_pos.at[row.Index] = ranks[ai]

            pj[hi] += 1; pj[ai] += 1
            gf[hi] += row.FTHG; gc[hi] += row.FTAG
            gf[ai] += row.FTAG; gc[ai] += row.FTHG

            if row.FTR == 'H':
                pts[hi] += 3; pg[hi] += 1; pp[ai] += 1
            elif row.FTR == 'A':
                pts[ai] += 3; pg[ai] += 1; pp[hi] += 1
            else:
                pts[hi] += 1; pts[ai] += 1; pe[hi] += 1; pe[ai] += 1

            last_jor = row.Jornada

        if last_jor is not None:
            snap = pd.DataFrame({
                'Equipo': teams, 'Pts': pts, 'PJ': pj, 'PG': pg,
                'PE': pe, 'PP': pp, 'GF': gf, 'GC': gc, 'DG': gf-gc
            })
            snap['Pos'] = snap['Pts'].rank(method='min', ascending=False).astype(int)
            snap = snap.sort_values(['Pts','DG','GF'], ascending=False)
            snap['Jornada'] = last_jor
            snap['League'] = l
            snap['Season'] = s
            tablas.append(snap)

    df['HomePosPrev'] = home_pos
    df['AwayPosPrev'] = away_pos
    df_clasificacion = pd.concat(tablas, ignore_index=True) if tablas else pd.DataFrame()

    # ResHtFt vectorizado - usa abreviaturas ya calculadas
    if 'HomeAbbr' in df.columns and 'AwayAbbr' in df.columns:
        abbr_map = {}
        abbr_map.update(dict(zip(df['HomeTeam'], df['HomeAbbr'])))
        abbr_map.update(dict(zip(df['AwayTeam'], df['AwayAbbr'])))
    else:
        abbr_map = {t: abreviar_equipo(t) for t in pd.unique(df[['HomeTeam','AwayTeam']].values.ravel())}
    ht_res = np.where(df['HTHG'] > df['HTAG'], df['HomeTeam'].map(abbr_map),
             np.where(df['HTHG'] < df['HTAG'], df['AwayTeam'].map(abbr_map), 'E'))
    ft_res = np.where(df['FTHG'] > df['FTAG'], df['HomeTeam'].map(abbr_map),
             np.where(df['FTHG'] < df['FTAG'], df['AwayTeam'].map(abbr_map), 'E'))
    df['ResHtFt'] = ht_res + '/' + ft_res

    # PUNTAJE RENDIMIENTO
    df['RivalProHome'] = df['AwayPosPrev'] <= 6
    df['RivalProAway'] = df['HomePosPrev'] <= 6
    df['HomePerf'] = np.where(df['FTR']=='H',1.5,np.where(df['FTR']=='D',0.5,0)) + 0.15*df['HST'] - 0.05*df['AST'] + 0.05*df['HC'] - 0.02*df['AC'] - 0.10*df['HY'] - 0.25*df['HR'] + 0.5*df['RivalProHome']*(df['FTR']=='H')
    df['AwayPerf'] = np.where(df['FTR']=='A',1.5,np.where(df['FTR']=='D',0.5,0)) + 0.15*df['AST'] - 0.05*df['HST'] + 0.05*df['AC'] - 0.02*df['HC'] - 0.10*df['AY'] - 0.25*df['AR'] + 0.5*df['RivalProAway']*(df['FTR']=='A')

    return df, df_clasificacion

   
#######################nuevo bloque: def get_df_base_calculado(_df, ligas_tuple, temps_tuple):

@st.cache_data
def get_df_base_calculado(_df, ligas_tuple, temps_tuple):
    df_fil = _df[_df['League'].isin(ligas_tuple) & _df['Season'].isin(temps_tuple)]
    return calcular_estado_jornada(df_fil)
 
 #######################nuevo bloque

#############filtro rachas

##########LOGICA: CALCULO RACHAS G/E/P

@st.cache_data
def _rachas(df_base, cond, loc, x_max=None):
    df = df_base.copy()
    if 'Jornada' not in df.columns:
        df['Jornada'] = 0

    h = df[['Date','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    h['Equipo'] = h['HomeTeam']
    h['Res'] = h['FTR'].map({'H':'G','A':'P','D':'E'})
    h['Loc'] = 'Local'

    a = df[['Date','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    a['Equipo'] = a['AwayTeam']
    a['Res'] = a['FTR'].map({'A':'G','H':'P','D':'E'})
    a['Loc'] = 'Visitante'

    d = pd.concat([h, a], ignore_index=True)
    if loc in ['Local','Visitante']:
        d = d[d['Loc'] == loc]

    d = d.sort_values(['Equipo','Date'])
    d['Jornada'] = pd.to_numeric(d['Jornada'], errors='coerce').fillna(0).astype(int)

    mapa = {"G": {'G'}, "P": {'P'}, "E": {'E'}, "G/E": {'G','E'}, "E/P": {'E','P'}, "G/P": {'G','P'}}
    cs = {'G','P','E'} if cond == "Todo" else mapa[cond]

    out = []
    for eq, g in d.groupby('Equipo'):
        s = g['Res'].tolist()
        js = g['Jornada'].tolist()
        runs = []
        run = []
        for r, j in zip(s, js):
            if r in cs:
                run.append(int(j))
            else:
                if run:
                    runs.append(run)
                    run = []
        if run:
            runs.append(run)

        max_seg = max((len(r) for r in runs), default=0)
        total = sum(1 for r in s if r in cs)
        pct = round(100 * total / len(s), 1) if s else 0
        ult5 = ''.join(s[-5:])

        if x_max:
            runs_x = [r for r in runs if len(r) >= x_max]
            count_x = len(runs_x)
            jornadas_x = sorted(set(j for r in runs_x for j in r))
            jornadas_str = ', '.join(f"J{j}" for j in jornadas_x) if jornadas_x else "-"
            texto = f"{eq} | {len(s)}J | {max_seg} max | {count_x}# | {pct}% | {ult5}\n↳ {jornadas_str}"
            out.append({'Equipo': texto, 'PJ': len(s), 'Max': max_seg, 'CountX': count_x, '%': pct})
        else:
            jornadas_ok = sorted(set(int(j) for r, j in zip(s, js) if r in cs))
            jornadas_str = ', '.join(f"J{j}" for j in jornadas_ok)
            texto = f"{eq} | {len(s)}J | {max_seg} max | {pct}% | {ult5}\n↳ {jornadas_str}"
            out.append({'Equipo': texto, 'PJ': len(s), 'Max': max_seg, '%': pct})

    return pd.DataFrame(out)
############fin filtro racchas

    


def limpiar_filtros():
    st.session_state.parte_gol_eq2 = "Todo"
    st.session_state.margen_jornadas_filtro = "Todos"
    st.session_state.marcador_filtro_eq2 = "Todos"
    st.session_state.marcador_filtro = "Todos"
    st.session_state.pct_marcador = 1
    st.session_state.columna_filtro = "Ninguno"
    st.session_state.operador_filtro = "="
    st.session_state.valor_filtro = "Ninguno"
    st.session_state.columna_filtro2 = "Ninguno"
    st.session_state.operador_filtro2 = "="
    st.session_state.valor_filtro2 = "Ninguno"
    st.session_state.alcance_filtro2 = "Todo"
    st.session_state.columna_filtro3 = "Ninguno"
    st.session_state.operador_filtro3 = "="
    st.session_state.valor_filtro3 = "Ninguno"
    st.session_state.alcance_filtro3 = "Todo"
    st.session_state.equipo_filtro = "Ninguno"
    st.session_state.resultado_filtro = "Ninguno"
    st.session_state.resultado_filtro_eq2 = "Ninguno"
    st.session_state.ambos_marcan = "Todos"
    st.session_state.ambos_marcan_eq2 = "Todos"
    st.session_state.equipo_clasificacion = "Ninguno"
    st.session_state.equipos_grafica = []
    st.session_state.condicion_filtro = "Todo"
    st.session_state.condicion_filtro3 = "Todo" # <-- AÑADE ESTA
    st.session_state.htft_filtro = "Todo"
    st.session_state.cuota_tipo = "Todo"
    st.session_state.cuota_operador = "Mayor o igual"
    st.session_state.rango_cuotas = (1.5, 10.0)
    st.session_state.jugador_filtro = "TODOS"
    st.session_state.rango_minutos = (0, 120)
    st.session_state.parte_gol = "Todo"
    st.session_state.alcance_filtro = "Todo"
    st.session_state.equipo2_filtro = "Ninguno"
    st.session_state.margen_filtro = "Todo"
    st.session_state.margen_filtro_eq2 = "Todo"
    st.session_state.ultimos_part_filtro = "Todos"




######"Filtros de partidos"



with st.expander("Filtros de partidos", expanded=False):
    ligas_disponibles = sorted(df['League'].unique())
    temporadas_disponibles = sorted(df['Season'].unique())

    st.caption(f"Ligas detectadas: {', '.join(ligas_disponibles)}")

    st.markdown("**Liga**")
    liga_sel = st.multiselect("Liga", ligas_disponibles, default=[ligas_disponibles[0]] if ligas_disponibles else [],
        format_func=lambda x: '\u2060'.join(x), label_visibility="collapsed", key="filtro_liga_main")

    st.markdown("**Temporada**")
    temp_sel = st.multiselect("Temporada", temporadas_disponibles, default=[temporadas_disponibles[-1]] if temporadas_disponibles else [], label_visibility="collapsed", key="filtro_temp_main")
    modo_vista = "Jornadas"

    df_fil = df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)]

    if df_fil.empty:
        st.stop()

    @st.cache_data
    def calcular_estado_jornada_rapido(df, temporadas, ligas):
        df_fil = df[df['League'].isin(ligas) & df['Season'].isin(temporadas)]
        return calcular_estado_jornada(df_fil)


    with st.spinner('Calculando clasificación...'):
        df_base, df_clas_base = get_df_base_calculado(df, tuple(liga_sel), tuple(temp_sel))

    df_rachas_full = df_base.copy()
    df_final = df_base.copy()
    df_clasificacion = df_clas_base.copy()
    
    jornadas = sorted(df_final['Jornada'].unique())  # <-- ESTA LÍNEA FALTABA
    

    if len(jornadas) > 0:
        min_j, max_j = int(min(jornadas)), int(max(jornadas))
        col_j1, col_j2 = st.columns(2)
        j_desde = col_j1.number_input("Jornada De", min_value=min_j, max_value=max_j, value=min_j, key='j_desde', step=1)
        j_hasta = col_j2.number_input("Jornada A", min_value=min_j, max_value=max_j, value=max_j, key='j_hasta', step=1)
        # Validamos que De <= A
        if j_desde > j_hasta:
            st.warning("Jornada 'De' no puede ser mayor que 'A'")
            j_desde = j_hasta
        rango_jornadas = (int(j_desde), int(j_hasta))
    else:
        rango_jornadas = (0, 0)

        # --- RANGO CUOTAS CON CAJITAS ---
    col_c1, col_c2 = st.columns(2)
    cuota_desde = col_c1.number_input(
        "Cuota De",
        min_value=1.0,
        max_value=40.0,
        value=st.session_state.rango_cuotas[0],
        step=0.05,
        key='cuota_desde'
    )
    cuota_hasta = col_c2.number_input(
        "Cuota A",
        min_value=1.0,
        max_value=40.0,
        value=st.session_state.rango_cuotas[1],
        step=0.05,
        key='cuota_hasta'
    )

    if cuota_desde > cuota_hasta:
        st.warning("Cuota 'De' no puede ser mayor que 'A'")
        cuota_desde = cuota_hasta

    rango_cuotas = (float(cuota_desde), float(cuota_hasta))
    st.session_state.rango_cuotas = rango_cuotas
    # --- FIN RANGO CUOTAS ---
    rango_minutos = st.slider("Minutos", 0, 120, st.session_state.rango_minutos, 1, key='rango_minutos')

if len(jornadas) > 0:
    df_final = df_final[(df_final['Jornada'] >= rango_jornadas[0]) & (df_final['Jornada'] <= rango_jornadas[1])]
    df_clasificacion = df_clasificacion[(df_clasificacion['Jornada'] >= rango_jornadas[0]) & (df_clasificacion['Jornada'] <= rango_jornadas[1])]

    df_base_h2h = df_final.copy()

    todos_eventos = {}
    for liga in liga_sel:
        for temp in temp_sel:
            todos_eventos.update(cargar_eventos(liga, temp))

    if 'marcador_filtro' not in st.session_state: st.session_state.marcador_filtro = "Todos"
    if 'marcador_filtro_eq2' not in st.session_state: st.session_state.marcador_filtro_eq2 = "Todos"
    if 'pct_marcador' not in st.session_state: st.session_state.pct_marcador = 0
    if 'columna_filtro' not in st.session_state: st.session_state.columna_filtro = "Ninguno"
    if 'operador_filtro' not in st.session_state: st.session_state.operador_filtro = "="
    if 'valor_filtro' not in st.session_state: st.session_state.valor_filtro = "Ninguno"
    if 'columna_filtro2' not in st.session_state: st.session_state.columna_filtro2 = "Ninguno"
    if 'operador_filtro2' not in st.session_state: st.session_state.operador_filtro2 = "="
    if 'valor_filtro2' not in st.session_state: st.session_state.valor_filtro2 = "Ninguno"
    if 'alcance_filtro2' not in st.session_state: st.session_state.alcance_filtro2 = "Todo"
    if 'columna_filtro3' not in st.session_state: st.session_state.columna_filtro3 = "Ninguno"
    if 'operador_filtro3' not in st.session_state: st.session_state.operador_filtro3 = "="
    if 'valor_filtro3' not in st.session_state: st.session_state.valor_filtro3 = "Ninguno"
    if 'alcance_filtro3' not in st.session_state: st.session_state.alcance_filtro3 = "Todo"
    if 'equipo_filtro' not in st.session_state: st.session_state.equipo_filtro = "Ninguno"
    if 'resultado_filtro' not in st.session_state: st.session_state.resultado_filtro = "Ninguno"
    if 'resultado_filtro_eq2' not in st.session_state: st.session_state.resultado_filtro_eq2 = "Ninguno"
    if 'ambos_marcan' not in st.session_state: st.session_state.ambos_marcan = "Todos"
    if 'ambos_marcan_eq2' not in st.session_state: st.session_state.ambos_marcan_eq2 = "Todos"
    if 'condicion_filtro' not in st.session_state: st.session_state.condicion_filtro = "Todo"
    if 'condicion_filtro3' not in st.session_state: st.session_state.condicion_filtro3 = "Todo" # <-- AÑADE ESTA
    if 'htft_filtro' not in st.session_state: st.session_state.htft_filtro = "Todo"
    if 'jugador_filtro' not in st.session_state: st.session_state.jugador_filtro = "TODOS"
    if 'cuota_tipo' not in st.session_state: st.session_state.cuota_tipo = "Todo"
    if 'parte_gol' not in st.session_state: st.session_state.parte_gol = "Todo"
    if 'parte_gol_eq2' not in st.session_state: st.session_state.parte_gol_eq2 = "Todo"
    if 'alcance_filtro' not in st.session_state: st.session_state.alcance_filtro = "Todo"
    if 'equipo2_filtro' not in st.session_state: st.session_state.equipo2_filtro = "Ninguno"
    if 'margen_filtro' not in st.session_state: st.session_state.margen_filtro = "Todo"
    if 'margen_filtro_eq2' not in st.session_state: st.session_state.margen_filtro_eq2 = "Todo"
    if 'ultimos_part_filtro' not in st.session_state: st.session_state.ultimos_part_filtro = "Todos"

    columnas_numericas = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','tirosTot','tirosPuertaTot','faltasTot','TargRojTot','HomePtsPrev','AwayPtsPrev','HomePosPrev','AwayPosPrev','HomePerf','AwayPerf']
    ABREV_COL = {
        'FTHG': 'GL','FTAG': 'GV','HTHG': 'G1L','HTAG': 'G1V',
        'HS': 'TL','AS': 'TV','HST': 'TPL','AST': 'TPV',
        'HF': 'FL','AF': 'FV','HC': 'CL','AC': 'CV',
        'HY': 'AL','AY': 'AV','HR': 'RL','AR': 'RV',
        'GolesTotales': 'GT','GolesHT': 'GHT','Goles2T': 'G2T',
        'corneTot': 'CT','TargAmTot': 'TAM',
        'tirosTot': 'TT','tirosPuertaTot': 'TPT','faltasTot': 'FT','TargRojTot': 'TRT',
        'HomePtsPrev': 'PtL','AwayPtsPrev': 'PtV',
        'HomePosPrev': 'PosL','AwayPosPrev': 'PosV',
        'HomePerf': 'PfL','AwayPerf': 'PfV',
        'Ninguno': '—',
    }
    opciones_col = [
        "Ninguno",
        "_GOL_",
        "GolesTotales", "GolesHT", "Goles2T", "FTHG", "FTAG", "HTHG", "HTAG",
        "_TARJ_",
        "TargAmTot", "TargRojTot", "HY", "AY", "HR", "AR",
        "_TIR_",
        "tirosTot", "tirosPuertaTot", "HS", "AS", "HST", "AST",
        "_CORN_",
        "corneTot", "HC", "AC",
        "_FALT_",
        "faltasTot", "HF", "AF",
        "_CLASF_",
        "HomePtsPrev", "AwayPtsPrev", "HomePosPrev", "AwayPosPrev", "HomePerf", "AwayPerf"
    ]
    equipos_disponibles = sorted(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

    opciones_1x2 = ["Ninguno","Gana","Pierde","Empata","Gana/Empata","Gana/Pierde","Empata/Pierde"]
    mapa_1x2 = {"Ninguno":"-", "Gana":"G", "Pierde":"P", "Empata":"E", "Gana/Empata":"GE", "Gana/Pierde":"GP", "Empata/Pierde":"EP"}
    ABREV_MARGEN = {"Todo":"—","Empate":"E","Gana 1":"G1","Gana 2":"G2","Gana 3+":"G3+","Pierde 1":"P1","Pierde 2":"P2","Pierde 3+":"P3+","Gana ≥2":"G2+","Pierde ≥2":"P2+"}
############filtros avanzados
    with st.expander("🎛 Filtros avanzados", expanded=False):
        # --- LINEA 1: Eq1 Eq2 (Eq2 en col 3 para caer encima de L/V3) ---
        l1 = st.columns(3)
        equipo_filtro = l1[0].selectbox("Eq1", ["Ninguno"] + equipos_disponibles, key='equipo_filtro')
        equipo2_filtro = l1[2].selectbox("Eq2", ["Ninguno"] + equipos_disponibles, key='equipo2_filtro')

        # --- LINEA 1b: L/V... L/V3 ---
        l1b = st.columns(3)
        condicion_filtro = l1b[0].selectbox("L/V", ["Todo", "Local", "Visitante"], key='condicion_filtro')
        condicion_filtro3 = l1b[2].selectbox("L/V3", ["Todo", "Local", "Visitante"], key='condicion_filtro3')

        # --- LINEA 2: Col1 Col2 Col3 ---
        l2 = st.columns(3)
        columna_filtro = l2[0].selectbox("Col1", opciones_col, format_func=lambda x: ABREV_COL.get(x, x), key='columna_filtro')
        columna_filtro2 = l2[1].selectbox("Col2", opciones_col, format_func=lambda x: ABREV_COL.get(x, x), key='columna_filtro2')
        columna_filtro3 = l2[2].selectbox("Col3", opciones_col, format_func=lambda x: ABREV_COL.get(x, x), key='columna_filtro3')

        # --- LINEA 3: Op1 Op2 Op3 ---
        l3 = st.columns(3)
        operador_filtro = l3[0].selectbox("Op1", ["=", ">", ">=", "<", "<="], key='operador_filtro')
        operador_filtro2 = l3[1].selectbox("Op2", ["=", ">", ">=", "<", "<="], key='operador_filtro2')
        operador_filtro3 = l3[2].selectbox("Op3", ["=", ">", ">=", "<", "<="], key='operador_filtro3')

        # --- LINEA 4: Vlr1 Vlr2 Vlr3 ---
        l4 = st.columns(3)
        valor_filtro = l4[0].selectbox("Vlr1", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro')
        valor_filtro2 = l4[1].selectbox("Vlr2", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro2')
        valor_filtro3 = l4[2].selectbox("Vlr3", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro3')

        # --- LINEA 5: Fav/Cntr1 Fav/Cntr2 Fav/Cntr3 ---
        l5 = st.columns(3)
        alcance_filtro = l5[0].selectbox("Fav/Cntr1", ["Todo","AF","C"] + [f"AF{i}" for i in range(31)] + [f"C{i}" for i in range(31)], key='alcance_filtro', help="Todo=total | AF=a favor | C=en contra")
        alcance_filtro2 = l5[1].selectbox("Fav/Cntr2", ["Todo","AF","C"] + [f"AF{i}" for i in range(31)] + [f"C{i}" for i in range(31)], key='alcance_filtro2')
        alcance_filtro3 = l5[2].selectbox("Fav/Cntr3", ["Todo","AF","C"] + [f"AF{i}" for i in range(31)] + [f"C{i}" for i in range(31)], key='alcance_filtro3')

        # --- LINEA 6: AM(Eq1) X/X AM3(Eq2) ---
        l6 = st.columns(3)
        ambos_marcan = l6[0].selectbox("AM (Eq1)", ["Todos","Si","No","Si1P","No1P","Si2P","No2P","Si1pNo2p","No1pSi2p","Si1pSi2p"], key='ambos_marcan')
        xx_filtro = l6[1].selectbox("X/X", ["Todo","G/X","E/X","P/X","X/G","X/E","X/P"], key='xx_filtro', help="G/X:Gana al descanso | X/G:Gana al final")
        ambos_marcan_eq2 = l6[2].selectbox("AM3 (Eq2)", ["Todos","Si","No","Si1P","No1P","Si2P","No2P","Si1pNo2p","No1pSi2p","Si1pSi2p"], key='ambos_marcan_eq2')

        # --- LINEA 7: 1x2 Eq1 R1x2 1x2 Eq2 --- (ORDEN FINAL)
        l7 = st.columns(3)
        resultado_filtro = l7[0].selectbox("1x2 (Eq1)", opciones_1x2, format_func=lambda x: mapa_1x2[x], key='resultado_filtro')
        cuota_tipo = l7[1].selectbox("R1x2", ["Ninguno","Todo","1","X","2"], key='cuota_tipo')
        resultado_filtro_eq2 = l7[2].selectbox("1x2 (Eq2)", opciones_1x2, format_func=lambda x: mapa_1x2[x], key='resultado_filtro_eq2')

        # --- LINEA 7b: MARGEN + HT/FT + MARGEN EQ2 ---
        l7b = st.columns(3)
        margen_filtro = l7b[0].selectbox("Margen", list(ABREV_MARGEN.keys()), format_func=lambda x: ABREV_MARGEN.get(x, x), key='margen_filtro')
        htft_filtro = l7b[1].selectbox("R=HT/FT", ["Todo","G/G","G/E","G/P","E/G","E/E","E/P","P/G","P/E","P/P","RE","FAIL"], key='htft_filtro')
        margen_filtro_eq2 = l7b[2].selectbox("Margen Eq2", list(ABREV_MARGEN.keys()), format_func=lambda x: ABREV_MARGEN.get(x, x), key='margen_filtro_eq2')

        # --- LINEA 8: Marcador Parte Eq1 Parte Eq2 % ---
        marcadores_unicos = sorted(
            (df_final['FTHG'].astype(int).astype(str) + '-' + df_final['FTAG'].astype(int).astype(str)).unique(),
            key=lambda s: (int(s.split('-')[0]), int(s.split('-')[1]))
        )
        l8 = st.columns(5)
        marcador_filtro = l8[0].selectbox("Marc Eq1", ["Todos"] + marcadores_unicos, key='marcador_filtro')
        marcador_filtro_eq2 = l8[1].selectbox("Marc Eq2", ["Todos"] + marcadores_unicos, key='marcador_filtro_eq2')
        parte_gol = l8[2].selectbox("Parte Eq1", ["Todo","1T","2T"], key='parte_gol')
        parte_gol_eq2 = l8[3].selectbox("Parte Eq2", ["Todo","1T","2T"], key='parte_gol_eq2')
        with l8[4]:
            st.caption("% De - A")
            c_p1, c_p2 = st.columns(2)
            # por defecto 1% a 100%
            if 'pct_min' not in st.session_state: st.session_state.pct_min = 1
            if 'pct_max' not in st.session_state: st.session_state.pct_max = 100

            pct_min = c_p1.number_input("min", min_value=0, max_value=100, value=st.session_state.pct_min, step=5, key='pct_min', label_visibility="collapsed")
            pct_max = c_p2.number_input("max", min_value=0, max_value=100, value=st.session_state.pct_max, step=5, key='pct_max', label_visibility="collapsed")

            if pct_min > pct_max:
                st.warning("Min no puede ser mayor que Max")
                pct_min = pct_max

            # compatibilidad con tu código viejo
            st.session_state.pct_marcador = pct_min
            pct_marcador = pct_min
            rango_pct = (pct_min, pct_max)

        # --- LINEA 9: Jugador ---
        from collections import defaultdict, Counter
        player_teams = defaultdict(Counter)
        for (ht, at, fecha), evs in todos_eventos.items():
            for ev in evs:
                if ev.get('missed') or not ev.get('player'):
                    continue
                team = ev.get('team')
                if team:
                    player_teams[ev['player']][team] += 1
        player_to_team = {p: max(cnts.items(), key=lambda x: x[1])[0] for p, cnts in player_teams.items()} if player_teams else {}
        lista_jug = sorted([p for p,t in player_to_team.items() if t==equipo_filtro]) if equipo_filtro!="Ninguno" else sorted(player_to_team.keys())

        # --- NUEVA CAJITA ULTIMOS PART. ---
        c_ult, c_mar = st.columns(2)
        ultimos_opciones = ["Todos"] + list(range(1, 39))
        ultimos_part_filtro = c_ult.selectbox("Últimos part.", ultimos_opciones, key='ultimos_part_filtro', help="Últimos N que tienen que cumplir el filtro")

        margen_j_opciones = ["Todos"] + list(range(1, 39))
        if 'margen_jornadas_filtro' not in st.session_state:
            st.session_state.margen_jornadas_filtro = "Todos"
        margen_jornadas_filtro = c_mar.selectbox("Margen J", margen_j_opciones, key='margen_jornadas_filtro', help="En cuantas jornadas busco esos N. Ej: Ult 5 + Margen 10 = 5 que cumplan dentro de las últimas 10 jugadas")

        jugador_filtro = st.selectbox("Jugador", ["TODOS"] + lista_jug, key='jugador_filtro')

        st.button("Limpiar", on_click=limpiar_filtros, use_container_width=False)
    
    
    
    
    # --- RESUMEN DE FILTROS ACTIVOS - FIX COL2 Y COL3 ---
    filtros_activos = []

    if equipo_filtro!= "Ninguno":
        filtros_activos.append(f"Eq1:{equipo_filtro}")
    if equipo2_filtro!= "Ninguno":
        filtros_activos.append(f"Eq2:{equipo2_filtro}")
    if condicion_filtro!= "Todo":
        filtros_activos.append(f"L/V:{condicion_filtro}")
    if condicion_filtro3!= "Todo":
        filtros_activos.append(f"L/V3:{condicion_filtro3}")
    if resultado_filtro!= "Ninguno":
        filtros_activos.append(f"1x2:{mapa_1x2[resultado_filtro]}")
    if resultado_filtro_eq2!= "Ninguno":
        filtros_activos.append(f"1x2 Eq2:{mapa_1x2[resultado_filtro_eq2]}")
    if ambos_marcan!= "Todos":
        filtros_activos.append(f"AM:{ambos_marcan}")
    if ambos_marcan_eq2!= "Todos":
        filtros_activos.append(f"AM3:{ambos_marcan_eq2}")
    if htft_filtro!= "Todo":
        filtros_activos.append(f"HT/FT:{htft_filtro}")
    if xx_filtro!= "Todo":
        filtros_activos.append(f"X/X:{xx_filtro}")
    if margen_filtro!= "Todo":
        filtros_activos.append(f"Margen:{ABREV_MARGEN[margen_filtro]}")
    if marcador_filtro!= "Todos":
        filtros_activos.append(f"Marc:{marcador_filtro}")
    if pct_marcador > 0:
        filtros_activos.append(f"Min%:{pct_marcador}%")
    if cuota_tipo not in ["Ninguno","Todo"]:
        filtros_activos.append(f"R1x2:{cuota_tipo}")
    if not (rango_cuotas[0]==1.5 and rango_cuotas[1]==10.0):
        filtros_activos.append(f"Cuotas:{rango_cuotas[0]}-{rango_cuotas[1]}")
    if parte_gol!= "Todo":
        filtros_activos.append(f"Parte:{parte_gol}")
    if jugador_filtro!= "TODOS":
        filtros_activos.append(f"Jug:{jugador_filtro}")
    if not (rango_minutos[0]==0 and rango_minutos[1]>=120):
        filtros_activos.append(f"Min:{rango_minutos[0]}-{rango_minutos[1]}")
    if str(ultimos_part_filtro)!="Todos":
        txt_ult = f"Ult:{ultimos_part_filtro}"
        if str(st.session_state.get('margen_jornadas_filtro',"Todos"))!="Todos":
            txt_ult += f"/{st.session_state.get('margen_jornadas_filtro')}J"
        filtros_activos.append(txt_ult)

    def fmt_col(col, op, val, alc):
        if col=="Ninguno" or val=="Ninguno":
            return None
        txt = f"{ABREV_COL.get(col, col)}{op}{val}"
        if alc!= "Todo":
            txt = f"{alc}:{txt}"
        return txt

    c1 = fmt_col(columna_filtro, operador_filtro, valor_filtro, alcance_filtro)
    c2 = fmt_col(columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2)
    c3 = fmt_col(columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3)

    if c1:
        filtros_activos.append(c1)
    if c2:
        filtros_activos.append(c2)
    if c3:
        filtros_activos.append(c3)

    if len(jornadas) > 0 and (rango_jornadas[0]!=min_j or rango_jornadas[1]!=max_j):
        filtros_activos.append(f"J:{rango_jornadas[0]}-{rango_jornadas[1]}")

       # --- RESUMEN FILTROS SIMPLE 2 LINEAS - FIX FINAL + MARC EQ2 ---
    eq1_list = []
    eq2_list = []

    if equipo_filtro!="Ninguno": eq1_list.append(f"{equipo_filtro}")
    if condicion_filtro!="Todo": eq1_list.append(f"L/V:{condicion_filtro}")
    if c1: eq1_list.append(c1)
    if c2: eq1_list.append(c2)
    if resultado_filtro!="Ninguno": eq1_list.append(f"1x2:{mapa_1x2[resultado_filtro]}")
    if ambos_marcan!="Todos": eq1_list.append(f"AM:{ambos_marcan}")
    if htft_filtro!="Todo": eq1_list.append(f"HT/FT:{htft_filtro}")
    if xx_filtro!="Todo": eq1_list.append(f"X/X:{xx_filtro}")
    if margen_filtro!="Todo": eq1_list.append(f"Margen:{ABREV_MARGEN[margen_filtro]}")
    if parte_gol!="Todo": eq1_list.append(f"Parte:{parte_gol}")
    if marcador_filtro!="Todos": eq1_list.append(f"Marc:{marcador_filtro}")

    if equipo2_filtro!="Ninguno": eq2_list.append(f"{equipo2_filtro}")
    if condicion_filtro3!="Todo": eq2_list.append(f"L/V3:{condicion_filtro3}")
    if c3: eq2_list.append(c3)
    if resultado_filtro_eq2!="Ninguno": eq2_list.append(f"1x2:{mapa_1x2[resultado_filtro_eq2]}")
    if ambos_marcan_eq2!="Todos": eq2_list.append(f"AM3:{ambos_marcan_eq2}")
    if margen_filtro_eq2!="Todo": eq2_list.append(f"Margen:{ABREV_MARGEN[margen_filtro_eq2]}")
    if parte_gol_eq2!="Todo": eq2_list.append(f"Parte:{parte_gol_eq2}")
    if marcador_filtro_eq2!="Todos": eq2_list.append(f"Marc:{marcador_filtro_eq2}")

    comunes = []
    if pct_marcador>1: comunes.append(f"Min%:{pct_marcador}%")
    if cuota_tipo not in ["Ninguno","Todo"]: comunes.append(f"R1x2:{cuota_tipo}")
    if not (rango_cuotas[0]==1.5 and rango_cuotas[1]==10.0): comunes.append(f"Cuotas:{rango_cuotas[0]}-{rango_cuotas[1]}")
    if jugador_filtro!="TODOS": comunes.append(f"Jug:{jugador_filtro}")
    if len(jornadas) > 0 and (rango_jornadas[0]!=min_j or rango_jornadas[1]!=max_j): comunes.append(f"J:{rango_jornadas[0]}-{rango_jornadas[1]}")
    if str(ultimos_part_filtro)!="Todos":
        if str(st.session_state.get('margen_jornadas_filtro',"Todos"))!="Todos":
            comunes.append(f"Ult:{ultimos_part_filtro}/{st.session_state.get('margen_jornadas_filtro')}J")
        else:
            comunes.append(f"Ult:{ultimos_part_filtro}")

    if eq1_list or eq2_list or comunes:
        txt = "<div style='font-size:10px; line-height:1.3; font-family:monospace; padding:2px 0'>filtros:<br>"
        if eq1_list:
            txt += "eq1: " + " | ".join(eq1_list) + "<br>"
        if eq2_list:
            txt += "eq2: " + " | ".join(eq2_list) + "<br>"
        if comunes:
            txt += "comun: " + " | ".join(comunes)
        txt += "</div>"
        st.markdown(txt, unsafe_allow_html=True)
    else:
        st.caption("filtros: ninguno")
    # --- FIN RESUMEN FILTROS ---
    # --- FIN RESUMEN FILTROS ---
    # --- FIN RESUMEN FILTROS ---

   ##########fin desplegable
    # === FIN FILTRO GOLES ===

    # === FIN FILTRO GOLES ===

    # === FILTRO EQUIPOS BASE ===
    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
        df_final = df_final[((df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)) | ((df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro))]
    elif equipo_filtro!= "Ninguno":
        df_final = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)]
    elif equipo2_filtro!= "Ninguno":
        df_final = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)]

    # === FILTRO LOCAL/VISITANTE H2H - UNION INDEPENDIENTE ===
    df_base_h2h_lv = df_final.copy() # guardamos base antes de L/V
    # No filtramos aquí, el filtrado L/V lo haremos dentro de cada Eq
    df_final = df_base_h2h_lv.copy()

##########LOGICA: FILTRO 1X2 GANA/PIERDE/EMPATA
    # === FILTROS 1X2 / AM / HTFT / CUOTAS / MARGEN / MARCADOR ===
    def _aplica_1x2(df_in, equipo_ref, modo_1x2):
        if modo_1x2 == "Ninguno":
            return df_in

        # FIX DEFINITIVO: Sin equipo, Gana/Pierde = que haya ganador (FTR!='D'), Empata = empate
        if equipo_ref=="Ninguno" or equipo_ref is None or equipo_ref=="":
            if modo_1x2 == "Gana": return df_in[df_in['FTR']!='D']
            if modo_1x2 == "Pierde": return df_in[df_in['FTR']!='D']
            if modo_1x2 == "Empata": return df_in[df_in['FTR']=='D']
            if modo_1x2 == "Gana/Empata": return df_in[df_in['FTR']!='A']
            if modo_1x2 == "Gana/Pierde": return df_in[df_in['FTR']!='D']
            if modo_1x2 == "Empata/Pierde": return df_in[df_in['FTR']!='H']
            return df_in

        if modo_1x2 == "Gana":
            return df_in[((df_in['HomeTeam']==equipo_ref) & (df_in['FTR']=='H')) | ((df_in['AwayTeam']==equipo_ref) & (df_in['FTR']=='A'))]
        elif modo_1x2 == "Pierde":
            return df_in[((df_in['HomeTeam']==equipo_ref) & (df_in['FTR']=='A')) | ((df_in['AwayTeam']==equipo_ref) & (df_in['FTR']=='H'))]
        elif modo_1x2 == "Empata":
            return df_in[df_in['FTR']=='D']
        elif modo_1x2 == "Gana/Empata":
            return df_in[~(((df_in['HomeTeam']==equipo_ref) & (df_in['FTR']=='A')) | ((df_in['AwayTeam']==equipo_ref) & (df_in['FTR']=='H')))]
        elif modo_1x2 == "Gana/Pierde":
            return df_in[df_in['FTR']!='D']
        elif modo_1x2 == "Empata/Pierde":
            return df_in[~(((df_in['HomeTeam']==equipo_ref) & (df_in['FTR']=='H')) | ((df_in['AwayTeam']==equipo_ref) & (df_in['FTR']=='A')))]
        return df_in

    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
        df_eq1 = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)].copy()
        df_eq2 = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)].copy()
        if resultado_filtro!= "Ninguno":
            df_eq1 = _aplica_1x2(df_eq1, equipo_filtro, resultado_filtro)
        if resultado_filtro_eq2!= "Ninguno":
            df_eq2 = _aplica_1x2(df_eq2, equipo2_filtro, resultado_filtro_eq2)
        df_final = pd.concat([df_eq1, df_eq2]).drop_duplicates()
    elif equipo_filtro!= "Ninguno":
        if resultado_filtro!= "Ninguno":
            df_final = _aplica_1x2(df_final, equipo_filtro, resultado_filtro)
    elif equipo2_filtro!= "Ninguno":
        if resultado_filtro_eq2!= "Ninguno":
            df_final = _aplica_1x2(df_final, equipo2_filtro, resultado_filtro_eq2)
    else:
        # Sin equipo en nombre -> no aplico 1x2 global, dejo todos los partidos (local y visitante)
        # El % real por equipo lo calcula luego cada equipo en "Filtro actual ≥%"
        pass


##########LOGICA: FILTRO AMBOS MARCAN


    # === FILTRO AM Eq1 y AM3 Eq2 (SEPARADOS) ===
    def _filtro_am(df_in, modo_am, parte):
        for col in ['FTHG','FTAG','HTHG','HTAG']:
            df_in[col] = pd.to_numeric(df_in[col], errors='coerce').fillna(0)

        am_1p = (df_in['HTHG'] > 0) & (df_in['HTAG'] > 0)
        am_2p = ((df_in['FTHG'] - df_in['HTHG']) > 0) & ((df_in['FTAG'] - df_in['HTAG']) > 0)

        if modo_am == "Si":
            if parte == "1T": return df_in[am_1p]
            elif parte == "2T": return df_in[am_2p]
            else: return df_in[(df_in['FTHG'] > 0) & (df_in['FTAG'] > 0)]
        elif modo_am == "No":
            if parte == "1T": return df_in[~am_1p]
            elif parte == "2T": return df_in[~am_2p]
            else: return df_in[~((df_in['FTHG'] > 0) & (df_in['FTAG'] > 0))]
        elif modo_am == "Si1P": return df_in[am_1p]
        elif modo_am == "No1P": return df_in[~am_1p]
        elif modo_am == "Si2P": return df_in[am_2p]
        elif modo_am == "No2P": return df_in[~am_2p]
        elif modo_am == "Si1pNo2p": return df_in[am_1p & ~am_2p]
        elif modo_am == "No1pSi2p": return df_in[~am_1p & am_2p]
        elif modo_am == "Si1pSi2p": return df_in[am_1p & am_2p]
        return df_in

    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
        df_eq1 = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)].copy()
        df_eq2 = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)].copy()
        if ambos_marcan!= "Todos":
            df_eq1 = _filtro_am(df_eq1, ambos_marcan, parte_gol)
        if ambos_marcan_eq2!= "Todos":
            df_eq2 = _filtro_am(df_eq2, ambos_marcan_eq2, parte_gol)
        df_final = pd.concat([df_eq1, df_eq2]).drop_duplicates()
    elif equipo_filtro!= "Ninguno":
        if ambos_marcan!= "Todos":
            df_final = _filtro_am(df_final, ambos_marcan, parte_gol)
    elif equipo2_filtro!= "Ninguno":
        if ambos_marcan_eq2!= "Todos":
            df_final = _filtro_am(df_final, ambos_marcan_eq2, parte_gol)
    else:
        if ambos_marcan!= "Todos":
            df_final = _filtro_am(df_final, ambos_marcan, parte_gol)
        elif ambos_marcan_eq2!= "Todos":
            df_final = _filtro_am(df_final, ambos_marcan_eq2, parte_gol)
    
    # === FILTRO NUEVO X/X - con y sin equipo ===
    if xx_filtro!= "Todo":
        if equipo_filtro!= "Ninguno" and equipo2_filtro == "Ninguno":
            es_local = df_final['HomeTeam'] == equipo_filtro
            ht_gana = np.where(es_local, df_final['HTHG'] > df_final['HTAG'], df_final['HTAG'] > df_final['HTHG'])
            ht_pierde = np.where(es_local, df_final['HTHG'] < df_final['HTAG'], df_final['HTAG'] < df_final['HTHG'])
            ht_empata = ~(ht_gana | ht_pierde)
            ft_gana = np.where(es_local, df_final['FTHG'] > df_final['FTAG'], df_final['FTAG'] > df_final['FTHG'])
            ft_pierde = np.where(es_local, df_final['FTHG'] < df_final['FTAG'], df_final['FTAG'] < df_final['FTHG'])
            ft_empata = ~(ft_gana | ft_pierde)
        else:
            ht_gana = df_final['HTHG'] > df_final['HTAG']
            ht_pierde = df_final['HTHG'] < df_final['HTAG']
            ht_empata = ~(ht_gana | ht_pierde)
            ft_gana = df_final['FTHG'] > df_final['FTAG']
            ft_pierde = df_final['FTHG'] < df_final['FTAG']
            ft_empata = ~(ft_gana | ft_pierde)

        if xx_filtro == "G/X":
            df_final = df_final[ht_gana]
        elif xx_filtro == "E/X":
            df_final = df_final[ht_empata]
        elif xx_filtro == "P/X":
            df_final = df_final[ht_pierde]
        elif xx_filtro == "X/G":
            df_final = df_final[ft_gana]
        elif xx_filtro == "X/E":
            df_final = df_final[ft_empata]
        elif xx_filtro == "X/P":
            df_final = df_final[ft_pierde]

    
    
    
    
    #######################################
    # === FILTRO HT/FT - con y sin equipo ===
    if htft_filtro != "Todo":
        if equipo_filtro != "Ninguno" and equipo2_filtro == "Ninguno":
            es_local = df_final['HomeTeam'] == equipo_filtro
            ht_gana = np.where(es_local, df_final['HTHG'] > df_final['HTAG'], df_final['HTAG'] > df_final['HTHG'])
            ht_pierde = np.where(es_local, df_final['HTHG'] < df_final['HTAG'], df_final['HTAG'] < df_final['HTHG'])
            ht_res = np.where(ht_gana, 'G', np.where(ht_pierde, 'P', 'E'))
            ft_gana = np.where(es_local, df_final['FTHG'] > df_final['FTAG'], df_final['FTAG'] > df_final['FTHG'])
            ft_pierde = np.where(es_local, df_final['FTHG'] < df_final['FTAG'], df_final['FTAG'] < df_final['FTHG'])
            ft_res = np.where(ft_gana, 'G', np.where(ft_pierde, 'P', 'E'))
        else:
            ht_gana = df_final['HTHG'] > df_final['HTAG']
            ht_pierde = df_final['HTHG'] < df_final['HTAG']
            ht_res = np.where(ht_gana, 'G', np.where(ht_pierde, 'P', 'E'))
            ft_gana = df_final['FTHG'] > df_final['FTAG']
            ft_pierde = df_final['FTHG'] < df_final['FTAG']
            ft_res = np.where(ft_gana, 'G', np.where(ft_pierde, 'P', 'E'))

        combo = ht_res + '/' + ft_res
        if htft_filtro == "RE":
            df_final = df_final[(ht_res != 'G') & (ft_res == 'G')]
        elif htft_filtro == "FAIL":
            df_final = df_final[((ht_res == 'G') & (ft_res != 'G')) | ((ht_res == 'E') & (ft_res == 'P'))]
        else:
            df_final = df_final[combo == htft_filtro]

    if cuota_tipo not in ["Ninguno","Todo"]:
        if cuota_tipo == "1":
            df_final = df_final[df_final['FTR'] == 'H']
            col = "B365H"
        elif cuota_tipo == "X":
            df_final = df_final[df_final['FTR'] == 'D']
            col = "B365D"
        elif cuota_tipo == "2":
            df_final = df_final[df_final['FTR'] == 'A']
            col = "B365A"
        else:
            col = None
        # mantiene tu filtro de rango de cuotas
        if col:
            df_final = df_final[(df_final[col] >= rango_cuotas[0]) & (df_final[col] <= rango_cuotas[1])]

##########LOGICA: FILTRO MARGEN VICTORIA/DERROTA - FIX DEFINITIVO PARTE 1T/2T/TODO
    def _aplica_margen(df_in, equipo_ref, margen_tipo, parte_tipo="Todo"):
        if margen_tipo == "Todo" or df_in.empty:
            return df_in
        df_in = df_in.copy()

        if parte_tipo == "1T":
            gh = df_in['HTHG'].to_numpy()
            ga = df_in['HTAG'].to_numpy()
        elif parte_tipo == "2T":
            gh = (df_in['FTHG'] - df_in['HTHG']).to_numpy()
            ga = (df_in['FTAG'] - df_in['HTAG']).to_numpy()
        else: # Todo = final
            gh = df_in['FTHG'].to_numpy()
            ga = df_in['FTAG'].to_numpy()

        if equipo_ref!= "Ninguno" and equipo_ref:
            es_loc = (df_in['HomeTeam'] == equipo_ref).to_numpy()
            dif = np.where(es_loc, gh - ga, ga - gh)
        else:
            if condicion_filtro == "Local":
                dif = gh - ga
            elif condicion_filtro == "Visitante":
                dif = ga - gh
            else:
                dif = gh - ga

        if equipo_ref == "Ninguno" and condicion_filtro == "Todo":
            # Sin equipo: Gana = local gana, Pierde = local pierde
            if margen_tipo == "Empate": return df_in[dif==0]
            elif margen_tipo == "Gana 1": return df_in[dif==1]
            elif margen_tipo == "Pierde 1": return df_in[dif==-1]
            elif margen_tipo == "Gana 2": return df_in[dif==2]
            elif margen_tipo == "Pierde 2": return df_in[dif==-2]
            elif margen_tipo == "Gana 3+": return df_in[dif>=3]
            elif margen_tipo == "Pierde 3+": return df_in[dif<=-3]
            elif margen_tipo == "Gana ≥2": return df_in[dif>=2]
            elif margen_tipo == "Pierde ≥2": return df_in[dif<=-2]
            else: return df_in

        if margen_tipo == "Empate": return df_in[dif==0]
        elif margen_tipo == "Gana 1": return df_in[dif==1]
        elif margen_tipo == "Gana 2": return df_in[dif==2]
        elif margen_tipo == "Gana 3+": return df_in[dif>=3]
        elif margen_tipo == "Pierde 1": return df_in[dif==-1]
        elif margen_tipo == "Pierde 2": return df_in[dif==-2]
        elif margen_tipo == "Pierde 3+": return df_in[dif<=-3]
        elif margen_tipo == "Gana ≥2": return df_in[dif>=2]
        elif margen_tipo == "Pierde ≥2": return df_in[dif<=-2]
        return df_in


    
    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
        df_eq1 = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)].copy()
        df_eq2 = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)].copy()
        if margen_filtro!= "Todo":
            df_eq1 = _aplica_margen(df_eq1, equipo_filtro, margen_filtro, parte_gol)
        if margen_filtro_eq2!= "Todo":
            df_eq2 = _aplica_margen(df_eq2, equipo2_filtro, margen_filtro_eq2, parte_gol_eq2)
        df_final = pd.concat([df_eq1, df_eq2]).drop_duplicates()
    elif equipo2_filtro!= "Ninguno":
        mf = margen_filtro_eq2 if margen_filtro_eq2!= "Todo" else margen_filtro
        mp = parte_gol_eq2 if margen_filtro_eq2!= "Todo" else parte_gol
        df_final = _aplica_margen(df_final, equipo2_filtro, mf, mp)
    else:
        if margen_filtro!= "Todo":
            df_final = _aplica_margen(df_final, equipo_filtro, margen_filtro, parte_gol)

    # --- FILTRO MARCADOR Eq1 / Eq2 INDEPENDIENTE ---
    def _aplica_marcador(df_in, marcador_txt):
        if marcador_txt=="Todos" or df_in.empty: return df_in
        gl, gv = map(int, marcador_txt.split('-'))
        return df_in[(df_in['FTHG']==gl) & (df_in['FTAG']==gv)]

    if equipo_filtro!="Ninguno" and equipo2_filtro!="Ninguno":
        df_eq1 = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)].copy()
        df_eq2 = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)].copy()
        df_eq1 = _aplica_marcador(df_eq1, marcador_filtro)
        df_eq2 = _aplica_marcador(df_eq2, marcador_filtro_eq2)
        df_final = pd.concat([df_eq1, df_eq2]).drop_duplicates()
    elif equipo2_filtro!="Ninguno":
        df_final = _aplica_marcador(df_final, marcador_filtro_eq2)
    else:
        df_final = _aplica_marcador(df_final, marcador_filtro)

# --- FILTRO COLUMNAS CRUZADO SOLO Eq1 ---
    def _aplica_filtro_col(df_in, col, op, val_str, alcance_str, eq1):
        import re
        import numpy as np
        if col in ["Ninguno","_GOL_","_TARJ_","_TIR_","_CORN_","_FALT_","_CLASF_"] or val_str=="Ninguno" or df_in.empty:
            return df_in
        alcance = str(alcance_str)
        tipo = "AF" if alcance.startswith("AF") else "C" if alcance.startswith("C") else "Todo"
        m = re.match(r'^(AF|C)(\d+(\.\d+)?)$', alcance)
        val = float(m.group(2)) if m else float(val_str)
        equipo_ref = eq1 if eq1!="Ninguno" else None
        mapa = {'HC':'AC','AC':'HC','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
        def get_pair(c_nombre):
            if c_nombre == 'GolesHT': return (df_in['HTHG'].values, df_in['HTAG'].values)
            if c_nombre == 'GolesTotales': return (df_in['FTHG'].values, df_in['FTAG'].values)
            if c_nombre == 'Goles2T': return ((df_in['FTHG']-df_in['HTHG']).values, (df_in['FTAG']-df_in['HTAG']).values)
            if c_nombre == 'corneTot': return (df_in['HC'].values, df_in['AC'].values)
            if c_nombre == 'tirosTot': return (df_in['HS'].values, df_in['AS'].values)
            if c_nombre == 'tirosPuertaTot': return (df_in['HST'].values, df_in['AST'].values)
            if c_nombre == 'faltasTot': return (df_in['HF'].values, df_in['AF'].values)
            if c_nombre == 'TargAmTot': return (df_in['HY'].values, df_in['AY'].values)
            if c_nombre == 'TargRojTot': return (df_in['HR'].values, df_in['AR'].values)
            contra = mapa.get(c_nombre, c_nombre)
            v1 = df_in[c_nombre].values if c_nombre in df_in.columns else np.zeros(len(df_in))
            v2 = df_in[contra].values if contra in df_in.columns else v1
            return (v1, v2)
        vh, va = get_pair(col)
        if equipo_ref is None:
            if tipo in ("AF","C"):
                # Sin Eq1, AF/C no puede pre-filtrar. Dejamos todo y que el resumen filtre por equipo.
                # Si quieres que al menos un equipo cumpla: base = vh, pero dejamos pasar si vh cumple O va cumple
                if op == "=":
                    mask = (vh == val) | (va == val)
                elif op == ">":
                    mask = (vh > val) | (va > val)
                elif op == ">=":
                    mask = (vh >= val) | (va >= val)
                elif op == "<":
                    mask = (vh < val) | (va < val)
                else:
                    mask = (vh <= val) | (va <= val)
                return df_in[mask]
            else:
                base = vh + va if col in ['GolesHT','GolesTotales','Goles2T','corneTot','tirosTot','tirosPuertaTot','faltasTot','TargAmTot','TargRojTot'] else np.maximum(vh, va)
        else:
            es_loc = df_in['HomeTeam']==equipo_ref
            if tipo == "AF": base = np.where(es_loc, vh, va)
            elif tipo == "C": base = np.where(es_loc, va, vh)
            else: base = vh + va if col in ['GolesHT','GolesTotales','Goles2T','corneTot','tirosTot'] else np.where(es_loc, vh, va)
        if op == "=": mask = base == val
        elif op == ">": mask = base > val
        elif op == ">=": mask = base >= val
        elif op == "<": mask = base < val
        else: mask = base <= val
        return df_in[mask]

    def _cumple_una_col(df_in, col, op, val_str, alc):
        if col in ["Ninguno","_GOL_","_TARJ_","_TIR_","_CORN_","_FALT_","_CLASF_"] or val_str=="Ninguno":
            return np.ones(len(df_in), dtype=bool), np.ones(len(df_in), dtype=bool)
        import re
        val = float(val_str)
        # saca vh, va como ya haces
        if col == 'GolesHT': vh, va = df_in['HTHG'].values, df_in['HTAG'].values
        elif col == 'GolesTotales': vh, va = df_in['FTHG'].values, df_in['FTAG'].values
        elif col == 'Goles2T': vh, va = (df_in['FTHG']-df_in['HTHG']).values, (df_in['FTAG']-df_in['HTAG']).values
        elif col == 'corneTot': vh, va = df_in['HC'].values, df_in['AC'].values
        elif col == 'tirosTot': vh, va = df_in['HS'].values, df_in['AS'].values
        elif col == 'tirosPuertaTot': vh, va = df_in['HST'].values, df_in['AST'].values
        elif col == 'faltasTot': vh, va = df_in['HF'].values, df_in['AF'].values
        elif col == 'TargAmTot': vh, va = df_in['HY'].values, df_in['AY'].values
        elif col == 'TargRojTot': vh, va = df_in['HR'].values, df_in['AR'].values
        else:
            mapa = {'HC':'AC','AC':'HC','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
            contra = mapa.get(col, col)
            v1 = df_in[col].values if col in df_in.columns else np.zeros(len(df_in))
            v2 = df_in[contra].values if contra in df_in.columns else v1
            vh, va = v1, v2

        tipo = "AF" if str(alc).startswith("AF") else "C" if str(alc).startswith("C") else "Todo"

        if tipo == "Todo":
            base = vh + va if col in ['GolesHT','GolesTotales','Goles2T','corneTot','tirosTot','tirosPuertaTot','faltasTot','TargAmTot','TargRojTot'] else np.maximum(vh, va)
            if op == "=": ok = base == val
            elif op == ">": ok = base > val
            elif op == ">=": ok = base >= val
            elif op == "<": ok = base < val
            else: ok = base <= val
            return ok, ok
        else:
            # AF / C
            if tipo == "AF":
                base_home, base_away = vh, va
            else:
                base_home, base_away = va, vh

            # Si hay Eq1, solo mira ese lado
            if equipo_filtro!= "Ninguno":
                es_loc = df_in['HomeTeam'] == equipo_filtro
                base = np.where(es_loc, base_home, base_away)
                if op == "=": ok = base == val
                elif op == ">": ok = base > val
                elif op == ">=": ok = base >= val
                elif op == "<": ok = base < val
                else: ok = base <= val
                return ok, ok
            else:
                if op == "=": ok_h = base_home == val; ok_a = base_away == val
                elif op == ">": ok_h = base_home > val; ok_a = base_away > val
                elif op == ">=": ok_h = base_home >= val; ok_a = base_away >= val
                elif op == "<": ok_h = base_home < val; ok_a = base_away < val
                else: ok_h = base_home <= val; ok_a = base_away <= val
                return ok_h, ok_a

# --- H2H FINAL INDEPENDIENTE: Col1+Col2=Eq1, Col3=Eq2 ---
def _eval_team(df_in, team, col, op, val_str, alc):
    import re
    if col in ["Ninguno","_GOL_","_TARJ_","_TIR_","_CORN_","_FALT_","_CLASF_"] or val_str=="Ninguno" or df_in.empty:
        return np.ones(len(df_in), dtype=bool)

    m = re.match(r'^(AF|C)(\d+(\.\d+)?)$', str(alc))
    if m:
        tipo=m.group(1); val=float(m.group(2))
    else:
        tipo="AF" if str(alc).startswith("AF") else "C" if str(alc).startswith("C") else "Todo"
        try: val=float(val_str)
        except: return np.ones(len(df_in), dtype=bool)

    if col=='GolesHT': vh,va = df_in['HTHG'].values, df_in['HTAG'].values
    elif col=='GolesTotales': vh,va = df_in['FTHG'].values, df_in['FTAG'].values
    elif col=='Goles2T': vh,va = (df_in['FTHG']-df_in['HTHG']).values, (df_in['FTAG']-df_in['HTAG']).values
    elif col=='corneTot': vh,va = df_in['HC'].values, df_in['AC'].values
    elif col=='tirosTot': vh,va = df_in['HS'].values, df_in['AS'].values
    elif col=='tirosPuertaTot': vh,va = df_in['HST'].values, df_in['AST'].values
    elif col=='faltasTot': vh,va = df_in['HF'].values, df_in['AF'].values
    elif col=='TargAmTot': vh,va = df_in['HY'].values, df_in['AY'].values
    elif col=='TargRojTot': vh,va = df_in['HR'].values, df_in['AR'].values
    else:
        mapa={'HC':'AC','AC':'HC','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
        contra=mapa.get(col,col)
        v1=df_in[col].values if col in df_in.columns else np.zeros(len(df_in))
        v2=df_in[contra].values if contra in df_in.columns else v1
        vh,va=v1,v2

    # SIN EQUIPO -> respeta L/V y respeta AF/C
    if team=="Ninguno":
        # determina si miramos solo local, solo visitante o ambos
        # usa la variable global condicion_filtro / condicion_filtro3
        try:
            lv_global = condicion_filtro if 'condicion_filtro' in globals() else "Todo"
        except:
            lv_global = "Todo"
        
        if tipo=="Todo":
            base=vh+va
            if op=="=": ok=base==val
            elif op==">": ok=base>val
            elif op==">=": ok=base>=val
            elif op=="<": ok=base<val
            else: ok=base<=val
            return ok
        else:
            base_home = vh
            base_away = va
            if op=="=": ok_h=base_home==val; ok_a=base_away==val
            elif op==">": ok_h=base_home>val; ok_a=base_away>val
            elif op==">=": ok_h=base_home>=val; ok_a=base_away>=val
            elif op=="<": ok_h=base_home<val; ok_a=base_away<val
            else: ok_h=base_home<=val; ok_a=base_away<=val
            
            if lv_global == "Local":
                return ok_h
            elif lv_global == "Visitante":
                return ok_a
            else:
                # sin L/V, AF sin equipo = cualquiera que cumpla
                return ok_h | ok_a
    else:
        es_loc=df_in['HomeTeam']==team
        es_team=es_loc | (df_in['AwayTeam']==team)
        if tipo=="Todo":
            base=vh+va if col in ['GolesHT','GolesTotales','Goles2T','corneTot','tirosTot','tirosPuertaTot','faltasTot','TargAmTot','TargRojTot'] else np.where(es_loc,vh,va)
        elif tipo=="AF":
            base=np.where(es_loc,vh,va)
        else:
            base=np.where(es_loc,va,vh)
        es_team=es_loc | (df_in['AwayTeam']==team)

    if op=="=": ok=base==val
    elif op==">": ok=base>val
    elif op==">=": ok=base>=val
    elif op=="<": ok=base<val
    else: ok=base<=val

    if team=="Ninguno":
        return ok
    else:
        return np.where(es_team, ok, True)

# --- LV1 y LV2 SIEMPRE DEFINIDOS PARA QUE NO DE AMARILLO ---
if condicion_filtro == "Local":
    lv1 = df_final['HomeTeam']==equipo_filtro
elif condicion_filtro == "Visitante":
    lv1 = df_final['AwayTeam']==equipo_filtro
else:
    lv1 = pd.Series(True, index=df_final.index)

if condicion_filtro3 == "Local":
    lv2 = df_final['HomeTeam']==equipo2_filtro
elif condicion_filtro3 == "Visitante":
    lv2 = df_final['AwayTeam']==equipo2_filtro
else:
    lv2 = pd.Series(True, index=df_final.index)

m1 = _eval_team(df_final, equipo_filtro, columna_filtro, operador_filtro, valor_filtro, alcance_filtro)
m2 = _eval_team(df_final, equipo_filtro, columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2)
m3 = _eval_team(df_final, equipo2_filtro, columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3)

if equipo_filtro!="Ninguno" and equipo2_filtro!="Ninguno":
    is_eq1 = (df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)
    is_eq2 = (df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)
    # filtra cada equipo por separado y luego une
    part1 = df_final[is_eq1 & lv1 & m1 & m2]
    part2 = df_final[is_eq2 & lv2 & m3]
    df_final = pd.concat([part1, part2]).drop_duplicates()
elif equipo_filtro!="Ninguno":
    df_final = df_final[lv1 & m1 & m2]
elif equipo2_filtro!="Ninguno":
    df_final = df_final[lv2 & m3]
else:
    df_final = df_final[m1 & m2 & m3]
    if parte_gol!= "Todo" and equipo_filtro!= "Ninguno" and equipo2_filtro=="Ninguno":
        if parte_gol == "1T":
            df_final = df_final[((df_final['HomeTeam']==equipo_filtro)&(df_final['HTHG']>0))|((df_final['AwayTeam']==equipo_filtro)&(df_final['HTAG']>0))]
        elif parte_gol == "2T":
            df_final = df_final[((df_final['HomeTeam']==equipo_filtro)&((df_final['FTHG']-df_final['HTHG'])>0))|((df_final['AwayTeam']==equipo_filtro)&((df_final['FTAG']-df_final['HTAG'])>0))]
    # si no hay equipo, NO filtramos por parte (para que se vean todos los partidos)
    # 2) GOLES DETALLADOS (solo para mostrar)
    df_final['Goles'] = ''
    if todos_eventos and not df_final.empty:
        df_final['Goles'] = df_final.apply(
            lambda r: buscar_goles_partido(r, todos_eventos, rango_minutos[0], rango_minutos[1], parte_gol, equipo_filtro if equipo_filtro!="Ninguno" else None),
            axis=1
        )
        if not (rango_minutos[0] == 0 and rango_minutos[1] >= 120):
            df_final = df_final[df_final['Goles'].str.len() > 0]

    # --- FILTRO JUGADOR ---
    if jugador_filtro!= "TODOS" and not df_final.empty:
        df_final = df_final[df_final['Goles'].str.contains(jugador_filtro, case=False, na=False)]

    # --- FILTRO ULTIMOS X + MARGEN J - CON AF/C REAL POR EQUIPO - FINAL FIX Si1P ---
    if 'dict_ultimos' not in st.session_state:
        st.session_state.dict_ultimos = {}
    st.session_state.dict_ultimos = {}

    if str(ultimos_part_filtro)!="Todos" and len(df_final) > 0:
        n_ult = int(ultimos_part_filtro)
        margen_j = st.session_state.get('margen_jornadas_filtro', "Todos")
        margen_n = int(margen_j) if str(margen_j)!="Todos" else None

        df_total = df_base_h2h.copy() if 'df_base_h2h' in locals() else df_original.copy()
        df_total = df_total[(df_total['Jornada']>=rango_jornadas[0]) & (df_total['Jornada']<=rango_jornadas[1])]

        def get_base(row, col, eq, alcance):
            es_loc = row['HomeTeam']==eq
            if col=='GolesTotales': return row['FTHG']+row['FTAG']
            if col=='GolesHT': return row['HTHG']+row['HTAG']
            if col=='Goles2T': return (row['FTHG']-row['HTHG'])+(row['FTAG']-row['HTAG'])
            if col=='corneTot': return (row['HC']+row['AC']) if alcance=="Todo" else (row['HC'] if es_loc else row['AC'])
            if col=='tirosTot': return (row['HS']+row['AS']) if alcance=="Todo" else (row['HS'] if es_loc else row['AS'])
            if col=='tirosPuertaTot': return (row['HST']+row['AST']) if alcance=="Todo" else (row['HST'] if es_loc else row['AST'])
            if col=='TargAmTot': return (row['HY']+row['AY']) if alcance=="Todo" else (row['HY'] if es_loc else row['AY'])
            if col=='TargRojTot': return (row['HR']+row['AR']) if alcance=="Todo" else (row['HR'] if es_loc else row['AR'])
            if col=='faltasTot': return (row['HF']+row['AF']) if alcance=="Todo" else (row['HF'] if es_loc else row['AF'])
            if col in row:
                if alcance=="AF" or alcance=="C":
                    mapa={'FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HC':'AC','AC':'HC','HF':'AF','AF':'HF','HY':'AY','AY':'HY','HR':'AR','AR':'HR'}
                    if alcance=="AF": return row[col] if (es_loc and col in ['FTHG','HTHG','HS','HST','HC','HF','HY','HR'] or not es_loc and col in ['FTAG','HTAG','AS','AST','AC','AF','AY','AR']) else (row['HY'] if es_loc else row['AY'] if col=='TargAmTot' else row[col])
                    else:
                        contra=mapa.get(col,col)
                        return row[contra] if contra in row else row[col]
                return row[col]
            return 0

        def cumple_am(row):
            h1=row['HTHG']; a1=row['HTAG']; ft1=row['FTHG']; ft2=row['FTAG']
            h2=ft1-h1; a2=ft2-a1
            am_1p = (h1>0 and a1>0)
            am_2p = (h2>0 and a2>0)
            am_ft = (ft1>0 and ft2>0)
            if ambos_marcan=="Todos": return True
            if ambos_marcan=="Si": return am_ft
            if ambos_marcan=="No": return not am_ft
            if ambos_marcan=="Si1P": return am_1p
            if ambos_marcan=="No1P": return not am_1p
            if ambos_marcan=="Si2P": return am_2p
            if ambos_marcan=="No2P": return not am_2p
            if ambos_marcan=="Si1pNo2p": return am_1p and not am_2p
            if ambos_marcan=="No1pSi2p": return (not am_1p) and am_2p
            if ambos_marcan=="Si1pSi2p": return am_1p and am_2p
            return True

        def cumple_para_equipo(row, eq):
            if columna_filtro not in ["Ninguno","_GOL_","_TARJ_","_TIR_","_CORN_","_FALT_","_CLASF_"] and valor_filtro!="Ninguno":
                base = get_base(row, columna_filtro, eq, alcance_filtro)
                vv = float(valor_filtro)
                if operador_filtro=="=" and base!=vv: return False
                if operador_filtro==">" and not (base>vv): return False
                if operador_filtro==">=" and not (base>=vv): return False
                if operador_filtro=="<" and not (base<vv): return False
                if operador_filtro=="<=" and not (base<=vv): return False
            if columna_filtro2 not in ["Ninguno","_GOL_","_TARJ_","_TIR_","_CORN_","_FALT_","_CLASF_"] and valor_filtro2!="Ninguno":
                base = get_base(row, columna_filtro2, eq, alcance_filtro2)
                vv = float(valor_filtro2)
                if operador_filtro2=="=" and base!=vv: return False
                if operador_filtro2==">" and not (base>vv): return False
                if operador_filtro2==">=" and not (base>=vv): return False
                if operador_filtro2=="<" and not (base<vv): return False
                if operador_filtro2=="<=" and not (base<=vv): return False
            if not cumple_am(row): return False
            return True

        dict_tails = {}
        lista_final = []
        for eq in pd.unique(df_total[['HomeTeam','AwayTeam']].values.ravel()):
            df_eq_total = df_total[(df_total['HomeTeam']==eq) | (df_total['AwayTeam']==eq)].sort_values('Date')
            if len(df_eq_total) < n_ult: continue
            if margen_n is None:
                df_last_n = df_eq_total.tail(n_ult)
                if not all(cumple_para_equipo(r, eq) for _, r in df_last_n.iterrows()): continue
                df_a_guardar = df_last_n
            else:
                df_ventana = df_eq_total.tail(margen_n) if len(df_eq_total)>=margen_n else df_eq_total
                df_ok = df_ventana[df_ventana.apply(lambda r: cumple_para_equipo(r, eq), axis=1)]
                if len(df_ok) < n_ult: continue
                df_a_guardar = df_ok.sort_values('Date').tail(n_ult)
            dict_tails[eq] = df_a_guardar
            lista_final.append(df_a_guardar)

        st.session_state.dict_ultimos = dict_tails
        if lista_final:
            df_final = pd.concat(lista_final).drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League']).sort_values('Date').copy()
        else:
            df_final = df_final.iloc[0:0].copy()
    else:
        st.session_state.dict_ultimos = {}

######################################################################################
    if len(df_final) > 0:
        df_final['partidos'] = ''
        df_final['Tarjetas/Corners/goles'] = ''
    else:
        df_final['partidos'] = pd.Series(dtype='object')
        df_final['Tarjetas/Corners/goles'] = pd.Series(dtype='object')

    st.caption(f"Mostrando {len(df_final)} partidos")
  
  
  #################
  # --- CONTADOR GLOBAL POR JORNADA DIVIDIDO POR TEMPORADA + % ---
if len(df_final) > 0:
    conteo_j = df_final.groupby(['Season', 'Jornada']).size().reset_index(name='Veces')

    # Partidos por jornada: equipos únicos / 2
    partidos_por_jornada = df_final.groupby('Season').apply(
        lambda x: len(pd.unique(x[['HomeTeam','AwayTeam']].values.ravel())) // 2
    ).reset_index(name='PartidosXJornada')

    conteo_j = conteo_j.merge(partidos_por_jornada, on='Season')
    conteo_j['Pct'] = (conteo_j['Veces'] / conteo_j['PartidosXJornada'] * 100).round(1)

    # Calculamos % total de aparición de esa temporada
    total_por_temp = df_final.groupby('Season').size().reset_index(name='TotalFiltro')
    max_jornadas = 38 # LaLiga tiene 38 jornadas
    total_por_temp['TotalPosible'] = total_por_temp['Season'].map(
        lambda s: partidos_por_jornada.loc[partidos_por_jornada['Season'] == s, 'PartidosXJornada'].iloc[0] * max_jornadas
    )
    total_por_temp['PctTotal'] = (total_por_temp['TotalFiltro'] / total_por_temp['TotalPosible'] * 100).round(1)

    conteo_j = conteo_j.merge(total_por_temp[['Season', 'TotalFiltro', 'TotalPosible', 'PctTotal']], on='Season')
    conteo_j = conteo_j.sort_values(['Season', 'Jornada'], ascending=[False, False])

    total_jornadas = conteo_j['Jornada'].nunique()
    with st.expander(f"📊 Repeticiones por jornada ({total_jornadas} jornadas)", expanded=False):
            for season, grupo in conteo_j.groupby('Season', sort=False):
                partidos_xj = grupo['PartidosXJornada'].iloc[0]
                pct_total = grupo['PctTotal'].iloc[0]
                st.markdown(f"<div style='font-size:12px;font-weight:700;padding:4px 0 2px 0;color:#0A2342'>{season} | {partidos_xj} partidos/jornada | {pct_total}% del total</div>", unsafe_allow_html=True)
                for _, row in grupo.iterrows():
                    pct = row['Pct']
                    veces = int(row['Veces'])
                    partidos_xj = int(row['PartidosXJornada'])
                    st.markdown(f"<div style='font-size:11px;padding:1px 0 1px 8px;font-family:monospace'>J{int(row['Jornada'])} - {veces}# | <b>{pct}%</b> aprox {veces}/{partidos_xj}</div>", unsafe_allow_html=True)
   ####################
   
    # --- RESUMEN CON % - CARGA PROGRESIVA POR LIGA ---
    with st.expander(f"📊 Filtro actual ≥{pct_marcador}%", expanded=False):
        if 'num_ligas_filtro_actual' not in st.session_state:
            st.session_state.num_ligas_filtro_actual = 1
        if 'firma_ligas_filtro_actual' not in st.session_state:
            st.session_state.firma_ligas_filtro_actual = ""

        ligas_ordenadas_all = sorted(df_final['League'].dropna().unique()) if len(df_final) > 0 else []
        firma_actual = f"{'|'.join(ligas_ordenadas_all)}|{pct_marcador}|{equipo_filtro}|{equipo2_filtro}"
        if firma_actual!= st.session_state.firma_ligas_filtro_actual:
            st.session_state.num_ligas_filtro_actual = 1
            st.session_state.firma_ligas_filtro_actual = firma_actual

        num_a_mostrar = st.session_state.num_ligas_filtro_actual
        ligas_visibles = ligas_ordenadas_all[:num_a_mostrar] if ligas_ordenadas_all else []

        # TITULITO - Eq real = solo los que cumplen Ult
        if len(df_final) > 0 and ligas_visibles:
            df_visible_titulo = df_final[df_final['League'].isin(ligas_visibles)]
            ligas_mostrar = "|".join(ligas_visibles)
            if str(ultimos_part_filtro)!="Todos" and st.session_state.get('dict_ultimos'):
                num_equipos = len([eq for eq in st.session_state.dict_ultimos.keys() if eq in pd.unique(df_visible_titulo[['HomeTeam','AwayTeam']].values.ravel()) or True])
                # solo los que están en dict_ultimos y además tienen liga visible
                num_equipos = len(st.session_state.dict_ultimos)
                partidos_mostrar = len(df_visible_titulo)
            else:
                num_equipos = len(pd.unique(df_visible_titulo[['HomeTeam','AwayTeam']].values.ravel()))
                partidos_mostrar = len(df_visible_titulo)
            st.markdown(f"<div style='font-size:8px;font-family:monospace;color:#555;padding:0 0 4px 0'>Ligas: {ligas_mostrar} | Eq: {num_equipos} | Partidos: {partidos_mostrar} | Mostrando {len(ligas_visibles)}/{len(ligas_ordenadas_all)} ligas</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size:8px;font-family:monospace;color:#555;padding:0 0 4px 0'>Ligas: - | Eq: 0 | Partidos: 0 | Mostrando 0/{len(ligas_ordenadas_all)} ligas</div>", unsafe_allow_html=True)

        # ---- AQUI ESTA EL BOTON - SIEMPRE VISIBLE SI HAY +1 LIGA ----
        if ligas_ordenadas_all:
            if len(ligas_visibles) < len(ligas_ordenadas_all):
                siguiente = ligas_ordenadas_all[len(ligas_visibles)]
                if st.button(f"📥 Cargar siguiente liga: {siguiente} ({len(ligas_visibles)+1}/{len(ligas_ordenadas_all)})", key="btn_cargar_liga_filtro_actual", type="primary", use_container_width=True):
                    st.session_state.num_ligas_filtro_actual += 1
                    st.rerun()
            else:
                st.success(f"✅ Todas las ligas cargadas ({len(ligas_ordenadas_all)})")
            ######

            #botones cargar ligas
            st.markdown("""
            <style>
            /* Fuerza los 2 botones pequeños y uno al lado del otro */
            div[data-testid="stHorizontalBlock"]:has(button[key="btn_cargar_todas_filtro_actual"]) {
                gap: 6px!important;
            }
            button[key="btn_cargar_todas_filtro_actual"],
            button[key="btn_reset_filtro_actual"] {
                font-size: 9px!important;
                padding: 1px 8px!important;
                height: 24px!important;
                min-height: 24px!important;
                border-radius: 6px!important;
                line-height: 1!important;
                width: auto!important;
            }
            </style>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1], gap="small")
            with c1:
                if st.button("Cargar todas", key="btn_cargar_todas_filtro_actual", use_container_width=False):
                    st.session_state.num_ligas_filtro_actual = len(ligas_ordenadas_all)
                    st.rerun()
            with c2:
                if st.button("Reset a 1", key="btn_reset_filtro_actual", use_container_width=False):
                    st.session_state.num_ligas_filtro_actual = 1
                    st.rerun()

            st.markdown("---")

            # --- A PARTIR DE AQUI TU CODIGO ORIGINAL PERO FILTRADO POR ligas_visibles ---
            if len(df_final) > 0 and ligas_visibles:
                base = df_final[df_final['League'].isin(ligas_visibles)].copy()
                equipos_mostrar = []
                if equipo_filtro!= "Ninguno": equipos_mostrar.append(equipo_filtro)
                if equipo2_filtro!= "Ninguno" and equipo2_filtro not in equipos_mostrar: equipos_mostrar.append(equipo2_filtro)
                if not equipos_mostrar: equipos_mostrar = list(pd.unique(base[['HomeTeam','AwayTeam']].values.ravel()))

                base_total = df_original.copy()
                base_total = base_total[base_total['League'].isin(ligas_visibles) & base_total['Season'].isin(temp_sel)]
                base_total, _ = calcular_estado_jornada(base_total)
                base_total = base_total[(base_total['Jornada']>=rango_jornadas[0]) & (base_total['Jornada']<=rango_jornadas[1])]
                if equipo_filtro!= "Ninguno" or equipo2_filtro!= "Ninguno":
                    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
                        base_total = base_total[((base_total['HomeTeam']==equipo_filtro) | (base_total['AwayTeam']==equipo_filtro)) | ((base_total['HomeTeam']==equipo2_filtro) | (base_total['AwayTeam']==equipo2_filtro))]
                    elif equipo_filtro!= "Ninguno":
                        base_total = base_total[(base_total['HomeTeam']==equipo_filtro) | (base_total['AwayTeam']==equipo_filtro)]
                    elif equipo2_filtro!= "Ninguno":
                        base_total = base_total[(base_total['HomeTeam']==equipo2_filtro) | (base_total['AwayTeam']==equipo2_filtro)]

                datos_eq1 = []
                datos_eq2 = []
                datos_resto = []

                for eq in equipos_mostrar:
                    lv = condicion_filtro3 if eq==equipo2_filtro else condicion_filtro
                    if lv == "Local":
                        base_total_team = base_total[base_total['HomeTeam']==eq]
                        base_team_global = base[base['HomeTeam']==eq]
                    elif lv == "Visitante":
                        base_total_team = base_total[base_total['AwayTeam']==eq]
                        base_team_global = base[base['AwayTeam']==eq]
                    else:
                        base_total_team = base_total[(base_total['HomeTeam']==eq) | (base_total['AwayTeam']==eq)]
                        base_team_global = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]

                    part_tot = base_total_team

                    if str(ultimos_part_filtro)!="Todos":
                        # Si pide 5 y el equipo no está en dict_ultimos es que tiene <5, lo saltamos
                        if eq not in st.session_state.get('dict_ultimos', {}):
                            continue
                        df_tail_eq = st.session_state.dict_ultimos[eq]
                        part_ok = df_tail_eq[df_tail_eq['League'].isin(ligas_visibles)]
                    else:
                        part_ok = base_team_global

                    tot = len(part_tot)
                    hits = len(part_ok)
                    pct = (hits / tot * 100) if tot else 0

                    marc_eq = marcador_filtro_eq2 if eq==equipo2_filtro else marcador_filtro
                    if not (rango_pct[0] <= pct <= rango_pct[1]) and marc_eq=="Todos":
                        continue
                    if marc_eq!="Todos" and hits==0:
                        continue

                    rival = equipos_mostrar[1] if len(equipos_mostrar)==2 and eq==equipos_mostrar[0] else (equipos_mostrar[0] if len(equipos_mostrar)==2 else None)
                    margen_actual = margen_filtro_eq2 if eq == equipo2_filtro else margen_filtro
                    parte_actual = parte_gol_eq2 if eq == equipo2_filtro else parte_gol

                    if not part_ok.empty and margen_actual!= "Todo":
                        if parte_actual == "1T":
                            gh = part_ok['HTHG'].to_numpy()
                            ga = part_ok['HTAG'].to_numpy()
                        elif parte_actual == "2T":
                            gh = (part_ok['FTHG']-part_ok['HTHG']).to_numpy()
                            ga = (part_ok['FTAG']-part_ok['HTAG']).to_numpy()
                        else:
                            gh = part_ok['FTHG'].to_numpy()
                            ga = part_ok['FTAG'].to_numpy()
                        es_loc = (part_ok['HomeTeam']==eq).to_numpy()
                        dif_team = np.where(es_loc, gh-ga, ga-gh)
                        if margen_actual == "Empate": part_ok = part_ok[dif_team==0]
                        elif margen_actual == "Gana 1": part_ok = part_ok[dif_team==1]
                        elif margen_actual == "Pierde 1": part_ok = part_ok[dif_team==-1]
                        elif margen_actual == "Gana 2": part_ok = part_ok[dif_team==2]
                        elif margen_actual == "Pierde 2": part_ok = part_ok[dif_team==-2]
                        elif margen_actual == "Gana 3+": part_ok = part_ok[dif_team>=3]
                        elif margen_actual == "Pierde 3+": part_ok = part_ok[dif_team<=-3]
                        elif margen_actual == "Gana ≥2": part_ok = part_ok[dif_team>=2]
                        elif margen_actual == "Pierde ≥2": part_ok = part_ok[dif_team<=-2]

                    jors = jornadas_conteo(part_ok['Jornada'], part_ok, eq, rival, parte_actual) if not part_ok.empty else ""
                    racha = racha_comprimida_html(part_ok, eq) if not part_ok.empty else ""
                    racha_am = racha_ambos_marcan_html(part_ok) if not part_ok.empty else ""
                    html = f"""<div style='font-size:9px;line-height:1.2;margin:3px 0;padding:4px 0;border-bottom:1px solid #000;font-family:monospace;color:#000'>
<div style='font-size:10px;font-weight:900;line-height:1.1'>{hits}/{tot} - {hits}# {pct:.1f}%</div>
<div style='display:flex;flex-wrap:wrap;align-items:center;gap:1px 2px;margin:2px 0 1px 0'>{racha}</div>
<div style='display:flex;flex-wrap:wrap;align-items:center;gap:1px 2px;margin:1px 0 3px 0'>{racha_am}</div>
<div style='margin-top:4px'>{jors}</div>
</div>"""
                    if eq == equipo_filtro: datos_eq1.append((pct, hits, eq, html))
                    elif eq == equipo2_filtro: datos_eq2.append((pct, hits, eq, html))
                    else: datos_resto.append((pct, hits, eq, html))

                datos_eq1.sort(key=lambda x: (-x[0], -x[1]))
                datos_eq2.sort(key=lambda x: (-x[0], -x[1]))
                datos_resto.sort(key=lambda x: (-x[0], -x[1]))

                if equipo_filtro!="Ninguno" and equipo2_filtro!="Ninguno":
                    for pct, hits, eq, html in datos_eq1:
                        df_eq_liga = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]
                        liga_eq = "|".join(sorted(df_eq_liga['League'].dropna().unique())) if not df_eq_liga.empty else ""
                        st.markdown(f"<div style='font-size:8px;font-family:monospace;color:#000'>EQUIPO1: {eq} ({hits}) --> {liga_eq}</div>", unsafe_allow_html=True)
                        st.markdown(html, unsafe_allow_html=True)
                    st.markdown("---")
                    for pct, hits, eq, html in datos_eq2:
                        df_eq_liga = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]
                        liga_eq = "|".join(sorted(df_eq_liga['League'].dropna().unique())) if not df_eq_liga.empty else ""
                        st.markdown(f"<div style='font-size:8px;font-family:monospace;color:#000'>EQUIPO2: {eq} ({hits}) --> {liga_eq}</div>", unsafe_allow_html=True)
                        st.markdown(html, unsafe_allow_html=True)
                else:
                    todos = datos_eq1 + datos_eq2 + datos_resto
                    todos.sort(key=lambda x: (-x[0], -x[1]))
                    if todos:
                        for pct, hits, eq, html in todos:
                            df_eq_liga = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]
                            liga_eq = "|".join(sorted(df_eq_liga['League'].dropna().unique())) if not df_eq_liga.empty else ""
                            st.markdown(f"<div style='font-size:8px;font-family:monospace;color:#000'>{eq} ({hits}) --> {liga_eq}</div>", unsafe_allow_html=True)
                            st.markdown(html, unsafe_allow_html=True)
                    else:
                        st.warning(f"Ningún equipo llega al {pct_marcador}%")
            elif len(df_final) > 0 and not ligas_visibles:
                st.info("No hay ligas visibles, dale a cargar")
            else:
                st.info("No hay partidos con los filtros actuales")

            #############################################
            if equipo_filtro!= "Ninguno" and len(df_final) > 0:
                total = len(df_final)
                gana = len(df_final[((df_final['HomeTeam'] == equipo_filtro) & (df_final['FTR'] == 'H')) |
                                    ((df_final['AwayTeam'] == equipo_filtro) & (df_final['FTR'] == 'A'))])
                empata = len(df_final[df_final['FTR'] == 'D'])
                pierde = len(df_final[((df_final['HomeTeam'] == equipo_filtro) & (df_final['FTR'] == 'A')) |
                                    ((df_final['AwayTeam'] == equipo_filtro) & (df_final['FTR'] == 'H'))])

                gana_empata = gana + empata
                pierde_empata = pierde + empata

        

    

    columnas_mostrar = [
        'partidos', ""
    ]

    columnas_mostrar = [col for col in columnas_mostrar if col in df_final.columns]
    
    

    # --- CSS para las tablas ---

    
    def render_tabla_equipo(df_input, equipo_ref):
        df_tmp = df_input.copy()
        if todos_eventos and not df_tmp.empty:
            df_tmp['Goles'] = df_tmp.apply(
                lambda r: buscar_goles_partido(r, todos_eventos, rango_minutos[0], rango_minutos[1], parte_gol, equipo_ref),
                axis=1
            )
        else:
            df_tmp['Goles'] = ''
        if jugador_filtro!= "TODOS":
            df_tmp = df_tmp[df_tmp['Goles'].str.contains(jugador_filtro, case=False, na=False)]
        if len(df_tmp) > 0:
            df_tmp['partidos'] = df_tmp.apply(lambda row: formatear_partido(row, equipo_ref, cuota_tipo, row.get('Goles','')), axis=1)
        df_tmp = df_tmp.sort_values(['Jornada','Date'], ascending=[False, False]).head(150)
        return df_tmp[['partidos']].to_html(escape=False, index=False, classes='dataframe')

    # --- Partidos plegables CON BOTON ---
    with st.expander("📋 Partidos", expanded=False, key="exp_partidos"):
        
        # Estado inicial
        if 'ver_partidos' not in st.session_state:
            st.session_state.ver_partidos = False

        # Reset automático si cambias Eq1/Eq2/Jornada
        firma = f"{equipo_filtro}|{equipo2_filtro}|{rango_jornadas}|{cuota_tipo}"
        if 'firma_partidos' not in st.session_state:
            st.session_state.firma_partidos = firma
        if firma != st.session_state.firma_partidos:
            st.session_state.ver_partidos = False
            st.session_state.firma_partidos = firma

        c1, c2 = st.columns([1, 2])
        with c1:
            if not st.session_state.ver_partidos:
                if st.button("📥 Cargar partidos", key="btn_cargar_partidos", type="primary", use_container_width=True):
                    st.session_state.ver_partidos = True
                    st.rerun()
            else:
                if st.button("❌ Ocultar", key="btn_ocultar_partidos", use_container_width=True):
                    st.session_state.ver_partidos = False
                    st.rerun()
        with c2:
            if not st.session_state.ver_partidos:
                st.caption(f"Hay {len(df_final)} partidos listos. Dale a cargar para verlos.")
            else:
                st.caption(f"Mostrando {min(150, len(df_final))} de {len(df_final)} partidos")

        # SI NO HA DADO AL BOTON, NO HACE NADA MÁS
        if not st.session_state.ver_partidos:
            pass
        else:
            # --- TU LOGICA ORIGINAL A PARTIR DE AQUI ---
            if equipo_filtro != "Ninguno" and equipo2_filtro != "Ninguno":
                df1 = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)].sort_values(['Jornada','Date'], ascending=False).head(150)
                df2 = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)].sort_values(['Jornada','Date'], ascending=False).head(150)
                html1 = "".join([formatear_h2h_compacto(r, equipo_filtro) for _, r in df1.iterrows()])
                html2 = "".join([formatear_h2h_compacto(r, equipo2_filtro) for _, r in df2.iterrows()])
                h2h_html = f'''
                <div style="max-height:700px; overflow-y:auto; border:1px solid #ddd;">
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:0; position:sticky; top:0; background:#fff; z-index:5; border-bottom:2px solid #000;">
                    <div style="font-weight:700; font-size:11px; text-align:center; padding:4px">{equipo_filtro} ({len(df1)})</div>
                    <div style="font-weight:700; font-size:11px; text-align:center; padding:4px">{equipo2_filtro} ({len(df2)})</div>
                  </div>
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:6px;">
                    <div>{html1}</div>
                    <div>{html2}</div>
                  </div>
                </div>
                '''
                st.markdown(h2h_html, unsafe_allow_html=True)
            else:
                df_mostrar = df_final.sort_values(['Jornada','Date'], ascending=[False, False]).reset_index(drop=True)
                MAX_FILAS = 150
                if len(df_mostrar) > MAX_FILAS:
                    df_mostrar = df_mostrar.head(MAX_FILAS)
                partidos_html = []
                if len(df_mostrar) > 0:
                    for _, r in df_mostrar.iterrows():
                        partidos_html.append(formatear_partido(r, equipo_filtro if equipo_filtro != "Ninguno" else None, cuota_tipo, r.get('Goles','')))
                left_html = "".join(partidos_html[0::2])
                right_html = "".join(partidos_html[1::2])
                grid_html = f'''
                <div style="max-height:700px; overflow-y:auto; border:1px solid #ddd;">
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:6px;">
                    <div>{left_html}</div>
                    <div>{right_html}</div>
                  </div>
                </div>
                '''
                st.markdown(grid_html, unsafe_allow_html=True)



###########################################################
with st.expander("ℹ Info jornadas", key="exp_info"):
    for liga in liga_sel:
        for temp in temp_sel:
            subset = df_fil[(df_fil['League']==liga) & (df_fil['Season']==temp)]
            if not subset.empty:
                equipos = pd.unique(subset[['HomeTeam','AwayTeam']].values.ravel())
                n_equipos = len(equipos)
                st.write(f"**{liga} {temp}**: {n_equipos} equipos → {n_equipos//2} partidos por jornada")

            elif modo_vista == "Clasificación":
                

                if df_clasificacion.empty:
                    st.warning("No hay datos para ese rango de jornadas")
                else:
                    # Solo la última jornada del rango filtrado
                    j_ultima = int(df_clasificacion['Jornada'].max())
                    temp = temp_sel[-1] if temp_sel else df_clasificacion['Season'].iloc[0]
                    liga = liga_sel[0] if liga_sel else df_clasificacion['League'].iloc[0]

                    tabla = df_clasificacion[
                        (df_clasificacion['Season'] == temp) &
                        (df_clasificacion['League'] == liga) &
                        (df_clasificacion['Jornada'] == j_ultima)
                    ].sort_values('Pos').copy()

                    if tabla.empty:
                        st.warning("No hay datos de clasificación para esa liga/temporada/jornada")
                    else:
                        tabla['Equipo'] = tabla['Equipo'].str.title()

                        st.subheader(f"{liga} {temp} — Jornada {j_ultima}")

                        def color_pg_pe_pp(val, col):
                            if col == 'PG': return 'color:#0f8105; font-weight:700'
                            if col == 'PE': return 'color:#b45309; font-weight:700'
                            if col == 'PP': return 'color:#dc2626; font-weight:700'
                            return ''

                        styled = tabla[['Pos','Equipo','PJ','PG','PE','PP','GF','GC','DG','Pts']].style.map(
                            lambda v: color_pg_pe_pp(v, 'PG'), subset=['PG']
                        ).map(
                            lambda v: color_pg_pe_pp(v, 'PE'), subset=['PE']
                        ).map(
                            lambda v: color_pg_pe_pp(v, 'PP'), subset=['PP']
                        )

                        st.dataframe(
                            styled,
                            hide_index=True,
                            width='stretch',
                            height=600
                        )



################## modo clasificacion fin ############
########filtro rachas La UI (donde eliges Tipo, Condición, Dónde)
with st.expander("🔥 Filtro Rachas", expanded=False, key="exp_rachas"):
    c1, c2, c3, c4 = st.columns([1.2, 1.3, 0.9, 1.0])
    tipo = c1.selectbox("Tipo", ["Máximos", "%"], key="r_tipo")
    cond = c2.selectbox("R1x2", ["Todo","G","P","E","G/E","E/P","G/P"], key="r_cond")
    donde = c4.selectbox("Dónde", ["Todo","Local","Visitante"], key="r_donde")

    if tipo == "Máximos":
        x = c3.number_input("X max", 1, 20, 3, key="r_x")
    else:
        pct_min = c3.slider("% mínimo", 0, 100, 50, key="r_pct")

    # rango de jornadas SOLO para rachas
    jmin = int(df_rachas_full['Jornada'].min())
    jmax = int(df_rachas_full['Jornada'].max())
    rj1, rj2 = st.slider("Jornadas", jmin, jmax, (jmin, jmax), key="r_jornadas")

    src = df_rachas_full[(df_rachas_full['Jornada'] >= rj1) & (df_rachas_full['Jornada'] <= rj2)].copy()

    if not src.empty:
        if tipo == "Máximos":
            t = _rachas(src, cond, donde, x_max=x)
            res = t[t['CountX'] > 0].sort_values(['CountX','Max'], ascending=False)
        else:
            t = _rachas(src, cond, donde)
            res = t[t['%'] >= pct_min].sort_values(['%','Max'], ascending=False)

        st.caption(f"Rachas calculadas en J{rj1} a J{rj2} — {len(res)} equipos")
        st.dataframe(
            res[['Equipo']],
            width='stretch',
            hide_index=True,
            height=500,
            key="tabla_rachas_estable",
            column_config={"Equipo": st.column_config.TextColumn("Resumen / Jornadas")}
        )


            ############fin expander rachas
################buscador de equipos 1826 - 2205
with st.expander("🔍 Buscador de Equipos", expanded=False):
    st.markdown("""
    <style>
    /* Ancho completo para selects en este expander */
    div[data-testid="stExpander"] [data-testid="stSelectbox"] {
        width: 100%!important;
    }
    div[data-testid="stExpander"] [data-testid="stSelectbox"] > div {
        width: 100%!important;
        min-width: unset!important;
    }
    div[data-testid="stExpander"] [data-testid="stSelectbox"] > div > div {
        width: 100%!important;
        min-width: 100%!important;
    }
    /* Evita que las columnas compriman el contenido en móvil */
    div[data-testid="stExpander"] [data-testid="stHorizontalBlock"] > div {
        min-width: 45%!important;
        flex-shrink: 0!important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.caption("Busca equipos que cumplan condiciones en cualquier liga/temporada")

    df_busca = df.copy()

    col_liga, col_temp = st.columns(2)
    ligas_busca = col_liga.multiselect("Ligas", sorted(df_busca['League'].unique()), default=[], key="be2_ligas_v2")
    temps_busca = col_temp.multiselect("Temps", sorted(df_busca['Season'].unique()), default=[], key="be2_temps_v2")

    if ligas_busca: df_busca = df_busca[df_busca['League'].isin(ligas_busca)]
    if temps_busca: df_busca = df_busca[df_busca['Season'].isin(temps_busca)]

    if df_busca.empty:
        st.warning("Selecciona liga/temporada")
        st.stop()

    df_be, _ = calcular_estado_jornada(df_busca)

    # --- NIVEL 2: JORNADA DE/A en misma línea ---
    st.markdown("**Jornadas**")
    jmin, jmax = int(df_be['Jornada'].min()), int(df_be['Jornada'].max())
    col_j1, col_j2 = st.columns(2)
    j_desde_be = col_j1.number_input("De", min_value=jmin, max_value=jmax, value=jmin, step=1, key='be2_j_desde', label_visibility="collapsed")
    j_hasta_be = col_j2.number_input("A", min_value=jmin, max_value=jmax, value=jmax, step=1, key='be2_j_hasta', label_visibility="collapsed")
    if j_desde_be > j_hasta_be:
        st.warning("'De' no puede ser mayor que 'A'")
        j_desde_be = j_hasta_be
    j_rango = (int(j_desde_be), int(j_hasta_be))

    # --- NIVEL 3: MODO en línea completa ---
    modo_busca = st.radio("Modo búsqueda", ["Últimos X partidos", "% en rango jornadas"], horizontal=True, key="be2_modo")

    # --- NIVEL 4: CAJITA DINÁMICA + L/V EN MISMA LÍNEA ---
    de_busca = "-" # valor por defecto
    if modo_busca == "Últimos X partidos":
        c_ult, c_de, c_lv = st.columns([1,1,1])
        ultimos_x = c_ult.number_input("Últimos", 1, 38, 5, key="be2_ultimos")
        de_busca = c_de.selectbox("De", ["-"] + [str(i) for i in range(1, 51)], index=0, key="be2_de", help="Ej: Últimos 3 De 4 = 3 wins en los últimos 4")
        lv_busca = c_lv.selectbox("L/V", ["Todo","Local","Visitante"], key="be2_lv")
        pct_min_rango = None
    else:
        col_pct_lv1, col_pct_lv2 = st.columns(2)
        pct_min_rango = col_pct_lv1.number_input("% mín", 0, 100, 50, 5, key="be2_pct_min")
        ultimos_x = None
        lv_busca = col_pct_lv2.selectbox("L/V", ["Todo","Local","Visitante"], key="be2_lv")

    # --- NUEVO: FILTRO RESULTADO G/E/P/GE/GP/EP ---
    col_res_be = st.columns(1)[0]
    res_busca = col_res_be.selectbox("Res", ["Todo","G","E","P","GE","GP","EP"], key="be2_res",
                                     help="G:Gana | E:Empata | P:Pierde | GE:Gana/Empata | GP:Gana/Pierde | EP:Empata/Pierde")

    # --- RESTO IGUAL: Fav/Cntr1, AM, Vlr1, Parte ---
    colc1, colc2, colc3, colc4 = st.columns(4)
    fav_c1 = colc1.selectbox("Fav/Cntr1", ["Todo","AF","C"], key="be2_favc1", help="AF=a favor del equipo | C=en contra")
    am_busca = colc2.selectbox("AM", ["Todos","Si","No"], key="be2_am")
    vlr1_busca = colc3.selectbox("Vlr1", ["Ninguno"] + [i/2 for i in range(21)], key="be2_vlr1")
    parte_busca = colc4.selectbox("Parte", ["Todo","1T","2T"], key="be2_parte")

    # --- Col1, Op1, Minutos ---
    columnas_numericas_be = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','tirosTot','tirosPuertaTot','faltasTot','TargRojTot']
    ABREV_COL_BE = {
        'FTHG': 'GL','FTAG': 'GV','HTHG': 'G1L','HTAG': 'G1V',
        'HS': 'TL','AS': 'TV','HST': 'TPL','AST': 'TPV',
        'HF': 'FL','AF': 'FV','HC': 'CL','AC': 'CV',
        'HY': 'AL','AY': 'AV','HR': 'RL','AR': 'RV',
        'GolesTotales': 'GT','GolesHT': 'G1T','Goles2T': 'G2T',
        'corneTot': 'CT','TargAmTot': 'TAM',
        'tirosTot': 'TT','tirosPuertaTot': 'TPT','faltasTot': 'FT','TargRojTot': 'TRT',
        'Ninguno': '—',
    }
    colc5, colc6 = st.columns(2)
    col1_busca = colc5.selectbox("Col1", ["Ninguno"] + columnas_numericas_be, format_func=lambda x: ABREV_COL_BE.get(x, x), key="be2_col1")
    op1_busca = colc6.selectbox("Op1", ["=", ">", ">=", "<", "<="], key="be2_op1")

    st.caption("Minutos por parte")
    col_1t, col_2t, col_ext = st.columns(3)
    min_1t = col_1t.number_input("1ªT", min_value=0, max_value=60, value=45, step=1, key="be2_min_1t")
    min_2t = col_2t.number_input("2ªT", min_value=0, max_value=60, value=45, step=1, key="be2_min_2t")
    min_ext = col_ext.number_input("+", min_value=0, max_value=30, value=10, step=1, key="be2_min_ext", help="Añadido/Prórroga")

    # --- TEXTO SIMPLE DE LO SELECCIONADO ---
    lig_txt = ",".join(ligas_busca) if ligas_busca else "Todas"
    temp_txt = ",".join(temps_busca) if temps_busca else "Todas"
    modo_txt = f"Ult {ultimos_x}" if modo_busca=="Últimos X partidos" else f"%≥{pct_min_rango}"
    filtro_resumen = f"filtro: {lig_txt} | {temp_txt} | J{j_desde_be}-{j_hasta_be} | {modo_txt} | {lv_busca} | Res:{res_busca} | {fav_c1}:{col1_busca}{op1_busca}{vlr1_busca} | AM:{am_busca} | {parte_busca}"
    st.markdown(f"<div style='font-size:10px;font-family:monospace;background:#f3f4f6;padding:4px 6px;border-radius:6px;margin:6px 0'>{filtro_resumen}</div>", unsafe_allow_html=True)

    #########boton buscar equipos, aqui tb esta la logica de verlo "J30f 0-1

    if st.button("🔎 Buscar equipos", type="primary", width='stretch', key="be2_buscar"):
        equipos = pd.unique(df_be[['HomeTeam','AwayTeam']].values.ravel())
        resultados = []

        for eq in equipos:
            df_eq = df_be[(df_be['HomeTeam']==eq) | (df_be['AwayTeam']==eq)].copy()
            if df_eq.empty: continue

            if lv_busca == "Local":
                df_eq = df_eq[df_eq['HomeTeam']==eq]
            elif lv_busca == "Visitante":
                df_eq = df_eq[df_eq['AwayTeam']==eq]
            if df_eq.empty: continue

            df_eq = df_eq[(df_eq['Jornada']>=j_rango[0]) & (df_eq['Jornada']<=j_rango[1])]
            if df_eq.empty: continue
            df_eq = df_eq.sort_values('Date')

            es_ultimos = (modo_busca == "Últimos X partidos")
            if es_ultimos:
                # Si De = "-" => comportamiento antiguo: últimos X tienen que ser 100%
                if de_busca == "-":
                    df_ult = df_eq.tail(ultimos_x)
                    if len(df_ult) < ultimos_x:
                        continue
                    df_eq = df_ult.copy()
                    total = ultimos_x
                    ventana = ultimos_x
                    requeridos = ultimos_x
                else:
                    # Si De = 4 y Últimos = 3 => miro los últimos 4, pido al menos 3
                    ventana = int(de_busca)
                    requeridos = ultimos_x
                    if ventana < requeridos:
                        ventana = requeridos # seguridad
                    df_ult = df_eq.tail(ventana)
                    if len(df_ult) < ventana:
                        continue
                    df_eq = df_ult.copy()
                    total = ventana
            else:
                total = len(df_eq)
                ventana = total
                requeridos = 0

            es_local = df_eq['HomeTeam']==eq
            gana = ((es_local) & (df_eq['FTHG']>df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']>df_eq['FTHG']))
            pierde = ((es_local) & (df_eq['FTHG']<df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']<df_eq['FTHG']))
            empata = ~(gana | pierde)

            if res_busca == "G": mask_res = gana
            elif res_busca == "E": mask_res = empata
            elif res_busca == "P": mask_res = pierde
            elif res_busca == "GE": mask_res = gana | empata
            elif res_busca == "GP": mask_res = gana | pierde
            elif res_busca == "EP": mask_res = empata | pierde
            else: mask_res = pd.Series([True]*len(df_eq), index=df_eq.index)

            # Filtro 1x2 se aplica SIEMPRE antes de lo demás
            df_eq = df_eq[mask_res]
            if df_eq.empty: continue
            if not es_ultimos:
                total = len(df_eq) # en modo % el total es lo que queda tras G/E/P

            es_local = df_eq['HomeTeam']==eq

            if parte_busca == "1T":
                gf = np.where(es_local, df_eq['HTHG'], df_eq['HTAG'])
                gc = np.where(es_local, df_eq['HTAG'], df_eq['HTHG'])
            elif parte_busca == "2T":
                gf = np.where(es_local, df_eq['FTHG']-df_eq['HTHG'], df_eq['FTAG']-df_eq['HTAG'])
                gc = np.where(es_local, df_eq['FTAG']-df_eq['HTAG'], df_eq['FTHG']-df_eq['HTHG'])
            else:
                gf = np.where(es_local, df_eq['FTHG'], df_eq['FTAG'])
                gc = np.where(es_local, df_eq['FTAG'], df_eq['FTHG'])

            cumple = np.ones(len(df_eq), dtype=bool)

            if vlr1_busca!= "Ninguno":
                if fav_c1 == "AF": cumple = cumple & (gf > float(vlr1_busca))
                elif fav_c1 == "C": cumple = cumple & (gc > float(vlr1_busca))
                else: cumple = cumple & ((gf + gc) > float(vlr1_busca))

            if col1_busca!= "Ninguno" and vlr1_busca!= "Ninguno":
                mapa_col = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC','HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
                if fav_c1 == "AF": val_col = np.where(es_local, df_eq[col1_busca], df_eq.get(mapa_col.get(col1_busca, col1_busca), df_eq[col1_busca]))
                elif fav_c1 == "C": val_col = np.where(es_local, df_eq.get(mapa_col.get(col1_busca, col1_busca), 0), df_eq.get(col1_busca, 0))
                else: val_col = df_eq[col1_busca]
                val = float(vlr1_busca)
                if op1_busca == "=": cumple = cumple & (val_col == val)
                elif op1_busca == ">": cumple = cumple & (val_col > val)
                elif op1_busca == ">=": cumple = cumple & (val_col >= val)
                elif op1_busca == "<": cumple = cumple & (val_col < val)
                elif op1_busca == "<=": cumple = cumple & (val_col <= val)

            if am_busca == "Si": cumple = cumple & (gf > 0) & (gc > 0)
            elif am_busca == "No": cumple = cumple & ~((gf > 0) & (gc > 0))

            hits = int(cumple.sum())
            pct = hits / total * 100 if total else 0

            if es_ultimos:
                if de_busca == "-":
                    # Antiguo: 5 de 5
                    if hits != total:
                        continue
                else:
                    # Nuevo: 3 de 4
                    if hits < requeridos:
                        continue
            else:
                # MODO % = aquí sí vale 60%
                if pct < pct_min_rango:
                    continue

            if hits > 0:
                df_cumple = df_eq[cumple].copy().sort_values('Date')

                # MARCADOR REAL 0-1 fuera en vez de 1-0 - FIX gft/gct
                chips = []
                for _, rr in df_cumple.iterrows():
                    suf = 'c' if rr['HomeTeam']==eq else 'f'
                    real_home = int(rr['FTHG'])
                    real_away = int(rr['FTAG'])
                    
                    if rr['HomeTeam']==eq:
                        gano = real_home > real_away
                        perdio = real_home < real_away
                    else:
                        gano = real_away > real_home
                        perdio = real_away < real_home
                    
                    col = "#0f8105" if gano else "#f31818" if perdio else "#0A2342"
                    chips.append(f"<span style='display:inline-flex; border:1px solid #ccc; border-radius:12px; padding:2px 8px; margin:2px; color:{col}; font-weight:700'>J{int(rr['Jornada'])}{suf} {real_home}-{real_away}</span>")
                jors_html = "".join(chips)

                resultados.append({
                    'Equipo': eq, 'Liga': df_eq.iloc[0]['League'],
                    'PJ': total, 'Cumple': hits, '%': round(pct,1),
                    'Jornadas': jors_html
                })

        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(['%','Cumple'], ascending=False)
            st.success(f"Encontrados {len(df_res)} equipos")
            lineas_html = []
            for _, r in df_res.iterrows():
                linea = f"""<div style='font-size:11px; font-family:monospace; line-height:1.4; padding:6px 0; border-bottom:1px solid #eee;'>
                    <span style='color:#555; font-weight:700'>{r['Liga'][:3].upper()}</span> |
                    <span style='font-weight:900; color:#0A2342'>{r['Equipo']}</span><br>
                    <span style='color:#0f8105; font-weight:700'>{r['Cumple']}# {r['%']}%</span> — {r['Jornadas']}
                </div>"""
                lineas_html.append(linea)
            st.markdown(f"<div style='background:#fff; border:1px solid #ddd; max-height:700px; overflow-y:auto; padding:8px;'>{''.join(lineas_html)}</div>", unsafe_allow_html=True)
        else:
            st.warning("Ningún equipo cumple esas condiciones")

#########boton buscar equipos, aqui tb esta la logica de verlo "J30f 0-1
#####FIN
# --- RESUMEN JORNADAS + % G/E/P CORREGIDO ---
def resumen_jornadas_visual(df_partidos, df_clas, liga, season, j_desde, j_hasta, condicion_lv="Todo", filtro_res="Todo", ambos_marcan_clasif="Todos", goles_clasif="Todo", operador_goles_clasif="Todo", valor_goles_clasif="Todo"):
    df_liga = df_partidos[(df_partidos['League']==liga) & (df_partidos['Season']==season) &
                          (df_partidos['Jornada']>=j_desde) & (df_partidos['Jornada']<=j_hasta)].copy()
    if df_liga.empty: return []

    ult_j = df_liga['Jornada'].max()
    clas_ult = df_clas[(df_clas['League']==liga) & (df_clas['Season']==season) & (df_clas['Jornada']==ult_j)]
    if not clas_ult.empty:
        orden_equipos = clas_ult.sort_values('Pos')['Equipo'].tolist()
    else:
        orden_equipos = sorted(pd.unique(df_liga[['HomeTeam','AwayTeam']].values.ravel()))

    lineas = []
    for equipo in orden_equipos:
        df_eq_base = df_liga[(df_liga['HomeTeam']==equipo) | (df_liga['AwayTeam']==equipo)].copy()
        if df_eq_base.empty: continue

        if condicion_lv == "Local":
            df_eq_base = df_eq_base[df_eq_base['HomeTeam']==equipo]
        elif condicion_lv == "Visitante":
            df_eq_base = df_eq_base[df_eq_base['AwayTeam']==equipo]
        if df_eq_base.empty: continue

        es_local = df_eq_base['HomeTeam']==equipo
        gana_base = (es_local & (df_eq_base['FTHG']>df_eq_base['FTAG'])) | (~es_local & (df_eq_base['FTAG']>df_eq_base['FTHG']))
        pierde_base = (es_local & (df_eq_base['FTHG']<df_eq_base['FTAG'])) | (~es_local & (df_eq_base['FTAG']<df_eq_base['FTHG']))
        empata_base = ~(gana_base | pierde_base)

        total_pj = len(df_eq_base)
        n_g = gana_base.sum(); n_e = empata_base.sum(); n_p = pierde_base.sum()
        p_g = round(n_g/total_pj*100) if total_pj else 0
        p_e = round(n_e/total_pj*100) if total_pj else 0
        p_p = round(n_p/total_pj*100) if total_pj else 0

        pj_casa = es_local.sum()
        pj_fuera = (~es_local).sum()
        p_fx = round((~es_local & gana_base).sum()/pj_fuera*100) if pj_fuera else 0
        p_cx = round((es_local & gana_base).sum()/pj_casa*100) if pj_casa else 0
        p_fpx = round((~es_local & pierde_base).sum()/pj_fuera*100) if pj_fuera else 0
        p_cpx = round((es_local & pierde_base).sum()/pj_casa*100) if pj_casa else 0
        p_fex = round((~es_local & empata_base).sum()/pj_fuera*100) if pj_fuera else 0
        p_cex = round((es_local & empata_base).sum()/pj_casa*100) if pj_casa else 0

        df_eq_filtro = df_eq_base.copy()
        if filtro_res!= "Todo":
            if filtro_res == "G":
                df_eq_filtro = df_eq_filtro[gana_base]
            elif filtro_res == "E":
                df_eq_filtro = df_eq_filtro[empata_base]
            elif filtro_res == "P":
                df_eq_filtro = df_eq_filtro[pierde_base]
            elif filtro_res == "GE":
                df_eq_filtro = df_eq_filtro[gana_base | empata_base]
            elif filtro_res == "PE":
                df_eq_filtro = df_eq_filtro[pierde_base | empata_base]
            elif filtro_res == "GP":
                df_eq_filtro = df_eq_filtro[gana_base | pierde_base]

        # === FILTRO AMBOS MARCAN PARA CLASIF ===
        if ambos_marcan_clasif!= "Todos":
            for col in ['FTHG','FTAG','HTHG','HTAG']:
                df_eq_filtro[col] = pd.to_numeric(df_eq_filtro[col], errors='coerce').fillna(0)

            if ambos_marcan_clasif == "Si":
                df_eq_filtro = df_eq_filtro[(df_eq_filtro['FTHG'] > 0) & (df_eq_filtro['FTAG'] > 0)]
            elif ambos_marcan_clasif == "No":
                df_eq_filtro = df_eq_filtro[~((df_eq_filtro['FTHG'] > 0) & (df_eq_filtro['FTAG'] > 0))]
            elif ambos_marcan_clasif == "Si1P":
                df_eq_filtro = df_eq_filtro[(df_eq_filtro['HTHG'] > 0) & (df_eq_filtro['HTAG'] > 0)]
            elif ambos_marcan_clasif == "No1P":
                df_eq_filtro = df_eq_filtro[~((df_eq_filtro['HTHG'] > 0) & (df_eq_filtro['HTAG'] > 0))]
            elif ambos_marcan_clasif == "Si2P":
                df_eq_filtro = df_eq_filtro[((df_eq_filtro['FTHG'] - df_eq_filtro['HTHG']) > 0) & ((df_eq_filtro['FTAG'] - df_eq_filtro['HTAG']) > 0)]
            elif ambos_marcan_clasif == "No2P":
                df_eq_filtro = df_eq_filtro[~(((df_eq_filtro['FTHG'] - df_eq_filtro['HTHG']) > 0) & ((df_eq_filtro['FTAG'] - df_eq_filtro['HTAG']) > 0))]
        # === FIN FILTRO AM ===

        # === FILTRO GOLES PARA CLASIF ===
        if goles_clasif!= "Todo" and operador_goles_clasif!= "Todo" and valor_goles_clasif!= "Todo":
            es_local = df_eq_filtro['HomeTeam']==equipo
            val = float(valor_goles_clasif)

            if goles_clasif == "GT":
                goles_equipo = np.where(es_local, df_eq_filtro['FTHG'], df_eq_filtro['FTAG'])
            elif goles_clasif == "G1P":
                goles_equipo = np.where(es_local, df_eq_filtro['HTHG'], df_eq_filtro['HTAG'])
            elif goles_clasif == "G2P":
                goles_equipo = np.where(es_local, df_eq_filtro['FTHG'] - df_eq_filtro['HTHG'], df_eq_filtro['FTAG'] - df_eq_filtro['HTAG'])
            else:
                goles_equipo = np.zeros(len(df_eq_filtro))

            if operador_goles_clasif == ">":
                df_eq_filtro = df_eq_filtro[goles_equipo > val]
            elif operador_goles_clasif == "<":
                df_eq_filtro = df_eq_filtro[goles_equipo < val]
            elif operador_goles_clasif == "=":
                df_eq_filtro = df_eq_filtro[goles_equipo == val]
        # === FIN FILTRO GOLES ===

        if df_eq_filtro.empty: continue

        df_eq_filtro['res'] = np.where(gana_base[df_eq_filtro.index], 'win', np.where(pierde_base[df_eq_filtro.index], 'loss', 'draw'))
        df_eq_filtro['color'] = np.where(gana_base[df_eq_filtro.index], '#0f8105', np.where(pierde_base[df_eq_filtro.index], '#f31818', '#0A2342'))

        partes = []
        for (season, j), g in df_eq_filtro.groupby(['Season','Jornada'], sort=True):
            color = g['color'].iloc[0]
            es_loc_j = (g['HomeTeam']==equipo).iloc[0]
            sufijo = 'c' if es_loc_j else 'f'

            # FIX: marcador real Home-Away, no invertido
            real_home = int(g['FTHG'].iloc[0])
            real_away = int(g['FTAG'].iloc[0])
            res_j = f"{real_home}-{real_away}"

            txt = f"J{int(j)}{sufijo} {res_j}"

            # CAMBIO: añadir. si hay AM en algún partido de esa jornada
            if ((g['FTHG'] > 0) & (g['FTAG'] > 0)).any():
                txt += '●'

            if len(g) > 1:
                txt += f" - {len(g)}#"

            partidos_html = []
            for _, r in g.iterrows():
                partidos_html.append(formatear_h2h_compacto(r, equipo))
            resultado = "".join(partidos_html)

            partes.append(f"<details style='display:inline-flex;margin:2px'><summary style='color:{color};font-weight:700;cursor:pointer;list-style:none;display:inline-flex;padding:3px 8px;border:1px solid #ccc;border-radius:12px;background:#fff;white-space:nowrap;font-size:11px'>{txt}</summary><div style='background:#FFFFFF;border:2px solid #000;padding:4px;margin-top:2px;box-shadow:2px 2px 6px rgba(0,0,0,0.3);max-width:340px'>{resultado}</div></details>")

        # CAMBIO: nombre en mayúsculas, línea 2 G/P/E con f: y c:, línea 3 jornadas
        gana_c = int((es_local & gana_base).sum())
        gana_f = int((~es_local & gana_base).sum())
        pierde_c = int((es_local & pierde_base).sum())
        pierde_f = int((~es_local & pierde_base).sum())
        empata_c = int((es_local & empata_base).sum())
        empata_f = int((~es_local & empata_base).sum())
#######aqui se hace las jornadas de "clasif."" parte visual
        linea = f"""<div style='font-size:9px;line-height:1.4;margin:6px 0;padding-bottom:6px;border-bottom:1px solid #eee'>
        <b>{equipo.upper()}</b><br>
        <span style='color:#0f8105;font-weight:700'>G:{p_g}% {n_g}/{total_pj}</span> &nbsp; Casa:{p_cx}% {gana_c}/{pj_casa} &nbsp; Fuera:{p_fx}% {gana_f}/{pj_fuera}<br>
        <span style='color:#f31818;font-weight:700'>P:{p_p}% {n_p}/{total_pj}</span> &nbsp; Casa:{p_cpx}% {pierde_c}/{pj_casa} &nbsp; Fuera:{p_fpx}% {pierde_f}/{pj_fuera}<br>
        <span style='color:#0A2342;font-weight:700'>E:{p_e}% {n_e}/{total_pj}</span> &nbsp; Casa:{p_cex}% {empata_c}/{pj_casa} &nbsp; Fuera:{p_fex}% {empata_f}/{pj_fuera}<br>
        {" <span style='color:#999;font-weight:900'>|</span> ".join(partes)}
        </div>"""       
        lineas.append(linea)
    return lineas
######"clasif".

with st.expander("📅Clasif.G/E/P %", expanded=False):
    try:
        col_cl1, col_cl2 = st.columns(2)

        # --- CLAVE: default=[] SIEMPRE, no usa liga_sel ni temp_sel ---
        ligas_clasif = col_cl1.multiselect(
            "Liga",
            sorted(df_original['League'].unique()),
            default=[], # <-- Vacío fijo, no lee de arriba
            key="clasif_ligas_indep_v2" # <-- Key único nuevo por si acaso
        )
        temps_clasif = col_cl2.multiselect(
            "Temporada",
            sorted(df_original['Season'].unique()),
            default=[], # <-- Vacío fijo
            key="clasif_temps_indep_v2" # <-- Key único nuevo
        )

        if not ligas_clasif or not temps_clasif:
            st.markdown("<div style='font-size:11px'>Selecciona Liga y Temporada para ver el resumen</div>", unsafe_allow_html=True)
        else:
            df_base_clasif = df_original[df_original['League'].isin(ligas_clasif) & df_original['Season'].isin(temps_clasif)].copy()

            if df_base_clasif.empty:
                st.warning("No hay datos para esa combinación Liga/Temporada")
            else:
                df_base_clasif, df_clas_base_clasif = calcular_estado_jornada(df_base_clasif)

                if len(df_base_clasif) > 0:
                    # CAMBIO: 3 columnas ahora para meter AM
                    col_lv, col_res, col_am = st.columns([1, 1, 1])
                    condicion_lv = col_lv.selectbox(
                        "L/V",
                        ["Todo", "Local", "Visitante"],
                        key="clasf_lv_local"
                    )
                    filtro_res = col_res.selectbox(
                        "Res",
                        ["Todo", "G", "E", "P", "GE", "PE", "GP"],
                        key="clasf_res_local"
                    )
                    # NUEVO: Filtro Ambos Marcan
                    ambos_marcan_clasif = col_am.selectbox(
                        "AM",
                        ["Todos","Si","No","Si1P","No1P","Si2P","No2P"],
                        key="clasf_am_local"
                    )

                    # NUEVO: 3 columnas para filtro de Goles
                    col_g1, col_g2, col_g3 = st.columns([1, 1, 1])
                    goles_clasif = col_g1.selectbox("Goles", ["Todo","GT","G1P","G2P"], key="clasf_goles_local")
                    operador_goles_clasif = col_g2.selectbox("Op", ["Todo", ">", "<", "="], key="clasf_op_goles_local")
                    valor_goles_clasif = col_g3.selectbox("Vlr", ["Todo"] + [i/2 for i in range(1, 51)], key="clasf_valor_goles_local") # 0.5 a 25

                    # --- CAJITAS % ---
                    col_pct1, col_pct2 = st.columns(2)
                    pct_min = col_pct1.number_input(
                        "% Mín",
                        min_value=0,
                        max_value=100,
                        value=0,
                        step=1,
                        key="clasf_pct_min_local"
                    )
                    pct_max = col_pct2.number_input(
                        "% Máx",
                        min_value=0,
                        max_value=100,
                        value=100,
                        step=1,
                        key="clasf_pct_max_local"
                    )
                    if pct_min > pct_max:
                        st.warning("% Mín no puede ser mayor que % Máx")
                        pct_min = pct_max

                    # --- CAJITAS LIBRES PARA JORNADAS ---
                    col_j1, col_j2 = st.columns(2)

                    if 'Jornada' in df_base_clasif.columns and not df_base_clasif.empty:
                        j_min_default = int(df_base_clasif['Jornada'].min())
                        j_max_default = int(df_base_clasif['Jornada'].max())
                    else:
                        j_min_default = 1
                        j_max_default = 38

                    j_desde = col_j1.number_input(
                        "Jornada De",
                        min_value=1,
                        max_value=46,
                        value=j_min_default,
                        step=1,
                        key='clasf_j_desde_local'
                    )
                    j_hasta = col_j2.number_input(
                        "Jornada A",
                        min_value=1,
                        max_value=46,
                        value=j_max_default,
                        step=1,
                        key='clasf_j_hasta_local'
                    )
                    if j_desde > j_hasta:
                        st.warning("Jornada 'De' no puede ser mayor que 'A'")
                        j_desde = j_hasta

                    # --- GENERAR RESULTADOS CON DF_BASE_CLASIF ---
                    for liga in ligas_clasif:
                        for temp in temps_clasif:
                            # CAMBIO: paso ambos_marcan_clasif + los 3 nuevos de goles
                            lineas = resumen_jornadas_visual(
                                df_base_clasif, df_clas_base_clasif, liga, temp,
                                j_desde, j_hasta, condicion_lv, filtro_res, ambos_marcan_clasif,
                                goles_clasif, operador_goles_clasif, valor_goles_clasif
                            )

                            # Filtrar por %
                            if pct_min > 0 or pct_max < 100:
                                lineas_filtradas = []
                                for linea in lineas:
                                    pct_match = None
                                    if filtro_res == "G":
                                        m = re.search(r'G:(\d+)%', linea)
                                        if m: pct_match = int(m.group(1))
                                    elif filtro_res == "E":
                                        m = re.search(r'E:(\d+)%', linea)
                                        if m: pct_match = int(m.group(1))
                                    elif filtro_res == "P":
                                        m = re.search(r'P:(\d+)%', linea)
                                        if m: pct_match = int(m.group(1))
                                    else:
                                        m = re.search(r'G:(\d+)%', linea)
                                        if m: pct_match = int(m.group(1))

                                    if pct_match is not None and pct_min <= pct_match <= pct_max:
                                        lineas_filtradas.append(linea)
                                lineas = lineas_filtradas

                            if lineas:
                                st.markdown(
                                    f"<div style='background:#f8f9fa;padding:8px 10px;border-left:3px solid #0A2342;margin:6px 0 10px 0;font-size:11px'>"
                                    f"<b style='font-size:11px'>Filtro J{j_desde}-J{j_hasta} {condicion_lv} {filtro_res} AM:{ambos_marcan_clasif} {goles_clasif}:{operador_goles_clasif}:{valor_goles_clasif} %:{pct_min}-{pct_max} ({len(lineas)} equipos)</b><br>"
                                    + "<br>".join(lineas) + "</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.info(f"No hay datos en J{j_desde}-J{j_hasta} con esos filtros para {liga} {temp}")
                else:
                    st.warning("No hay partidos con los filtros actuales")

   
    except Exception as e:
        st.error(f"Error en Clasif: {str(e)}")
        st.caption("Si persiste, borra cache o revisa que el parquet tenga columnas Jornada/Date")





#################generador de apuesta


with st.expander("🎯 Creador Apuestas", expanded=False):
    st.caption("Predicción universal - misma tarjeta")

    col_l, col_t = st.columns(2)
    ca_liga = col_l.selectbox("Liga", sorted(df['League'].unique()), key="ca_liga")
    ca_temp = col_t.selectbox("Temporada", sorted(df[df['League']==ca_liga]['Season'].unique(), reverse=True), key="ca_temp")

    df_creador_base = df[(df['League']==ca_liga) & (df['Season']==ca_temp)].copy()
    df_creador, _ = calcular_estado_jornada(df_creador_base)

    jmin_all = int(df_creador['Jornada'].min()); jmax_all = int(df_creador['Jornada'].max())
    j1, j2 = st.slider("Jornadas a analizar", jmin_all, jmax_all, (jmin_all, jmax_all), key="ca_jornadas")

    equipos = sorted(pd.unique(df_creador[['HomeTeam','AwayTeam']].values.ravel()))
    col_eq1, col_eq2 = st.columns(2)
    eq1 = col_eq1.selectbox("Eq1 (local)", [""] + equipos, key="ca_eq1")
    eq2 = col_eq2.selectbox("Eq2 (visitante)", [""] + [e for e in equipos if e != eq1], key="ca_eq2")

    if st.button("Generar partido", key="ca_gen", width='stretch') and eq1 and eq2:
        df_r = df_creador[(df_creador['Jornada']>=j1) & (df_creador['Jornada']<=j2)].copy()
        m1 = df_r[(df_r['HomeTeam']==eq1)|(df_r['AwayTeam']==eq1)].sort_values('Date').tail(20)
        m2 = df_r[(df_r['HomeTeam']==eq2)|(df_r['AwayTeam']==eq2)].sort_values('Date').tail(20)

        if len(m1)<4 or len(m2)<4:
            st.warning("Necesitas mínimo 4 partidos en el rango")
            st.stop()

        # --- CALIBRACIÓN LIGA ---
        lg_home = df_r['FTHG'].mean(); lg_away = df_r['FTAG'].mean()
        lg_g = (lg_home + lg_away)/2 or 1.3
        home_adv = lg_home / max(lg_away, 0.1)

        def fuerza(eq, df_eq):
            w = np.exp(np.linspace(-0.5,0,len(df_eq))); w/=w.sum()
            loc = df_eq['HomeTeam']==eq
            gf = np.average(np.where(loc, df_eq['FTHG'], df_eq['FTAG']), weights=w)
            gc = np.average(np.where(loc, df_eq['FTAG'], df_eq['FTHG']), weights=w)
            htg = np.average(np.where(loc, df_eq['HTHG'], df_eq['HTAG']), weights=w)
            perf = np.clip(np.average(np.where(loc, df_eq['HomePerf'], df_eq['AwayPerf']), weights=w), 0.8, 1.8)
            pos = np.average(np.where(loc, df_eq['HomePosPrev'], df_eq['AwayPosPrev']), weights=w)
            hs = np.average(np.where(loc, df_eq['HS'], df_eq['AS']), weights=w)
            hst = np.average(np.where(loc, df_eq['HST'], df_eq['AST']), weights=w)
            hf = np.average(np.where(loc, df_eq['HF'], df_eq['AF']), weights=w)
            hc = np.average(np.where(loc, df_eq['HC'], df_eq['AC']), weights=w)
            hy = np.average(np.where(loc, df_eq['HY'], df_eq['AY']), weights=w)
            hr = np.average(np.where(loc, df_eq['HR'], df_eq['AR']), weights=w)

            atk = np.clip((gf/lg_g) * (0.7 + 0.3*perf/1.3), 0.65, 1.5)
            defe = np.clip((gc/lg_g) * (1.2 - 0.2*perf/1.3), 0.7, 1.4)

            # --- PEDIGREE HISTÓRICO (FIX) ---
            hist = 1.0
            temps = sorted(df['Season'].unique())
            if ca_temp in temps:
                idx = temps.index(ca_temp)
                prev_temps = temps[max(0, idx-3):idx]
                pos_hist = []
                for t in prev_temps:
                    df_t_base = df[(df['League']==ca_liga) & (df['Season']==t)]
                    if df_t_base.empty: continue
                    df_t, _ = calcular_estado_jornada(df_t_base)  # cacheado
                    ult_j = df_t['Jornada'].max()
                    r = df_t[(df_t['Jornada']==ult_j) & ((df_t['HomeTeam']==eq)|(df_t['AwayTeam']==eq))]
                    if not r.empty:
                        row = r.iloc[-1]
                        p = row['HomePosPrev'] if row['HomeTeam']==eq else row['AwayPosPrev']
                        pos_hist.append(p)
                if pos_hist:
                    avg_pos = np.mean(pos_hist)
                    hist = float(np.clip(1.18 - (avg_pos-1)*0.018, 0.88, 1.15))

            atk = np.clip(atk * hist, 0.6, 1.6)
            defe = np.clip(defe * (2 - hist), 0.65, 1.5)

            return {'atk':atk,'def':defe,'p1':htg/max(gf,0.1),'perf':perf,'pos':pos,
                    'hs':hs,'hst':hst,'hf':hf,'hc':hc,'hy':hy,'hr':hr}

        f1, f2 = fuerza(eq1,m1), fuerza(eq2,m2)
        pos_fact = np.clip(1 + (f2['pos']-f1['pos'])*0.01, 0.9, 1.1)

        # contexto
        pts1 = m1.iloc[-1]['HomePtsPrev'] if m1.iloc[-1]['HomeTeam']==eq1 else m1.iloc[-1]['AwayPtsPrev']
        pts2 = m2.iloc[-1]['HomePtsPrev'] if m2.iloc[-1]['HomeTeam']==eq2 else m2.iloc[-1]['AwayPtsPrev']
        jor_actual = (j1+j2)//2
        n_eq = df_r['HomeTeam'].nunique()
        peso_h, peso_a = 1.0, 1.0

        # últimos 8 jornadas
        if jor_actual > jmax_all - 8:
            peso_h *= 1.07; peso_a *= 1.07

        # ... (tu lógica de descenso, derbi, venganza, hundido, vida o muerte se mantiene igual) ...
        # [Pega aquí tus bloques de rivalidad/venganza/hundido sin cambios]

        lam_h = np.clip(lg_g * f1['atk'] * f2['def'] * home_adv * pos_fact * peso_h, 0.4, 2.8)
        lam_a = np.clip(lg_g * f2['atk'] * f1['def'] / home_adv / pos_fact * peso_a, 0.4, 2.6)

        g1, g2 = int(round(lam_h)), int(round(lam_a))
        h1 = int(round(lam_h * f1['p1'])); a1 = int(round(lam_a * f2['p1']))
        h2, a2 = max(0,g1-h1), max(0,g2-a1)

        ab1, ab2 = abreviar_equipo(eq1), abreviar_equipo(eq2)
        ht_res = ab1 if h1>a1 else ab2 if a1>h1 else 'E'
        ft_res = ab1 if g1>g2 else ab2 if g2>g1 else 'E'

        html = f"""
        <div style='font-family:monospace; font-size:11px; line-height:1.15; padding:6px; background:#fff; border:2px solid #000'>
        <b>{ca_liga} {ca_temp} | J{j1}-{j2}</b><br>
        {ht_res}/{ft_res}<br>
        {ab1} {g1}-{g2} {ab2}<br>
        Perf:{f1['perf']:.1f}-{f2['perf']:.1f}<br>
        1p:{h1}G | 1p:{a1}G<br>
        2p:{h2}G | 2p:{a2}G<br>
        {int(f1['hs'])}T {int(f1['hst'])}TP {int(f1['hf'])}F {int(f1['hc'])}C {int(f1['hy'])}A {int(f1['hr'])}R<br>
        {int(f2['hs'])}T {int(f2['hst'])}TP {int(f2['hf'])}F {int(f2['hc'])}C {int(f2['hy'])}A {int(f2['hr'])}R
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
AGENDA_FILE = 'agenda_apuestas.json'
def cargar_agenda():
    if os.path.exists(AGENDA_FILE):
        try:
            with open(AGENDA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"banca_inicial": 1000.0, "apuestas": data}
                return data
        except:
            return {"banca_inicial": 1000.0, "apuestas": []}
    return {"banca_inicial": 1000.0, "apuestas": []}

def guardar_agenda(data):
    with open(AGENDA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.fragment
def mostrar_agenda():
    with st.expander("🗓️ Agenda Apuestas", expanded=False):
        agenda_data = cargar_agenda()
        banca_inicial = st.number_input("💰 Banca inicial €", 0.0, 1000000.0,
                                       float(agenda_data.get("banca_inicial", 1000)), 10.0,
                                       key="banca_ini_frag")
        agenda_data["banca_inicial"] = banca_inicial
        apuestas = agenda_data.get("apuestas", [])

        tab_live, tab_comb, tab_pre = st.tabs(["LIVE", "COMBINADA", "PREPARTIDO"])

        def form_apuesta(tipo_agenda):
            with st.form(f"form_{tipo_agenda}", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                equipos = sorted(pd.unique(df[['HomeTeam','AwayTeam']].values.ravel()))
                eq1 = c1.selectbox("Local", [""] + equipos, key=f"eq1_{tipo_agenda}")
                eq2 = c2.selectbox("Visitante", [""] + equipos, key=f"eq2_{tipo_agenda}")

                liga = ""
                if eq1 and eq2:
                    m = df[((df['HomeTeam']==eq1)&(df['AwayTeam']==eq2))|((df['HomeTeam']==eq2)&(df['AwayTeam']==eq1))]
                    if not m.empty:
                        liga = m.sort_values('Date', ascending=False).iloc[0]['League']
                ligas = [""] + sorted(df['League'].unique())
                liga = c3.selectbox("Liga", ligas, index=ligas.index(liga) if liga in ligas else 0, key=f"liga_{tipo_agenda}")

                c4, c5, c6 = st.columns(3)
                cuota = c4.number_input("Cuota", 1.01, 100.0, 1.90, 0.01, key=f"cuota_{tipo_agenda}")
                stake = c5.number_input("Stake", 0.0, 10000.0, 10.0, 0.5, key=f"stake_{tipo_agenda}")
                minuto = c6.number_input("Min", 0, 120, 0, key=f"min_{tipo_agenda}")

                c7, c8 = st.columns([1,2])
                tipo_apuesta = c7.selectbox("Tipo", ["Over","Under","Hándicap","1X2","BTTS","Corners","Otro"], key=f"tap_{tipo_agenda}")
                detalle = c8.text_input("Detalle (ej: 0.5 1ª)", "", key=f"det_{tipo_agenda}")
                marcador = st.text_input("Marcador", "0-0", key=f"marc_{tipo_agenda}")

                if st.form_submit_button("💾 Guardar PENDIENTE"):
                    if eq1 and eq2:
                        apuestas.append({
                            "id": int(datetime.now().timestamp()*1000),
                            "fecha": datetime.now().strftime("%d/%m %H:%M"),
                            "tipo": tipo_agenda,
                            "partido": f"{eq1} vs {eq2}",
                            "liga": liga,
                            "tipo_apuesta": tipo_apuesta,
                            "cuota": cuota,
                            "stake": stake,
                            "marcador": marcador,
                            "detalle": detalle,
                            "minuto": minuto,
                            "resultado": "Pendiente",
                            "beneficio": 0
                        })
                        agenda_data["apuestas"] = apuestas
                        guardar_agenda(agenda_data)

        with tab_live: form_apuesta("LIVE")
        with tab_comb: form_apuesta("COMBINADA")
        with tab_pre: form_apuesta("PREPARTIDO")

        if apuestas:
            df_ag = pd.DataFrame(apuestas)
            banca_actual = banca_inicial + df_ag['beneficio'].sum()

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Banca", f"{banca_actual:.0f}€", f"{df_ag['beneficio'].sum():+.0f}€")
            c2.metric("Pend", len(df_ag[df_ag['resultado']=='Pendiente']))
            c3.metric("Ganadas", len(df_ag[df_ag['resultado']=='Ganada']))
            c4.metric("ROI", f"{df_ag['beneficio'].sum()/df_ag['stake'].sum()*100:.1f}%" if df_ag['stake'].sum()>0 else "0%")

            # === DASHBOARD EDGE ===
            with st.expander("📊 Ver dónde tengo edge", expanded=False):
                df_analisis = df_ag[df_ag['resultado']!= 'Pendiente'].copy()
                
                # FILTROS DINÁMICOS
                f1,f2,f3,f4 = st.columns(4)
                ligas_f = f1.multiselect("Liga", df_analisis['liga'].dropna().unique())
                tipos_f = f2.multiselect("Tipo", df_analisis.get('tipo_apuesta', pd.Series()).dropna().unique())
                res_f = f3.multiselect("Resultado", ["Ganada","Perdida"], default=["Ganada","Perdida"])
                txt_f = f4.text_input("Detalle contiene", placeholder="over, 1ª, corner")
                
                if ligas_f: df_analisis = df_analisis[df_analisis['liga'].isin(ligas_f)]
                if tipos_f: df_analisis = df_analisis[df_analisis['tipo_apuesta'].isin(tipos_f)]
                if res_f: df_analisis = df_analisis[df_analisis['resultado'].isin(res_f)]
                if txt_f: df_analisis = df_analisis[df_analisis['detalle'].str.contains(txt_f, case=False, na=False)]
                if not df_analisis.empty:
                    tab1, tab2, tab3 = st.tabs(["Por Liga", "Por Tipo", "Por Equipo"])
                    with tab1:
                        liga_stats = df_analisis.groupby('liga').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),L=('resultado', lambda x: (x=='Perdida').sum()),Stake=('stake','sum'),Benef=('beneficio','sum')).reset_index()
                        liga_stats['Win%'] = (liga_stats['W']/liga_stats['Ap']*100).round(0).astype(int)
                        liga_stats['ROI%'] = (liga_stats['Benef']/liga_stats['Stake']*100).round(1)
                        st.dataframe(liga_stats.sort_values('ROI%', ascending=False), hide_index=True, width='stretch', column_config={"liga":"Liga","Ap":"Ap","W":"✅","L":"❌","Win%":"%W","ROI%":"ROI","Benef":"€"})
                    with tab2:
                        tipo_stats = df_analisis.groupby('tipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum'),Stake=('stake','sum')).reset_index()
                        tipo_stats['ROI%'] = (tipo_stats['Benef']/tipo_stats['Stake']*100).round(1)
                        st.dataframe(tipo_stats.sort_values('ROI%', ascending=False), hide_index=True, width='stretch')
                    with tab3:
                        df_analisis['equipo'] = df_analisis['partido'].str.split(' vs ').str[0]
                        equipo_stats = df_analisis.groupby('equipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum')).reset_index()
                        equipo_stats = equipo_stats[equipo_stats['Ap']>=2]
                        equipo_stats['Win%'] = (equipo_stats['W']/equipo_stats['Ap']*100).round(0).astype(int)
                        st.dataframe(equipo_stats.sort_values('Benef', ascending=False).head(10), hide_index=True, width='stretch', column_config={"equipo":"Equipo","Ap":"Ap","W":"✅","Win%":"%W","Benef":"€"})
                else:
                    st.info("Cierra apuestas para ver stats")

            # LISTA RÁPIDA CON BORRADO INSTANTÁNEO
                        
            for ap in sorted(apuestas, key=lambda x: x['id'], reverse=True)[:50]:
                col1,col2,col3,col4 = st.columns([1.3,4.5,2.2,0.6])
                col1.caption(f"{ap['fecha']}")
                col2.write(f"**{ap['partido']}** {ap['marcador']} · **{ap.get('detalle','')}** · min {ap.get('minuto',0)}' · {ap.get('tipo','')}")
                col3.write(f"{ap['stake']}€ @ {ap['cuota']} → **{ap['resultado']}**")
                if col4.button("🗑️", key=f"del_{ap['id']}"):
                    # Borrado rápido sin rerun completo
                    agenda_data["apuestas"] = [a for a in apuestas if a['id']!= ap['id']]
                    guardar_agenda(agenda_data)

            # CERRAR APUESTAS - FUERA DEL BUCLE
            pend = [a for a in apuestas if a['resultado']=='Pendiente']
            if pend:
                opciones = {a['id']: f"{a['fecha']} | {a['partido']} ({a['marcador']}) - {a['stake']}€ @ {a['cuota']}" for a in pend}
                sel_id = st.selectbox("Cerrar apuesta", options=list(opciones.keys()),
                                     format_func=lambda x: opciones[x], key="sel_cerrar")

                col_r1, col_r2 = st.columns([1,2])
                res = col_r1.radio("Resultado", ["Ganada","Perdida","Nula"], horizontal=True, key="res_radio")

                if col_r2.button("💾 Guardar resultado", width='stretch', key="btn_guardar"):
                    for a in apuestas:
                        if a['id'] == sel_id:
                            a['resultado'] = res
                            if res == "Ganada":
                                a['beneficio'] = round((a['cuota']-1) * a['stake'], 2)
                            elif res == "Perdida":
                                a['beneficio'] = -a['stake']
                            else:
                                a['beneficio'] = 0
                            break
                    agenda_data["apuestas"] = apuestas
                    guardar_agenda(agenda_data)
            else:
                st.info("No hay pendientes")

# LLAMAR AL FRAGMENTO
mostrar_agenda()


################# filtro resumen
with st.expander("📋 Resumen", expanded=False):
    col_izq, col_der = st.columns(2)

    ligas_res = sorted(df['League'].unique())
    temps_res = sorted(df['Season'].unique())

    # FILA 1: Liga1 Liga2 - con multiselect
    liga1_res = col_izq.multiselect("Liga", ligas_res, default=[liga_sel[0]] if liga_sel else [], key="res_liga1")
    liga2_res = col_der.multiselect("Liga2", ligas_res, key="res_liga2")

    # FILA 2: Temp1 Temp2 - con multiselect
    temp1_res = col_izq.multiselect("Temporada", temps_res, default=[temp_sel[-1]] if temp_sel else [], key="res_temp1")
    temp2_res = col_der.multiselect("Temp2", temps_res, key="res_temp2")

    # FILA 3: Equipo1 Equipo2
    df_res_base1 = df[df['League'].isin(liga1_res) & df['Season'].isin(temp1_res)] if liga1_res and temp1_res else pd.DataFrame()
    equipos_res1 = sorted(pd.unique(df_res_base1[['HomeTeam','AwayTeam']].values.ravel())) if not df_res_base1.empty else []
    equipo_res = col_izq.selectbox("Equipo", [""] + equipos_res1, key="res_equipo1")

    equipos_res2 = []
    if liga2_res and temp2_res:
        df_res_base2 = df[df['League'].isin(liga2_res) & df['Season'].isin(temp2_res)]
        equipos_res2 = sorted(pd.unique(df_res_base2[['HomeTeam','AwayTeam']].values.ravel()))
    equipo2_res = col_der.selectbox("Equipo2", [""] + equipos_res2, key="res_equipo2")

    def calcular_stats_equipo(df_res_base, equipo_res, temps_res):
        if not equipo_res or df_res_base.empty:
            return None

        df_res, df_clas_res = calcular_estado_jornada(df_res_base)
        df_eq_total = df_res[(df_res['HomeTeam']==equipo_res) | (df_res['AwayTeam']==equipo_res)].copy()

        if df_eq_total.empty:
            return None

        lista_stats = []
        temps_ordenadas = sorted(temps_res, reverse=True)

        for temp in temps_ordenadas:
            df_eq = df_eq_total[df_eq_total['Season']==temp].copy()
            if df_eq.empty:
                continue

            total = len(df_eq)
            es_local = df_eq['HomeTeam']==equipo_res

            gana = ((es_local) & (df_eq['FTHG']>df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']>df_eq['FTHG']))
            pierde = ((es_local) & (df_eq['FTHG']<df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']<df_eq['FTHG']))
            empata = ~(gana | pierde)

            n_g, n_e, n_p = gana.sum(), empata.sum(), pierde.sum()
            pct_g, pct_e, pct_p = round(n_g/total*100), round(n_e/total*100), round(n_p/total*100)

            gf = np.where(es_local, df_eq['FTHG'], df_eq['FTAG'])
            gc = np.where(es_local, df_eq['FTAG'], df_eq['FTHG'])
            gf_tot, gc_tot = gf.sum(), gc.sum()
            gf_avg, gc_avg = round(gf.mean(),2), round(gc.mean(),2)

            hs = np.where(es_local, df_eq['HS'], df_eq['AS'])
            hst = np.where(es_local, df_eq['HST'], df_eq['AST'])
            hf = np.where(es_local, df_eq['HF'], df_eq['AF'])
            hc = np.where(es_local, df_eq['HC'], df_eq['AC'])
            hy = np.where(es_local, df_eq['HY'], df_eq['AY'])
            hr = np.where(es_local, df_eq['HR'], df_eq['AR'])

            am = ((gf > 0) & (gc > 0)).sum()
            over25 = (gf + gc > 2.5).sum()

            racha_actual = 0
            mejor_racha = 0
            for res in np.where(gana, 'G', np.where(pierde, 'P', 'E')):
                if res == 'G':
                    racha_actual += 1
                    mejor_racha = max(mejor_racha, racha_actual)
                else:
                    racha_actual = 0

            df_clas_temp = df_clas_res[(df_clas_res['Equipo']==equipo_res) & (df_clas_res['Season']==temp)]
            if not df_clas_temp.empty:
                ult_j = df_clas_temp['Jornada'].max()
                fila_final = df_clas_temp[df_clas_temp['Jornada']==ult_j].iloc[0]
                pos_final = int(fila_final['Pos'])
                pts_final = int(fila_final['Pts'])
            else:
                pos_final = 0
                pts_final = 0

            ult5 = ''.join(['G' if g else 'P' if p else 'E' for g,p in zip(gana.tail(5), pierde.tail(5))])
            jors_html = jornadas_conteo(df_eq['Jornada'], df_eq, equipo_res, None)

            lista_stats.append({
                'temp': temp, 'total': total, 'n_g': n_g, 'n_e': n_e, 'n_p': n_p,
                'pct_g': pct_g, 'pct_e': pct_e, 'pct_p': pct_p,
                'gf_tot': gf_tot, 'gc_tot': gc_tot, 'gf_avg': gf_avg, 'gc_avg': gc_avg,
                'am': am, 'over25': over25, 'hs': hs.mean(), 'hst': hst.mean(),
                'hf': hf.mean(), 'hc': hc.mean(), 'hy': hy.mean(), 'hr': hr.mean(),
                'mejor_racha': mejor_racha, 'ult5': ult5, 'pos_final': pos_final,
                'pts_final': pts_final, 'jors_html': jors_html, 'equipo': equipo_res
            })

        return lista_stats, df_clas_res, df_eq_total

    if st.button("🔍 Buscar resumen", type="primary", width='stretch', key="btn_resumen"):
        if not equipo_res:
            st.warning("Selecciona al menos Equipo")
        else:
            # Equipo 1 - ya son listas, no hace falta convertir
            stats1 = calcular_stats_equipo(df_res_base1, equipo_res, temp1_res)

            # Equipo 2 si existe
            stats2 = None
            if equipo2_res and liga2_res and temp2_res:
                df_res_base2 = df[df['League'].isin(liga2_res) & df['Season'].isin(temp2_res)]
                stats2 = calcular_stats_equipo(df_res_base2, equipo2_res, temp2_res)

            if not stats1:
                st.warning(f"{equipo_res} no tiene partidos en esa selección")
            else:
                lista_stats1, df_clas_res1, df_eq_total1 = stats1

                # === MINI RESUMEN EQ1 ===
                if lista_stats1:
                    filas = []
                    for s in lista_stats1: # Recorro todas las temps seleccionadas
                        df_temp = df_eq_total1[(df_eq_total1['Season']==s['temp'])].copy()
                        if df_temp.empty:
                            continue
                        es_local = df_temp['HomeTeam']==equipo_res
                        gana = ((es_local) & (df_temp['FTHG']>df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']>df_temp['FTHG']))
                        pierde = ((es_local) & (df_temp['FTHG']<df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']<df_temp['FTHG']))
                        empata = ~(gana | pierde)

                        g = int(gana.sum())
                        e = int(empata.sum())
                        p = int(pierde.sum())
                        pts = g*3 + e

                        dft = df_clas_res1[(df_clas_res1['Equipo']==equipo_res) & (df_clas_res1['Season']==s['temp'])]
                        if not dft.empty:
                            ult_jornada = dft.sort_values('Jornada').iloc[-1]
                            pos = int(ult_jornada['Pos'])
                        else:
                            pos = 0

                        linea = f"<div style='font-size:10px; font-family:monospace; line-height:1.2'><b>{equipo_res.title()}</b> {s['temp']}: <b>{pos}º</b> {pts}pts | <span style='color:#15803d'>{g}G</span> <span style='color:#000000'>{e}E</span> <span style='color:#b91c1c'>{p}P</span></div>"
                        filas.append(linea)

                    st.caption(f"Resumen {equipo_res}")
                    st.markdown("\n".join(filas), unsafe_allow_html=True)

                # === MINI RESUMEN EQ2 SI EXISTE ===
                if stats2:
                    lista_stats2, df_clas_res2, df_eq_total2 = stats2
                    filas2 = []
                    for s in lista_stats2:
                        df_temp = df_eq_total2[(df_eq_total2['Season']==s['temp'])].copy()
                        if df_temp.empty:
                            continue
                        es_local = df_temp['HomeTeam']==equipo2_res
                        gana = ((es_local) & (df_temp['FTHG']>df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']>df_temp['FTHG']))
                        pierde = ((es_local) & (df_temp['FTHG']<df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']<df_temp['FTHG']))
                        empata = ~(gana | pierde)

                        g = int(gana.sum())
                        e = int(empata.sum())
                        p = int(pierde.sum())
                        pts = g*3 + e

                        dft = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season']==s['temp'])]
                        if not dft.empty:
                            ult_jornada = dft.sort_values('Jornada').iloc[-1]
                            pos = int(ult_jornada['Pos'])
                        else:
                            pos = 0

                        linea = f"<div style='font-size:10px; font-family:monospace; line-height:1.2'><b>{equipo2_res.title()}</b> {s['temp']}: <b>{pos}º</b> {pts}pts | <span style='color:#15803d'>{g}G</span> <span style='color:#000000'>{e}E</span> <span style='color:#b91c1c'>{p}P</span></div>"
                        filas2.append(linea)

                    st.caption(f"Resumen {equipo2_res}")
                    st.markdown("\n".join(filas2), unsafe_allow_html=True)

                # === GRÁFICA POSICIÓN vs JORNADA - COLORES POR TEMPORADA ===
                import matplotlib.pyplot as plt
                import matplotlib.colors as mcolors
                
                # Paleta con contraste bueno
                PALETA = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#e377c2', '#17becf', '#bcbd22', '#8c564b', '#000000']
                
                df_graf1 = df_clas_res1[(df_clas_res1['Equipo']==equipo_res) & (df_clas_res1['Season'].isin(temp1_res))]

                fig = plt.figure(figsize=(5, 2.8), dpi=150)
                ax = fig.add_subplot(111)
                
                leyendas = []
                max_pos = 0

                # Equipo 1 - un color distinto por temporada
                for idx, temp in enumerate(temp1_res):
                    d = df_graf1[df_graf1['Season']==temp].sort_values('Jornada')
                    if not d.empty:
                        color = PALETA[idx % len(PALETA)]
                        line, = ax.plot(d['Jornada'], d['Pos'], linewidth=1.4, linestyle='-', color=color, alpha=0.95)
                        max_pos = max(max_pos, d['Pos'].max())
                        color_hex = mcolors.to_hex(line.get_color())
                        leyendas.append(f"<span style='color:{color_hex}; font-size:14px'>—</span> {equipo_res} {temp}")

                # Equipo 2 - sigue la paleta para no repetir colores
                if stats2:
                    df_graf2 = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season'].isin(temp2_res))]
                    for idx, temp in enumerate(temp2_res):
                        d = df_graf2[df_graf2['Season']==temp].sort_values('Jornada')
                        if not d.empty:
                            color = PALETA[(len(temp1_res) + idx) % len(PALETA)]
                            # Eq2 con linea discontinua para diferenciar equipos
                            line, = ax.plot(d['Jornada'], d['Pos'], linewidth=1.4, linestyle='--', color=color, alpha=0.95)
                            max_pos = max(max_pos, d['Pos'].max())
                            color_hex = mcolors.to_hex(line.get_color())
                            leyendas.append(f"<span style='color:{color_hex}; font-size:14px'>--</span> {equipo2_res} {temp}")
                        max_pos = max(max_pos, d['Pos'].max())
                        color_hex = mcolors.to_hex(line.get_color())
                        leyendas.append(f"<span style='color:{color_hex}; font-size:14px'>—</span> {equipo_res} {temp}")

                # Equipo 2 - linea naranja fina lisa (ANTES ERA -- AHORA -)
                if stats2:
                    df_graf2 = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season'].isin(temp2_res))]
                    for temp in temp2_res:
                        d = df_graf2[df_graf2['Season']==temp].sort_values('Jornada')
                        if not d.empty:
                            line, = ax.plot(d['Jornada'], d['Pos'], linewidth=1.2, linestyle='-', color='#ff7f0e', alpha=0.9)
                            max_pos = max(max_pos, d['Pos'].max())
                            color_hex = mcolors.to_hex(line.get_color())
                            leyendas.append(f"<span style='color:{color_hex}; font-size:14px'>—</span> {equipo2_res} {temp}")

                # Eje invertido 1º arriba
                ax.invert_yaxis()
                ax.set_ylim(max_pos + 1, 0.5)
                ax.set_xlabel("Jornada", fontsize=8)
                ax.set_ylabel("Posición", fontsize=8)
                ax.set_xticks(range(1, 39, 2))
                ax.set_yticks(range(1, int(max_pos)+2))
                ax.grid(True, alpha=0.25, linestyle=':', linewidth=0.5)
                ax.tick_params(labelsize=7)
                plt.tight_layout(pad=0.3)
                st.pyplot(fig, use_container_width=True)
                plt.close()
                
                if leyendas:
                    st.markdown("<div style='font-size:10px; line-height:1.4; margin-top:4px'>" + " &nbsp; ".join(leyendas) + "</div>", unsafe_allow_html=True)
                # === TARJETAS DETALLADAS EQ1 ===
                for i, s in enumerate(lista_stats1):
                    st.markdown(f"""
                    <div style='background:#f8f9fa;padding:8px 10px;border-left:4px solid #0A2342;margin:6px 0;font-family:monospace;font-size:10px;line-height:1.4'>
                    <b style='font-size:12px'>{s['equipo'].title()} | {s['temp']}</b><br>
                    <b>{s['total']}PJ</b> → <span style='color:#0f8105;font-weight:900'>{s['n_g']}G {s['pct_g']}%</span> |
                    <span style='color:#b45309;font-weight:900'>{s['n_e']}E {s['pct_e']}%</span> |
                    <span style='color:#dc2626;font-weight:900'>{s['n_p']}P {s['pct_p']}%</span><br>
                    <b>Goles:</b> {s['gf_tot']}GF {s['gc_tot']}GC | Prom: {s['gf_avg']}-{s['gc_avg']} | AM:{s['am']}/{s['total']} ({round(s['am']/s['total']*100)}%) | Over2.5:{s['over25']}/{s['total']} ({round(s['over25']/s['total']*100)}%)<br>
                    <b>Stats:</b> {s['hs']:.1f}T {s['hst']:.1f}TP {s['hf']:.1f}F {s['hc']:.1f}C {s['hy']:.1f}A {s['hr']:.1f}R<br>
                    <b>Racha:</b> Mejor {s['mejor_racha']}G | Últ5: {s['ult5']}<br>
                    <b>Pos final:</b> {s['pos_final']}º | <b>Pts final:</b> {s['pts_final']}<br>
                    <b>Jornadas:</b> {s['jors_html']}
                    </div>
                    """, unsafe_allow_html=True)

                # === TARJETAS DETALLADAS EQ2 SI EXISTE ===
                if stats2:
                    lista_stats2, _, _ = stats2
                    for i, s in enumerate(lista_stats2):
                        st.markdown(f"""
                        <div style='background:#e0f2fe;padding:10px 12px;border-left:4px solid #0369a1;margin:8px 0;font-family:monospace;font-size:12px;line-height:1.6'>
                        <b style='font-size:14px'>{s['equipo'].title()} | {s['temp']}</b><br>
                        <b>{s['total']}PJ</b> → <span style='color:#0f8105;font-weight:900'>{s['n_g']}G {s['pct_g']}%</span> |
                        <span style='color:#b45309;font-weight:900'>{s['n_e']}E {s['pct_e']}%</span> |
                        <span style='color:#dc2626;font-weight:900'>{s['n_p']}P {s['pct_p']}%</span><br>
                        <b>Goles:</b> {s['gf_tot']}GF {s['gc_tot']}GC | Prom: {s['gf_avg']}-{s['gc_avg']} | AM:{s['am']}/{s['total']} ({round(s['am']/s['total']*100)}%) | Over2.5:{s['over25']}/{s['total']} ({round(s['over25']/s['total']*100)}%)<br>
                        <b>Stats:</b> {s['hs']:.1f}T {s['hst']:.1f}TP {s['hf']:.1f}F {s['hc']:.1f}C {s['hy']:.1f}A {s['hr']:.1f}R<br>
                        <b>Racha:</b> Mejor {s['mejor_racha']}G | Últ5: {s['ult5']}<br>
                        <b>Pos final:</b> {s['pos_final']}º | <b>Pts final:</b> {s['pts_final']}<br>
                        <b>Jornadas:</b> {s['jors_html']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        ##############FIN APP
