import re
import unicodedata
import streamlit as st

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔒 App Privada")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Entrar"):
            # La contraseña está en Secrets, no en el código
            if pwd == st.secrets.get("PASSWORD"):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Incorrecta")
        st.stop()

check_password()
import os
import pathlib
import json



st.set_page_config(
    page_title="Filtro Jornada",
    layout="wide",
    initial_sidebar_state="collapsed"
)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt # type: ignore
from functools import lru_cache
from datetime import datetime
import subprocess
import sys
import time
import streamlit.components.v1 as components

LOG_FILE = str(pathlib.Path(__file__).parent / "descarga_log.txt")
PERSIST_FILE = str(pathlib.Path(__file__).parent / "filtros_guardados.json")
def log_terminal(msg):
    try:
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        if 'terminal_lines' not in st.session_state:
            st.session_state.terminal_lines = []
        st.session_state.terminal_lines.append(line)
        st.session_state.terminal_lines = st.session_state.terminal_lines[-100:]
    except:
        pass

# FIX MOVIL SEGURO - V2 no peta persistencia
try:
    if "filtro_liga_main" in st.query_params:
        val = str(st.query_params.get("filtro_liga_main", ""))
        if any(x in val for x in ["B1","D1","E0","SC0","SP1","N1","P1","F1","I1","T1"]):
            st.query_params.clear()
            if os.path.exists(PERSIST_FILE):
                try:
                    os.remove(PERSIST_FILE)
                except:
                    pass
except:
    pass

#####################################################################################
##########Claro, aquí están tus límites con el Plan PRO:
##########📊 Por minuto: 300 solicitudes/minuto 📊 Por día: 7,500 solicitudes/día
##########Recuerda que:
##############################El límite diario se reinicia cada día a las 00:00 UTC
##########Si alcanzas el límite de 300 solicitudes por minuto, recibirás un mensaje de error en lugar de los datos solicitados
##########Puedes rastrear tu uso en cualquier momento desde el dashboard o revisando el header x-ratelimit-requests-remaining en cada respuesta de la API


st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)
#############################css visualizacion filtros avanzados columnas todo centrado y bien - 1 SOLO CARTEL
st.markdown("""
<style>
html, body { background: #FFFFFF!important; overflow-x: hidden!important; }
[data-testid="stAppViewContainer"]{ background-color: #FFFFFF!important; }
[data-testid="stDeployButton"],[data-testid="stToolbar"],#MainMenu,footer{display:none!important}
.block-container{padding:3rem 10px .5rem 10px!important; max-width:100%!important}
div[data-testid="stExpanderDetails"]{ padding:6px 4px!important; }
div[data-testid="stExpander"] [data-testid="stHorizontalBlock"]{
  display: grid!important;
  grid-template-columns: repeat(3, minmax(0, 1fr))!important;
  gap: 6px!important;
  width: 100%!important;
}
div[data-testid="stExpander"] [data-testid="stHorizontalBlock"] > div{
  width: 100%!important; min-width: 0!important; max-width: none!important; flex: none!important;
}
###tamaño letra desplegables filtros avanzados#####
div[data-testid="stExpander"] [data-testid="stWidgetLabel"] p{
  font-size: 13px!important; margin: 0 0 1px 0!important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>
""", unsafe_allow_html=True)
#############################css visualizacion filtros avanzados columnas todo centrado y bien FIN


# --- LIMPIEZA FORZADA DE CACHE VIEJO --- (ahora con botón)

def normaliza(nombre: str) -> str:
    # quita acentos, pasa a mayúsculas, limpia espacios
    n = unicodedata.normalize('NFKD', str(nombre))
    n = n.encode('ASCII', 'ignore').decode('ASCII')
    n = n.upper().strip()
    n = re.sub(r'\s+', ' ', n)
    # FIX PUZZLE GOLES - B = II
    n = n.replace("REAL SOCIEDAD B", "REAL SOCIEDAD II")
    n = n.replace("CELTA DE VIGO B", "CELTA DE VIGO II")
    n = n.replace("SOC B", "REAL SOCIEDAD II")
    n = n.replace("RSO B", "REAL SOCIEDAD II")
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



def persistir():
    try:
        # guarda solo lo serializable - FIX DEFINITIVO no guardar NINGUN boton (bool)
        data = {}
        for k, v in st.session_state.items():
            if k.startswith("FormSubmitter"): continue
            if k.startswith("terminal_lines"): continue
            if k.startswith("ultima_descarga"): continue
            if k.startswith("pausa_descarga"): continue
            if k.startswith("btn_"): continue
            if k.startswith("btn"): continue
            if "btn_" in k: continue
            if k == "be2_buscar": continue
            if k.startswith("be2_buscar"): continue
            if k.endswith("_buscar"): continue
            if k == "ca_gen": continue
            if k.startswith("ca_gen"): continue
            if k.startswith("ca_") and isinstance(v, bool): continue
            if k.startswith("be2_") and isinstance(v, bool): continue
            if isinstance(v, bool): continue
            try:
                json.dumps(v)
                data[k] = v
            except:
                pass
        with open(PERSIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except:
        pass

def cargar_persistencia():
    try:
        if os.path.exists(PERSIST_FILE):
            with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k in st.session_state: continue
                    if "buscar" in k.lower(): continue
                    if k.startswith("btn_") or k.startswith("btn"): continue
                    if k.startswith("ca_") and isinstance(v, bool): continue
                    if k.startswith("be2_") and isinstance(v, bool): continue
                    if k.endswith("_buscar"): continue
                    if isinstance(v, bool): continue
                    if k.startswith("FormSubmitter"): continue
                    try:
                        st.session_state[k] = v
                    except:
                        pass
    except:
        pass
    # limpieza extra por si quedó el bool en memoria del movil
    for kk in list(st.session_state.keys()):
        if "buscar" in kk.lower() and isinstance(st.session_state.get(kk), bool):
            try:
                del st.session_state[kk]
            except:
                pass

cargar_persistencia()

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
        base_html = _formatear_h2h_compacto_cached(key)
        # NUEVO: añade goles con minuto/jugador/asistente si hay eventos cargados
        try:
            if 'todos_eventos' in globals() and todos_eventos:
                goles = buscar_goles_partido(row, todos_eventos, 0, 120, "Todo", equipo_ref)
                if goles:
                    base_html = base_html.replace("</div>", f"<div style='font-size:10px;color:#000;line-height:1.2;margin-top:3px;border-top:1px dashed #999;padding-top:2px'>{goles}</div></div>")
        except:
            pass
        return base_html
    except Exception:
        return "<div style='font-size:10px'>-</div>"
##################### FIN H2H UNICO #####################

# --- PRIMERA jornadas_conteo SIMPLE ELIMINADA - SE QUEDA LA FINAL CON RE ---


def racha_comprimida_html(df_team, equipo):
    if df_team.empty:
        return ""
    df_team = df_team.drop_duplicates(subset=['Date','HomeTeam','AwayTeam']).sort_values('Date')
    res = []
    for _, r in df_team.iterrows():
        is_home = r['HomeTeam'] == equipo
        hg, ag = int(r['FTHG']), int(r['FTAG'])
        if is_home:
            res.append('G' if hg>ag else 'P' if hg<ag else 'E')
        else:
            res.append('G' if ag>hg else 'P' if ag<hg else 'E')
    if not res:
        return ""
    comp = []
    cnt = 1
    for i in range(1, len(res)):
        if res[i]==res[i-1]: cnt+=1
        else: comp.append((cnt,res[i-1])); cnt=1
    comp.append((cnt,res[-1]))
    sep = "<span style='color:#bbb;font-size:11px;margin:0 3px'>|</span>"
    parts = []
    for c, letra in comp:
        col = "#0f8105" if letra=='G' else "#f31818" if letra=='P' else "#0A2342"
        parts.append(f"<span style='color:{col};font-weight:700;font-size:11px;line-height:1.1'>{c}{letra}</span>")
    # FIX: inline y nowrap para que no se rompa en vertical
    return f"<span style='display:inline;white-space:nowrap'>{sep.join(parts)}</span>"
############################################
def racha_ambos_marcan_html(df_team):
    if df_team.empty:
        return ""
    df_team = df_team.drop_duplicates(subset=['Date','HomeTeam','AwayTeam']).sort_values('Date')
    res = ['si' if int(r['FTHG'])>0 and int(r['FTAG'])>0 else 'no' for _,r in df_team.iterrows()]
    if not res:
        return ""
    comp = []
    cnt=1
    for i in range(1,len(res)):
        if res[i]==res[i-1]: cnt+=1
        else: comp.append(f"{cnt}{res[i-1]}"); cnt=1
    comp.append(f"{cnt}{res[-1]}")
    sep = "<span style='color:#bbb;font-size:11px;margin:0 3px'>|</span>"
    inner = []
    for x in comp:
        inner.append(f"<span style='font-size:11px;font-weight:700;color:#000;line-height:1.1'>{x}</span>")
    return f"<span style='display:inline;white-space:nowrap'>{sep.join(inner)}</span>"
    ##############
# --- PRIMER EXPANDER DUPLICADO ELIMINADO - SE MANTIENE SOLO FINAL UNICO ---
#################script
# BLOQUE LIMPIO - PEGA ESTO DONDE ESTABA TU EXPANDER DUPLICADO

with st.expander("⚙ Opciones avanzadas"):
    if 'pausa_descarga' not in st.session_state:
        st.session_state.pausa_descarga = False
    if 'ultima_descarga' not in st.session_state:
        st.session_state.ultima_descarga = None
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("⏸ Pausa", use_container_width=True, key="btn_pausa_global_widget"):
            st.session_state.pausa_descarga = True
            st.toast("Pausando tras este partido...")
    with col_p2:
        if st.button("▶ Continuar", use_container_width=True, key="btn_continua_global"):
            st.session_state.pausa_descarga = False
            if st.session_state.ultima_descarga == "2627":
                st.session_state["accion_continuar_2627"] = True
            elif st.session_state.ultima_descarga == "2226":
                st.session_state["accion_continuar_2226"] = True
            elif st.session_state.ultima_descarga == "especificas":
                st.session_state["accion_continuar_especificas"] = True
            st.rerun()
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🧹 Borrar cache / cookies (40kb)", use_container_width=True, key="btn_borrar_cache_final_unico"):
            if os.path.exists("filtros_guardados.json"):
                try:
                    os.remove("filtros_guardados.json")
                except:
                    pass
            for root, dirs, files in os.walk('.', topdown=False):
                for name in dirs:
                    if name == '__pycache__':
                        try:
                            import shutil
                            shutil.rmtree(os.path.join(root, name))
                        except:
                            pass
            st.query_params.clear()
            try:
                st.cache_data.clear()
            except:
                pass
            try:
                st.cache_resource.clear()
            except:
                pass
            st.rerun()
    with col_b:
        trigger_2627 = st.session_state.pop("accion_continuar_2627", False)
        if trigger_2627 or st.button("🔄 Actualizar 26/27", use_container_width=True, key="btn_2627_final_unico"):
            st.toast("Usa el botón de abajo FIX TOTAL")
            st.rerun()
    with col_c:
        trigger_2226 = st.session_state.pop("accion_continuar_2226", False)
        if trigger_2226 or st.button("⬇ BAJAR LIGAS ESPECIFICAS", use_container_width=True, key="btn_especificas_final_unico"):
            st.toast("Usa el botón de abajo")
            st.rerun()



    trigger_esp = st.session_state.pop("accion_continuar_especificas", False)
    if trigger_esp or st.button("Generar partido", key="ca_gen_especificas", use_container_width=True):
        import requests as _req2
        try:
            API_KEY2 = str(st.secrets["API_KEY"]).strip()
        except:
            st.error("Falta API_KEY en Secrets")
            st.stop()
        def _check_quota():
            try:
                rr = _req2.get("https://v3.football.api-sports.io/status", headers={"x-apisports-key": API_KEY2}, timeout=15)
                if rr.status_code == 200:
                    j = rr.json()
                    gastadas = j.get('response',{}).get('requests',{}).get('current', 0)
                    limite = j.get('response',{}).get('requests',{}).get('limit_day', 7500)
                    return int(limite - gastadas)
                h = rr.headers.get('x-ratelimit-requests-remaining')
                if h is not None: return int(str(h).strip())
            except: pass
            return 7500
        _quedan = _check_quota()
        if _quedan < 100:
            st.error(f"⛔ No hay respuestas. Te quedan {_quedan}/7500. Resetea a las 02:00 hora Madrid.")
            st.stop()
        MAPA_ESPECIFICAS = {"K League 1":292,"K League 2":293,"J1 League":98,"J2 League":99,"Saudi Professional League":307,"Bundesliga":78,"2. Liga":79,"Jupiler Pro League":144,"Challenger Pro League":145,"Super League":207,"Challenge League":208,"UAE League":301,"League One":46}
        TEMPORADAS = [2022,2023,2024,2025,2026]
        req2=[0]; prog2=st.progress(0); should_stop=False
        df_base2 = pd.read_csv("ligas_2122_a_2627_SIN_DUPLICADOS.csv", on_bad_lines='skip', engine='python') if os.path.exists("ligas_2122_a_2627_SIN_DUPLICADOS.csv") else pd.DataFrame()
        existentes=set()
        if not df_base2.empty:
            try:
                d=df_base2.copy(); d["Date"]=pd.to_datetime(d["Date"], dayfirst=True, errors='coerce').dt.strftime("%d/%m/%Y"); d["HomeTeam"]=d["HomeTeam"].apply(normaliza); d["AwayTeam"]=d["AwayTeam"].apply(normaliza); d["League"]=d.get("League", pd.Series([""]*len(d))).astype(str); d["Season"]=d.get("Season", pd.Series([""]*len(d))).astype(str)
                for _, r in d.iterrows():
                    if float(r.get('HS',0))==0 and float(r.get('B365H',0))==0: continue
                    existentes.add((r["Date"], r["HomeTeam"], r["AwayTeam"], r["League"], r["Season"]))
            except: pass
        nuevos=[]
        st.session_state.ultima_descarga = "especificas"
        total=len(MAPA_ESPECIFICAS)*len(TEMPORADAS); step=0
        for nom, lid in MAPA_ESPECIFICAS.items():
            if should_stop: break
            for y in TEMPORADAS:
                if req2[0]>=7400: should_stop=True; break
                step+=1; prog2.progress(step/total, text=f"{nom} {y} {req2[0]}/7500")
                try:
                    time.sleep(0.35); r=_req2.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": API_KEY2}, params={"league": lid, "season": y}, timeout=30); req2[0]+=1
                    if r.status_code!=200: continue
                    fixtures=r.json().get("response", [])
                except: continue
                for fx in fixtures:
                    if st.session_state.get('pausa_descarga'):
                        if nuevos:
                            pd.DataFrame(nuevos).to_csv("ligas_2122_a_2627_SIN_DUPLICADOS.csv", mode='a', header=not os.path.exists("ligas_2122_a_2627_SIN_DUPLICADOS.csv") or os.path.getsize("ligas_2122_a_2627_SIN_DUPLICADOS.csv")==0, index=False); nuevos=[]
                        st.warning("⏸ Pausado"); st.stop()
                    if fx["fixture"]["status"]["short"] not in ["FT","AET","PEN"]: continue
                    date_str=pd.to_datetime(fx["fixture"]["date"][:10]).strftime("%d/%m/%Y"); home=normaliza(fx["teams"]["home"]["name"]); away=normaliza(fx["teams"]["away"]["name"]); season_str=f"{y}/{y+1}"
                    if (date_str, home, away, nom, season_str) in existentes: continue
                    ft_h=fx["goals"]["home"] or 0; ft_a=fx["goals"]["away"] or 0; ht_h=fx["score"]["halftime"]["home"] or 0; ht_a=fx["score"]["halftime"]["away"] or 0; ftr="H" if ft_h>ft_a else "A" if ft_a>ft_h else "D"
                    row={"Date":date_str,"League":nom,"Season":season_str,"HomeTeam":home,"AwayTeam":away,"FTHG":ft_h,"FTAG":ft_a,"HTHG":ht_h,"HTAG":ht_a,"FTR":ftr,"B365H":0,"B365D":0,"B365A":0,"HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0}
                    try:
                        time.sleep(0.35); rs=_req2.get("https://v3.football.api-sports.io/fixtures/statistics", headers={"x-apisports-key": API_KEY2}, params={"fixture": fx["fixture"]["id"]}, timeout=20); req2[0]+=1
                        if rs.status_code==200 and len(rs.json().get("response",[]))==2:
                            for j, td in enumerate(rs.json()["response"]):
                                sd={s["type"]: s["value"] for s in td["statistics"] if s["value"] is not None}
                                if j==0: row["HS"]=sd.get("Total Shots",0) or 0; row["HST"]=sd.get("Shots on Goal",0) or 0; row["HF"]=sd.get("Fouls",0) or 0; row["HC"]=sd.get("Corner Kicks",0) or 0; row["HY"]=sd.get("Yellow Cards",0) or 0; row["HR"]=sd.get("Red Cards",0) or 0
                                else: row["AS"]=sd.get("Total Shots",0) or 0; row["AST"]=sd.get("Shots on Goal",0) or 0; row["AF"]=sd.get("Fouls",0) or 0; row["AC"]=sd.get("Corner Kicks",0) or 0; row["AY"]=sd.get("Yellow Cards",0) or 0; row["AR"]=sd.get("Red Cards",0) or 0
                    except: pass
                    if row["HS"]==0 and row["HST"]==0 and row["HC"]==0:
                        continue
                    try:
                        time.sleep(0.35); ro=_req2.get("https://v3.football.api-sports.io/odds", headers={"x-apisports-key": API_KEY2}, params={"fixture": fx["fixture"]["id"], "bookmaker": 8}, timeout=20); req2[0]+=1
                        if ro.status_code==200:
                            resp=ro.json().get("response",[])
                            if resp and resp[0].get("bookmakers"):
                                for bet in resp[0]["bookmakers"][0].get("bets",[]):
                                    if bet["name"]=="Match Winner":
                                        for val in bet["values"]:
                                            if val["value"]=="Home": row["B365H"]=float(val["odd"])
                                            elif val["value"]=="Draw": row["B365D"]=float(val["odd"])
                                            elif val["value"]=="Away": row["B365A"]=float(val["odd"])
                    except: pass
                    nuevos.append(row)
        if nuevos:
            pd.DataFrame(nuevos).to_csv("ligas_2122_a_2627_SIN_DUPLICADOS.csv", mode='a', header=not os.path.exists("ligas_2122_a_2627_SIN_DUPLICADOS.csv") or os.path.getsize("ligas_2122_a_2627_SIN_DUPLICADOS.csv")==0, index=False)
        st.success(f"✅ ESPECIFICAS {req2[0]}/7500 - {len(nuevos)} partidos completos guardados")
        st.cache_data.clear()
        st.rerun()
#####
#######
###################################################################################################
##################################ligas

def esta_completo_row(row_dict):
    try:
        # Solo exige totales, 1P/2P opcional en 26/27 porque API no lo da aun
        if int(row_dict.get('HS',0) or 0)==0 and int(row_dict.get('HC',0) or 0)==0:
            return False, ['sin_stats']
        return True, []
    except:
        return False, ['error']

# push_csv_a_github ELIMINADO - SOLO LOCAL
####################3expander descargas 26 27###########################################################################################################
#############################################
####################3expander descargas 26 27###########################################################################################################
#############################################
####################3expander descargas 26 27###########################################################################################################
#############################################
######################3expander de botones

with st.expander("📥 Descargas 26/27 - FIX + AUTO GITHUB", expanded=False):

    if 'pausa_2627' not in st.session_state: st.session_state.pausa_2627 = False
    col_pause, col_cont = st.columns(2)
    with col_pause:
        if st.button("⏸ Pausar 26/27", use_container_width=True, key="btn_pausar_2627_fix"):
            st.session_state.pausa_2627 = True
            st.toast("Se pausará al terminar este partido")
    with col_cont:
        if st.button("▶ Continuar 26/27", use_container_width=True, key="btn_continuar_2627_fix"):
            st.session_state.pausa_2627 = False
            st.toast("Continuando...")
            st.rerun()
#############################
#############################
#############3boton europa 2627
if st.button("🏆 GRANDES 1ª EUROPA 26/27 - FIX", use_container_width=True, key="btn_grandes_1a_2627"):
    import requests as _req, time, pathlib, pandas as pd, os, json
    try:
        API_KEY = str(st.secrets["API_KEY"]).strip()
    except:
        st.error("Falta API_KEY"); st.stop()

    TEMPORADA = 2026
    BASE = pathlib.Path(r"C:\Users\toshiba\Desktop\APP_FUTBOL")
    BASE.mkdir(parents=True, exist_ok=True)
    FILE_CUR = BASE / "partidos_2627_actual.csv"
    FILE_GOLES = BASE / "goles_2627_actual.csv"
    PROG_FILE = BASE / "progreso_grandes_1a.json"

    MAPA_GRANDES_1A = {
        "Premier League": 39, "LaLiga EA Sports": 140, "Bundesliga": 78,
        "Serie A Italia": 135, "Ligue 1": 61, "Eredivisie": 88,
        "Liga Portugal": 94, "Jupiler Pro League": 144, "Süper Lig": 203,
        "Super League": 207, "Superliga Dinamarca": 119, "Premiership Escocia": 179,
        "Bundesliga Austria": 218, "Allsvenskan Suecia": 113,
        # === NUEVAS QUE PIDES ===
        "Super League Grecia": 197,
        "Championship Inglaterra": 40,
        "2. Bundesliga Alemania": 79,
    }

    if 'normaliza' not in globals():
        def normaliza(s):
            import unicodedata; return unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode().strip()

    def _tiene_minimo_resultado(rd):
        if not rd: return False
        try:
            if rd.get('FTHG') is None or rd.get('FTAG') is None: return False
            if rd.get('HTHG') is None or rd.get('HTAG') is None: return False
            return True
        except: return False

    fids_existentes=set(); map_fid_to_row={}; map_fid_to_goles={}
    if FILE_CUR.exists() and FILE_CUR.stat().st_size>0:
        try:
            d=pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
            d = d[pd.to_numeric(d['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
            fids_existentes.update(d['fixture_id'].astype(str).tolist())
            for _, r in d.iterrows(): map_fid_to_row[str(r['fixture_id'])]=r.to_dict()
        except: pass
    if FILE_GOLES.exists() and FILE_GOLES.stat().st_size>0:
        try:
            dg=pd.read_csv(FILE_GOLES, on_bad_lines='skip', engine='python')
            for fid, grupo in dg.groupby('fixture_id'):
                validos = grupo[pd.to_numeric(grupo['minuto'], errors='coerce').notna()]
                validos = validos[validos['minuto'].astype(str).str.strip() != '']
                map_fid_to_goles[str(fid)] = validos.to_dict('records')
        except: pass

    liga_start_idx=0
    if PROG_FILE.exists():
        try: liga_start_idx=int(json.loads(PROG_FILE.read_text(encoding='utf-8')).get("liga_idx",0))
        except: pass

    req=[0]; prog=st.progress(0.0)
    lista_ligas=list(MAPA_GRANDES_1A.items())

    for idx_liga in range(liga_start_idx, len(lista_ligas)):
        nom,lid=lista_ligas[idx_liga]
        prog.progress(idx_liga/len(lista_ligas), text=f"{nom} | {len(fids_existentes)} partidos | req:{req[0]}")
        try:
            time.sleep(0.4)
            r=_req.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": API_KEY}, params={"league": lid, "season": TEMPORADA}, timeout=30); req[0]+=1
            fixtures=r.json().get("response", [])
            tmp_vistos={}
            for fx in fixtures:
                if fx["fixture"]["status"]["short"] not in ["FT","AET","PEN"]: continue
                fid=str(fx["fixture"]["id"])
                if fid in ["0","0.0"]: continue
                clave = (fx["fixture"]["date"][:10], normaliza(fx["teams"]["home"]["name"]), normaliza(fx["teams"]["away"]["name"]))
                tmp_vistos[clave]=fx
            fixtures=list(tmp_vistos.values())
        except: continue

        for fx in fixtures:
            if st.session_state.get('pausa_2627', False):
                st.warning("PAUSADO"); st.stop()
            fid=str(fx["fixture"]["id"])
            date_str=pd.to_datetime(fx["fixture"]["date"][:10]).strftime("%d/%m/%Y")
            home=normaliza(fx["teams"]["home"]["name"]); away=normaliza(fx["teams"]["away"]["name"])
            ft_h,ft_a=fx["goals"]["home"], fx["goals"]["away"]
            ht_h,ht_a=fx["score"]["halftime"]["home"], fx["score"]["halftime"]["away"]

            # === PASO 1 - RESULTADO ===
            if ft_h is None or ft_a is None or ht_h is None or ht_a is None:
                continue # Incompleto, que lo intente otro dia
            ft_h=int(ft_h); ft_a=int(ft_a); ht_h=int(ht_h or 0); ht_a=int(ht_a or 0)
            total_goles = ft_h + ft_a

            # ¿Partido ya COMPLETO segun tu definicion? -> nunca mas se toca
            if fid in fids_existentes:
                rd_ex = map_fid_to_row.get(fid, {})
                if _tiene_minimo_resultado(rd_ex): # PASO 1 OK
                    total_guardado = int(rd_ex.get('FTHG',0) or 0) + int(rd_ex.get('FTAG',0) or 0)
                    if total_guardado==0:
                        continue # 0-0 completo
                    goles_guardados = map_fid_to_goles.get(fid, [])
                    if len(goles_guardados) >= total_guardado:
                        continue # COMPLETO = 1 OK + 2 INTENTADO + 3 OK

            # Preparamos row base
            row={"Date":date_str,"League":nom,"Season":f"{TEMPORADA}/{TEMPORADA+1}","HomeTeam":home,"AwayTeam":away,"FTHG":ft_h,"FTAG":ft_a,"HTHG":ht_h,"HTAG":ht_a,"FTR":"H" if ft_h>ft_a else "A" if ft_a>ft_h else "D","B365H":0,"B365D":0,"B365A":0,"HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0,"HomePasses":0,"AwayPasses":0,"HomeSaves":0,"AwaySaves":0,"HomePos":0,"AwayPos":0,"fixture_id": fx["fixture"]["id"]}

            # === PASO 2 - STATS ===
            if fid in fids_existentes and map_fid_to_row.get(fid):
                # Ya intentado -> no pedir nunca mas
                rd_old = map_fid_to_row.get(fid)
                for k in ['HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','HomePasses','AwayPasses','HomeSaves','AwaySaves','HomePos','AwayPos']:
                    if k in rd_old: row[k]=rd_old[k]
            else:
                # No intentado -> pedir 1 sola vez
                try:
                    time.sleep(0.4); rs=_req.get("https://v3.football.api-sports.io/fixtures/statistics", headers={"x-apisports-key": API_KEY}, params={"fixture": fid}, timeout=20); req[0]+=1
                    if rs.status_code==200 and len(rs.json().get("response",[]))==2:
                        for j,td in enumerate(rs.json()["response"]):
                            sd={s["type"]: s["value"] for s in td["statistics"] if s["value"] is not None}
                            def gi(k):
                                v=sd.get(k)
                                try: return int(str(v).replace("%","").strip() or 0)
                                except: return 0
                            if j==0:
                                row["HS"]=gi("Total Shots"); row["HST"]=gi("Shots on Goal"); row["HC"]=gi("Corner Kicks"); row["HomePasses"]=gi("Total passes"); row["HF"]=gi("Fouls"); row["HY"]=gi("Yellow Cards"); row["HR"]=gi("Red Cards"); row["HomeSaves"]=gi("Goalkeeper Saves"); row["HomePos"]=gi("Ball Possession")
                            else:
                                row["AS"]=gi("Total Shots"); row["AST"]=gi("Shots on Goal"); row["AC"]=gi("Corner Kicks"); row["AwayPasses"]=gi("Total passes"); row["AF"]=gi("Fouls"); row["AY"]=gi("Yellow Cards"); row["AR"]=gi("Red Cards"); row["AwaySaves"]=gi("Goalkeeper Saves"); row["AwayPos"]=gi("Ball Possession")
                except: pass

            # === PASO 3 - GOLES ===
            goles_temp=[]
            if total_goles>0:
                try:
                    time.sleep(0.4); re_=_req.get("https://v3.football.api-sports.io/fixtures/events", headers={"x-apisports-key": API_KEY}, params={"fixture": fid}, timeout=20); req[0]+=1
                    if re_.status_code==200:
                        for ev in re_.json().get("response", []):
                            if ev["type"]=="Goal":
                                minuto = ev["time"]["elapsed"]
                                if minuto is None: continue
                                goleador = ev["player"]["name"] if ev["player"]["name"] else None
                                asistente = ev["assist"]["name"] if ev["assist"]["name"] else None
                                goles_temp.append({"Date":date_str,"League":nom,"Season":f"{TEMPORADA}/{TEMPORADA+1}","HomeTeam":home,"AwayTeam":away,"minuto":minuto,"parte":"1P" if (minuto or 0)<=45 else "2P","goleador":goleador,"asistente":asistente,"equipo":normaliza(ev["team"]["name"]),"tipo":ev["detail"],"fixture_id": fid})
                except: pass

                # ¿API aun no da ningun minuto? -> Guarda PASO 1 y 2, y deja PASO 3 incompleto para otro dia
                if not goles_temp:
                    # Guarda solo partido con stats, sin goles, para no volver a pedir stats
                    try:
                        if FILE_CUR.exists():
                            df_cur = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                            df_cur = df_cur[df_cur['fixture_id'].astype(str)!=fid]
                            df_cur.to_csv(FILE_CUR, index=False)
                    except: pass
                    pd.DataFrame([row]).to_csv(FILE_CUR, mode='a', header=not FILE_CUR.exists() or FILE_CUR.stat().st_size==0, index=False)
                    fids_existentes.add(fid)
                    map_fid_to_row[fid]=row
                    st.write(f"⏳ {nom} - {home} {ft_h}-{ft_a} {away} | Guardado sin minutos, reintentará goles")
                    continue

            # Guardado COMPLETO - ya paso PASO 1 y 2, y PASO 3 tiene minutos (o es 0-0)
            try:
                if FILE_CUR.exists():
                    df_cur = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                    df_cur = df_cur[df_cur['fixture_id'].astype(str)!=fid]
                    df_cur.to_csv(FILE_CUR, index=False)
            except: pass
            pd.DataFrame([row]).to_csv(FILE_CUR, mode='a', header=not FILE_CUR.exists() or FILE_CUR.stat().st_size==0, index=False)

            if goles_temp:
                try:
                    if FILE_GOLES.exists():
                        dg_cur = pd.read_csv(FILE_GOLES, on_bad_lines='skip', engine='python')
                        dg_cur = dg_cur[dg_cur['fixture_id'].astype(str)!=fid]
                        dg_cur.to_csv(FILE_GOLES, index=False)
                except: pass
                pd.DataFrame(goles_temp).to_csv(FILE_GOLES, mode='a', header=not FILE_GOLES.exists() or FILE_GOLES.stat().st_size==0, index=False)
                map_fid_to_goles[fid]=goles_temp

            fids_existentes.add(fid)
            map_fid_to_row[fid]=row
            st.write(f"✅ {nom} - {home} {ft_h}-{ft_a} {away} | Goles guardados: {len(goles_temp)}/{total_goles}")

            if req[0]>=850: st.warning("Limite 850, dale otra vez"); st.stop()

        try: PROG_FILE.write_text(json.dumps({"liga_idx": idx_liga+1}), encoding='utf-8')
        except: pass

    if PROG_FILE.exists(): os.remove(PROG_FILE)
    st.success(f"TERMINADO GRANDES 1A: {len(fids_existentes)} partidos | req {req[0]}"); st.cache_data.clear(); st.rerun()
########################################boton J1 2026/27 FORZADO - SIN FILTRO STATS
######################################## CHECKLIST CHINA 1 + 2 - ESTE AÑO NUEVO - NO PETE
######################################## CHECKLIST KOREA K1 - K LEAGUE 1
    if st.button("✅ CHECKLIST KOREA K1 K2 ESTE AÑO", use_container_width=True, key="btn_check_korea_k1_k2"):
        import requests as _req
        try: API_KEY = str(st.secrets["API_KEY"]).strip()
        except: st.error("Falta API_KEY"); st.stop()

        for LIGA_ID, NOMBRE in [(292,"K League 1"), (293,"K League 2")]:
            r=_req.get("https://v3.football.api-sports.io/leagues", headers={"x-apisports-key": API_KEY}, params={"id":LIGA_ID}, timeout=20)
            data=r.json().get("response",[])
            if data:
                seasons=data[0].get("seasons",[])
                curr=[s for s in seasons if s.get("current")]
                st.write(f"--- {NOMBRE} ID={LIGA_ID} ---")
                st.write(f"Seasons en API: {[s['year'] for s in seasons[-5:]]}")
                if curr:
                    st.success(f"CURRENT -> Year: {curr[0]['year']} Start: {curr[0]['start']} End: {curr[0]['end']}")

            for year in [2025,2026,2027]:
                rr=_req.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": API_KEY}, params={"league":LIGA_ID,"season":year}, timeout=20)
                st.write(f" fixtures season {year} -> {len(rr.json().get('response',[]))} en API")
##############################################################
###################################################################
############################################################
if st.button("🇰🇷 KOREA K1+K2 2026 - FIX", use_container_width=True, key="btn_korea_fix"):
    import requests as _req, time, pathlib, pandas as pd, base64, os, json
    try: API_KEY = str(st.secrets["API_KEY"]).strip()
    except: st.error("Falta API_KEY"); st.stop()
    if 'normaliza' not in globals():
        def normaliza(s): return str(s).upper().strip()

    BASE = pathlib.Path(r"C:\Users\toshiba\Desktop\APP_FUTBOL")
    BASE.mkdir(parents=True, exist_ok=True)
    FILE_CUR = BASE / "partidos_2627_actual.csv"
    FILE_GOLES = BASE / "goles_2627_actual.csv"

    existentes=set(); goles_fids=set()
    if FILE_CUR.exists() and FILE_CUR.stat().st_size>0:
        try:
            d=pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
            d=d[pd.to_numeric(d['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
            existentes=set(d['fixture_id'].astype(str).tolist())
        except: pass
    if FILE_GOLES.exists() and FILE_GOLES.stat().st_size>0:
        try:
            dg=pd.read_csv(FILE_GOLES, on_bad_lines='skip', engine='python')
            dg=dg[pd.to_numeric(dg['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
            goles_fids=set(dg['fixture_id'].astype(str).tolist())
        except: pass

    LIGAS=[(292,"K League 1"),(293,"K League 2")]
    req=[0]
    for LIGA_ID,NOMBRE in LIGAS:
        try:
            time.sleep(0.35)
            r=_req.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": API_KEY}, params={"league":LIGA_ID,"season":2026}, timeout=30)
            req[0]+=1
            fixtures=[f for f in r.json().get("response",[]) if f["fixture"]["status"]["short"] in ["FT","AET","PEN"] and str(f["fixture"]["id"]) not in ["0","0.0"]]
            st.write(f"{NOMBRE} nuevos {len(fixtures)}")
        except Exception as e:
            st.error(f"{NOMBRE} error {e}"); continue

        for fx in fixtures:
            if st.session_state.get('pausa_2627', False):
                st.warning("⏸ PAUSADO - dale a Continuar 26/27")
                st.stop()
            fid=str(fx["fixture"]["id"])
            if fid in ["0","0.0"]: continue

            if fid in existentes and fid in goles_fids:
                try:
                    d_ex = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                    d_ex = d_ex[pd.to_numeric(d_ex['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
                    row_ex = d_ex[d_ex['fixture_id'].astype(str)==fid]
                    if not row_ex.empty:
                        hs_ex = int(float(row_ex.iloc[0].get('HS',0) or 0))
                        hc_ex = int(float(row_ex.iloc[0].get('HC',0) or 0))
                        hp_ex = int(float(row_ex.iloc[0].get('HomePasses',0) or 0))
                        if not (hs_ex==0 and hc_ex==0 and hp_ex==0):
                            continue
                except:
                    pass

            date_str=pd.to_datetime(fx["fixture"]["date"][:10]).strftime("%d/%m/%Y")
            home=normaliza(fx["teams"]["home"]["name"]); away=normaliza(fx["teams"]["away"]["name"])
            ft_h=fx["goals"]["home"] or 0; ft_a=fx["goals"]["away"] or 0
            ht_h=fx["score"]["halftime"]["home"] or 0; ht_a=fx["score"]["halftime"]["away"] or 0
            row={"Date":date_str,"League":NOMBRE,"Season":"2026","HomeTeam":home,"AwayTeam":away,"FTHG":ft_h,"FTAG":ft_a,"HTHG":ht_h,"HTAG":ht_a,"FTR":"H" if ft_h>ft_a else "A" if ft_a>ft_h else "D","B365H":0,"B365D":0,"B365A":0,"HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0,"HomePasses":0,"AwayPasses":0,"HomeSaves":0,"AwaySaves":0,"HomePos":0,"AwayPos":0,"HS_1P":0,"AS_1P":0,"HST_1P":0,"AST_1P":0,"HF_1P":0,"AF_1P":0,"HC_1P":0,"AC_1P":0,"HY_1P":0,"AY_1P":0,"HR_1P":0,"AR_1P":0,"HomePasses_1P":0,"AwayPasses_1P":0,"HomePos_1P":0,"AwayPos_1P":0,"HS_2P":0,"AS_2P":0,"HST_2P":0,"AST_2P":0,"HF_2P":0,"AF_2P":0,"HC_2P":0,"AC_2P":0,"HY_2P":0,"AY_2P":0,"HR_2P":0,"AR_2P":0,"HomePasses_2P":0,"AwayPasses_2P":0,"HomePos_2P":0,"AwayPos_2P":0,"fixture_id":fid}
            goles_temp=[]

            try:
                time.sleep(0.35)
                re_=_req.get("https://v3.football.api-sports.io/fixtures/events", headers={"x-apisports-key": API_KEY}, params={"fixture": fid}, timeout=20); req[0]+=1
                if re_.status_code==200:
                    for ev in re_.json().get("response", []):
                        if ev["type"]=="Goal":
                            goles_temp.append({"Date":date_str,"League":NOMBRE,"Season":"2026","HomeTeam":home,"AwayTeam":away,"minuto":ev["time"]["elapsed"],"parte":"1P" if (ev["time"]["elapsed"] or 0)<=45 else "2P","goleador":ev["player"]["name"],"asistente":ev["assist"]["name"] or "","jugador_tarjeta":"","equipo":normaliza(ev["team"]["name"]),"tipo":ev["detail"],"fixture_id": fid})
                        elif ev["type"]=="Card":
                            goles_temp.append({"Date":date_str,"League":NOMBRE,"Season":"2026","HomeTeam":home,"AwayTeam":away,"minuto":ev["time"]["elapsed"],"parte":"1P" if (ev["time"]["elapsed"] or 0)<=45 else "2P","goleador":"","asistente":"","jugador_tarjeta":ev["player"]["name"],"equipo":normaliza(ev["team"]["name"]),"tipo":ev["detail"],"fixture_id": fid})
            except: pass

            tiene_stats=False
            try:
                time.sleep(0.35)
                rs=_req.get("https://v3.football.api-sports.io/fixtures/statistics", headers={"x-apisports-key": API_KEY}, params={"fixture": fid}, timeout=20); req[0]+=1
                if rs.status_code==200 and len(rs.json().get("response",[]))==2:
                    for j,td in enumerate(rs.json()["response"]):
                        sd={s["type"]: s["value"] for s in td["statistics"] if s["value"] is not None}
                        def gi(k):
                            v=sd.get(k)
                            try: return int(str(v).replace("%","").strip() or 0)
                            except: return 0
                        if j==0: row["HS"]=gi("Total Shots"); row["HST"]=gi("Shots on Goal"); row["HF"]=gi("Fouls"); row["HC"]=gi("Corner Kicks"); row["HY"]=gi("Yellow Cards"); row["HR"]=gi("Red Cards"); row["HomePasses"]=gi("Total passes"); row["HomePos"]=gi("Ball Possession")
                        else: row["AS"]=gi("Total Shots"); row["AST"]=gi("Shots on Goal"); row["AF"]=gi("Fouls"); row["AC"]=gi("Corner Kicks"); row["AY"]=gi("Yellow Cards"); row["AR"]=gi("Red Cards"); row["AwayPasses"]=gi("Total passes"); row["AwayPos"]=gi("Ball Possession")
                    if not (row["HS"]==0 and row["HC"]==0 and row["HomePasses"]==0):
                        tiene_stats=True
            except: pass

            tiene_goles = len(goles_temp)>0
            if not tiene_stats and not tiene_goles:
                continue

            if tiene_goles and fid not in goles_fids:
                pd.DataFrame(goles_temp).to_csv(FILE_GOLES, mode='a', header=not FILE_GOLES.exists() or FILE_GOLES.stat().st_size==0, index=False)
                goles_fids.add(fid)
                st.write(f"✅ GOLES KOREA {home} vs {away} {len(goles_temp)} events")

            if tiene_stats:
                if fid in existentes and FILE_CUR.exists():
                    try:
                        df_cur = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                        df_cur = df_cur[pd.to_numeric(df_cur['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
                        df_cur = df_cur[df_cur['fixture_id'].astype(str)!=fid]
                        df_cur.to_csv(FILE_CUR, index=False)
                    except: pass
                pd.DataFrame([row]).to_csv(FILE_CUR, mode='a', header=not FILE_CUR.exists() or FILE_CUR.stat().st_size==0, index=False)
                existentes.add(fid)
                st.write(f"✅ STATS KOREA {home} vs {away} - req {req[0]}")
            else:
                st.write(f"⚠ SOLO GOLES (sin stats) {home} vs {away} - {len(goles_temp)} goles")

            if req[0]>=900:
                st.warning("Limite 900"); st.stop()
    st.success(f"TERMINADO KOREA {len(existentes)}")
#########################################################################
####################################################################
#################################################################
######################################## BOTON CHINA 1+2 NUEVA 2026/27 DEBAJO DEL CHECKLIST
if st.button("🇨🇳 CHINA 1+2 NUEVA 2026/27 - GUARDA AUTOMATICO", use_container_width=True, key="btn_china_nueva_2627_auto"):
    import requests as _req, time, pathlib, pandas as pd, base64
    try: API_KEY = str(st.secrets["API_KEY"]).strip()
    except: st.error("Falta API_KEY"); st.stop()
    if 'normaliza' not in globals():
        def normaliza(s): return str(s).upper().strip()

    BASE = pathlib.Path(r"C:\Users\toshiba\Desktop\APP_FUTBOL")
    BASE.mkdir(parents=True, exist_ok=True)
    FILE_CUR = BASE / "partidos_2627_actual.csv"
    FILE_GOLES = BASE / "goles_2627_actual.csv"

    existentes=set(); goles_fids=set()
    if FILE_CUR.exists() and FILE_CUR.stat().st_size>0:
        try:
            d=pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
            d=d[pd.to_numeric(d['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
            existentes=set(d['fixture_id'].astype(str).tolist())
        except: pass
    if FILE_GOLES.exists() and FILE_GOLES.stat().st_size>0:
        try:
            dg=pd.read_csv(FILE_GOLES, on_bad_lines='skip', engine='python')
            dg=dg[pd.to_numeric(dg['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
            goles_fids=set(dg['fixture_id'].astype(str).tolist())
        except: pass

    def tiene_stats(sr):
        if len(sr)!=2: return False
        for td in sr:
            sd={s["type"]:s["value"] for s in td["statistics"] if s["value"] is not None}
            if sd.get("Total Shots") is None and sd.get("Corner Kicks") is None and sd.get("Total passes") is None: return False
        return True

    LIGAS = [(169, "Chinese Super League", "2026"), (170, "China League One", "2026")]
    SEASON_API = 2026
    req=[0]; total_nuevos=0

    for LIGA_ID, NOMBRE, SEASON_LABEL in LIGAS:
        try:
            r=_req.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": API_KEY}, params={"league":LIGA_ID,"season":SEASON_API}, timeout=30)
            req[0]+=1
            data=r.json().get("response",[])
            fixtures=[f for f in data if f["fixture"]["status"]["short"] in ["FT","AET","PEN"] and str(f["fixture"]["id"]) not in ["0","0.0"]]
            st.write(f"{NOMBRE} nuevos {len(fixtures)}")
        except Exception as e:
            st.error(f"{NOMBRE} error {e}"); continue

        for fx in fixtures:
            if st.session_state.get('pausa_2627', False):
                st.warning("⏸ PAUSADO - dale a Continuar 26/27")
                st.stop()
            if req[0]>=900:
                st.warning("Limite 900 req, dale otra vez para seguir")
                st.stop()
            fid=str(fx["fixture"]["id"])
            if fid in ["0","0.0"]: continue
            if fid in existentes and fid in goles_fids:
                try:
                    d_ex = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                    d_ex = d_ex[pd.to_numeric(d_ex['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
                    row_ex = d_ex[d_ex['fixture_id'].astype(str)==fid]
                    if not row_ex.empty:
                        hs_ex = int(float(row_ex.iloc[0].get('HS',0) or 0))
                        hc_ex = int(float(row_ex.iloc[0].get('HC',0) or 0))
                        hp_ex = int(float(row_ex.iloc[0].get('HomePasses',0) or 0))
                        if not (hs_ex==0 and hc_ex==0 and hp_ex==0):
                            continue
                except: pass

            date_str=pd.to_datetime(fx["fixture"]["date"][:10]).strftime("%d/%m/%Y")
            home=normaliza(fx["teams"]["home"]["name"]); away=normaliza(fx["teams"]["away"]["name"])
            ft_h=fx["goals"]["home"] or 0; ft_a=fx["goals"]["away"] or 0
            ht_h=fx["score"]["halftime"]["home"] or 0; ht_a=fx["score"]["halftime"]["away"] or 0

            row={"Date":date_str,"League":NOMBRE,"Season":SEASON_LABEL,"HomeTeam":home,"AwayTeam":away,"FTHG":ft_h,"FTAG":ft_a,"HTHG":ht_h,"HTAG":ht_a,"FTR":"H" if ft_h>ft_a else "A" if ft_a>ft_h else "D","B365H":0,"B365D":0,"B365A":0,"HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0,"HomePasses":0,"AwayPasses":0,"HomeSaves":0,"AwaySaves":0,"HomePos":0,"AwayPos":0,"HS_1P":0,"AS_1P":0,"HST_1P":0,"AST_1P":0,"HF_1P":0,"AF_1P":0,"HC_1P":0,"AC_1P":0,"HY_1P":0,"AY_1P":0,"HR_1P":0,"AR_1P":0,"HomePasses_1P":0,"AwayPasses_1P":0,"HomePos_1P":0,"AwayPos_1P":0,"HS_2P":0,"AS_2P":0,"HST_2P":0,"AST_2P":0,"HF_2P":0,"AF_2P":0,"HC_2P":0,"AC_2P":0,"HY_2P":0,"AY_2P":0,"HR_2P":0,"AR_2P":0,"HomePasses_2P":0,"AwayPasses_2P":0,"HomePos_2P":0,"AwayPos_2P":0,"fixture_id":fid}

            goles_temp=[]
            tiene_goles=False
            tiene_stats=False
            try:
                time.sleep(0.35)
                re_=_req.get("https://v3.football.api-sports.io/fixtures/events", headers={"x-apisports-key": API_KEY}, params={"fixture":fid}, timeout=20); req[0]+=1
                if re_.status_code==200:
                    for ev in re_.json().get("response",[]):
                        if ev["type"] in ["Goal","Card"]:
                            goles_temp.append({"Date":date_str,"League":NOMBRE,"Season":SEASON_LABEL,"HomeTeam":home,"AwayTeam":away,"minuto":ev["time"]["elapsed"],"parte":"1P" if (ev["time"]["elapsed"] or 0)<=45 else "2P","goleador":ev["player"]["name"] if ev["type"]=="Goal" else "","asistente":ev["assist"]["name"] if ev["type"]=="Goal" and ev["assist"]["name"] else "","jugador_tarjeta":ev["player"]["name"] if ev["type"]=="Card" else "","equipo":normaliza(ev["team"]["name"]),"tipo":ev["detail"],"fixture_id": fid})
                    if len(goles_temp)>0:
                        tiene_goles=True
            except: pass

            try:
                time.sleep(0.35)
                rs=_req.get("https://v3.football.api-sports.io/fixtures/statistics", headers={"x-apisports-key": API_KEY}, params={"fixture":fid}, timeout=20); req[0]+=1
                if rs.status_code==200 and len(rs.json().get("response",[]))==2:
                    for j,td in enumerate(rs.json().get("response",[])):
                        sd={s["type"]:s["value"] for s in td["statistics"] if s["value"] is not None}
                        def gi(k):
                            v=sd.get(k)
                            try: return int(str(v).replace("%","").strip() or 0)
                            except: return 0
                        if j==0:
                            row["HS"]=gi("Total Shots"); row["HST"]=gi("Shots on Goal"); row["HF"]=gi("Fouls"); row["HC"]=gi("Corner Kicks"); row["HY"]=gi("Yellow Cards"); row["HR"]=gi("Red Cards"); row["HomePasses"]=gi("Total passes"); row["HomeSaves"]=gi("Goalkeeper Saves"); row["HomePos"]=gi("Ball Possession")
                        else:
                            row["AS"]=gi("Total Shots"); row["AST"]=gi("Shots on Goal"); row["AF"]=gi("Fouls"); row["AC"]=gi("Corner Kicks"); row["AY"]=gi("Yellow Cards"); row["AR"]=gi("Red Cards"); row["AwayPasses"]=gi("Total passes"); row["AwaySaves"]=gi("Goalkeeper Saves"); row["AwayPos"]=gi("Ball Possession")
                    if not (row["HS"]==0 and row["HC"]==0 and row["HomePasses"]==0):
                        tiene_stats=True
            except: pass

            if not tiene_stats and not tiene_goles:
                continue

            if tiene_goles and fid not in goles_fids:
                pd.DataFrame(goles_temp).to_csv(FILE_GOLES, mode='a', header=not FILE_GOLES.exists() or FILE_GOLES.stat().st_size==0, index=False)
                goles_fids.add(fid)
                st.write(f"✅ GOLES CHINA {home} vs {away} {len(goles_temp)} events")

            if tiene_stats:
                if fid in existentes and FILE_CUR.exists():
                    try:
                        df_cur = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                        df_cur = df_cur[pd.to_numeric(df_cur['fixture_id'], errors='coerce').fillna(0).astype(int)!=0]
                        df_cur = df_cur[df_cur['fixture_id'].astype(str)!=fid]
                        df_cur.to_csv(FILE_CUR, index=False)
                    except: pass
                pd.DataFrame([row]).to_csv(FILE_CUR, mode='a', header=not FILE_CUR.exists() or FILE_CUR.stat().st_size==0, index=False)
                existentes.add(fid); total_nuevos+=1
                st.write(f"✅ STATS CHINA {home} vs {away} - req {req[0]}")

    st.success(f"TERMINADO {total_nuevos} nuevos")
######################################## FIN BOTON CHINA
###############################################
#############################################
#####################fin ligas especificas 26 27
# FIX: si viene del valor viejo 1.5-10.0 lo reseteamos a 1.01-100

# FIX: si viene del valor viejo 1.5-10.0 lo reseteamos a 1.01-100
if 'rango_cuotas' not in st.session_state or st.session_state.rango_cuotas == (1.5, 10.0) or st.session_state.rango_cuotas[0] == 1.5:
    st.session_state.rango_cuotas = (1.01, 100.0)
# No tocar cuota_desde / cuota_hasta en session_state, lo maneja el widget
if 'rango_minutos' not in st.session_state:
    st.session_state.rango_minutos = (0, 120)
if 'ultimas_jornadas_filtro' not in st.session_state:
    st.session_state.ultimas_jornadas_filtro = "-"
if 'pct_marcador' not in st.session_state:
    st.session_state.pct_marcador = 1
if 'xx_filtro' not in st.session_state: st.session_state.xx_filtro = "Todo"


#########################################
########################################
##########################################
@st.cache_data(show_spinner=False)

def cargar_todo(_cache_buster=0):
    import os, pathlib, re
    import pandas as pd
    import numpy as np
    try:
        BASE = pathlib.Path(__file__).parent.resolve()
    except:
        BASE = pathlib.Path.cwd().resolve()
    df_completo = pd.DataFrame()
    candidatos = [BASE / "ligas_2122_a_2627_SIN_DUPLICADOS.csv", BASE / "partidos_2627_actual.csv"]
    dfs = []
    for p in candidatos:
        if p.exists() and p.stat().st_size > 0:
            try:
                try: d = pd.read_csv(p, on_bad_lines='skip', engine='python')
                except: d = pd.read_csv(p, sep=';', on_bad_lines='skip', engine='python')
                if not d.empty: dfs.append(d)
            except: pass
    if dfs:
        df_completo = pd.concat(dfs, ignore_index=True)
    if df_completo.empty:
        return pd.DataFrame()
    df = df_completo.copy()

    # FIX COLUMNAS ALTERNATIVAS - tu SOLO_RESULTADO usa GolLocal_FT
    mapa_cols = {
        'GolLocal_FT':'FTHG', 'GolVisitante_FT':'FTAG',
        'GolLocal_1P':'HTHG', 'GolVisitante_1P':'HTAG',
        'GolLocal_2P':'FTHG_2P', 'GolVisitante_2P':'FTAG_2P'
    }
    for old,new in mapa_cols.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]
    # si aún no hay FTHG intenta desde Resultado tipo "2-1"
    if 'FTHG' not in df.columns or df['FTHG'].sum()==0:
        if 'Resultado' in df.columns:
            try:
                tmp = df['Resultado'].astype(str).str.extract(r'(\d+)\s*-\s*(\d+)')
                df['FTHG'] = pd.to_numeric(tmp[0], errors='coerce')
                df['FTAG'] = pd.to_numeric(tmp[1], errors='coerce')
            except:
                pass

    # LIMPIEZA
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df[df['Date'].notna()]
    for col in ['League','Season','HomeTeam','AwayTeam']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('"','').str.replace("'",'')
    for col in ['HomeTeam','AwayTeam']:
        if col in df.columns:
            df[col] = df[col].apply(normaliza)

    # FIX 1 - MAPA BUNDESLIGA PARA UNIFICAR DUPLICADOS (ESTO QUITA 34 EQ -> 18)
    mapa_bundes = {
        'B LEIPZIG':'RB LEIPZIG', 'RB LEIPZIG':'RB LEIPZIG',
        'BAYERN MUNCHEN':'BAYERN MUNICH', 'BAYERN MUNICH':'BAYERN MUNICH',
        'BORUSSIA DORTMUND':'DORTMUND', 'DORTMUND':'DORTMUND',
        'VFB STUTTGART':'STUTTGART', 'STUTTGART':'STUTTGART',
        '1899 HOFFENHEIM':'HOFFENHEIM', 'HOFFENHEIM':'HOFFENHEIM',
        'BAYER LEVERKUSEN':'LEVERKUSEN', 'LEVERKUSEN':'LEVERKUSEN',
        'SC FREIBURG':'FREIBURG', 'FREIBURG':'FREIBURG',
        'EIN FRANKFURT':'EINTRACHT FRANKFURT', 'EINTRACHT FRANKFURT':'EINTRACHT FRANKFURT',
        'FC AUGSBURG':'AUGSBURG', 'AUGSBURG':'AUGSBURG',
        'FSV MAINZ 05':'MAINZ', 'MAINZ':'MAINZ',
        'BORUSSIA MONCHENGLADBACH':'MGLADBACH', 'MGLADBACH':'MGLADBACH',
        'HAMBURGER SV':'HAMBURG', 'HAMBURG':'HAMBURG',
        '1. FC KOLN':'KOLN', 'FC KOLN':'KOLN', 'KOLN':'KOLN',
        'VFL WOLFSBURG':'WOLFSBURG', 'WOLFSBURG':'WOLFSBURG',
        '1. FC HEIDENHEIM':'HEIDENHEIM', 'HEIDENHEIM':'HEIDENHEIM',
        'FC ST. PAULI':'ST PAULI', 'ST PAULI':'ST PAULI',
        'SC PADERBORN 07':'PADERBORN'
    }

    mapa_unifica = {
        # Holanda
        'HERACLES ALMELO':'HERACLES','SC HERACLES ALMELO':'HERACLES','SC HERACLES':'HERACLES',
        'FC GRONINGEN':'GRONINGEN','PEC ZWOLLE':'ZWOLLE','FC ZWOLLE':'ZWOLLE','FC VOLENDAM':'VOLENDAM','SC TELSTAR':'TELSTAR',
        'ADO DEN HAAG':'ADO DEN HAAG','CAMBUUR':'CAMBUUR','WILLEM II':'WILLEM II','NEC NIJMEGEN':'NEC','GO AHEAD EAGLES':'GO AHEAD EAGLES',
        'AFC AJAX':'AJAX','AJAX AMSTERDAM':'AJAX','AZ ALKMAAR':'AZ','PSV EINDHOVEN':'PSV','FC TWENTE':'TWENTE','FC TWENTE ENSCHEDE':'TWENTE','FC UTRECHT':'UTRECHT','SC HEERENVEEN':'HEERENVEEN','SBV EXCELSIOR':'EXCELSIOR','EXCELSIOR ROTTERDAM':'EXCELSIOR','SPARTA ROTTERDAM':'SPARTA','FORTUNA SITTARD':'FORTUNA SITTARD',
        # España general
        'ATLETICO DE MADRID':'ATLETICO MADRID','ATH MADRID':'ATLETICO MADRID','ATH. MADRID':'ATLETICO MADRID','AT MADRID':'ATLETICO MADRID','ATHLETIC CLUB':'ATHLETIC BILBAO','VALLECANO':'RAYO VALLECANO','RAYO VALLECANO MADRID':'RAYO VALLECANO','DEPORTIVO ALAVES':'ALAVES','LEVANTE UD':'LEVANTE','ELCHE CF':'ELCHE','REAL OVIEDO':'OVIEDO',
        # FIX HYPERMOTION 25/26 - ESTO TE ARREGLA EL 720 -> 462 y 29 -> 22
        'RACING SANTANDER':'RACING SANTANDER','RACING DE SANTANDER':'RACING SANTANDER','SANTANDER':'RACING SANTANDER','RAC':'RACING SANTANDER','SAN':'RACING SANTANDER',
        'DEPORTIVO LA CORUNA':'DEPORTIVO LA CORUNA','LA CORUNA':'DEPORTIVO LA CORUNA','DEP':'DEPORTIVO LA CORUNA','DEPORTIVO':'DEPORTIVO LA CORUNA','CORUNA':'DEPORTIVO LA CORUNA','DEPORTIVO A CORUNA':'DEPORTIVO LA CORUNA','RC DEPORTIVO':'DEPORTIVO LA CORUNA',
        'SPORTING GIJON':'SPORTING GIJON','SP GIJON':'SPORTING GIJON','SPO':'SPORTING GIJON','SPORTING DE GIJON':'SPORTING GIJON','REAL SPORTING':'SPORTING GIJON','SP':'SPORTING GIJON',
        'AD CEUTA FC':'CEUTA','CEUTA':'CEUTA','AD CEUTA':'CEUTA','CEUTA FC':'CEUTA','AD':'CEUTA','CEU':'CEUTA',
        'FC ANDORRA':'FC ANDORRA','ANDORRA':'FC ANDORRA','AND':'FC ANDORRA','F C ANDORRA':'FC ANDORRA',
        'GRANADA':'GRANADA','GRANADA CF':'GRANADA','GRANADA CLUB DE FUTBOL':'GRANADA','GRA':'GRANADA',
        'REAL SOCIEDAD B':'REAL SOCIEDAD II','REAL SOCIEDAD II':'REAL SOCIEDAD II','SOCIEDAD B':'REAL SOCIEDAD II','RSO B':'REAL SOCIEDAD II','SOC B':'REAL SOCIEDAD II','SOC':'REAL SOCIEDAD II','REAL SOCIEDAD DE FUTBOL B':'REAL SOCIEDAD II',
        'CORDOBA':'CORDOBA','COR':'CORDOBA','CORDOBA CF':'CORDOBA',
        'LAS PALMAS':'LAS PALMAS','LPA':'LAS PALMAS','UD LAS PALMAS':'LAS PALMAS',
        'CULTURAL LEONESA':'CULTURAL LEONESA','CUL':'CULTURAL LEONESA','CULTURAL Y DEPORTIVA LEONESA':'CULTURAL LEONESA',
        'SP G':'SPORTING GIJON',
    }
    # aplica primero holanda/espana luego bundes
    df['HomeTeam'] = df['HomeTeam'].replace(mapa_unifica).replace(mapa_bundes)
    df['AwayTeam'] = df['AwayTeam'].replace(mapa_unifica).replace(mapa_bundes)

    # FIX 2 - DEDUP REAL V6 - fecha sin hora + season normalizada
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df[df['Date'].notna()].copy()
    df['Date_only'] = df['Date'].dt.strftime('%Y-%m-%d')

    if 'fixture_id' in df.columns:
        df = df.sort_values(['Date','fixture_id'], na_position='last')
        # 1º por fixture_id
        mask_id = df['fixture_id'].notna()
        df_id = df[mask_id].drop_duplicates(subset=['fixture_id'], keep='last')
        df_noid = df[~mask_id]
        df = pd.concat([df_id, df_noid], ignore_index=True)

    # 2º por clave real, prioriza el que tiene cuota
    if 'B365H' in df.columns:
        df['__tiene_cuota'] = pd.to_numeric(df['B365H'], errors='coerce').fillna(0) > 1.0
        df = df.sort_values(['__tiene_cuota','Date'], ascending=[False, True])
    # clave definitiva sin hora
    df = df.drop_duplicates(subset=['Date_only','HomeTeam','AwayTeam','League','Season'], keep='first')
    df = df.drop(columns=[c for c in ['__tiene_cuota','Date_only'] if c in df.columns])
    df = df.sort_values('Date')

    df = df.sort_values('Date')
    def norm_season(s):
        s = str(s).strip()
        import re
        m = re.match(r'^(\d{4})/(\d{4})$', s)
        if m:
            y1 = int(m.group(1)); y2 = int(m.group(2))
            if y2 - y1 == 1:
                return s
            if y1 == 2020 and y2 >= 2022:
                return f"{y2-1}/{y2}"
            return f"{y1}/{y1+1}"
        if re.match(r'^\d{4}$', s):
            y = int(s[:4])
            return f"{y}/{y+1}"
        return s
    df['Season'] = df['Season'].apply(norm_season)
    mapa_ligas_todo = {
        'Jupiler':'Jupiler Pro League',
        'Jupiler Pro League':'Jupiler Pro League',
        'Eredivisie':'Eredivisie',
        'Premier':'Premier League',
        'LaLiga':'LaLiga EA Sports',
        'SC1': 'Saudi Professional League',
        'SC2': 'Saudi First Division League',
        'SC3': 'Saudi Second Division League',
        'Primeira Liga': 'Liga Portugal',
        'Serie A Betano': 'Serie A Brasil',
        'LaLiga2': 'LaLiga Hypermotion',
        'Copa': 'Taça de Portugal',
        'Copa de Primera': 'Copa de Primera Paraguay',
        'President Cup': 'UAE President Cup',
        'T1': 'Thai League 1',
        'Nike liga': 'Nike Liga',
        'NB I.': 'NB I',
        'Bundesliga - Femenina': 'Bundesliga Femenina',
        'Superliga': 'Superliga Dinamarca',
        'Super League 2': 'Super League 2 Grecia',
    }
    df['League'] = df['League'].replace(mapa_ligas_todo)
        # FIX LIGA MAL ETIQUETADA 26/27 - si es Hypermotion pero tiene equipos de Primera, corrige a EA Sports
    try:
        EQUIPOS_PRIMERA = {"REAL MADRID","BARCELONA","ATLETICO MADRID","SEVILLA","BETIS","VILLARREAL","VALENCIA","ATHLETIC BILBAO","REAL SOCIEDAD","MALLORCA","GIRONA","OSASUNA","CELTA","RAYO VALLECANO","GETAFE","ALAVES","LAS PALMAS","ESPANYOL","ELCHE","LEVANTE","OVIEDO","VALLADOLID"}
        mask_hyper = df['League'].astype(str).str.contains('Hypermotion', case=False, na=False)
        mask_primera_team = df['HomeTeam'].isin(EQUIPOS_PRIMERA) | df['AwayTeam'].isin(EQUIPOS_PRIMERA)
        # Si en 2026/2027 Hypermotion aparece un equipo de primera, era Primera realmente
        df.loc[mask_hyper & mask_primera_team & (df['Season']=='2026/2027'), 'League'] = 'LaLiga EA Sports'
    except:
        pass
    df = df[df['League'].notna() & (df['League']!='nan')]
    cols_num = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','HomePasses','AwayPasses','HomePasses_1P','AwayPasses_1P','HomePasses_2P','AwayPasses_2P','HomeSaves','AwaySaves','HomePos','AwayPos','HomePos_1P','AwayPos_1P','HomePos_2P','AwayPos_2P','HS_1P','AS_1P','HST_1P','AST_1P','HF_1P','AF_1P','HC_1P','AC_1P','HY_1P','AY_1P','HR_1P','AR_1P','HS_2P','AS_2P','HST_2P','AST_2P','HF_2P','AF_2P','HC_2P','AC_2P','HY_2P','AY_2P','HR_2P','AR_2P']
    for col in cols_num:
        if col not in df.columns:
            df[col]=0
    for col in cols_num:
        df[col] = pd.to_numeric(df.get(col,0), errors='coerce').fillna(0)
    if 'FTR' not in df.columns:
        df['FTR'] = np.where(df['FTHG']>df['FTAG'],'H',np.where(df['FTHG']<df['FTAG'],'A','D'))
    for col in ['B365H','B365D','B365A']:
        df[col] = pd.to_numeric(df.get(col,np.nan), errors='coerce')
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
    try:
        EQUIPOS_SUIZA = {"BASEL","BASEL 1893","YOUNG BOYS","BSC YOUNG BOYS","SERVETTE","SERVETTE FC","LUZERN","FC LUZERN","ZURICH","FC ZURICH","ST GALLEN","FC ST. GALLEN","SION","FC SION","GRASSHOPPERS","GRASSHOPPER","LAUSANNE","LAUSANNE-SPORT","VADUZ","FC VADUZ","LUGANO","FC LUGANO","WINTERTHUR","YVERDON","WIL","FC WIL"}
        mask_suiza = df['HomeTeam'].isin(EQUIPOS_SUIZA) | df['AwayTeam'].isin(EQUIPOS_SUIZA)
        mask_mal = df['League'].astype(str).str.contains('AUSTRIA', case=False, na=False)
        df.loc[mask_suiza & mask_mal, 'League'] = 'Super League'
    except:
        pass
    return df.copy()
######################################################
def cargar_eventos(league=None, season=None):
    import os, glob, pandas as pd
    rutas = glob.glob('**/goles*.csv', recursive=True) + ['goles_2627_actual.csv','goles_2627_actual_PUZZLE.csv','goles_2627_actual_LIMPIO.csv']
    dfs=[]
    for f in set(rutas):
        if os.path.exists(f):
            try:
                df=pd.read_csv(f, dtype=str, on_bad_lines='skip', engine='python')
                if not df.empty and any('minuto' in c.lower() for c in df.columns):
                    dfs.append(df)
            except: pass
    if not dfs: return {}
    df_g=pd.concat(dfs, ignore_index=True)
    try: df_g=df_g.drop_duplicates(subset=['fixture_id','minuto','goleador','tipo','equipo'], keep='first')
    except: pass
    eventos={}
    for fid, g in df_g.groupby('fixture_id'):
        try: fid_c=str(int(float(str(fid))))
        except: continue
        evs=[]
        for _,r in g.sort_values('minuto').iterrows():
            try:
                m=int(float(str(r.get('minuto','0')).split('+')[0] or 0))
                gol=str(r.get('goleador','')).strip()
                if not gol or gol.lower() in ['nan','']: continue
                tipo=str(r.get('tipo','')).lower()
                evs.append({"minute":m,"player":gol,"assist":str(r.get('asistente','')).strip(),"team":str(r.get('equipo','')).upper(),"penalty":'pen' in tipo and 'miss' not in tipo,"missed":'miss' in tipo})
            except: continue
        eventos[fid_c]=evs
        eventos[str(fid)]=evs
    return eventos

def buscar_goles_partido(row, eventos_dict, min_min=0, max_min=120, parte="Todo", equipo_filtro=None):
    import pandas as pd
    if pd.isna(row['Date']): return ""
    try:
        fid=str(row.get('fixture_id','')).strip()
        fid_c=str(int(float(fid))) if fid not in ['','nan','0','0.0','None'] else ""
        evs=eventos_dict.get(fid_c,[]) or eventos_dict.get(fid,[]) or []
        if not evs:
            try:
                fthg=int(float(row['FTHG'])); ftag=int(float(row['FTAG']))
                if fthg+ftag>0:
                    return f"<span style='color:#581C87;font-weight:700'>{fthg}-{ftag} (sin detalle)</span>"
            except: pass
            return ""
        txt=[]
        for ev in evs:
            if ev.get('missed'): continue
            m=ev.get('minute',0)
            if parte=="1T" and m>45: continue
            if parte=="2T" and m<=45: continue
            if not (min_min <= m <= max_min): continue
            minuto_txt=f"{m}'(pen)" if ev.get('penalty') else f"{m}'"
            minuto_morado=f"<span style='color:#581C87;font-weight:900'>{minuto_txt}</span>"
            gol_text=f"{minuto_morado} {ev.get('player','')}"
            assist=ev.get('assist','')
            if assist and assist.lower()!='nan' and assist!="":
                gol_text+=f" ({assist})"
            txt.append(f"<span style='font-weight:600;color:#000'>{gol_text}</span>")
        return " | ".join(txt)
    except:
        return ""

def jornadas_conteo(jornadas, df_ref=None, equipo=None, rival=None, parte="Todo"):
    if pd.isna(row['Date']):
        return ""
    try:
        key = (row['HomeTeam'], row['AwayTeam'], row['Date'].strftime('%Y-%m-%d'))
        evs = eventos_dict.get(key, [])
        # FALLBACK SI API NO DIO GOLES PERO HAY RESULTADO
        if not evs and (int(row['FTHG']) + int(row['FTAG'])) > 0:
            return f"<span style='color:#581C87;font-weight:700'>{int(row['FTHG'])}-{int(row['FTAG'])} (API sin eventos)</span>"
        if not evs: return ""
        hg = int(row['FTHG']); ag = int(row['FTAG'])
        ganador = row['HomeTeam'] if hg > ag else row['AwayTeam'] if ag > hg else None
        filtro_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro!= "Ninguno" else None
        txt = []
        for ev in evs:
            if ev.get('missed'): continue
            minuto = int(ev.get('minute',0) or 0)
            if parte == "1T" and minuto > 45: continue
            if parte == "2T" and minuto <= 45: continue
            if not (min_min <= minuto <= max_min): continue
            team = ev.get('team','')
            minuto_txt = f"{minuto}'(pen)" if ev.get('penalty') else f"{minuto}'"
            minuto_morado = f"<span style='color:#581C87;font-weight:900'>{minuto_txt}</span>"
            gol_text = f"{minuto_morado} {ev.get('player','')}"
            if ev.get('assist'): gol_text += f" ({ev['assist']})"
            estilos = []
            if ganador and team == ganador: estilos.append("font-weight:900;color:#000")
            else: estilos.append("font-weight:600;color:#444")
            if filtro_norm and team == filtro_norm: estilos.append("text-decoration:underline;text-decoration-thickness:2px")
            txt.append(f"<span style=\"{';'.join(estilos)}\">{gol_text}</span>")
        # SI SIGUE VACIO PERO HAY GOLES, MUESTRA FALLBACK
        if not txt and (hg+ag)>0:
            return f"<span style='color:#581C87;font-weight:700'>{hg}-{ag} (sin detalle)</span>"
        return " | ".join(txt)
    except:
        return ""
    if pd.isna(row['Date']):
        return ""
    try:
        key = (row['HomeTeam'], row['AwayTeam'], row['Date'].strftime('%Y-%m-%d'))
        evs = eventos_dict.get(key, [])
        if not evs: return ""
        hg = int(row['FTHG']); ag = int(row['FTAG'])
        ganador = row['HomeTeam'] if hg > ag else row['AwayTeam'] if ag > hg else None
        filtro_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro!= "Ninguno" else None
        txt = []
        for ev in evs:
            if ev.get('missed'): continue
            minuto = int(ev.get('minute',0) or 0)
            if parte == "1T" and minuto > 45: continue
            if parte == "2T" and minuto <= 45: continue
            if not (min_min <= minuto <= max_min): continue
            team = ev.get('team','')
            minuto_txt = f"{minuto}'(pen)" if ev.get('penalty') else f"{minuto}'"
            minuto_morado = f"<span style='color:#581C87;font-weight:900'>{minuto_txt}</span>"
            gol_text = f"{minuto_morado} {ev.get('player','')}"
            if ev.get('assist'): gol_text += f" ({ev['assist']})"
            estilos = []
            if ganador and team == ganador: estilos.append("font-weight:900;color:#000")
            else: estilos.append("font-weight:600;color:#444")
            if filtro_norm and team == filtro_norm: estilos.append("text-decoration:underline;text-decoration-thickness:2px")
            txt.append(f"<span style=\"{';'.join(estilos)}\">{gol_text}</span>")
        return " | ".join(txt)
    except:
        return ""

def jornadas_conteo(jornadas, df_ref=None, equipo=None, rival=None, parte="Todo"):
    from collections import Counter
    if df_ref is None or equipo is None:
        c = Counter(jornadas)
        return "|".join([f"J{int(j)}-{c[j]}#" if c[j]>1 else f"J{int(j)}" for j in sorted(c)])
    df_eq = df_ref[(df_ref['HomeTeam']==equipo) | (df_ref['AwayTeam']==equipo)] if len(df_ref) > 300 else df_ref
    if df_eq.empty: return ""
    # FIX 1: quita duplicados reales que te creaban J39 y doble viñeta
    df_eq = df_eq.drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League','Season'])
    is_home_s = (df_eq['HomeTeam']==equipo)
    final_gf_arr = np.where(is_home_s, df_eq['FTHG'].to_numpy(), df_eq['FTAG'].to_numpy())
    final_gc_arr = np.where(is_home_s, df_eq['FTAG'].to_numpy(), df_eq['FTHG'].to_numpy())
    win_s = pd.Series(final_gf_arr > final_gc_arr, index=df_eq.index)
    loss_s = pd.Series(final_gf_arr < final_gc_arr, index=df_eq.index)
    partes = []
    for (season, j), g in df_eq.groupby(['Season','Jornada'], sort=True):
        g = g.drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League','Season'])
        if g.empty: continue
        # FIX 2: si por duplicado quedan 2 filas en la misma jornada, quédate con 1 -> 1 sola viñeta
        if len(g) > 1:
            g = g.sort_values('Date').head(1)
        if g.empty: continue
        if win_s.loc[g.index].all(): color = '#0f8105'
        elif loss_s.loc[g.index].all(): color = '#f31818'
        else: color = '#0A2342'
        first_row = g.iloc[0]
        is_h_first = first_row['HomeTeam']==equipo
        if len(g)==1: sufijo_final = 'c' if is_h_first else 'f'
        else:
            all_home = (g['HomeTeam']==equipo).all()
            all_away = (g['AwayTeam']==equipo).all()
            sufijo_final = 'c' if all_home else 'f' if all_away else 'cf'
        real_home = int(first_row['FTHG']); real_away = int(first_row['FTAG'])
        # Mantiene Abbr si existe, si no 3 letras
        try: home_short = str(first_row['HomeAbbr'])
        except: home_short = str(first_row['HomeTeam'])[:3].upper()
        try: away_short = str(first_row['AwayAbbr'])
        except: away_short = str(first_row['AwayTeam'])[:3].upper()
        h_pos = int(first_row.get('HomePosPrev', 0)); a_pos = int(first_row.get('AwayPosPrev', 0))
        es_local = first_row['HomeTeam'] == equipo
        try: rojas_eq = int(first_row['HR']) if es_local else int(first_row['AR'])
        except: rojas_eq = 0
        rojo_html = f"<span style='color:#dc2626;font-weight:900'> {' -'*rojas_eq}</span>" if rojas_eq>0 else ""
        if es_local:
            htgf, htgc = int(first_row['HTHG']), int(first_row['HTAG']); ftgf, ftgc = real_home, real_away
        else:
            htgf, htgc = int(first_row['HTAG']), int(first_row['HTHG']); ftgf, ftgc = real_away, real_home
        res_ht = 'G' if htgf > htgc else 'P' if htgf < htgc else 'E'
        res_ft = 'G' if ftgf > ftgc else 'P' if ftgf < ftgc else 'E'
        am = " ▪" if real_home > 0 and real_away > 0 else ""
        MORADO = "#581C87"
        # --- RE COLORES ---
        re_html = ""
        if res_ht == 'P' and res_ft == 'E':
            re_html = "<span style='display:inline-block;background:#facc15;color:#000;font-weight:900;font-size:9px;padding:0 4px;border-radius:3px;margin-left:3px;border:1px solid #eab308'>RE</span>"
        elif res_ht == 'G' and res_ft == 'P':
            re_html = "<span style='display:inline-block;background:#ef4444;color:#fff;font-weight:900;font-size:9px;padding:0 4px;border-radius:3px;margin-left:3px'>RE</span>"
        elif res_ht == 'P' and res_ft == 'G':
            re_html = "<span style='display:inline-block;background:#22c55e;color:#fff;font-weight:900;font-size:9px;padding:0 4px;border-radius:3px;margin-left:3px'>RE</span>"
        if es_local:
            txt = f"J{int(j)}{sufijo_final}<u><span style='color:{MORADO};font-weight:900'>{h_pos}º</span> {home_short}{rojo_html} {real_home}</u>-{real_away} {away_short} <span style='color:{MORADO}'>{a_pos}º</span> {res_ht}/{res_ft}{re_html}{am}"
        else:
            txt = f"J{int(j)}{sufijo_final}<span style='color:{MORADO}'>{h_pos}º</span> {home_short} {real_home}-<u>{real_away} {away_short}{rojo_html} <span style='color:{MORADO};font-weight:900'>{a_pos}º</span></u> {res_ht}/{res_ft}{re_html}{am}"
        # --- AÑADIDO: goles SEGUIDO en misma linea - FIX globals ---
        goles_inline = ""
        try:
            ev_dict = globals().get('todos_eventos', None)
            if ev_dict is None:
                ev_dict = locals().get('todos_eventos', {})
            if ev_dict:
                gt = buscar_goles_partido(first_row, ev_dict, 0, 120, parte, equipo)
                if gt:
                    goles_inline = f"<span style='font-size:10px;font-weight:400;margin-left:3px;white-space:normal'>{gt}</span>"
                else:
                    goles_inline = ""
        except: pass
        es_h2h = False
        if rival: es_h2h = ((g['HomeTeam']==equipo) & (g['AwayTeam']==rival)).any() or ((g['HomeTeam']==rival) & (g['AwayTeam']==equipo)).any()
        viñeta = "".join([formatear_h2h_compacto(r, equipo) for _, r in g.iterrows()])
        estilos_summary = f"color:{color};font-weight:700;cursor:pointer;list-style:none;display:inline-block;background:transparent;border:none;padding:1px 3px;margin:0;white-space:nowrap;font-size:11px;font-family:monospace;letter-spacing:-0.4px;word-spacing:-1.2px;line-height:20px"
        if es_h2h: estilos_summary += ";text-decoration:underline;text-decoration-thickness:2px"
        jx_html = f"""<details style="display:block;width:100%;margin:0;padding:5px 0 5px 2px;position:relative;border-bottom:1px solid #eeeeee">
        <summary style="{estilos_summary};white-space:normal;line-height:1.25"><span>{txt}{goles_inline}</span></summary>
        <div style="position:absolute;top:100%;left:0;z-index:9999;background:#FFFFFF;border:2px solid #000;padding:4px;margin-top:4px;width:92vw;max-width:360px;min-width:280px;text-align:left;white-space:normal;max-height:400px;overflow-y:auto;box-shadow:0 4px 12px rgba(0,0,0,0.3)">{viñeta}</div>
    </details>"""
        partes.append(jx_html)
    # Ahora cada partido en su propia linea
    return f"<div style='display:flex;flex-direction:column;gap:3px;padding:2px 0'>{''.join(partes)}</div>"

#############################################
######################################
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
    # FIX 26/27 - solo hay totales, 1P/2P viene a 0
    hp = int(row.get('HomePasses',0) or 0); ap = int(row.get('AwayPasses',0) or 0)
    hp_1p = int(row.get('HomePasses_1P',0) or 0); ap_1p = int(row.get('AwayPasses_1P',0) or 0)
    hp_2p = int(row.get('HomePasses_2P',0) or 0); ap_2p = int(row.get('AwayPasses_2P',0) or 0)
    hsav = int(row.get('HomeSaves',0) or 0); asav = int(row.get('AwaySaves',0) or 0)
    hpos_pct = row.get('HomePos',''); apos_pct = row.get('AwayPos','')

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

    MORADO_STYLE = "color:#581C87; font-weight:900; font-size:9px;"
    hg_txt = f"<span style='{style_base}'>{hg_num}</span>"; ag_txt = f"<span style='{style_base}'>{ag_num}</span>"
    hpts_txt = f"<span style='{style_base}'>{hpts}</span>"; apts_txt = f"<span style='{style_base}'>{apts}</span>"
    hpos_txt = f"<span style='{MORADO_STYLE}'>{hpos}º</span>"; apos_txt = f"<span style='{MORADO_STYLE}'>{apos}º</span>"
    ht_txt = ht_disp; at_txt = at_disp
    home_perf_txt = f"<span style='{style_base}'>{home_perf:.1f}</span>"
    away_perf_txt = f"<span style='{style_base}'>{away_perf:.1f}</span>"

    if hg_num > ag_num:
        ht_txt = f"<span style='{style_ganador}'>{ht_disp}</span>"; hg_txt = f"<span style='{style_ganador}'>{hg_num}</span>"
        hpts_txt = f"<span style='{style_ganador}'>{hpts}</span>"
        # hpos_txt se queda morado, no lo toques
        home_perf_txt = f"<span style='{style_ganador}'>{home_perf:.1f}</span>"
    elif ag_num > hg_num:
        at_txt = f"<span style='{style_ganador}'>{at_disp}</span>"; ag_txt = f"<span style='{style_ganador}'>{ag_num}</span>"
        apts_txt = f"<span style='{style_ganador}'>{apts}</span>"
        # apos_txt se queda morado, no lo toques
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
    # NUEVO: pases/posesión/paradas
    extras = []
    # Si hay 1P/2P (ligas viejas) muestro desglose, si no solo totales (26/27)
    if hp_1p or ap_1p or hp_2p or ap_2p:
        extras.append(f"1P:{hp_1p}P-{ap_1p}P")
        extras.append(f"2P:{hp_2p}P-{ap_2p}P")
    elif hp or ap:
        extras.append(f"{hp}P-{ap}P")

    if str(hpos_pct).strip() not in ['', '0', '0.0', 'nan', 'None']:
        extras.append(f"{hpos_pct}% Pos {apos_pct}%")
    if hsav or asav:
        # 0 paradas es real, lo mostramos igual si hay pases para no confundir con falta de datos
        if hp or ap:
            extras.append(f"{hsav}Par-{asav}Par")
    extras_html = f"<div style='font-size:7px;color:#000'>{' | '.join(extras)}</div>" if extras else ""

    goles_html = f"<div style='font-size:9px;color:{NAVY};line-height:1.2;margin-top:2px'>{goles_txt}</div>" if goles_txt else ""
    return f'<div translate="no" lang="zxx" style="border-bottom:2px solid #000; padding-bottom:4px; margin-bottom:6px">{top_line}{date_line}{odds_html}{ht_line}{st_line}{ft_line}{pos_line}{pts_line}{perf_line}{stats_html}{extras_html}{goles_html}</div>'
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

@st.cache_data(show_spinner=False)
def calcular_estado_jornada(df):
    if df.empty or 'Date' not in df.columns:
        return df.copy(), pd.DataFrame()
    df = df.sort_values(['League','Season','Date']).copy()
    # 1) Jornada FIX V6 DEFINITIVO - esperado + tope real
    df['Jornada'] = 0
    for (l, s), g in df.groupby(['League','Season'], sort=False):
        g = g.sort_values(['Date','HomeTeam','AwayTeam'])
        if g.empty:
            continue
        teams = pd.unique(g[['HomeTeam','AwayTeam']].values.ravel())
        n_teams = len(teams)
        if n_teams < 2:
            continue

        # Jornadas reales de esa liga
        exp_jornadas = (n_teams - 1) * 2
        # Ej: 20 equipos=38, 22 equipos=42, 18 equipos=34
        if exp_jornadas < 10:
            exp_jornadas = 38
        partidos_por_jornada = n_teams // 2

        jornada = 1
        vistos = set()

        for idx in g.index:
            ht = df.loc[idx, 'HomeTeam']
            at = df.loc[idx, 'AwayTeam']

            if ht in vistos or at in vistos:
                jornada += 1
                if jornada > exp_jornadas:
                    jornada = exp_jornadas
                vistos = set()

            df.loc[idx, 'Jornada'] = jornada
            vistos.add(ht)
            vistos.add(at)

            if len(vistos) >= n_teams:
                if jornada < exp_jornadas:
                    jornada += 1
                vistos = set()
    df['Jornada'] = df['Jornada'].astype(int)
    

    # 2) Puntos del partido
    df['HPts'] = np.where(df['FTR']=='H', 3, np.where(df['FTR']=='D', 1, 0))
    df['APts'] = np.where(df['FTR']=='A', 3, np.where(df['FTR']=='D', 1, 0))

    # 3) Puntos previos - FIX: acumulado TOTAL por equipo (casa+fuera)
    _pts_acum = {}
    _home_prev = {}
    _away_prev = {}
    for _idx in df.sort_values(['League','Season','Date','Jornada']).index:
        _r = df.loc[_idx]
        _k_ht = (_r['League'], _r['Season'], _r['HomeTeam'])
        _k_at = (_r['League'], _r['Season'], _r['AwayTeam'])
        _home_prev[_idx] = _pts_acum.get(_k_ht, 0)
        _away_prev[_idx] = _pts_acum.get(_k_at, 0)
        _pts_acum[_k_ht] = _pts_acum.get(_k_ht, 0) + int(_r['HPts'])
        _pts_acum[_k_at] = _pts_acum.get(_k_at, 0) + int(_r['APts'])
    df['HomePtsPrev'] = pd.Series(_home_prev).reindex(df.index).fillna(0).astype(int)
    df['AwayPtsPrev'] = pd.Series(_away_prev).reindex(df.index).fillna(0).astype(int)

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

@st.cache_data(show_spinner=False)
def get_df_base_calculado(_df, ligas_tuple, temps_tuple):
    df_fil = _df[_df['League'].isin(ligas_tuple) & _df['Season'].isin(temps_tuple)]
    return calcular_estado_jornada(df_fil)
 

def limpiar_filtros():
    st.session_state.seguidos_filtro = "-"
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






# --- FIX MOVIL: buster de cache basado en fecha/tamaño del CSV para que vea lo nuevo de GitHub ---
try:
    import pathlib
    _BASE_TMP = pathlib.Path(__file__).parent.resolve()
    _p1 = _BASE_TMP / "ligas_2122_a_2627_SIN_DUPLICADOS.csv"
    _p2 = _BASE_TMP / "partidos_2627_actual.csv"
    _buster = 0
    if _p1.exists():
        _buster = int(_p1.stat().st_mtime) + int(_p1.stat().st_size)
    if _p2.exists():
        _buster += int(_p2.stat().st_mtime)
except:
    _buster = 0

try:
    df = cargar_todo(_cache_buster=_buster)
except Exception as e:
    st.error(f"Error carga: {e}")
    import traceback
    st.code(traceback.format_exc()[:1000])
    df = pd.DataFrame()
df_original = df.copy() if not df.empty else pd.DataFrame()

if df.empty or 'League' not in df.columns:
    st.error("DF vacio - pon ligas_2122_a_2526.csv + partidos_2627_actual.csv o ligas_2122_a_2627_COMPLETO.csv en app/")
    st.stop()

with st.expander("Filtros de partidos", expanded=False):
    ligas_disponibles = sorted([str(x) for x in df['League'].dropna().unique()])
    temporadas_disponibles = sorted([str(x) for x in df['Season'].dropna().unique()])
    st.success(f"✅ CSV: {len(df)} filas | {len(ligas_disponibles)} LIGAS | {len(temporadas_disponibles)} TEMPORADAS - 26/27 YA DISPONIBLE")
    st.info(f"LIGAS: {', '.join(ligas_disponibles[:10])}... total {len(ligas_disponibles)}")
    st.info(f"TEMPORADAS: {', '.join(temporadas_disponibles)}")
    # DEBUG: fuerza que salga 2026/2027 si esta en el CSV
    st.sidebar.write(f"DEBUG FILTROS: {len(ligas_disponibles)} ligas | Temps {temporadas_disponibles}")
    if '2026/2027' not in temporadas_disponibles:
        st.sidebar.error("2026/2027 NO esta en df['Season'] - revisa CSV")
    # Muestra equipos nuevos si estan
    if 'Eredivisie' in ligas_disponibles:
        eq_ered = sorted(df[df['League']=='Eredivisie']['HomeTeam'].unique())
        st.sidebar.write(f"Eredivisie equipos: {eq_ered[:20]}")
    # Busca VOLENDAM TELSTAR
    for team in ['VOLENDAM','TELSTAR','HERACLES']:
        if team in df['HomeTeam'].values or team in df['AwayTeam'].values:
            st.sidebar.success(f"Equipo {team} ENCONTRADO")
        else:
            st.sidebar.warning(f"Equipo {team} NO encontrado")

    st.caption(f"Ligas detectadas: {', '.join(ligas_disponibles)} | Total {len(ligas_disponibles)}")

    st.markdown("**Liga**")
    # FIX MOVIL: traductor B1,D1,E0 -> nombre real - NO ROMPE NADA - VERSION LIMPIA
    MAPA_CODIGOS_VIEJOS = {
        "B1":"Jupiler Pro League", "D1":"Bundesliga", "D2":"2. Bundesliga",
        "E0":"Premier League", "E1":"Championship", "E2":"League One", "E3":"League Two", "EC":"Conference",
        "F1":"Ligue 1", "F2":"Ligue 2", "G1":"Super League Grecia", "I1":"Serie A Italia", "I2":"Serie B Italia",
        "N1":"Eredivisie", "P1":"Liga Portugal", "SC0":"Premiership Escocia", "SC1":"Championship Escocia",
        "SP1":"LaLiga EA Sports", "SP2":"LaLiga Hypermotion", "T1":"Süper Lig",
        "SC2":"Saudi Professional League", "SC3":"Saudi Second Division League"
    }
    if 'filtro_liga_main' in st.session_state:
        try:
            _val = st.session_state['filtro_liga_main']
            if isinstance(_val, list) and len(_val) > 0 and _val[0] in MAPA_CODIGOS_VIEJOS:
                _new = [MAPA_CODIGOS_VIEJOS.get(x, x) for x in _val]
                _new = [x for x in _new if x in ligas_disponibles]
                st.session_state['filtro_liga_main'] = _new if _new else (ligas_disponibles if ligas_disponibles else [])
        except:
            pass
    _def_liga = ligas_disponibles if ligas_disponibles else []
    liga_sel = st.multiselect("Liga", ligas_disponibles, default=_def_liga, key="filtro_liga_main", on_change=persistir)

    st.markdown("**Temporada**")
    # DEFAULT: 2026/2027 si existe, si no la última
    _def_temp = ["2026/2027"] if "2026/2027" in temporadas_disponibles else ([temporadas_disponibles[-1]] if temporadas_disponibles else [])
    temp_sel = st.multiselect("Temporada", temporadas_disponibles, default=_def_temp, label_visibility="collapsed", key="filtro_temp_main", on_change=persistir)
    modo_vista = "Jornadas"

    st.info(f"SELECCION ACTUAL: Liga={liga_sel} | Temp={temp_sel} | Filas={len(df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)])}")
    df_fil = df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)]

    if df_fil.empty:
        st.warning("Selecciona al menos 1 liga y 1 temporada")
        st.stop()

    # calcular_estado_jornada_rapido eliminado - usamos get_df_base_calculado (1 solo cache)


    with st.spinner('Calculando clasificación...'):
        df_base, df_clas_base = get_df_base_calculado(df, tuple(liga_sel), tuple(temp_sel))


    df_final = df_base.copy()
    df_clasificacion = df_clas_base.copy()
    
    jornadas = sorted(df_final['Jornada'].unique())  # <-- ESTA LÍNEA FALTABA
    

    if len(jornadas) > 0:
        min_j = 1
        max_j = int(max(jornadas))

        # Solo inicializa si no existe, nunca reescribas después del widget
        if 'j_desde' not in st.session_state:
            st.session_state.j_desde = min_j
        if 'j_hasta' not in st.session_state:
            st.session_state.j_hasta = max_j
        if 'firma_jornadas_auto' not in st.session_state:
            st.session_state.firma_jornadas_auto = ""

        firma_jornadas = f"{','.join(sorted(liga_sel))}|{','.join(sorted(temp_sel))}"
        if st.session_state.firma_jornadas_auto!= firma_jornadas:
            st.session_state.j_desde = min_j
            st.session_state.j_hasta = max_j
            st.session_state.firma_jornadas_auto = firma_jornadas

        col_j1, col_j2 = st.columns(2)
        col_j1.number_input("Jornada De", min_value=min_j, max_value=max_j, key='j_desde', step=1, on_change=persistir)
        col_j2.number_input("Jornada A", min_value=min_j, max_value=max_j, key='j_hasta', step=1, on_change=persistir)

        # Leemos del session_state que ya escribió el widget
        j_desde = int(st.session_state.j_desde)
        j_hasta = int(st.session_state.j_hasta)

        if j_desde > j_hasta:
            j_desde = j_hasta
            st.session_state.j_hasta = j_desde

        # Clamp por seguridad por si viene de URL vieja
        j_desde = max(min_j, min(j_desde, max_j))
        j_hasta = max(min_j, min(j_hasta, max_j))

        rango_jornadas = (int(j_desde), int(j_hasta))
    else:
        rango_jornadas = (0, 0)

    # --- NUEVO: TEMPORADA% ---
    # 0% = J1, 100% = ultima jornada del rango actual (ej J30)
    st.markdown("**Temporada%**")
    pct_ops = ["-"] + list(range(0, 101, 5))
    col_tp1, col_tp2 = st.columns(2)
    temp_pct_desde = col_tp1.selectbox("De %", pct_ops, key='temp_pct_desde')
    temp_pct_hasta = col_tp2.selectbox("A %", pct_ops, key='temp_pct_hasta')

    # conversion % -> jornada real
    def _pct_a_jornada(pct_val, _min_j, _max_j):
        if str(pct_val) == "-":
            return None
        try:
            p = int(pct_val)
        except:
            return None
        if p <= 0:
            return _min_j
        if p >= 100:
            return _max_j
        # formula: J = min + (max-min)*p/100
        return int(round(_min_j + (_max_j - _min_j) * p / 100.0))

    if len(jornadas) > 0:
        _j_desde_pct = _pct_a_jornada(temp_pct_desde, min_j, max_j)
        _j_hasta_pct = _pct_a_jornada(temp_pct_hasta, min_j, max_j)
        # logica de rango porcentual
        if _j_desde_pct is None and _j_hasta_pct is None:
            rango_jornadas_pct = None # sin efecto
        elif _j_desde_pct is not None and _j_hasta_pct is None:
            rango_jornadas_pct = (_j_desde_pct, max_j)
        elif _j_desde_pct is None and _j_hasta_pct is not None:
            rango_jornadas_pct = (min_j, _j_hasta_pct)
        else:
            # ambos definidos, asegura De <= A
            if _j_desde_pct > _j_hasta_pct:
                _j_desde_pct, _j_hasta_pct = _j_hasta_pct, _j_desde_pct
            rango_jornadas_pct = (_j_desde_pct, _j_hasta_pct)
    else:
        rango_jornadas_pct = None

    if rango_jornadas_pct:
        st.caption(f"Temp% {temp_pct_desde}-{temp_pct_hasta}% => J{rango_jornadas_pct[0]} - J{rango_jornadas_pct[1]}")
    st.session_state['rango_jornadas_pct'] = rango_jornadas_pct if 'rango_jornadas_pct' in locals() else None
    # --- FIN TEMPORADA% ---

    # --- RANGO CUOTAS CON CAJITAS ---
    col_c1, col_c2 = st.columns(2)
    # Usa rango_cuotas como fuente, no session_state directo para evitar conflicto
    _def_desde = st.session_state.rango_cuotas[0] if 'rango_cuotas' in st.session_state else 1.01
    cuota_desde = col_c1.number_input(
        "Cuota De",
        min_value=1.01,
        max_value=100.0,
        value=float(_def_desde),
        step=0.05,
        key='cuota_desde_fix'
    )
    _def_hasta = st.session_state.rango_cuotas[1] if 'rango_cuotas' in st.session_state else 100.0
    cuota_hasta = col_c2.number_input(
        "Cuota A",
        min_value=1.01,
        max_value=100.0,
        value=float(_def_hasta),
        step=0.05,
        key='cuota_hasta_fix'
    )

    if cuota_desde > cuota_hasta:
        st.warning("Cuota 'De' no puede ser mayor que 'A'")
        cuota_desde = cuota_hasta

    rango_cuotas = (float(cuota_desde), float(cuota_hasta))
    try:
        st.session_state.rango_cuotas = rango_cuotas
    except:
        pass
    # --- FIN RANGO CUOTAS ---
    # --- NUEVO: ULTIMAS JORNADAS ---
    st.markdown("**Ultimas jornadas**")
    ultimas_jornadas_filtro = st.selectbox(
        "Ultimas jornadas",
        ["-"] + list(range(1, 41)),
        key='ultimas_jornadas_filtro',
        label_visibility="collapsed"
    )
    # mantenemos rango_minutos fijo para no romper goles
    rango_minutos = (0, 120)
    st.session_state.rango_minutos = rango_minutos

# --- CIERRE EXPANDER FILTROS DE PARTIDOS PARA FIX CLOUD ---
#########filtro rango de ultimas jornadas
if len(jornadas) > 0:
    df_final = df_final[(df_final['Jornada'] >= rango_jornadas[0]) & (df_final['Jornada'] <= rango_jornadas[1])]
    df_clasificacion = df_clasificacion[(df_clasificacion['Jornada'] >= rango_jornadas[0]) & (df_clasificacion['Jornada'] <= rango_jornadas[1])]
    # --- FILTRO TEMPORADA% ---
    _pct_range = st.session_state.get('rango_jornadas_pct', None)
    if _pct_range is not None:
        df_final = df_final[(df_final['Jornada'] >= _pct_range[0]) & (df_final['Jornada'] <= _pct_range[1])]
        df_clasificacion = df_clasificacion[(df_clasificacion['Jornada'] >= _pct_range[0]) & (df_clasificacion['Jornada'] <= _pct_range[1])]

    # --- FILTRO ULTIMAS X JORNADAS ---
    if str(st.session_state.get('ultimas_jornadas_filtro', '-'))!= "-":
        try:
            x = int(st.session_state.ultimas_jornadas_filtro)
            max_jor = df_final.groupby(['League','Season'])['Jornada'].transform('max')
            df_final = df_final[df_final['Jornada'] >= (max_jor - x + 1)]
            max_jor_clas = df_clasificacion.groupby(['League','Season'])['Jornada'].transform('max')
            df_clasificacion = df_clasificacion[df_clasificacion['Jornada'] >= (max_jor_clas - x + 1)]
        except:
            pass

    df_base_h2h = df_final.copy()

    todos_eventos = {}
    for liga in liga_sel:
        for temp in temp_sel:
            todos_eventos.update(cargar_eventos(liga, temp))
#########filtro rango de ultimas jornadas
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
    if 'clasif_eq1_modo' not in st.session_state: st.session_state.clasif_eq1_modo = "-"
    if 'clasif_eq1_de' not in st.session_state: st.session_state.clasif_eq1_de = 0
    if 'clasif_eq1_a' not in st.session_state: st.session_state.clasif_eq1_a = 100


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
    # FIX: muestra todos los equipos historicos de la liga seleccionada, no solo de la temp seleccionada, para que aparezca VOLENDAM aunque 26/27 solo tenga 9 partidos
    try:
        _df_teams_source = df[df['League'].isin(liga_sel)] if liga_sel else df
        equipos_disponibles = sorted(pd.unique(_df_teams_source[['HomeTeam','AwayTeam']].values.ravel()))
    except:
        equipos_disponibles = sorted(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

    opciones_1x2 = ["Ninguno","Gana","Pierde","Empata","Gana/Empata","Gana/Pierde","Empata/Pierde"]
    mapa_1x2 = {"Ninguno":"-", "Gana":"G", "Pierde":"P", "Empata":"E", "Gana/Empata":"GE", "Gana/Pierde":"GP", "Empata/Pierde":"EP"}
    ABREV_MARGEN = {"Todo":"—","Empate":"E","Gana 1":"G1","Gana 2":"G2","Gana 3+":"G3+","Pierde 1":"P1","Pierde 2":"P2","Pierde 3+":"P3+","Gana ≥2":"G2+","Pierde ≥2":"P2+"}
# COMIENZA TODO FILTROS AVANZADOS - YA FUERA, SIN NESTED
############filtros avanzados

with st.expander("🎛 Filtros avanzados", expanded=False):
        # --- LINEA 1: Eq1 Eq2 ---
        l1 = st.columns(2)
        equipo_filtro = l1[0].selectbox("Eq1", ["Ninguno"] + equipos_disponibles, key='equipo_filtro')
        equipo2_filtro = l1[1].selectbox("Eq2", ["Ninguno"] + equipos_disponibles, key='equipo2_filtro')

        # --- LINEA 1b: L/V... L/V3 ---
        l1b = st.columns(2)
        condicion_filtro = l1b[0].selectbox("L/V", ["Todo", "Local", "Visitante"], key='condicion_filtro')
        condicion_filtro3 = l1b[1].selectbox("L/V3", ["Todo", "Local", "Visitante"], key='condicion_filtro3')

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
        if 'seguidos_filtro' not in st.session_state:
            st.session_state.seguidos_filtro = "-"
        l7b = st.columns(3)
        margen_filtro = l7b[0].selectbox("Margen G|P|1T-2T", list(ABREV_MARGEN.keys()), format_func=lambda x: ABREV_MARGEN.get(x, x), key='margen_filtro')
        htft_filtro = l7b[1].selectbox("R=HT/FT", ["Todo","G/G","G/E","G/P","E/G","E/E","E/P","P/G","P/E","P/P","RE","FAIL"], key='htft_filtro')
        margen_filtro_eq2 = l7b[2].selectbox("Margen G|P|1T-2T Eq2", list(ABREV_MARGEN.keys()), format_func=lambda x: ABREV_MARGEN.get(x, x), key='margen_filtro_eq2')

        # --- LINEA 7c: SEGUIDOS + %Clasif Eq1 + %Temp Eq1 = 3 POR LINEA SIN HUECOS ---
        l7c = st.columns(3)
        seguidos_filtro = l7c[0].selectbox("Seguidos partidos", ["-"] + list(range(1, 101)), key='seguidos_filtro')

        with l7c[1]:
            st.markdown("<div style='font-size:10px'>%Clasif Eq1</div>", unsafe_allow_html=True)
            st.selectbox("modo_clasif", ["-", "Rango"], key='clasif_eq1_modo', label_visibility="collapsed")
            if st.session_state.clasif_eq1_modo == "Rango":
                st.markdown("<div style='font-size:9px;margin:2px 0 -2px 0'>De (min)</div>", unsafe_allow_html=True)
                st.number_input("De_min", 0, 100, key='clasif_eq1_de', label_visibility="collapsed")
                st.markdown("<div style='font-size:9px;margin:6px 0 -2px 0'>A (max)</div>", unsafe_allow_html=True)
                st.number_input("A_max", 0, 100, key='clasif_eq1_a', label_visibility="collapsed")

        with l7c[2]:
            st.empty()
        # --- LINEA 8: Marcador Parte Eq1 Parte Eq2 % ---
        marcadores_ft = sorted(
            (df_final['FTHG'].astype(int).astype(str) + '-' + df_final['FTAG'].astype(int).astype(str)).unique(),
            key=lambda s: (int(s.split('-')[0]), int(s.split('-')[1]))
        )
        marcadores_ht = sorted(
            (df_final['HTHG'].astype(int).astype(str) + '-' + df_final['HTAG'].astype(int).astype(str)).unique(),
            key=lambda s: (int(s.split('-')[0]), int(s.split('-')[1]))
        )
        marcadores_1t = [f"{m} 1T" for m in marcadores_ht]
        marcadores_combinados = ["Todos"] + marcadores_ft + marcadores_1t

        l8 = st.columns(5)
        marcador_filtro = l8[0].selectbox("Marc Eq1", marcadores_combinados, key='marcador_filtro')
        marcador_filtro_eq2 = l8[1].selectbox("Marc Eq2", marcadores_combinados, key='marcador_filtro_eq2')
        parte_gol = l8[2].selectbox("Parte Eq1", ["Todo","1T","2T"], key='parte_gol')
        parte_gol_eq2 = l8[3].selectbox("Parte Eq2", ["Todo","1T","2T"], key='parte_gol_eq2')
        with l8[4]:
            st.caption("% De - A")
            c_p1, c_p2 = st.columns(2)
            # por defecto 1% a 100% - FIX seguro para móvil
            def _safe_pct(v, default):
                try:
                    return int(float(str(v).strip()))
                except:
                    return default
            # limpia si vienen como texto desde la URL - init seguro
            if 'pct_min' not in st.session_state:
                st.session_state.pct_min = 1
            if 'pct_max' not in st.session_state:
                st.session_state.pct_max = 100
            # si venía guardado con 70 por defecto, resetea a 1 para que no tape todo
            if st.session_state.get('pct_min', 1) == 70 and st.session_state.get('pct_max', 100) == 100:
                # solo la primera vez, luego respeta lo que pongas
                if 'pct_fix_70' not in st.session_state:
                    st.session_state.pct_min = 1
                    st.session_state.pct_fix_70 = True
            st.session_state.pct_min = _safe_pct(st.session_state.get('pct_min', 70), 1)
            st.session_state.pct_max = _safe_pct(st.session_state.get('pct_max', 100), 100)

            pct_min = c_p1.number_input("min", min_value=0, max_value=100, value=int(st.session_state.get('pct_min', 70)), step=5, key='pct_min_fix', label_visibility="collapsed")
            pct_max = c_p2.number_input("max", min_value=0, max_value=100, value=int(st.session_state.get('pct_max', 100)), step=5, key='pct_max_fix', label_visibility="collapsed")

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



# --- CIERRE FORZADO DE Filtros de partidos ---
# todo lo de arriba era dentro del expander, aquí ya estamos FUERA

col_limp, col_save = st.columns(2)
with col_limp:
    st.button("Limpiar", on_click=limpiar_filtros, use_container_width=True)
with col_save:
    if st.button("💾 Guardar 2h+", use_container_width=True):
        persistir()
        st.toast("Filtros guardados")

####################FIN FILTROS AVANZADOS BLOQUE ENTERO

# --- RESUMEN DE FILTROS ACTIVOS - SIEMPRE VISIBLE FUERA DE EXPANDERS ---
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
    es_cuota_default = (rango_cuotas[0]<=1.01 and rango_cuotas[1]<=1.01) or (rango_cuotas[0]<=1.01 and rango_cuotas[1]>=99)
    if cuota_tipo not in ["Ninguno","Todo"] and not es_cuota_default:
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

       # --- RESUMEN FILTROS SIMPLE 2 LINEAS - FIX FINAL + MARC EQ2 + TEMP Y J ---
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
    # FIX: esconder cuotas cuando es el default 1.01-1.01 o 1.01-100 o Todo/Ninguno
    es_cuota_default = (rango_cuotas[0]<=1.01 and rango_cuotas[1]<=1.01) or (rango_cuotas[0]<=1.01 and rango_cuotas[1]>=99)
    if cuota_tipo not in ["Ninguno","Todo"] and not es_cuota_default:
        comunes.append(f"Cuotas:{rango_cuotas[0]}-{rango_cuotas[1]}")
    if jugador_filtro!="TODOS": comunes.append(f"Jug:{jugador_filtro}")
    if str(ultimos_part_filtro)!="Todos":
        if str(st.session_state.get('margen_jornadas_filtro',"Todos"))!="Todos":
            comunes.append(f"Ult:{ultimos_part_filtro}/{st.session_state.get('margen_jornadas_filtro')}J")
        else:
            comunes.append(f"Ult:{ultimos_part_filtro}")

    # --- AÑADIDO TEMP, J, ULTIMAS, MARGEN Y SEGUIDOS - FIX MOSTRAR SIEMPRE ---
    temp_txt = ", ".join(temp_sel) if 'temp_sel' in locals() and temp_sel else "-"
    j_txt = f"J{rango_jornadas[0]} - J{rango_jornadas[1]}" if 'rango_jornadas' in locals() else "-"
    ult_val = str(st.session_state.get('ultimas_jornadas_filtro', '-'))
    ult_txt = "-" if ult_val=="-" or ult_val=="" else f"Ult {ult_val}J"

    margen_resumen = []
    if 'margen_filtro' in locals() and margen_filtro!= "Todo":
        margen_resumen.append(f"Eq1:{margen_filtro}")
    if 'margen_filtro_eq2' in locals() and margen_filtro_eq2!= "Todo":
        margen_resumen.append(f"Eq2:{margen_filtro_eq2}")
    margen_txt = " | ".join(margen_resumen) if margen_resumen else "-"

    # --- SEGUIDOS - SIEMPRE VISIBLE Y DESDE SESSION_STATE ---
    seg_val = str(st.session_state.get('seguidos_filtro', '-'))
    seguidos_txt = "-" if seg_val=="-" or seg_val=="" else f"{seg_val} seguidos"
    if seg_val!="-" and seg_val!="":
        if f"Seg:{seg_val}" not in comunes:
            comunes.append(f"Seg:{seg_val}")

    # --- %Clasif Eq1 para resumen ---
    clasif_resumen_txt = "-"
    if st.session_state.get('clasif_eq1_modo', '-') == "Rango":
        de_c = st.session_state.get('clasif_eq1_de', 0)
        a_c = st.session_state.get('clasif_eq1_a', 100)
        clasif_resumen_txt = f"{de_c}-{a_c}% del lider"
        if f"%Clasif:{de_c}-{a_c}%" not in comunes:
            comunes.append(f"%Clasif:{de_c}-{a_c}%")

    # --- LIGAS DE FILTROS DE PARTIDOS ---
    ligas_txt = ", ".join(liga_sel) if 'liga_sel' in locals() and liga_sel else "Todas"

    # --- TEXTO TEMPORADA% PARA RESUMEN ---
    _tp_d = str(st.session_state.get('temp_pct_desde', '-'))
    _tp_h = str(st.session_state.get('temp_pct_hasta', '-'))
    if _tp_d == "-" and _tp_h == "-":
        temp_pct_txt = "-"
    else:
        temp_pct_txt = f"{_tp_d}% - {_tp_h}%"
        if 'rango_jornadas_pct' in locals() and rango_jornadas_pct is not None:
            temp_pct_txt += f" (J{rango_jornadas_pct[0]}-J{rango_jornadas_pct[1]})"

    if eq1_list or eq2_list or comunes or temp_sel:
        txt = "<div style='font-size:10px; line-height:1.3; font-family:monospace; padding:2px 0'>filtros:<br>"
        txt += f"Ligas: {ligas_txt}<br>"
        txt += f"Temp: {temp_txt}<br>"
        txt += f"J: {j_txt}<br>"
        txt += f"Temporada%: {temp_pct_txt}<br>"
        txt += f"Ultimas jornadas: {ult_txt}<br>"
        txt += f"Margen: {margen_txt}<br>"
        txt += f"%Clasif Eq1: {clasif_resumen_txt}<br>"
        if eq1_list:
            txt += "eq1: " + " | ".join(eq1_list) + "<br>"
        txt += f"Seguidos: {seguidos_txt}<br>"
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





# === FILTRO EQUIPOS BASE + FILTROS AVANZADOS UNIFICADO - FIX FINAL L/V + AND ===
import re

def _parse_alcance(alc_str):
    s = str(alc_str)
    m = re.match(r'^(AF|C)(\d+(\.\d+)?)?$', s)
    if s in ("AF","C","Todo"): return s, None
    if m:
        tipo = m.group(1)
        if m.group(2):
            try: return tipo, float(m.group(2))
            except: return tipo, None
        return tipo, None
    return "Todo", None

def _mask_1x2(df_in, eq, modo, cond_lv="Todo"):
    if modo=="Ninguno" or df_in.empty: 
        return pd.Series(True, index=df_in.index)
    if eq=="Ninguno":
        if cond_lv=="Local":
            return df_in['FTR']=='H'
        if cond_lv=="Visitante":
            return df_in['FTR']=='A'
        return pd.Series(True, index=df_in.index)
    es_loc = df_in['HomeTeam']==eq
    if modo=="Gana": return (es_loc & (df_in['FTR']=='H')) | (~es_loc & (df_in['FTR']=='A'))
    if modo=="Pierde": return (es_loc & (df_in['FTR']=='A')) | (~es_loc & (df_in['FTR']=='H'))
    if modo=="Empata": return df_in['FTR']=='D'
    if modo=="Gana/Empata": return ~((es_loc & (df_in['FTR']=='A')) | (~es_loc & (df_in['FTR']=='H')))
    if modo=="Gana/Pierde": return df_in['FTR']!='D'
    if modo=="Empata/Pierde": return ~((es_loc & (df_in['FTR']=='H')) | (~es_loc & (df_in['FTR']=='A')))
    return pd.Series(True, index=df_in.index)

def _mask_am(df_in, modo, parte, eq="Ninguno", cond_lv="Todo"):
    if modo=="Todos" or df_in.empty: return pd.Series(True, index=df_in.index)
    am_1p = (df_in['HTHG']>0) & (df_in['HTAG']>0)
    am_2p = ((df_in['FTHG']-df_in['HTHG'])>0) & ((df_in['FTAG']-df_in['HTAG'])>0)
    am_ft = (df_in['FTHG']>0) & (df_in['FTAG']>0)
    if modo=="Si": return am_ft
    if modo=="No": return ~am_ft
    if modo=="Si1P": return am_1p
    if modo=="No1P": return ~am_1p
    if modo=="Si2P": return am_2p
    if modo=="No2P": return ~am_2p
    if modo=="Si1pNo2p": return am_1p & ~am_2p
    if modo=="No1pSi2p": return ~am_1p & am_2p
    if modo=="Si1pSi2p": return am_1p & am_2p
    return pd.Series(True, index=df_in.index)

def _mask_xx(df_in, eq, modo, cond_lv="Todo"):
    if modo=="Todo" or df_in.empty: return pd.Series(True, index=df_in.index)
    if eq=="Ninguno":
        if cond_lv=="Local":
            ht_g = df_in['HTHG']>df_in['HTAG']; ht_p = df_in['HTHG']<df_in['HTAG']; ht_e = ~(ht_g|ht_p)
            ft_g = df_in['FTHG']>df_in['FTAG']; ft_p = df_in['FTHG']<df_in['FTAG']; ft_e = ~(ft_g|ft_p)
        elif cond_lv=="Visitante":
            ht_g = df_in['HTAG']>df_in['HTHG']; ht_p = df_in['HTAG']<df_in['HTHG']; ht_e = ~(ht_g|ht_p)
            ft_g = df_in['FTAG']>df_in['FTHG']; ft_p = df_in['FTAG']<df_in['FTHG']; ft_e = ~(ft_g|ft_p)
        else:
            ht_g = df_in['HTHG']>df_in['HTAG']; ht_p = df_in['HTHG']<df_in['HTAG']; ht_e = ~(ht_g|ht_p)
            ft_g = df_in['FTHG']>df_in['FTAG']; ft_p = df_in['FTHG']<df_in['FTAG']; ft_e = ~(ft_g|ft_p)
    else:
        es_loc = df_in['HomeTeam']==eq
        ht_g = np.where(es_loc, df_in['HTHG']>df_in['HTAG'], df_in['HTAG']>df_in['HTHG'])
        ht_p = np.where(es_loc, df_in['HTHG']<df_in['HTAG'], df_in['HTAG']<df_in['HTHG'])
        ht_e = ~(ht_g|ht_p)
        ft_g = np.where(es_loc, df_in['FTHG']>df_in['FTAG'], df_in['FTAG']>df_in['FTHG'])
        ft_p = np.where(es_loc, df_in['FTHG']<df_in['FTAG'], df_in['FTAG']<df_in['FTHG'])
        ft_e = ~(ft_g|ft_p)
    if modo=="G/X": return pd.Series(ht_g, index=df_in.index)
    if modo=="E/X": return pd.Series(ht_e, index=df_in.index)
    if modo=="P/X": return pd.Series(ht_p, index=df_in.index)
    if modo=="X/G": return pd.Series(ft_g, index=df_in.index)
    if modo=="X/E": return pd.Series(ft_e, index=df_in.index)
    if modo=="X/P": return pd.Series(ft_p, index=df_in.index)
    return pd.Series(True, index=df_in.index)

def _mask_htft(df_in, eq, modo, cond_lv="Todo"):
    if modo=="Todo" or df_in.empty: return pd.Series(True, index=df_in.index)
    if eq=="Ninguno":
        if cond_lv=="Local":
            ht_g=df_in['HTHG']>df_in['HTAG']; ht_p=df_in['HTHG']<df_in['HTAG']
            ft_g=df_in['FTHG']>df_in['FTAG']; ft_p=df_in['FTHG']<df_in['FTAG']
        elif cond_lv=="Visitante":
            ht_g=df_in['HTAG']>df_in['HTHG']; ht_p=df_in['HTAG']<df_in['HTHG']
            ft_g=df_in['FTAG']>df_in['FTHG']; ft_p=df_in['FTAG']<df_in['FTHG']
        else:
            ht_g=df_in['HTHG']>df_in['HTAG']; ht_p=df_in['HTHG']<df_in['HTAG']
            ft_g=df_in['FTHG']>df_in['FTAG']; ft_p=df_in['FTHG']<df_in['FTAG']
        ht_res=np.where(ht_g,'G',np.where(ht_p,'P','E'))
        ft_res=np.where(ft_g,'G',np.where(ft_p,'P','E'))
    else:
        es_loc=df_in['HomeTeam']==eq
        ht_g=np.where(es_loc, df_in['HTHG']>df_in['HTAG'], df_in['HTAG']>df_in['HTHG'])
        ht_p=np.where(es_loc, df_in['HTHG']<df_in['HTAG'], df_in['HTAG']<df_in['HTHG'])
        ht_res=np.where(ht_g,'G',np.where(ht_p,'P','E'))
        ft_g=np.where(es_loc, df_in['FTHG']>df_in['FTAG'], df_in['FTAG']>df_in['FTHG'])
        ft_p=np.where(es_loc, df_in['FTHG']<df_in['FTAG'], df_in['FTAG']<df_in['FTHG'])
        ft_res=np.where(ft_g,'G',np.where(ft_p,'P','E'))
    if modo=="RE": return pd.Series((ht_res!='G')&(ft_res=='G'), index=df_in.index)
    if modo=="FAIL": return pd.Series(((ht_res=='G')&(ft_res!='G'))|((ht_res=='E')&(ft_res=='P')), index=df_in.index)
    return pd.Series((ht_res+'/'+ft_res)==modo, index=df_in.index)

def _mask_margen(df_in, eq, margen_tipo, parte_tipo, cond_lv):
    if margen_tipo=="Todo" or df_in.empty: return pd.Series(True, index=df_in.index)
    if parte_tipo=="1T": gh=df_in['HTHG'].values; ga=df_in['HTAG'].values
    elif parte_tipo=="2T": gh=(df_in['FTHG']-df_in['HTHG']).values; ga=(df_in['FTAG']-df_in['HTAG']).values
    else: gh=df_in['FTHG'].values; ga=df_in['FTAG'].values
    if eq!="Ninguno":
        es_loc=(df_in['HomeTeam']==eq).values
        dif=np.where(es_loc, gh-ga, ga-gh)
    else:
        if cond_lv=="Local": dif=gh-ga
        elif cond_lv=="Visitante": dif=ga-gh
        else: dif=np.abs(gh-ga)  # FIX: para Todo cuenta ambos lados
        # FIX para Gana/Pierde con Todo
        if margen_tipo.startswith("Gana"):
            if margen_tipo=="Gana 1": return pd.Series(np.abs(gh-ga)==1, index=df_in.index)
            if margen_tipo=="Gana 2": return pd.Series(np.abs(gh-ga)==2, index=df_in.index)
            if margen_tipo=="Gana 3+": return pd.Series(np.abs(gh-ga)>=3, index=df_in.index)
            if margen_tipo=="Gana ≥2": return pd.Series(np.abs(gh-ga)>=2, index=df_in.index)
        if margen_tipo.startswith("Pierde"):
            return pd.Series(np.abs(gh-ga)>=1, index=df_in.index) # mismo que Gana para Todo
    if margen_tipo=="Empate": return pd.Series(dif==0, index=df_in.index)
    if eq=="Ninguno" and cond_lv=="Todo":
        if margen_tipo in ("Gana 1","Pierde 1"): return pd.Series(np.abs(dif)==1, index=df_in.index)
        if margen_tipo in ("Gana 2","Pierde 2"): return pd.Series(np.abs(dif)==2, index=df_in.index)
        if margen_tipo in ("Gana 3+","Pierde 3+"): return pd.Series(np.abs(dif)>=3, index=df_in.index)
        if margen_tipo in ("Gana \u22652","Pierde \u22652"): return pd.Series(np.abs(dif)>=2, index=df_in.index)
    if margen_tipo=="Gana 1": return pd.Series(dif==1, index=df_in.index)
    if margen_tipo=="Gana 2": return pd.Series(dif==2, index=df_in.index)
    if margen_tipo=="Gana 3+": return pd.Series(dif>=3, index=df_in.index)
    if margen_tipo=="Pierde 1": return pd.Series(dif==-1, index=df_in.index)
    if margen_tipo=="Pierde 2": return pd.Series(dif==-2, index=df_in.index)
    if margen_tipo=="Pierde 3+": return pd.Series(dif<=-3, index=df_in.index)
    if margen_tipo=="Gana \u22652": return pd.Series(dif>=2, index=df_in.index)
    if margen_tipo=="Pierde \u22652": return pd.Series(dif<=-2, index=df_in.index)
    return pd.Series(True, index=df_in.index)

def _mask_marcador(df_in, eq, marcador_txt, cond_lv="Todo"):
    if marcador_txt=="Todos" or df_in.empty:
        return pd.Series(True, index=df_in.index)

    txt = str(marcador_txt).strip()
    es_1t = txt.endswith("1T")
    clean = txt.replace(" 1T","").strip()

    try:
        gl, gv = map(int, clean.split('-'))
    except:
        return pd.Series(True, index=df_in.index)

    col_h, col_a = ('HTHG','HTAG') if es_1t else ('FTHG','FTAG')

    if eq=="Ninguno":
        if cond_lv=="Local": return (df_in[col_h]==gl) & (df_in[col_a]==gv)
        if cond_lv=="Visitante": return (df_in[col_h]==gv) & (df_in[col_a]==gl)
        return ((df_in[col_h]==gl) & (df_in[col_a]==gv)) | ((df_in[col_h]==gv) & (df_in[col_a]==gl))
    es_loc = df_in['HomeTeam']==eq
    return ((es_loc & (df_in[col_h]==gl) & (df_in[col_a]==gv)) | (~es_loc & (df_in[col_h]==gv) & (df_in[col_a]==gl)))

def _get_base_col(df_in, col, eq, alcance_str, cond_lv="Todo"):
    es_loc = df_in['HomeTeam']==eq if eq!="Ninguno" else None
    tipo, val_fijo = _parse_alcance(alcance_str)

    # Mapa de totales -> (casa, fuera) real
    TOT_MAP = {
        'corneTot':('HC','AC'),
        'tirosTot':('HS','AS'),
        'tirosPuertaTot':('HST','AST'),
        'faltasTot':('HF','AF'),
        'TargAmTot':('HY','AY'),
        'TargRojTot':('HR','AR'),
        'GolesTotales':('FTHG','FTAG'),
        'GolesHT':('HTHG','HTAG'),
    }

    def _retorna(vh, va, es_loc, cond_lv, es_total=False, af_arr=None, c_arr=None, tot_arr=None):
        if es_total:
            # Para totales, AF = del equipo, C = del rival, Todo = suma
            if eq!="Ninguno":
                if tipo=="AF": return af_arr
                if tipo=="C": return c_arr
                return tot_arr
            else:
                if cond_lv=="Local":
                    if tipo=="AF": return vh
                    if tipo=="C": return va
                    return vh+va
                elif cond_lv=="Visitante":
                    if tipo=="AF": return va
                    if tipo=="C": return vh
                    return vh+va
                else:
                    if tipo=="AF": return np.maximum(vh, va)
                    if tipo=="C": return np.minimum(vh, va)
                    return vh+va
        else:
            if eq!="Ninguno":
                if tipo=="AF": return np.where(es_loc, vh, va)
                if tipo=="C": return np.where(es_loc, va, vh)
                return vh+va if col in ['GolesHT','GolesTotales','Goles2T','corneTot'] else np.where(es_loc, vh, va)
            else:
                if cond_lv=="Local":
                    if tipo=="AF": return vh
                    if tipo=="C": return va
                    return vh+va if col in ['GolesHT','GolesTotales'] else vh
                elif cond_lv=="Visitante":
                    if tipo=="AF": return va
                    if tipo=="C": return vh
                    return vh+va if col in ['GolesHT','GolesTotales'] else va
                else:
                    if tipo=="AF": return np.maximum(vh, va)
                    if tipo=="C": return np.minimum(vh, va)
                    return vh+va

    # Caso especial totales
    if col in TOT_MAP:
        cH, cA = TOT_MAP[col]
        if col == 'Goles2T':
            vh = (df_in['FTHG']-df_in['HTHG']).values
            va = (df_in['FTAG']-df_in['HTAG']).values
        elif col == 'GolesHT':
            vh = df_in['HTHG'].values
            va = df_in['HTAG'].values
        elif col == 'GolesTotales':
            vh = df_in['FTHG'].values
            va = df_in['FTAG'].values
        else:
            vh = df_in[cH].values if cH in df_in.columns else np.zeros(len(df_in))
            va = df_in[cA].values if cA in df_in.columns else np.zeros(len(df_in))
        # Calculo AF/C/TOT correcto
        if eq!="Ninguno":
            af_arr = np.where(es_loc, vh, va)
            c_arr = np.where(es_loc, va, vh)
            tot_arr = vh+va
        else:
            af_arr = vh
            c_arr = va
            tot_arr = vh+va
        return _retorna(vh, va, es_loc, cond_lv, es_total=True, af_arr=af_arr, c_arr=c_arr, tot_arr=tot_arr), val_fijo

    if col=='Goles2T': vh,va = (df_in['FTHG']-df_in['HTHG']).values, (df_in['FTAG']-df_in['HTAG']).values
    elif col=='GolesHT': vh,va = df_in['HTHG'].values, df_in['HTAG'].values
    elif col=='GolesTotales': vh,va = df_in['FTHG'].values, df_in['FTAG'].values
    else:
        mapa={'HC':'AC','AC':'HC','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
        contra=mapa.get(col,col)
        v1=df_in[col].values if col in df_in.columns else np.zeros(len(df_in))
        v2=df_in[contra].values if contra in df_in.columns else v1
        vh,va=v1,v2
    return _retorna(vh, va, es_loc, cond_lv), val_fijo

def _mask_columna(df_in, eq, col, op, val_str, alcance_str, cond_lv="Todo"):
    if col in ["Ninguno","_GOL_","_TARJ_","_TIR_","_CORN_","_FALT_","_CLASF_"] or val_str=="Ninguno" or df_in.empty:
        return pd.Series(True, index=df_in.index)
    base, val_fijo = _get_base_col(df_in, col, eq, alcance_str, cond_lv)
    try: val = float(val_fijo if val_fijo is not None else val_str)
    except: return pd.Series(True, index=df_in.index)
    if op=="=": return pd.Series(base==val, index=df_in.index)
    if op==">": return pd.Series(base>val, index=df_in.index)
    if op==">=": return pd.Series(base>=val, index=df_in.index)
    if op=="<": return pd.Series(base<val, index=df_in.index)
    if op=="<=": return pd.Series(base<=val, index=df_in.index)
    return pd.Series(True, index=df_in.index)

def _mask_cuota(df_in, tipo, rango, eq="Ninguno", cond_lv="Todo"):
    if df_in.empty:
        return pd.Series(True, index=df_in.index)
    if tipo in ["Ninguno","Todo","-",""]:
        return pd.Series(True, index=df_in.index)
    try:
        r0 = float(rango[0]); r1 = float(rango[1])
        # 1.01-1.01 o 1.01-100 = SIN FILTRO
        if (r0 <= 1.01 and r1 <= 1.01) or (r0 <= 1.01 and r1 >= 99):
            return pd.Series(True, index=df_in.index)
    except:
        return pd.Series(True, index=df_in.index)

    mapa_cuota = {"1":"B365H","X":"B365D","2":"B365A","Local":"B365H","Visitante":"B365A","Empate":"B365D"}
    col = mapa_cuota.get(str(tipo).strip())
    if not col or col not in df_in.columns:
        return pd.Series(True, index=df_in.index)

    vals = pd.to_numeric(df_in[col], errors='coerce').fillna(0)
    # solo cuotas válidas >1.0
    mask_rango = (vals >= float(rango[0])) & (vals <= float(rango[1])) & (vals > 1.0)
    return pd.Series(mask_rango.values, index=df_in.index)

def filtra_equipo(df_base, eq, cond_lv, res, am, parte, xx, htft, margen, marcador, col1, op1, val1, alc1, col2, op2, val2, alc2, col3, op3, val3, alc3, cuota_tipo, rango_cuotas):
    df = df_base.copy()
    if cond_lv=="Local": df = df[df['HomeTeam']==eq] if eq!="Ninguno" else df
    elif cond_lv=="Visitante": df = df[df['AwayTeam']==eq] if eq!="Ninguno" else df
    else: df = df[(df['HomeTeam']==eq)|(df['AwayTeam']==eq)] if eq!="Ninguno" else df
    if df.empty: return df
    df = df[_mask_1x2(df, eq, res, cond_lv)]
    df = df[_mask_am(df, am, parte, eq, cond_lv)]
    df = df[_mask_xx(df, eq, xx, cond_lv)]
    df = df[_mask_htft(df, eq, htft, cond_lv)]
    df = df[_mask_margen(df, eq, margen, parte, cond_lv)]
    df = df[_mask_marcador(df, eq, marcador, cond_lv)]
    df = df[_mask_columna(df, eq, col1, op1, val1, alc1, cond_lv)]
    df = df[_mask_columna(df, eq, col2, op2, val2, alc2, cond_lv)]
    df = df[_mask_columna(df, eq, col3, op3, val3, alc3, cond_lv)]
    df = df[_mask_cuota(df, cuota_tipo, rango_cuotas, eq, cond_lv)]
    return df

# --- APLICACION REAL - V2 INDEPENDIENTE (no rompe nada, solo hace OR) ---
df_base_h2h = df_final.copy()
df_base_h2h_lv = df_base_h2h.copy()

def _hay_filtros_eq1_v2():
    if columna_filtro!="Ninguno" and valor_filtro!="Ninguno": return True
    if columna_filtro2!="Ninguno" and valor_filtro2!="Ninguno": return True
    if resultado_filtro!="Ninguno": return True
    if ambos_marcan!="Todos": return True
    if xx_filtro!="Todo": return True
    if htft_filtro!="Todo": return True
    if margen_filtro!="Todo": return True
    if marcador_filtro!="Todos": return True
    if cuota_tipo not in ["Ninguno","Todo"]: return True
    return False

def _hay_filtros_eq2_v2():
    if columna_filtro3!="Ninguno" and valor_filtro3!="Ninguno": return True
    if resultado_filtro_eq2!="Ninguno": return True
    if ambos_marcan_eq2!="Todos": return True
    if margen_filtro_eq2!="Todo": return True
    if marcador_filtro_eq2!="Todos": return True
    return False

def _filtra_global_eq1_v2(df_in):
    df = df_in.copy()
    df = df[_mask_1x2(df, "Ninguno", resultado_filtro, condicion_filtro)]
    df = df[_mask_am(df, ambos_marcan, parte_gol, "Ninguno", condicion_filtro)]
    df = df[_mask_xx(df, "Ninguno", xx_filtro, condicion_filtro)]
    df = df[_mask_htft(df, "Ninguno", htft_filtro, condicion_filtro)]
    df = df[_mask_margen(df, "Ninguno", margen_filtro, parte_gol, condicion_filtro)]
    df = df[_mask_marcador(df, "Ninguno", marcador_filtro, condicion_filtro)]
    df = df[_mask_columna(df, "Ninguno", columna_filtro, operador_filtro, valor_filtro, alcance_filtro, condicion_filtro)]
    df = df[_mask_columna(df, "Ninguno", columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2, condicion_filtro)]
    df = df[_mask_cuota(df, cuota_tipo, rango_cuotas, "Ninguno", condicion_filtro)]
    return df

def _filtra_global_eq2_v2(df_in):
    df = df_in.copy()
    df = df[_mask_1x2(df, "Ninguno", resultado_filtro_eq2, condicion_filtro3)]
    df = df[_mask_am(df, ambos_marcan_eq2, parte_gol_eq2, "Ninguno", condicion_filtro3)]
    df = df[_mask_margen(df, "Ninguno", margen_filtro_eq2, parte_gol_eq2, condicion_filtro3)]
    df = df[_mask_marcador(df, "Ninguno", marcador_filtro_eq2, condicion_filtro3)]
    df = df[_mask_columna(df, "Ninguno", columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3, condicion_filtro3)]
    df = df[_mask_cuota(df, cuota_tipo, rango_cuotas, "Ninguno", condicion_filtro3)]
    return df

dfs_v2 = []

# CASO 1: los dos equipos puestos -> cada uno con SUS filtros solamente
if equipo_filtro!="Ninguno" and equipo2_filtro!="Ninguno":
    df_eq1 = filtra_equipo(df_base_h2h, equipo_filtro, condicion_filtro, resultado_filtro, ambos_marcan, parte_gol, xx_filtro, htft_filtro, margen_filtro, marcador_filtro, columna_filtro, operador_filtro, valor_filtro, alcance_filtro, columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2, "Ninguno","=","Ninguno","Todo", cuota_tipo, rango_cuotas)
    df_eq2 = filtra_equipo(df_base_h2h, equipo2_filtro, condicion_filtro3, resultado_filtro_eq2, ambos_marcan_eq2, parte_gol_eq2, xx_filtro, htft_filtro, margen_filtro_eq2, marcador_filtro_eq2, columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3, "Ninguno","=","Ninguno","Todo", "Ninguno","=","Ninguno","Todo", cuota_tipo, rango_cuotas)
    dfs_v2 = [df_eq1, df_eq2]

# CASO 2: solo Eq1 con equipo -> Eq1 con sus filtros + si Eq2 tiene filtros globales, añadelos también (OR)
elif equipo_filtro!="Ninguno":
    df_eq1 = filtra_equipo(df_base_h2h, equipo_filtro, condicion_filtro, resultado_filtro, ambos_marcan, parte_gol, xx_filtro, htft_filtro, margen_filtro, marcador_filtro, columna_filtro, operador_filtro, valor_filtro, alcance_filtro, columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2, "Ninguno","=","Ninguno","Todo", cuota_tipo, rango_cuotas)
    dfs_v2.append(df_eq1)
    if _hay_filtros_eq2_v2():
        dfs_v2.append(_filtra_global_eq2_v2(df_base_h2h))

# CASO 3: solo Eq2 con equipo -> igual
elif equipo2_filtro!="Ninguno":
    df_eq2 = filtra_equipo(df_base_h2h, equipo2_filtro, condicion_filtro3, resultado_filtro_eq2, ambos_marcan_eq2, parte_gol_eq2, xx_filtro, htft_filtro, margen_filtro_eq2, marcador_filtro_eq2, columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3, "Ninguno","=","Ninguno","Todo", "Ninguno","=","Ninguno","Todo", cuota_tipo, rango_cuotas)
    dfs_v2.append(df_eq2)
    if _hay_filtros_eq1_v2():
        dfs_v2.append(_filtra_global_eq1_v2(df_base_h2h))

# CASO 4: ningún equipo -> si hay filtros en Eq1 y Eq2, une ambos (OR), si no, comportamiento antiguo
else:
    if _hay_filtros_eq1_v2() and _hay_filtros_eq2_v2():
        dfs_v2 = [_filtra_global_eq1_v2(df_base_h2h), _filtra_global_eq2_v2(df_base_h2h)]
    elif _hay_filtros_eq1_v2():
        dfs_v2 = [_filtra_global_eq1_v2(df_base_h2h)]
    elif _hay_filtros_eq2_v2():
        dfs_v2 = [_filtra_global_eq2_v2(df_base_h2h)]
    else:
        df_final = df_base_h2h.copy()
        df_final = df_final[_mask_1x2(df_final, "Ninguno", "Ninguno", condicion_filtro)]
        df_final = df_final[_mask_am(df_final, ambos_marcan, parte_gol, "Ninguno", condicion_filtro)]
        if ambos_marcan_eq2!="Todos":
            df_final = df_final[_mask_am(df_final, ambos_marcan_eq2, parte_gol_eq2, "Ninguno", condicion_filtro3)]
        df_final = df_final[_mask_xx(df_final, "Ninguno", xx_filtro, condicion_filtro)]
        df_final = df_final[_mask_htft(df_final, "Ninguno", htft_filtro, condicion_filtro)]
        df_final = df_final[_mask_margen(df_final, "Ninguno", margen_filtro, parte_gol, condicion_filtro)]
        if margen_filtro_eq2!="Todo":
            df_final = df_final[_mask_margen(df_final, "Ninguno", margen_filtro_eq2, parte_gol_eq2, condicion_filtro3)]
        df_final = df_final[_mask_marcador(df_final, "Ninguno", marcador_filtro, condicion_filtro)]
        if marcador_filtro_eq2!="Todos":
            df_final = df_final[_mask_marcador(df_final, "Ninguno", marcador_filtro_eq2, condicion_filtro3)]
        df_final = df_final[_mask_columna(df_final, "Ninguno", columna_filtro, operador_filtro, valor_filtro, alcance_filtro, condicion_filtro)]
        df_final = df_final[_mask_columna(df_final, "Ninguno", columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2, condicion_filtro)]
        df_final = df_final[_mask_columna(df_final, "Ninguno", columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3, condicion_filtro)]
        df_final = df_final[_mask_cuota(df_final, cuota_tipo, rango_cuotas, "Ninguno", condicion_filtro)]

if dfs_v2:
    # Une con OR y quita duplicados - visualización intacta
    df_final = pd.concat(dfs_v2).drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League']).sort_values('Date')

# --- FILTRO %Clasif Eq1 FIX DEFINITIVO ---
if st.session_state.get('clasif_eq1_modo', '-') == "Rango" and not df_final.empty:
    try:
        pct_de = float(st.session_state.get('clasif_eq1_de', 0))
        pct_a = float(st.session_state.get('clasif_eq1_a', 100))
        if pct_de > pct_a: pct_de, pct_a = pct_a, pct_de
        df_clas_f = df_clas_base.copy()
        idx_max = df_clas_f.groupby(['League','Season'])['Jornada'].transform('max')
        df_last = df_clas_f[df_clas_f['Jornada'] == idx_max].copy()
        df_last = df_last[df_last['Season'].isin(temp_sel)]
        if liga_sel:
            df_last = df_last[df_last['League'].isin(liga_sel)]
        equipos_ok_clasif = set()
        for (liga, temp), g_last in df_last.groupby(['League','Season']):
            lider_pts = g_last['Pts'].max()
            if lider_pts <= 0: continue
            g_last['pct_lider'] = g_last['Pts'] / lider_pts * 100.0
            ok = g_last[(g_last['pct_lider'] >= pct_de - 0.01) & (g_last['pct_lider'] <= pct_a + 0.01)]['Equipo'].tolist()
            if pct_de <= 1:
                ok += g_last[g_last['Pts'] <= 0]['Equipo'].tolist()
            equipos_ok_clasif.update(ok)
        st.session_state.equipos_ok_clasif = equipos_ok_clasif
        if equipos_ok_clasif:
            df_final = df_final[(df_final['HomeTeam'].isin(equipos_ok_clasif)) | (df_final['AwayTeam'].isin(equipos_ok_clasif))].copy()
        else:
            df_final = df_final.iloc[0:0].copy()
    except Exception as e:
        st.warning(f"Error filtro %Clasif: {e}")
        st.session_state.equipos_ok_clasif = set()
else:
    st.session_state.equipos_ok_clasif = set()

## --- FILTRO SEGUIDOS N - V9 FINAL ---
if str(st.session_state.get('seguidos_filtro','-')) not in ["-",""] and len(df_base_h2h) > 0:
    try:
        n_seg = int(st.session_state.get('seguidos_filtro'))
        if n_seg >= 2:
            lv_seg = condicion_filtro if equipo_filtro!="Ninguno" else condicion_filtro3 if equipo2_filtro!="Ninguno" else condicion_filtro
            # BASE REAL CON TODOS LOS PARTIDOS Y JORNADA
            df_base_rachas = df_base.copy()
            try:
                df_base_rachas = df_base_rachas[df_base_rachas['League'].isin(liga_sel) & df_base_rachas['Season'].isin(temp_sel)]
                df_base_rachas = df_base_rachas[(df_base_rachas['Jornada']>=rango_jornadas[0]) & (df_base_rachas['Jornada']<=rango_jornadas[1])]
            except: pass

            equipos_revisar = pd.unique(df_base_rachas[['HomeTeam','AwayTeam']].values.ravel())
            if equipo_filtro!="Ninguno": equipos_revisar = [equipo_filtro]
            elif equipo2_filtro!="Ninguno": equipos_revisar = [equipo2_filtro]

            lista_rachas = []
            dict_rachas = {}

            for eq in equipos_revisar:
                df_eq = df_base_rachas[(df_base_rachas['HomeTeam']==eq) | (df_base_rachas['AwayTeam']==eq)].copy()
                if lv_seg == "Local": df_eq = df_eq[df_eq['HomeTeam']==eq]
                elif lv_seg == "Visitante": df_eq = df_eq[df_eq['AwayTeam']==eq]
                df_eq = df_eq.sort_values('Date')
                if len(df_eq) < n_seg: continue

                m = pd.Series(True, index=df_eq.index)
                m &= _mask_1x2(df_eq, eq, resultado_filtro if eq!=equipo2_filtro else resultado_filtro_eq2, lv_seg)
                m &= _mask_am(df_eq, ambos_marcan if eq!=equipo2_filtro else ambos_marcan_eq2, parte_gol if eq!=equipo2_filtro else parte_gol_eq2, eq, lv_seg)
                m &= _mask_xx(df_eq, eq, xx_filtro, lv_seg)
                m &= _mask_htft(df_eq, eq, htft_filtro, lv_seg)
                m &= _mask_margen(df_eq, eq, margen_filtro if eq!=equipo2_filtro else margen_filtro_eq2, parte_gol if eq!=equipo2_filtro else parte_gol_eq2, lv_seg)
                m &= _mask_marcador(df_eq, eq, marcador_filtro if eq!=equipo2_filtro else marcador_filtro_eq2, lv_seg)
                m &= _mask_columna(df_eq, eq, columna_filtro, operador_filtro, valor_filtro, alcance_filtro, lv_seg)
                m &= _mask_columna(df_eq, eq, columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2, lv_seg)
                m &= _mask_columna(df_eq, eq, columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3, lv_seg)
                m &= _mask_cuota(df_eq, cuota_tipo, rango_cuotas, eq, lv_seg)
                df_eq['cumple'] = m

                racha_actual = []
                rachas_eq = []
                for _, r in df_eq.iterrows():
                    if r['cumple']:
                        racha_actual.append(r)
                    else:
                        if len(racha_actual) >= n_seg:
                            rachas_eq.append(pd.DataFrame(racha_actual))
                        racha_actual = []
                if len(racha_actual) >= n_seg:
                    rachas_eq.append(pd.DataFrame(racha_actual))

                if rachas_eq:
                    df_racha_eq = pd.concat(rachas_eq).drop_duplicates(subset=['Date','HomeTeam','AwayTeam'])
                    dict_rachas[eq] = df_racha_eq
                    lista_rachas.append(df_racha_eq)

            if lista_rachas:
                df_final = pd.concat(lista_rachas).drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League']).sort_values('Date').copy()
                if 'cumple' in df_final.columns: df_final = df_final.drop(columns=['cumple'])
                st.session_state.dict_ultimos = dict_rachas
            else:
                df_final = df_final.iloc[0:0].copy()
                st.session_state.dict_ultimos = {}
    except Exception as e:
        st.error(f"Error Seguidos V9: {e}")


######################################################################################
    if len(df_final) > 0:
        df_final['partidos'] = ''
        df_final['Tarjetas/Corners/goles'] = ''
    else:
        df_final['partidos'] = pd.Series(dtype='object')
        df_final['Tarjetas/Corners/goles'] = pd.Series(dtype='object')

    # FIX: % siempre activo, aunque haya %Clasif
    _pct_min = int(st.session_state.get('pct_min', 1))
    _pct_max = int(st.session_state.get('pct_max', 100))
    if not (_pct_min == 1 and _pct_max == 100) and len(df_final) > 0:
        # total por equipo en la liga/temp/jornada seleccionada (sin filtros)
        _base_tot = df_original.copy()
        try:
            _base_tot = _base_tot[_base_tot['League'].isin(liga_sel) & _base_tot['Season'].isin(temp_sel)]
        except:
            pass
        try:
            _base_tot = _base_tot[(_base_tot['Jornada'] >= rango_jornadas[0]) & (_base_tot['Jornada'] <= rango_jornadas[1])]
        except:
            pass
        _base_tot, _ = calcular_estado_jornada(_base_tot)

        _equipos_ok = []
        for _eq in pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()):
            _tot = len(_base_tot[(_base_tot['HomeTeam']==_eq) | (_base_tot['AwayTeam']==_eq)])
            if _tot == 0:
                continue
            # hits = lo que ya pasó todos los filtros (GT, AM, Margen, 1x2) para ESE equipo
            _hits = len(df_final[(df_final['HomeTeam']==_eq) | (df_final['AwayTeam']==_eq)])
            _pct = (_hits / _tot * 100) if _tot else 0
            if _pct_min <= _pct <= _pct_max and _hits > 0:
                _equipos_ok.append(_eq)

        if _equipos_ok:
            df_final = df_final[(df_final['HomeTeam'].isin(_equipos_ok)) | (df_final['AwayTeam'].isin(_equipos_ok))]
        else:
            df_final = df_final.iloc[0:0]

    dict_ult = st.session_state.get('dict_ultimos', {})
    if dict_ult:
        ok = st.session_state.get('equipos_ok_clasif', set())
        if ok:
            total_partidos_real = sum(len(df) for eq, df in dict_ult.items() if eq in ok)
        else:
            total_partidos_real = sum(len(df) for df in dict_ult.values())
    else:
        total_partidos_real = len(df_final)

    st.caption(f"Mostrando {total_partidos_real} partidos")
  
  
  #################
  # --- CONTADOR GLOBAL POR JORNADA DIVIDIDO POR TEMPORADA + % ---
if len(df_final) > 0:
    conteo_j = df_final.groupby(['Season', 'Jornada']).size().reset_index(name='Veces')

    # Partidos por jornada: equipos únicos / 2
    partidos_por_jornada = df_final.groupby('Season').apply(
        lambda x: len(pd.unique(x[['HomeTeam','AwayTeam']].values.ravel())) // 2,
        include_groups=False
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
   
# --- FIX: df_final siempre existe aunque expander esté cerrado ---
if 'df_final' not in locals() or df_final is None:
    df_final = pd.DataFrame()

pct_filtro_actual = int(st.session_state.get('pct_min', 1))
with st.container(border=True):
    st.markdown(f"### 📊 Filtro actual ≥{pct_filtro_actual}%")
    if len(df_final) == 0:
        st.error(f"0 partidos - Filtros: Ligas={liga_sel} Temp={temp_sel} J={rango_jornadas if 'rango_jornadas' in locals() else '-'} Min%={pct_filtro_actual}% -> Baja Min% a 1% y pon J1-J38")
        st.caption(f"DEBUG: df_base={len(df_base) if 'df_base' in locals() else 0} | df_final={len(df_final)} | liga_sel={liga_sel} | temp_sel={temp_sel}")

    if 'num_ligas_filtro_actual' not in st.session_state:
        st.session_state.num_ligas_filtro_actual = 1
    if 'firma_ligas_filtro_actual' not in st.session_state:
        st.session_state.firma_ligas_filtro_actual = ""

    c_limp1, c_limp2 = st.columns([1,1])
    with c_limp1:
        if st.button("🧹 Limpiar vista", key="btn_limpiar_vista_final_unico_999", use_container_width=True):
            st.session_state.num_ligas_filtro_actual = 1
            st.session_state.firma_ligas_filtro_actual = ""
            st.session_state.dict_ultimos = {}
            if 'ver_partidos' in st.session_state:
                st.session_state.ver_partidos = False
            st.rerun()
    with c_limp2:
        st.caption(f"Cargadas: {st.session_state.get('num_ligas_filtro_actual',0)}")
        if st.button("🔄 Cargar", key="btn_forzar_carga_vista", use_container_width=True):
            st.session_state.num_ligas_filtro_actual = 1
            st.session_state.firma_ligas_filtro_actual = ""
            st.rerun()

    vista_limpia = st.session_state.get('num_ligas_filtro_actual', 1) <= 0
    if vista_limpia:
        st.session_state.num_ligas_filtro_actual = 1
        st.session_state.firma_ligas_filtro_actual = ""
        st.info("Vista reseteada a 1. Cargando...")
        st.rerun()

    ligas_ordenadas_all = sorted(df_final['League'].dropna().unique()) if len(df_final) > 0 else []
    # si solo hay 1 liga seleccionada, respeta el orden de liga_sel, si no todas las del df_final
    if 'liga_sel' in locals() and len(liga_sel) >= 1:
        # ordena por liga_sel para que respete lo que has marcado
        ligas_ordenadas_all = sorted(liga_sel)

    firma_actual = f"{'|'.join(ligas_ordenadas_all)}|{pct_marcador}|{equipo_filtro}|{equipo2_filtro}|{margen_filtro}|{margen_filtro_eq2}|{resultado_filtro}|{resultado_filtro_eq2}|{ambos_marcan}|{ambos_marcan_eq2}|{marcador_filtro}|{marcador_filtro_eq2}|{parte_gol}|{parte_gol_eq2}|{cuota_tipo}|{rango_cuotas}|{ultimos_part_filtro}|{st.session_state.get('margen_jornadas_filtro')}|{st.session_state.get('seguidos_filtro')}|{st.session_state.get('clasif_eq1_modo')}|{len(df_final)}"
    if firma_actual!= st.session_state.firma_ligas_filtro_actual:
        st.session_state.num_ligas_filtro_actual = 1
        st.session_state.firma_ligas_filtro_actual = firma_actual
        if 'ver_partidos' in st.session_state:
            st.session_state.ver_partidos = True

    ligas_visibles = ligas_ordenadas_all[:st.session_state.num_ligas_filtro_actual]

    # TITULITO - FIX FINAL MINIRRESUMEN - SOLO EQUIPOS FILTRADOS
    if len(df_final) > 0 and ligas_visibles:
        df_visible_titulo = df_final[df_final['League'].isin(ligas_visibles)]
        ligas_mostrar = "|".join(ligas_visibles) if ligas_visibles else "-"
        dict_ult = st.session_state.get('dict_ultimos', {})
        ok_clasif = st.session_state.get('equipos_ok_clasif', set())
        if equipo_filtro!="Ninguno" and equipo2_filtro!="Ninguno":
            equipos_con_partidos_set = {equipo_filtro, equipo2_filtro}
        elif equipo_filtro!="Ninguno":
            equipos_con_partidos_set = {equipo_filtro}
        elif equipo2_filtro!="Ninguno":
            equipos_con_partidos_set = {equipo2_filtro}
        elif dict_ult:
            equipos_con_partidos_set = set(dict_ult.keys())
            if ok_clasif:
                equipos_con_partidos_set = {e for e in equipos_con_partidos_set if e in ok_clasif}
        else:
            if ok_clasif:
                equipos_con_partidos_set = ok_clasif.intersection(set(pd.unique(df_visible_titulo[['HomeTeam','AwayTeam']].values.ravel()))) if ok_clasif else set(pd.unique(df_visible_titulo[['HomeTeam','AwayTeam']].values.ravel()))
                if not equipos_con_partidos_set:
                    equipos_con_partidos_set = ok_clasif
            else:
                equipos_con_partidos_set = set(pd.unique(df_visible_titulo[['HomeTeam','AwayTeam']].values.ravel()))
        equipos_clasif = list(equipos_con_partidos_set)
        equipos_con_partidos = equipos_con_partidos_set
        if dict_ult:
            partidos_mostrar = sum(len(df) for eq, df in dict_ult.items() if eq in equipos_con_partidos_set)
        else:
            partidos_mostrar = len(df_visible_titulo)
        num_equipos = len(equipos_clasif)
        from collections import defaultdict
        equipos_por_liga = defaultdict(list)
        
        def get_liga_eq_fix(equipo_fix):
            try:
                # FIX: usa df_visible_titulo que sí existe en el muro, no base_total
                df_eq_liga = df_visible_titulo[(df_visible_titulo['HomeTeam']==equipo_fix) | (df_visible_titulo['AwayTeam']==equipo_fix)]
                if df_eq_liga.empty:
                    df_eq_liga = df_final[(df_final['HomeTeam']==equipo_fix) | (df_final['AwayTeam']==equipo_fix)]
                if df_eq_liga.empty:
                    # fallback a df_original
                    df_eq_liga = df_original[(df_original['HomeTeam']==equipo_fix) | (df_original['AwayTeam']==equipo_fix)]
                if df_eq_liga.empty:
                    return "OTRA"
                return df_eq_liga['League'].value_counts().idxmax()
            except:
                return "OTRA"

        for eq in equipos_clasif:
            d = df_clas_base[df_clas_base['Equipo']==eq]
            if not d.empty:
                d = d.sort_values('Jornada').iloc[-1]
                pos = int(d['Pos']); pts = int(d['Pts'])
            else:
                pos = 999; pts = 0
            
            liga_eq = get_liga_eq_fix(eq)  # <-- AQUI ESTABA EL FALLO
            equipos_por_liga[liga_eq].append((pos, eq, pts))
        lista_bloques = []
        for liga in sorted(equipos_por_liga.keys()):
            equipos_por_liga[liga].sort(key=lambda x: x[0])
            lista_eq_liga = []
            for pos, eq, pts in equipos_por_liga[liga]:
                pos_txt = f"{pos}º {pts}pts" if pos!=999 else "Xº Xpts"
                txt = f"<b style='color:#000;font-size:9px'>{eq.lower()}</b> <span style='color:#4B0082;font-size:9px;font-weight:900'>{pos_txt}</span>"
                lista_eq_liga.append(txt)
            bloque = f"<b><i style='color:#000;font-size:10px'>{liga}:</i></b> " + " <span style='color:#555'>|</span> ".join(lista_eq_liga)
            lista_bloques.append(bloque)
        equipos_txt = "<br>".join(lista_bloques) if lista_bloques else "sin equipos"
        with st.expander(f"🧱 muro equipos ligas - {num_equipos} equipos - {partidos_mostrar} partidos", expanded=True):
            st.markdown(f"<div style='font-size:11px;font-family:monospace;color:#555;padding:0 0 4px 0;line-height:1.5'>Ligas: {ligas_mostrar} | Eq: {num_equipos} | Partidos: {partidos_mostrar} | Mostrando {len(ligas_visibles)}/{len(ligas_ordenadas_all)} ligas<br>{equipos_txt}</div>", unsafe_allow_html=True)

        # ---- AQUI ESTA EL BOTON - SIEMPRE VISIBLE SI HAY +1 LIGA ----
        if ligas_ordenadas_all:
            if len(ligas_visibles) < len(ligas_ordenadas_all):
                siguiente = ligas_ordenadas_all[len(ligas_visibles)]
                if st.button(f"📥 Cargar siguiente liga: {siguiente} ({len(ligas_visibles)+1}/{len(ligas_ordenadas_all)})", key="btn_cargar_liga_filtro_actual", type="primary", use_container_width=True):
                    st.session_state.num_ligas_filtro_actual += 1
                    st.rerun()
            else:
                st.markdown(f"<span style='color:#0f4d0f;font-size:10px;font-family:monospace'>Todas las ligas cargadas ({len(ligas_ordenadas_all)})</span>", unsafe_allow_html=True)

            # --- BOTONES CARGAR (se quedan igual) ---
            st.markdown("""
            <style>
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

        # --- NUEVO: MINI RESUMEN SIEMPRE VISIBLE (no depende de ligas_visibles) ---
        try:
            if not df_final.empty:
                _pct_min = int(st.session_state.get('pct_min', 1))
                _pct_max = int(st.session_state.get('pct_max', 100))
                dict_ult = st.session_state.get('dict_ultimos', {})
                ok_clasif = st.session_state.get('equipos_ok_clasif', set())

                _base_tot = df_original.copy()
                try:
                    _base_tot = _base_tot[_base_tot['League'].isin(liga_sel) & _base_tot['Season'].isin(temp_sel)]
                    _base_tot = _base_tot[(_base_tot['Jornada']>=rango_jornadas[0]) & (_base_tot['Jornada']<=rango_jornadas[1])]
                except:
                    pass

                from collections import defaultdict
                equipos_por_liga = defaultdict(list)

                if dict_ult:
                    _candidatos = set(dict_ult.keys())
                else:
                    _candidatos = set(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

                if equipo_filtro!="Ninguno":
                    _candidatos = {equipo_filtro} if equipo_filtro in _candidatos else set()
                if equipo2_filtro!="Ninguno":
                    _candidatos.add(equipo2_filtro)

                if ok_clasif:
                    _candidatos = {e for e in _candidatos if e in ok_clasif}

                for eq in sorted(_candidatos):
                    _lv = condicion_filtro if equipo_filtro!="Ninguno" else condicion_filtro3 if equipo2_filtro!="Ninguno" else "Todo"
                    if _lv == "Local":
                        _base_tot_lv = _base_tot[_base_tot['HomeTeam']==eq]
                    elif _lv == "Visitante":
                        _base_tot_lv = _base_tot[_base_tot['AwayTeam']==eq]
                    else:
                        _base_tot_lv = _base_tot[(_base_tot['HomeTeam']==eq) | (_base_tot['AwayTeam']==eq)]
                    _tot_eq = len(_base_tot_lv)
                    if _tot_eq==0:
                        continue
                    if eq in dict_ult and not dict_ult[eq].empty:
                        _hits_eq = len(dict_ult[eq])
                        _liga_eq = dict_ult[eq]['League'].iloc[0] if 'League' in dict_ult[eq].columns and not dict_ult[eq].empty else "OTRA"
                    else:
                        _df_eq = df_final[(df_final['HomeTeam']==eq) | (df_final['AwayTeam']==eq)]
                        _hits_eq = len(_df_eq)
                        _liga_eq = _df_eq['League'].iloc[0] if not _df_eq.empty else "OTRA"

                    if _hits_eq==0:
                        continue
                    _pct = _hits_eq / _tot_eq * 100
                    if not (_pct_min <= _pct <= _pct_max):
                        continue
                    # YA NO FILTRAMOS POR ligas_visibles - por eso se ve siempre
                    equipos_por_liga[_liga_eq].append(f"{eq.lower()} ({_hits_eq})")
                #
                if equipos_por_liga:
                    total_eq = sum(len(set(v)) for v in equipos_por_liga.values())
                    with st.expander(f"📁 Equipos que pasan filtro ({total_eq} equipos)", expanded=True):
                        st.markdown(f"**📁 Equipos que pasan filtro ({total_eq} equipos)**")
                        for liga in sorted(equipos_por_liga.keys()):
                            lista = sorted(set(equipos_por_liga[liga]))
                            if not lista:
                                continue
                            with st.expander(f"{liga.upper()} ({len(lista)})", expanded=False):
                                st.markdown(
                                    f"<div style='font-size:11px;font-family:monospace;line-height:1.7;background:transparent;padding:2px 0'>"
                                    f"<b style='font-size:12px;font-weight:900'>{liga.upper()}:</b><br>{' | '.join(lista)}"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                else:
                    st.caption("Mini resumen: 0 equipos pasan el %")
        except Exception:
            pass

        if not vista_limpia:
            # --- A PARTIR DE AQUI TU CODIGO ORIGINAL PERO FILTRADO POR ligas_visibles ---
            if len(df_final) > 0 and ligas_visibles:
                base = df_final[df_final['League'].isin(ligas_visibles)].copy()
                equipos_mostrar = []
                if equipo_filtro!= "Ninguno": equipos_mostrar.append(equipo_filtro)
                if equipo2_filtro!= "Ninguno" and equipo2_filtro not in equipos_mostrar: equipos_mostrar.append(equipo2_filtro)
                if not equipos_mostrar: equipos_mostrar = list(pd.unique(base[['HomeTeam','AwayTeam']].values.ravel()))

                # --- FILTRO REAL ULT X/Y PARA COMUN (sin seguidos) - FIX DEFINITIVO base_total definido + incluye Col1/Col2/Col3 + GUARDA VENTANA PARA VISUAL ---
                ult_f = str(st.session_state.get('ultimos_part_filtro', 'Todos'))
                marg_f = str(st.session_state.get('margen_jornadas_filtro', 'Todos'))
                if ult_f!= "Todos" and marg_f!= "Todos" and str(st.session_state.get('seguidos_filtro','-')) in ["-",""]:
                    try:
                        need = int(ult_f)
                        ventana = int(marg_f)
                        equipos_filtrados_ult = []
                        dict_ult_real_temp = {} # NUEVO: guarda ventana
                        # FIX: usa base (df_final filtrado por ligas_visibles) en vez de base_total que aun no existe aqui
                        _df_base_ult = base if 'base' in locals() and not base.empty else df_final
                        for eq in equipos_mostrar:
                            df_eq_total = _df_base_ult[(_df_base_ult['HomeTeam']==eq) | (_df_base_ult['AwayTeam']==eq)].sort_values('Date')
                            if len(df_eq_total) < need:
                                continue
                            df_last = df_eq_total.tail(ventana).copy()
                            if df_last.empty:
                                continue
                            # aplica los mismos filtros que el muro (margen, am, 1x2, etc) + columnas
                            df_last = df_last[_mask_1x2(df_last, eq, resultado_filtro if eq!=equipo2_filtro else resultado_filtro_eq2, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            df_last = df_last[_mask_am(df_last, ambos_marcan if eq!=equipo2_filtro else ambos_marcan_eq2, parte_gol if eq!=equipo2_filtro else parte_gol_eq2, eq, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            df_last = df_last[_mask_margen(df_last, eq, margen_filtro if eq!=equipo2_filtro else margen_filtro_eq2, parte_gol if eq!=equipo2_filtro else parte_gol_eq2, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            df_last = df_last[_mask_marcador(df_last, eq, marcador_filtro if eq!=equipo2_filtro else marcador_filtro_eq2, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            df_last = df_last[_mask_columna(df_last, eq, columna_filtro, operador_filtro, valor_filtro, alcance_filtro, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            df_last = df_last[_mask_columna(df_last, eq, columna_filtro2, operador_filtro2, valor_filtro2, alcance_filtro2, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            df_last = df_last[_mask_columna(df_last, eq, columna_filtro3, operador_filtro3, valor_filtro3, alcance_filtro3, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                            if len(df_last) >= need:
                                equipos_filtrados_ult.append(eq)
                                dict_ult_real_temp[eq] = df_last # NUEVO
                        equipos_mostrar = equipos_filtrados_ult
                        # NUEVO: guarda ventana para visual sin romper nada
                        if dict_ult_real_temp:
                            st.session_state.dict_ultimos = dict_ult_real_temp
                            st.session_state.dict_ultimos_es_ventana = True
                            st.session_state.ventana_ult = ventana
                            st.session_state.need_ult = need
                    except Exception as e:
                        # no rompe, solo log
                        pass
                                # Si Seguidos activo, solo los que tienen racha
                if str(st.session_state.get('seguidos_filtro','-')) not in ["-",""] and st.session_state.get('dict_ultimos'):
                    equipos_mostrar = list(st.session_state.dict_ultimos.keys())
                # --- PARCHE: si hay filtro %Clasif, solo mostrar TOP ---
                if st.session_state.get('equipos_ok_clasif'):
                    ok_set = st.session_state.equipos_ok_clasif
                    base_teams = set(pd.unique(base[['HomeTeam','AwayTeam']].values.ravel()))
                    ok_in_base = [e for e in base_teams if e in ok_set]
                    if equipo_filtro != "Ninguno" or equipo2_filtro != "Ninguno":
                        equipos_mostrar = [e for e in equipos_mostrar if e in ok_set]
                    else:
                        equipos_mostrar = ok_in_base
                # --- FIN PARCHE ---
                base_total = df_original.copy()
                base_total = base_total[base_total['League'].isin(ligas_visibles) & base_total['Season'].isin(temp_sel)]
                if base_total.empty:
                    base_total = base_total.copy()
                else:
                    base_total, _ = calcular_estado_jornada(base_total)
                if not base_total.empty and 'Jornada' in base_total.columns:
                    base_total = base_total[(base_total['Jornada']>=rango_jornadas[0]) & (base_total['Jornada']<=rango_jornadas[1])]
                _pct_range2 = st.session_state.get('rango_jornadas_pct', None)
                if _pct_range2 is not None:
                    base_total = base_total[(base_total['Jornada']>=_pct_range2[0]) & (base_total['Jornada']<=_pct_range2[1])]
                if equipo_filtro!= "Ninguno" or equipo2_filtro!= "Ninguno":
                    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
                        base_total = base_total[((base_total['HomeTeam']==equipo_filtro) | (base_total['AwayTeam']==equipo_filtro)) | ((base_total['HomeTeam']==equipo2_filtro) | (base_total['AwayTeam']==equipo2_filtro))]
                    elif equipo_filtro!= "Ninguno":
                        base_total = base_total[(base_total['HomeTeam']==equipo_filtro) | (base_total['AwayTeam']==equipo_filtro)]
                    elif equipo2_filtro!= "Ninguno":
                        base_total = base_total[(base_total['HomeTeam']==equipo2_filtro) | (base_total['AwayTeam']==equipo2_filtro)]
                # FIX HALIFAX: quita equipos que no tienen ni 1 J con margen A FAVOR
                base_filtrado_real = base.copy()
                equipos_con_j = []
                for eq in equipos_mostrar:
                    df_tmp = base_filtrado_real[(base_filtrado_real['HomeTeam']==eq) | (base_filtrado_real['AwayTeam']==eq)]
                    if df_tmp.empty:
                        continue
                    # recalcula margen a favor del equipo
                    if margen_filtro!="Todo":
                        df_tmp = df_tmp[_mask_margen(df_tmp, eq, margen_filtro, parte_gol, condicion_filtro if eq!=equipo2_filtro else condicion_filtro3)]
                    if margen_filtro_eq2!="Todo" and eq==equipo2_filtro:
                        df_tmp = df_tmp[_mask_margen(df_tmp, eq, margen_filtro_eq2, parte_gol_eq2, condicion_filtro3)]
                    if not df_tmp.empty:
                        equipos_con_j.append(eq)
                equipos_mostrar = equipos_con_j
                datos_eq1 = []
                datos_eq2 = []
                datos_resto = []
                #
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

                    tot_sin_filtrar = len(base_total_team)

                    modo_eq = resultado_filtro_eq2 if eq==equipo2_filtro else resultado_filtro
                    if modo_eq!= "Ninguno":
                        es_loc_glob = base_team_global['HomeTeam']==eq
                        if modo_eq == "Pierde":
                            base_team_global = base_team_global[(es_loc_glob & (base_team_global['FTR']=='A')) | (~es_loc_glob & (base_team_global['FTR']=='H'))]
                        elif modo_eq == "Gana":
                            base_team_global = base_team_global[(es_loc_glob & (base_team_global['FTR']=='H')) | (~es_loc_glob & (base_team_global['FTR']=='A'))]
                        elif modo_eq == "Empata":
                            base_team_global = base_team_global[base_team_global['FTR']=='D']
                        elif modo_eq == "Gana/Empata":
                            base_team_global = base_team_global[~((es_loc_glob & (base_team_global['FTR']=='A')) | (~es_loc_glob & (base_team_global['FTR']=='H')))]
                        elif modo_eq == "Gana/Pierde":
                            base_team_global = base_team_global[base_team_global['FTR']!='D']
                        elif modo_eq == "Empata/Pierde":
                            base_team_global = base_team_global[~((es_loc_glob & (base_team_global['FTR']=='H')) | (~es_loc_glob & (base_team_global['FTR']=='A')))]

                    part_tot = tot_sin_filtrar

                    # FIX SEGUIDOS: part_ok debe ser su propia racha - PARCHE SEGURO no rompe nada
                    dict_ult_check = st.session_state.get('dict_ultimos', {})
                    if str(st.session_state.get('seguidos_filtro','-')) not in ["-",""] and eq in dict_ult_check:
                        part_ok = dict_ult_check[eq]
                        part_ok = part_ok[part_ok['League'].isin(ligas_visibles)] if not part_ok.empty else part_ok
                    elif str(ultimos_part_filtro)!="Todos" and dict_ult_check:
                        if eq not in dict_ult_check:
                            continue
                        df_tail_eq = dict_ult_check[eq]
                        part_ok = df_tail_eq[df_tail_eq['League'].isin(ligas_visibles)]
                    else:
                        part_ok = base_team_global

                    tot = part_tot
                    hits = len(part_ok)
                    pct = (hits / tot * 100) if tot else 0

                    # FIX % De - A
                    _pct_min = int(st.session_state.get('pct_min', 1))
                    _pct_max = int(st.session_state.get('pct_max', 100))
                    if not (_pct_min <= pct <= _pct_max):
                        continue

                    marc_eq = marcador_filtro_eq2 if eq==equipo2_filtro else marcador_filtro
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

                    # --- FIJO DENTRO DE TEMP SELECCIONADA ---
                    df_tmp = df_original[df_original['Season'].isin(temp_sel)] if 'temp_sel' in locals() and temp_sel else df_original
                    df_eq_fijo = df_tmp[(df_tmp['HomeTeam']==eq) | (df_tmp['AwayTeam']==eq)].sort_values('Date')

                                        # --- TEXTO SEGUIDOS - V9 USA DICT_RACHAS DIRECTO ---
                    texto_seg = ""
                    seg_val_str = str(st.session_state.get('seguidos_filtro', '-'))
                    if seg_val_str not in ["-", ""] and eq in st.session_state.get('dict_ultimos', {}):
                        df_racha_eq = st.session_state.dict_ultimos[eq].sort_values('Date')
                        rachas_j = []
                        cur = [int(df_racha_eq.iloc[0]['Jornada'])]
                        for i in range(1, len(df_racha_eq)):
                            cur.append(int(df_racha_eq.iloc[i]['Jornada']))
                        partes_txt = ",".join([f"J{j}" for j in df_racha_eq['Jornada'].tolist()])
                        texto_seg = f"<div style='font-size:9px;font-weight:900;margin-top:4px;color:#0A2342;line-height:1.2'>1# {partes_txt}</div>"

                    # --- NUEVO: DIVIDIDO POR TEMPORADA CON POS/PTS POR TEMP ---
                    seasons_list = sorted(base_total_team['Season'].dropna().unique().tolist())
                    if 'temp_sel' in locals() and temp_sel:
                        seasons_list = [s for s in temp_sel if s in seasons_list]

                    html_temporadas = ""
                    for _season in seasons_list:
                        _df_season = base_total_team[base_total_team['Season']==_season]
                        _part_ok_season = part_ok[part_ok['Season']==_season] if not part_ok.empty and 'Season' in part_ok.columns else part_ok
                        _df_eq_fijo_season = df_eq_fijo[df_eq_fijo['Season']==_season] if not df_eq_fijo.empty and 'Season' in df_eq_fijo.columns else df_eq_fijo

                        _racha = racha_comprimida_html(_df_eq_fijo_season, eq) if not _df_eq_fijo_season.empty else ""
                        _racha_am = racha_ambos_marcan_html(_df_eq_fijo_season) if not _df_eq_fijo_season.empty else ""
                        _jors = jornadas_conteo(_part_ok_season['Jornada'], _part_ok_season, eq, rival, parte_actual) if not _part_ok_season.empty else ""

                        # Pos y Pts finales de ESA temporada (no total)
                        try:
                            _d_clas = df_clas_base[(df_clas_base['Equipo']==eq) & (df_clas_base['Season']==_season)]
                            if not _d_clas.empty:
                                _d_last = _d_clas.sort_values('Jornada').iloc[-1]
                                _pos_txt = f"{int(_d_last['Pos'])}º {int(_d_last['Pts'])}pts"
                            else:
                                _pos_txt = "Xº Xpts"
                        except:
                            _pos_txt = "Xº Xpts"

                        try:
                            _es_loc = _df_season['HomeTeam']==eq
                            _tot = len(_df_season)
                            _tot_c = int(_es_loc.sum()); _tot_f = int(_tot - _tot_c)
                            _gana = ((_es_loc) & (_df_season['FTHG']>_df_season['FTAG'])) | ((~_es_loc) & (_df_season['FTAG']>_df_season['FTHG']))
                            _pierde = ((_es_loc) & (_df_season['FTHG']<_df_season['FTAG'])) | ((~_es_loc) & (_df_season['FTAG']<_df_season['FTHG']))
                            _empata = ~(_gana | _pierde)
                            _g_all = int(_gana.sum()); _e_all = int(_empata.sum()); _p_all = int(_pierde.sum())
                            _g_c = int((_gana & _es_loc).sum()); _g_f = int(_g_all - _g_c)
                            _e_c = int((_empata & _es_loc).sum()); _e_f = int(_e_all - _e_c)
                            _p_c = int((_pierde & _es_loc).sum()); _p_f = int(_p_all - _p_c)
                            _resumen_gep = f"<div style='font-size:10px;line-height:1.1;color:#000;margin:1px 0 2px 0;font-family:monospace'><span style='color:#0f8105;font-weight:900'>G:{_g_all}/{_tot}</span> <span style='color:#000'>(c{_g_c}/{_tot_c} | f{_g_f}/{_tot_f})</span> | <span style='color:#0A2342;font-weight:900'>E:{_e_all}/{_tot}</span> <span style='color:#000'>(c{_e_c}/{_tot_c} | f{_e_f}/{_tot_f})</span> | <span style='color:#f31818;font-weight:900'>P:{_p_all}/{_tot}</span> <span style='color:#000'>(c{_p_c}/{_tot_c} | f{_p_f}/{_tot_f})</span></div>"
                            _am = (_df_season['FTHG']>0) & (_df_season['FTAG']>0)
                            _si_all = int(_am.sum()); _no_all = int(_tot - _si_all)
                            _si_c = int((_am & _es_loc).sum()); _si_f = int(_si_all - _si_c)
                            _no_c = int(_tot_c - _si_c); _no_f = int(_tot_f - _si_f)
                            _resumen_am = f"<div style='font-size:10px;line-height:1.1;color:#000;margin:0 0 2px 0;font-family:monospace'><span style='font-weight:900'>Si:{_si_all}/{_tot}</span> <span style='color:#000'>(c{_si_c}/{_tot_c} | f{_si_f}/{_tot_f})</span> | <span style='font-weight:900'>No:{_no_all}/{_tot}</span> <span style='color:#000'>(c{_no_c}/{_tot_c} | f{_no_f}/{_tot_f})</span></div>"
                        except:
                            _resumen_gep = ""; _resumen_am = ""; _tot=0

                        html_temporadas += f"""<div style='background:#FFFFFF'>
<div style='font-size:10px;font-weight:900;color:#0A2342;margin-bottom:3px'>{_season} - {eq.lower()} {_pos_txt} ({_tot}PJ)</div>
{_resumen_gep}
<div style='display:flex;flex-wrap:wrap;align-items:center;gap:1px 2px;margin:2px 0 1px 0'>{_racha}</div>
<div style='display:flex;flex-wrap:wrap;align-items:center;gap:1px 2px;margin:1px 0 1px 0'>{_racha_am}</div>
{_resumen_am}
<div style='margin-top:4px'>{_jors}</div>
</div>"""

                    html = f"""<div style='font-size:9px;line-height:1.2;margin:3px 0;padding:4px 0;border-bottom:2px solid #000;font-family:monospace;color:#000'>
<div style='font-size:10px;font-weight:900;line-height:1.1'>{hits}/{tot} - {hits}# {pct:.1f}% (TOTAL {len(seasons_list)} temps)</div>
{texto_seg}
{html_temporadas}
</div>"""
                    if eq == equipo_filtro: datos_eq1.append((pct, hits, eq, html))
                    elif eq == equipo2_filtro: datos_eq2.append((pct, hits, eq, html))
                    else: datos_resto.append((pct, hits, eq, html))

                datos_eq1.sort(key=lambda x: (-x[0], -x[1]))
                datos_eq2.sort(key=lambda x: (-x[0], -x[1]))
                datos_resto.sort(key=lambda x: (-x[0], -x[1]))
                #
                if 'datos_eq1' not in locals(): datos_eq1 = []
                if 'datos_eq2' not in locals(): datos_eq2 = []
                if 'datos_resto' not in locals(): datos_resto = []

                with st.expander(f"📋 partidos filtro - {len(equipos_mostrar)} equipos", expanded=True):
                    def get_pos_pts_html(eq):
                        d = df_clas_base[df_clas_base['Equipo']==eq]
                        if not d.empty:
                            d = d.sort_values('Jornada').iloc[-1]
                            return f"<b style='color:#000;font-size:9px'>{eq.lower()}</b> <span style='color:#4B0082;font-size:9px;font-weight:900'>{int(d['Pos'])}º {int(d['Pts'])}pts</span>"
                        return f"<b style='color:#000;font-size:9px'>{eq.lower()}</b> <span style='color:#4B0082;font-size:9px;font-weight:900'>Xº Xpts</span>"

                    def get_liga_eq(eq):
                        df_eq_liga = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]
                        return "|".join(sorted(df_eq_liga['League'].dropna().unique())) if not df_eq_liga.empty else ""

                    if equipo_filtro!="Ninguno" and equipo2_filtro!="Ninguno":
                        for pct, hits, eq, html in datos_eq1:
                            liga_eq = get_liga_eq(eq)
                            pos_html = get_pos_pts_html(eq)
                            st.markdown(f"<div style='font-size:9px;font-family:monospace;color:#000'>EQUIPO1: {pos_html} ({hits}) --> {liga_eq}</div>", unsafe_allow_html=True)
                            st.markdown(html, unsafe_allow_html=True)
                        st.markdown("---")
                        for pct, hits, eq, html in datos_eq2:
                            liga_eq = get_liga_eq(eq)
                            pos_html = get_pos_pts_html(eq)
                            st.markdown(f"<div style='font-size:9px;font-family:monospace;color:#000'>EQUIPO2: {pos_html} ({hits}) --> {liga_eq}</div>", unsafe_allow_html=True)
                            st.markdown(html, unsafe_allow_html=True)
                    else:
                        todos = datos_eq1 + datos_eq2 + datos_resto
                        todos.sort(key=lambda x: (-x[0], -x[1]))
                        if todos:
                            for pct, hits, eq, html in todos:
                                liga_eq = get_liga_eq(eq)
                                pos_html = get_pos_pts_html(eq)
                                st.markdown(f"<div style='font-size:9px;font-family:monospace;color:#000'>{pos_html} ({hits}) --> {liga_eq}</div>", unsafe_allow_html=True)
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
    with st.expander("📋 Partidos", expanded=False):
        
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
with st.expander("ℹ Info jornadas"):
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
                            use_container_width=True,
                            height=600
                        )



################## modo clasificacion fin ############
########filtro rachas La UI (donde eliges Tipo, Condición, Dónde)



            ############fin expander rachas
################buscador de equipos 1826 - 2205
with st.expander("🔍 Buscador de Equipos + IA (optimizado)", expanded=False):
    st.markdown("""
    <style>
    div[data-testid="stExpander"] [data-testid="stSelectbox"] { width: 100%!important; }
    div[data-testid="stExpander"] [data-testid="stSelectbox"] > div { width: 100%!important; min-width: unset!important; }
    div[data-testid="stExpander"] [data-testid="stSelectbox"] > div > div { width: 100%!important; min-width: 100%!important; }
    div[data-testid="stExpander"] [data-testid="stHorizontalBlock"] > div { min-width: 45%!important; flex-shrink: 0!important; }
    </style>
    """, unsafe_allow_html=True)

    st.caption("Busca equipos que cumplan condiciones - optimizado 10x + IA sin cuota")

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
    st.markdown("**Jornadas**")
    jmin, jmax = int(df_be['Jornada'].min()), int(df_be['Jornada'].max())
    col_j1, col_j2 = st.columns(2)
    j_desde_be = col_j1.number_input("De", min_value=jmin, max_value=jmax, value=jmin, step=1, key='be2_j_desde', label_visibility="collapsed")
    j_hasta_be = col_j2.number_input("A", min_value=jmin, max_value=jmax, value=jmax, step=1, key='be2_j_hasta', label_visibility="collapsed")
    if j_desde_be > j_hasta_be: j_desde_be = j_hasta_be
    j_rango = (int(j_desde_be), int(j_hasta_be))
    df_be = df_be[(df_be['Jornada']>=j_rango[0]) & (df_be['Jornada']<=j_rango[1])].copy()
    if df_be.empty:
        st.warning("Sin partidos en ese rango J")
        st.stop()

    modo_busca = st.radio("Modo búsqueda", ["Últimos X partidos", "% en rango jornadas"], horizontal=True, key="be2_modo")
    de_busca = "-"
    if modo_busca == "Últimos X partidos":
        c_ult, c_de, c_lv = st.columns([1,1,1])
        ultimos_x = c_ult.number_input("Últimos", 1, 38, 5, key="be2_ultimos")
        de_busca = c_de.selectbox("De", ["-"] + [str(i) for i in range(1, 51)], index=0, key="be2_de")
        lv_busca = c_lv.selectbox("L/V", ["Todo","Local","Visitante"], key="be2_lv")
        pct_min_rango = 0
        pct_max_rango = 100
    else:
        col_pct1, col_pct2, col_pct_lv = st.columns([1,1,1])
        pct_min_rango = col_pct1.number_input("% De", 0, 100, 1, 5, key="be2_pct_min")
        pct_max_rango = col_pct2.number_input("% A", 0, 100, 100, 5, key="be2_pct_max")
        if pct_min_rango > pct_max_rango: pct_min_rango = pct_max_rango
        ultimos_x = None
        lv_busca = col_pct_lv.selectbox("L/V", ["Todo","Local","Visitante"], key="be2_lv")

    col_res_be = st.columns(1)[0]
    res_busca = col_res_be.selectbox("Res", ["Todo","G","E","P","GE","GP","EP"], key="be2_res")
    colc1, colc2, colc3, colc4 = st.columns(4)
    fav_c1 = colc1.selectbox("Fav/Cntr1", ["Todo","AF","C"], key="be2_favc1")
    am_busca = colc2.selectbox("AM", ["Todos","Si","No","Si1P","No1P","Si2P","No2P","Si1pNo2p","No1pSi2p","Si1pSi2p"], key="be2_am")
    vlr1_busca = colc3.selectbox("Vlr1", ["Ninguno"] + [i/2 for i in range(21)], key="be2_vlr1")
    parte_busca = colc4.selectbox("Parte", ["Todo","1T","2T"], key="be2_parte")
    columnas_numericas_be = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','tirosTot','tirosPuertaTot','faltasTot','TargRojTot']
    ABREV_COL_BE = {'FTHG':'GL','FTAG':'GV','HTHG':'G1L','HTAG':'G1V','HS':'TL','AS':'TV','HST':'TPL','AST':'TPV','HF':'FL','AF':'FV','HC':'CL','AC':'CV','HY':'AL','AY':'AV','HR':'RL','AR':'RV','GolesTotales':'GT','GolesHT':'G1T','Goles2T':'G2T','corneTot':'CT','TargAmTot':'TAM','tirosTot':'TT','tirosPuertaTot':'TPT','faltasTot':'FT','TargRojTot':'TRT','Ninguno':'—'}
    colc5, colc6 = st.columns(2)
    col1_busca = colc5.selectbox("Col1", ["Ninguno"] + columnas_numericas_be, format_func=lambda x: ABREV_COL_BE.get(x, x), key="be2_col1")
    op1_busca = colc6.selectbox("Op1", ["=", ">", ">=", "<", "<="], key="be2_op1")

    filtro_resumen = f"{','.join(ligas_busca) or 'Todas'} | {','.join(temps_busca) or 'Todas'} | J{j_desde_be}-{j_hasta_be} | {modo_busca} | {lv_busca} | {res_busca} | {fav_c1}:{col1_busca}{op1_busca}{vlr1_busca} | {am_busca} | {parte_busca}"
    st.markdown(f"<div style='font-size:10px;font-family:monospace;background:#f3f4f6;padding:4px 6px;border-radius:6px;margin:6px 0'>{filtro_resumen}</div>", unsafe_allow_html=True)

    # Limpieza persistencia vieja (igual que original)
    for _k in list(st.session_state.keys()):
        if "be2_buscar" in _k:
            try: del st.session_state[_k]
            except: pass

    if st.button("🔎 Buscar equipos", type="primary", use_container_width=True, key="be2_search_final_2026"):
        df_be = df_be.sort_values('Date')
        # --- INDEX RAPIDO ---
        from collections import defaultdict
        equipos_dict = defaultdict(list)
        for idx, r in df_be.iterrows():
            equipos_dict[r['HomeTeam']].append(idx)
            equipos_dict[r['AwayTeam']].append(idx)

        equipos = list(equipos_dict.keys())
        resultados = []
        es_ultimos = (modo_busca == "Últimos X partidos")

        for eq in equipos:
            idxs = equipos_dict[eq]
            if es_ultimos and len(idxs) < (ultimos_x if de_busca=="-" else max(int(de_busca), ultimos_x)):
                continue
            df_eq = df_be.loc[idxs].copy()
            if lv_busca == "Local": df_eq = df_eq[df_eq['HomeTeam']==eq]
            elif lv_busca == "Visitante": df_eq = df_eq[df_eq['AwayTeam']==eq]
            if df_eq.empty: continue

            if es_ultimos:
                if de_busca == "-":
                    if len(df_eq) < ultimos_x: continue
                    df_vent = df_eq.tail(ultimos_x)
                    total = ultimos_x
                    requeridos = ultimos_x
                else:
                    ventana = int(de_busca)
                    requeridos = ultimos_x
                    if ventana < requeridos: ventana = requeridos
                    if len(df_eq) < ventana: continue
                    df_vent = df_eq.tail(ventana)
                    total = len(df_vent)
                df_eq = df_vent.copy()
            else:
                total = len(df_eq)

            is_home = (df_eq['HomeTeam'].values == eq)
            fthg = df_eq['FTHG'].values
            ftag = df_eq['FTAG'].values

            gana = (is_home & (fthg>ftag)) | (~is_home & (ftag>fthg))
            pierde = (is_home & (fthg<ftag)) | (~is_home & (ftag<fthg))
            empata = ~(gana | pierde)

            if res_busca == "G": mask_res = gana
            elif res_busca == "E": mask_res = empata
            elif res_busca == "P": mask_res = pierde
            elif res_busca == "GE": mask_res = gana | empata
            elif res_busca == "GP": mask_res = gana | pierde
            elif res_busca == "EP": mask_res = empata | pierde
            else: mask_res = np.ones(len(df_eq), dtype=bool)

            df_eq = df_eq[mask_res]
            if df_eq.empty: continue
            if not es_ultimos:
                total = len(df_eq)

            is_home = (df_eq['HomeTeam'].values == eq)
            if parte_busca == "1T":
                gf = np.where(is_home, df_eq['HTHG'].values, df_eq['HTAG'].values)
                gc = np.where(is_home, df_eq['HTAG'].values, df_eq['HTHG'].values)
            elif parte_busca == "2T":
                gf = np.where(is_home, df_eq['FTHG'].values-df_eq['HTHG'].values, df_eq['FTAG'].values-df_eq['HTAG'].values)
                gc = np.where(is_home, df_eq['FTAG'].values-df_eq['HTAG'].values, df_eq['FTHG'].values-df_eq['HTHG'].values)
            else:
                gf = np.where(is_home, df_eq['FTHG'].values, df_eq['FTAG'].values)
                gc = np.where(is_home, df_eq['FTAG'].values, df_eq['FTHG'].values)

            cumple = np.ones(len(df_eq), dtype=bool)

            # Col1 Vlr1
            if col1_busca!="Ninguno" and vlr1_busca!="Ninguno":
                try:
                    if col1_busca in ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR']:
                        mapa_col = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC','HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
                        contra = mapa_col.get(col1_busca, col1_busca)
                        v_home = df_eq[col1_busca].values
                        v_away = df_eq[contra].values if contra in df_eq.columns else v_home
                        if fav_c1=="AF": base = np.where(is_home, v_home, v_away)
                        elif fav_c1=="C": base = np.where(is_home, v_away, v_home)
                        else: base = np.where(is_home, v_home, v_away)
                    else:
                        # totales
                        if col1_busca=='GolesTotales': base = df_eq['FTHG'].values+df_eq['FTAG'].values
                        elif col1_busca=='GolesHT': base = df_eq['HTHG'].values+df_eq['HTAG'].values
                        elif col1_busca=='Goles2T': base = (df_eq['FTHG'].values-df_eq['HTHG'].values)+(df_eq['FTAG'].values-df_eq['HTAG'].values)
                        elif col1_busca=='corneTot': base = df_eq['HC'].values+df_eq['AC'].values
                        elif col1_busca=='tirosTot': base = df_eq['HS'].values+df_eq['AS'].values
                        elif col1_busca=='tirosPuertaTot': base = df_eq['HST'].values+df_eq['AST'].values
                        else: base = gf+gc
                    val = float(vlr1_busca)
                    if op1_busca=="=": cumple = cumple & (base==val)
                    elif op1_busca==">": cumple = cumple & (base>val)
                    elif op1_busca==">=": cumple = cumple & (base>=val)
                    elif op1_busca=="<": cumple = cumple & (base<val)
                    elif op1_busca=="<=": cumple = cumple & (base<=val)
                except: pass
            elif col1_busca=="Ninguno" and vlr1_busca!="Ninguno":
                if fav_c1=="AF": base = gf
                elif fav_c1=="C": base = gc
                else: base = gf+gc
                val = float(vlr1_busca)
                if op1_busca=="=": cumple = cumple & (base==val)
                elif op1_busca==">": cumple = cumple & (base>val)
                elif op1_busca==">=": cumple = cumple & (base>=val)
                elif op1_busca=="<": cumple = cumple & (base<val)
                elif op1_busca=="<=": cumple = cumple & (base<=val)

            if am_busca=="Si": cumple = cumple & (gf>0) & (gc>0)
            elif am_busca=="No": cumple = cumple & ~((gf>0) & (gc>0))
            elif am_busca=="Si1P":
                gf1 = np.where(is_home, df_eq['HTHG'].values, df_eq['HTAG'].values)
                gc1 = np.where(is_home, df_eq['HTAG'].values, df_eq['HTHG'].values)
                cumple = cumple & (gf1>0) & (gc1>0)
            elif am_busca=="No1P":
                gf1 = np.where(is_home, df_eq['HTHG'].values, df_eq['HTAG'].values)
                gc1 = np.where(is_home, df_eq['HTAG'].values, df_eq['HTHG'].values)
                cumple = cumple & ~((gf1>0) & (gc1>0))
            elif am_busca=="Si2P":
                gf2 = np.where(is_home, df_eq['FTHG'].values-df_eq['HTHG'].values, df_eq['FTAG'].values-df_eq['HTAG'].values)
                gc2 = np.where(is_home, df_eq['FTAG'].values-df_eq['HTAG'].values, df_eq['FTHG'].values-df_eq['HTHG'].values)
                cumple = cumple & (gf2>0) & (gc2>0)
            elif am_busca=="No2P":
                gf2 = np.where(is_home, df_eq['FTHG'].values-df_eq['HTHG'].values, df_eq['FTAG'].values-df_eq['HTAG'].values)
                gc2 = np.where(is_home, df_eq['FTAG'].values-df_eq['HTAG'].values, df_eq['FTHG'].values-df_eq['HTHG'].values)
                cumple = cumple & ~((gf2>0) & (gc2>0))

            hits = int(cumple.sum())
            if es_ultimos:
                if de_busca=="-":
                    if hits!=total: continue
                else:
                    if hits < requeridos: continue
                pct = hits/total*100 if total else 0
            else:
                pct = hits/total*100 if total else 0
                if pct < pct_min_rango or pct > pct_max_rango: continue

            if hits>0:
                df_cumple = df_eq[cumple].copy()
                df_cumple = df_cumple.sort_values('Date')
                partes = []
                for _, rr in df_cumple.iterrows():
                    suf = 'c' if rr['HomeTeam']==eq else 'f'
                    rh = int(rr['FTHG']); ra = int(rr['FTAG'])
                    am = " ▪" if rh>0 and ra>0 else ""
                    partes.append(f"<b>J{int(rr['Jornada'])}{suf} {rh}-{ra}{am}</b>")
                jors_html = " | ".join(partes)
                hs_avg = float(df_cumple['HS'].mean()) if 'HS' in df_cumple.columns else 0.0
                gf_avg = float(gf[cumple].mean()) if len(gf[cumple])>0 else 0.0
                # IA SCORE SIN CUOTA - FIX PARÉNTESIS
                score_ia = int(min(95, max(5, float(pct)*0.7 + gf_avg*10 + hs_avg)))
                resultados.append({'Equipo':eq,'Liga':df_eq['League'].iloc[0],'PJ':total,'Cumple':hits,'%':round(pct,1),'Jornadas':jors_html,'HS':hs_avg,'GF':gf_avg,'IA':score_ia})

        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(['%','Cumple'], ascending=False)
            from collections import defaultdict
            por_liga = defaultdict(list)
            for _, r in df_res.iterrows():
                por_liga[r['Liga']].append(r['Equipo'])
            leyenda_ligas = []
            for liga in sorted(por_liga.keys()):
                eqs = sorted(set(por_liga[liga]))
                leyenda_ligas.append(f"<div style='font-size:10px;font-family:monospace;line-height:1.2'><b>{liga.upper()}:</b> {', '.join(eqs)}</div>")
            st.markdown(f"<div style='font-size:10px;font-family:monospace;background:#f3f4f6;padding:6px;border-radius:6px;margin:6px 0'><b>Encontrados {len(df_res)} equipos en {len(por_liga)} ligas - Optimizado + IA</b><br>{''.join(leyenda_ligas)}</div>", unsafe_allow_html=True)
            if 'be_pag' not in st.session_state:
                st.session_state.be_pag = 1
            POR_PAG = 100
            limite = st.session_state.be_pag * POR_PAG
            df_mostrar = df_res.head(limite)
            lineas_html=[]
            for _, r in df_mostrar.iterrows():
                linea=f"<div style='font-size:11px; font-family:monospace; line-height:1.4; padding:8px 0; border-bottom:1px solid #ddd;'><div style='font-size:12px; font-weight:900; color:#0A2342;'>{r['Equipo'].upper()} IA {r['IA']}% {r['Cumple']}# {r['%']}% {r['GF']:.1f}GF</div><div style='margin-top:4px;'>{r['Jornadas']}</div></div>"
                lineas_html.append(linea)
            st.markdown(f"<div style='background:#fff; border:1px solid #ddd; max-height:700px; overflow-y:auto; padding:8px;'>{''.join(lineas_html)}</div>", unsafe_allow_html=True)
            restantes = len(df_res) - len(df_mostrar)
            if restantes > 0:
                if st.button(f"Cargar 100 mas ({restantes} restantes)", use_container_width=True, key=f"be_cargar_mas_{st.session_state.be_pag}_{len(df_res)}"):
                    st.session_state.be_pag += 1
                    st.rerun()
            else:
                if len(df_res) > POR_PAG:
                    if st.button("Volver al inicio (100)", use_container_width=True, key=f"be_reset_pag_{len(df_res)}"):
                        st.session_state.be_pag = 1
                        st.rerun()
        else:
            st.warning("Ningun equipo cumple esas condiciones")
            st.session_state.be_pag = 1
###################################
#######################################

with st.expander("🎯 Creador Apuestas", expanded=False):
    st.caption("Predicción universal - misma tarjeta")

    col_l, col_t = st.columns(2)
    ca_liga = col_l.selectbox("Liga", sorted(df['League'].unique()), key="ca_liga")
    ca_temp = col_t.selectbox("Temporada", sorted(df[df['League']==ca_liga]['Season'].unique(), reverse=True), key="ca_temp")

    df_creador_base = df[(df['League']==ca_liga) & (df['Season']==ca_temp)].copy()
    df_creador, _ = calcular_estado_jornada(df_creador_base)

    jmin_all = int(df_creador['Jornada'].min()); jmax_all = int(df_creador['Jornada'].max())
    if jmin_all >= jmax_all:
        j1, j2 = jmin_all, jmax_all
        st.caption(f"Jornadas a analizar: J{j1} (única)")
    else:
        j1, j2 = st.slider("Jornadas a analizar", jmin_all, jmax_all, (jmin_all, jmax_all), key="ca_jornadas")

    equipos = sorted(pd.unique(df_creador[['HomeTeam','AwayTeam']].values.ravel()))
    col_eq1, col_eq2 = st.columns(2)
    eq1 = col_eq1.selectbox("Eq1 (local)", [""] + equipos, key="ca_eq1")
    eq2 = col_eq2.selectbox("Eq2 (visitante)", [""] + [e for e in equipos if e != eq1], key="ca_eq2")

    if st.button("Generar partido", key="ca_gen_creador", use_container_width=True) and eq1 and eq2:
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
            w = np.exp(np.linspace(-0.5,0,len(df_eq)))
            w/=w.sum()
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
    with st.expander("🗓 Agenda Apuestas", expanded=False):
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

            # === DASHBOARD EDGE === - FIX NESTED
            with st.container(border=True):
                st.markdown("**📊 Ver dónde tengo edge**")
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
                        st.dataframe(liga_stats.sort_values('ROI%', ascending=False), hide_index=True, use_container_width=True, column_config={"liga":"Liga","Ap":"Ap","W":"✅","L":"❌","Win%":"%W","ROI%":"ROI","Benef":"€"})
                    with tab2:
                        tipo_stats = df_analisis.groupby('tipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum'),Stake=('stake','sum')).reset_index()
                        tipo_stats['ROI%'] = (tipo_stats['Benef']/tipo_stats['Stake']*100).round(1)
                        st.dataframe(tipo_stats.sort_values('ROI%', ascending=False), hide_index=True, use_container_width=True)
                    with tab3:
                        df_analisis['equipo'] = df_analisis['partido'].str.split(' vs ').str[0]
                        equipo_stats = df_analisis.groupby('equipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum')).reset_index()
                        equipo_stats = equipo_stats[equipo_stats['Ap']>=2]
                        equipo_stats['Win%'] = (equipo_stats['W']/equipo_stats['Ap']*100).round(0).astype(int)
                        st.dataframe(equipo_stats.sort_values('Benef', ascending=False).head(10), hide_index=True, use_container_width=True, column_config={"equipo":"Equipo","Ap":"Ap","W":"✅","Win%":"%W","Benef":"€"})
                else:
                    st.info("Cierra apuestas para ver stats")

            # LISTA RÁPIDA CON BORRADO INSTANTÁNEO
                        
            for ap in sorted(apuestas, key=lambda x: x['id'], reverse=True)[:50]:
                col1,col2,col3,col4 = st.columns([1.3,4.5,2.2,0.6])
                col1.caption(f"{ap['fecha']}")
                col2.write(f"**{ap['partido']}** {ap['marcador']} · **{ap.get('detalle','')}** · min {ap.get('minuto',0)}' · {ap.get('tipo','')}")
                col3.write(f"{ap['stake']}€ @ {ap['cuota']} → **{ap['resultado']}**")
                if col4.button("🗑", key=f"del_{ap['id']}"):
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

                if col_r2.button("💾 Guardar resultado", use_container_width=True, key="btn_guardar"):
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

    liga1_res = col_izq.multiselect("Liga", ligas_res, default=[liga_sel[0]] if liga_sel else [], key="res_liga1")
    liga2_res = col_der.multiselect("Liga2", ligas_res, key="res_liga2")

    temp1_res = col_izq.multiselect("Temporada", temps_res, default=[temp_sel[-1]] if temp_sel else [], key="res_temp1")
    temp2_res = col_der.multiselect("Temp2", temps_res, key="res_temp2")

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
            n_g, n_e, n_p = int(gana.sum()), int(empata.sum()), int(pierde.sum())
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

    if 'resumen_buscado' not in st.session_state:
        st.session_state.resumen_buscado = False

    if st.button("Buscar resumen", type="primary", use_container_width=True, key="btn_resumen"):
        st.session_state.resumen_buscado = True

    if st.session_state.resumen_buscado:
        if not equipo_res:
            st.warning("Selecciona al menos Equipo")
        else:
            stats1 = calcular_stats_equipo(df_res_base1, equipo_res, temp1_res)
            stats2 = None
            if equipo2_res and liga2_res and temp2_res:
                df_res_base2 = df[df['League'].isin(liga2_res) & df['Season'].isin(temp2_res)]
                stats2 = calcular_stats_equipo(df_res_base2, equipo2_res, temp2_res)

            if not stats1:
                st.warning(f"{equipo_res} no tiene partidos")
            else:
                lista_stats1, df_clas_res1, df_eq_total1 = stats1

                # === MINI RESUMEN EQ1 CON DELTA ===
                if lista_stats1:
                    temp_orden_asc = sorted(lista_stats1, key=lambda x: x['temp'])
                    historial = {}
                    for s in lista_stats1:
                        dft = df_clas_res1[(df_clas_res1['Equipo']==equipo_res) & (df_clas_res1['Season']==s['temp'])]
                        pos = int(dft.sort_values('Jornada').iloc[-1]['Pos']) if not dft.empty else 0
                        historial[s['temp']] = {'pos':pos,'pts':s['pts_final'],'g':s['n_g'],'e':s['n_e'],'p':s['n_p']}

                    # calculo delta en orden cronologico asc
                    delta_map = {}
                    for idx, s in enumerate(temp_orden_asc):
                        if idx==0: 
                            delta_map[s['temp']]=""
                            continue
                        cur = historial.get(s['temp']); prev = historial.get(temp_orden_asc[idx-1]['temp'])
                        if not cur or not prev: 
                            delta_map[s['temp']]=""
                            continue
                        d_pos = prev['pos'] - cur['pos']
                        d_pts = cur['pts'] - prev['pts']
                        d_g = cur['g'] - prev['g']
                        d_e = cur['e'] - prev['e']
                        d_p = cur['p'] - prev['p']
                        c_pos = "#0f8105" if d_pos>0 else "#dc2626" if d_pos<0 else "#6b7280"
                        c_pts = "#0f8105" if d_pts>0 else "#dc2626" if d_pts<0 else "#6b7280"
                        c_g = "#0f8105" if d_g>0 else "#dc2626" if d_g<0 else "#6b7280"
                        c_e = "#b45309" if d_e!=0 else "#6b7280"
                        c_p = "#dc2626" if d_p>0 else "#0f8105" if d_p<0 else "#6b7280"
                        d_pos_col = f"<span style='color:{c_pos};font-weight:900'>{d_pos:+d}&ordm;</span>" if cur['pos'] and prev['pos'] else ""
                        delta_map[s['temp']] = f" | {d_pos_col} <span style='color:{c_pts};font-weight:900'>{d_pts:+d}pts</span> <span style='color:{c_g};font-weight:900'>{d_g:+d}G</span> <span style='color:{c_e};font-weight:900'>{d_e:+d}E</span> <span style='color:{c_p};font-weight:900'>{d_p:+d}P</span>"

                    # render en orden descendente (mas reciente arriba)
                    temp_orden_desc = sorted(lista_stats1, key=lambda x: x['temp'], reverse=True)
                    filas = []
                    for s in temp_orden_desc:
                        cur = historial.get(s['temp'])
                        if not cur: continue
                        delta_html = delta_map.get(s['temp'],"")
                        linea = f"<div style='font-size:10px;font-family:monospace'><b>{equipo_res.title()}</b> {s['temp']}: <span style='color:#4B0082;font-weight:900'>{cur['pos']}&ordm; {cur['pts']}pts</span> | {cur['g']}G {cur['e']}E {cur['p']}P<span style='font-size:9px'>{delta_html}</span></div>"
                        filas.append(linea)
                    st.caption(f"Resumen {equipo_res}")
                    st.markdown("\n".join(filas), unsafe_allow_html=True)

                # === MINI RESUMEN EQ2 CON DELTA ===
                if stats2:
                    lista_stats2, df_clas_res2, df_eq_total2 = stats2
                    temp_orden2_asc = sorted(lista_stats2, key=lambda x: x['temp'])
                    historial2 = {}
                    for s in lista_stats2:
                        dft = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season']==s['temp'])]
                        pos = int(dft.sort_values('Jornada').iloc[-1]['Pos']) if not dft.empty else 0
                        historial2[s['temp']] = {'pos':pos,'pts':s['pts_final'],'g':s['n_g'],'e':s['n_e'],'p':s['n_p']}

                    delta_map2 = {}
                    for idx, s in enumerate(temp_orden2_asc):
                        if idx==0:
                            delta_map2[s['temp']]=""
                            continue
                        cur = historial2.get(s['temp']); prev = historial2.get(temp_orden2_asc[idx-1]['temp'])
                        if not cur or not prev:
                            delta_map2[s['temp']]=""
                            continue
                        d_pos = prev['pos'] - cur['pos']
                        d_pts = cur['pts'] - prev['pts']
                        d_g = cur['g'] - prev['g']
                        d_e = cur['e'] - prev['e']
                        d_p = cur['p'] - prev['p']
                        c_pos = "#0f8105" if d_pos>0 else "#dc2626" if d_pos<0 else "#6b7280"
                        c_pts = "#0f8105" if d_pts>0 else "#dc2626" if d_pts<0 else "#6b7280"
                        c_g = "#0f8105" if d_g>0 else "#dc2626" if d_g<0 else "#6b7280"
                        c_e = "#b45309" if d_e!=0 else "#6b7280"
                        c_p = "#dc2626" if d_p>0 else "#0f8105" if d_p<0 else "#6b7280"
                        d_pos_col = f"<span style='color:{c_pos};font-weight:900'>{d_pos:+d}&ordm;</span>" if cur['pos'] and prev['pos'] else ""
                        delta_map2[s['temp']] = f" | {d_pos_col} <span style='color:{c_pts};font-weight:900'>{d_pts:+d}pts</span> <span style='color:{c_g};font-weight:900'>{d_g:+d}G</span> <span style='color:{c_e};font-weight:900'>{d_e:+d}E</span> <span style='color:{c_p};font-weight:900'>{d_p:+d}P</span>"

                    temp_orden2_desc = sorted(lista_stats2, key=lambda x: x['temp'], reverse=True)
                    filas2 = []
                    for s in temp_orden2_desc:
                        cur = historial2.get(s['temp'])
                        if not cur: continue
                        delta_html = delta_map2.get(s['temp'],"")
                        linea = f"<div style='font-size:10px;font-family:monospace'><b>{equipo2_res.title()}</b> {s['temp']}: <span style='color:#4B0082;font-weight:900'>{cur['pos']}&ordm; {cur['pts']}pts</span> | {cur['g']}G {cur['e']}E {cur['p']}P<span style='font-size:9px'>{delta_html}</span></div>"
                        filas2.append(linea)
                    st.caption(f"Resumen {equipo2_res}")
                    st.markdown("\n".join(filas2), unsafe_allow_html=True)

                # === GRAFICA MEJORADA CON PUNTOS G/P/E - SIN LEYENDA ===
                import matplotlib.pyplot as plt
                PALETA = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#e377c2', '#17becf', '#bcbd22', '#8c564b', '#000000']

                def _resultados_por_jornada(df_eq_total_temp, equipo):
                    res = {}
                    df_t = df_eq_total_temp.sort_values('Jornada')
                    for _, r in df_t.iterrows():
                        es_loc = r['HomeTeam'] == equipo
                        if es_loc:
                            if r['FTHG'] > r['FTAG']: res[int(r['Jornada'])] = 'G'
                            elif r['FTHG'] < r['FTAG']: res[int(r['Jornada'])] = 'P'
                            else: res[int(r['Jornada'])] = 'E'
                        else:
                            if r['FTAG'] > r['FTHG']: res[int(r['Jornada'])] = 'G'
                            elif r['FTAG'] < r['FTHG']: res[int(r['Jornada'])] = 'P'
                            else: res[int(r['Jornada'])] = 'E'
                    return res

                df_graf1 = df_clas_res1[(df_clas_res1['Equipo']==equipo_res) & (df_clas_res1['Season'].isin(temp1_res))]
                fig = plt.figure(figsize=(5, 2.8), dpi=150)
                ax = fig.add_subplot(111)
                leyendas = []
                max_pos = 0

                for idx, temp in enumerate(temp1_res):
                    d = df_graf1[df_graf1['Season']==temp].sort_values('Jornada')
                    if not d.empty:
                        color = PALETA[idx % len(PALETA)]
                        ax.plot(d['Jornada'], d['Pos'], linewidth=1.4, color=color, alpha=0.7, zorder=1)
                        max_pos = max(max_pos, d['Pos'].max())
                        df_eq_t = df_eq_total1[(df_eq_total1['Season']==temp) & ((df_eq_total1['HomeTeam']==equipo_res)|(df_eq_total1['AwayTeam']==equipo_res))]
                        res_map = _resultados_por_jornada(df_eq_t, equipo_res)
                        col_map = {'G':'#0f8105', 'P':'#dc2626', 'E':'#000000'}
                        for _, row in d.iterrows():
                            j = int(row['Jornada'])
                            r = res_map.get(j, 'E')
                            ax.scatter(j, row['Pos'], c=col_map[r], s=22, zorder=5, edgecolors='white', linewidths=0.4)
                        leyendas.append(f"<span style='color:{color};font-size:14px'>-</span> {equipo_res} {temp}")

                if stats2:
                    df_graf2 = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season'].isin(temp2_res))]
                    for idx, temp in enumerate(temp2_res):
                        d = df_graf2[df_graf2['Season']==temp].sort_values('Jornada')
                        if not d.empty:
                            color = PALETA[(len(temp1_res)+idx) % len(PALETA)]
                            ax.plot(d['Jornada'], d['Pos'], linewidth=1.4, linestyle='--', color=color, alpha=0.7, zorder=1)
                            max_pos = max(max_pos, d['Pos'].max())
                            df_eq_t = df_eq_total2[(df_eq_total2['Season']==temp) & ((df_eq_total2['HomeTeam']==equipo2_res)|(df_eq_total2['AwayTeam']==equipo2_res))]
                            res_map = _resultados_por_jornada(df_eq_t, equipo2_res)
                            col_map = {'G':'#0f8105', 'P':'#dc2626', 'E':'#000000'}
                            for _, row in d.iterrows():
                                j = int(row['Jornada'])
                                r = res_map.get(j, 'E')
                                ax.scatter(j, row['Pos'], c=col_map[r], s=22, zorder=5, edgecolors='white', linewidths=0.4)
                            leyendas.append(f"<span style='color:{color};font-size:14px'>--</span> {equipo2_res} {temp}")

                ax.invert_yaxis()
                ax.set_ylim(max_pos+1, 0.5)
                ax.set_xlabel("Jornada", fontsize=8)
                ax.set_ylabel("Posicion", fontsize=8)
                ax.set_xticks(range(1, 39, 2))
                ax.grid(True, alpha=0.25, linestyle=':', linewidth=0.5)
                ax.tick_params(labelsize=7)
                plt.tight_layout(pad=0.3)
                st.pyplot(fig, use_container_width=True)
                plt.close()
                if leyendas:
                    st.markdown("<div style='font-size:10px;line-height:1.4'>" + " &nbsp; ".join(leyendas) + "</div>", unsafe_allow_html=True)

                # --- HELPER NUEVO (ponlo justo antes del for) ---
                def jornadas_simples_resumen(df_temp, equipo, condicion_fn):
                    if df_temp.empty:
                        return "-"
                    df_temp = df_temp.sort_values('Jornada')
                    out = []
                    for _, r in df_temp.iterrows():
                        if not condicion_fn(r):
                            continue
                        suf = 'c' if r['HomeTeam'] == equipo else 'f'
                        out.append(f"J{int(r['Jornada'])}{suf}")
                    return " | ".join(out) if out else "-"

                # === TARJETAS EQ1 - MEJORADO ===
                for i, s in enumerate(lista_stats1):
                    df_temp_cf = df_eq_total1[(df_eq_total1['Season']==s['temp'])].copy()
                    df_casa = df_temp_cf[df_temp_cf['HomeTeam']==s['equipo']]
                    df_fuera = df_temp_cf[df_temp_cf['AwayTeam']==s['equipo']]
                    def g_e_p(df_x, es_casa):
                        if df_x.empty: return 0,0,0
                        if es_casa:
                            g = (df_x['FTHG']>df_x['FTAG']).sum()
                            p = (df_x['FTHG']<df_x['FTAG']).sum()
                        else:
                            g = (df_x['FTAG']>df_x['FTHG']).sum()
                            p = (df_x['FTAG']<df_x['FTHG']).sum()
                        e = len(df_x)-g-p
                        return int(g),int(e),int(p)
                    g_c,e_c,p_c = g_e_p(df_casa, True)
                    g_f,e_f,p_f = g_e_p(df_fuera, False)
                    df_r = df_temp_cf.sort_values('Date')
                    seq = []
                    for _, r in df_r.iterrows():
                        es_c = r['HomeTeam']==s['equipo']
                        seq.append('G' if (r['FTHG']>r['FTAG'] if es_c else r['FTAG']>r['FTHG']) else 'P' if (r['FTHG']<r['FTAG'] if es_c else r['FTAG']<r['FTHG']) else 'E')
                    max_g = max_p = cur_g = cur_p = 0
                    for x in seq:
                        if x=='G': cur_g+=1; max_g=max(max_g,cur_g)
                        else: cur_g=0
                        if x=='P': cur_p+=1; max_p=max(max_p,cur_p)
                        else: cur_p=0

                    total_1p = len(df_temp_cf)
                    total_gol_1p = df_temp_cf['HTHG'] + df_temp_cf['HTAG']
                    g05_1p = (total_gol_1p > 0.5).sum()
                    g1_1p = (total_gol_1p > 1).sum()
                    g15_1p = (total_gol_1p > 1.5).sum()
                    si1p = ((df_temp_cf['HTHG']>0) & (df_temp_cf['HTAG']>0)).sum()
                    
                    pct_g05 = round(g05_1p/total_1p*100) if total_1p else 0
                    pct_g1 = round(g1_1p/total_1p*100) if total_1p else 0
                    pct_g15 = round(g15_1p/total_1p*100) if total_1p else 0
                    pct_si1p = round(si1p/total_1p*100) if total_1p else 0

                    jor_g05 = jornadas_simples_resumen(df_temp_cf, s['equipo'], lambda r: (r['HTHG']+r['HTAG']) > 0.5)
                    jor_g1 = jornadas_simples_resumen(df_temp_cf, s['equipo'], lambda r: (r['HTHG']+r['HTAG']) > 1)
                    jor_g15 = jornadas_simples_resumen(df_temp_cf, s['equipo'], lambda r: (r['HTHG']+r['HTAG']) > 1.5)
                    jor_si1p = jornadas_simples_resumen(df_temp_cf, s['equipo'], lambda r: r['HTHG']>0 and r['HTAG']>0)

                    st.markdown(f"""
                    <div style='background:#f8f9fa;padding:10px 10px;border-left:4px solid #0A2342;margin:8px 0 0 0;font-family:monospace;font-size:11px;line-height:1.5'>
                    <b style='font-size:13px'>{s['equipo'].title()} | {s['temp']}</b><br>
                    <b>{s['total']}PJ</b> -> <span style='color:#0f8105;font-weight:900'>{s['n_g']}G {s['pct_g']}%</span> | <span style='color:#b45309;font-weight:900'>{s['n_e']}E {s['pct_e']}%</span> | <span style='color:#dc2626;font-weight:900'>{s['n_p']}P {s['pct_p']}%</span><br>
                    <span style='color:#000'>Casa: <span style='color:#0f8105'>{g_c}G</span> <span style='color:#b45309'>{e_c}E</span> <span style='color:#dc2626'>{p_c}P</span> | Fuera: <span style='color:#0f8105'>{g_f}G</span> <span style='color:#b45309'>{e_f}E</span> <span style='color:#dc2626'>{p_f}P</span></span><br>
                    <b>Goles:</b> {int(s['gf_tot'])}GF {int(s['gc_tot'])}GC | Prom: {s['gf_avg']:.2f}-{s['gc_avg']:.2f} | AM:{s['am']}/{s['total']} ({round(s['am']/s['total']*100)}%) | Over2.5:{s['over25']}/{s['total']} ({round(s['over25']/s['total']*100)}%)<br>
                    <b>GStats 1P:</b> G1T>0.5: {g05_1p}/{total_1p} ({pct_g05}%) | >1: {g1_1p}/{total_1p} ({pct_g1}%) | >1.5: {g15_1p}/{total_1p} ({pct_g15}%)<br>
                    <div style='font-size:10px;color:#333;margin:2px 0 2px 12px;line-height:1.4'>
                    >0.5: {jor_g05}<br>
                    >1: {jor_g1}<br>
                    >1.5: {jor_g15}
                    </div>
                    <b>Si1P:</b> {si1p}/{total_1p} ({pct_si1p}%)<br>
                    <div style='font-size:10px;color:#333;margin:2px 0 2px 12px'>{jor_si1p}</div>
                    <b>Stats:</b> {s['hs']:.1f}T | {s['hst']:.1f}TP | {s['hf']:.1f}F | {s['hc']:.1f}C | {s['hy']:.1f}A | {s['hr']:.1f}R<br>
                    <b>Racha:</b> Mejor <span style='color:#0f8105;font-weight:900'>{max_g}G</span> | Peor <span style='color:#dc2626;font-weight:900'>{max_p}P</span><br>
                    <b>Pos final:</b> <span style='color:#4B0082;font-weight:900'>{s['pos_final']}º</span> | <b>Pts final:</b> <span style='color:#4B0082;font-weight:900'>{s['pts_final']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    key_j = f"ver_jor_{s['equipo']}_{s['temp']}_eq1"
                    if key_j not in st.session_state:
                        st.session_state[key_j] = False
                    with st.container(border=True):
                        st.markdown(f"**Jornadas {s['equipo'].title()} {s['temp']} ({s['total']})**")
                        if not st.session_state[key_j]:
                            if st.button(f"Cargar partidos {s['equipo'].title()}", key=f"btn_{key_j}", type="primary", use_container_width=True):
                                st.session_state[key_j] = True
                                st.rerun()
                        else:
                            c1,c2 = st.columns([1,3])
                            if c1.button("Ocultar", key=f"hide_{key_j}"):
                                st.session_state[key_j] = False
                                st.rerun()
                            c2.caption(f"{s['equipo'].title()} | {s['temp']}")
                            st.markdown(f"<div style='background:#fff;border:1px solid #ddd;padding:6px;max-height:500px;overflow-y:auto'>{s['jors_html']}</div>", unsafe_allow_html=True)

                # === TARJETAS EQ2 ===
                if stats2:
                    lista_stats2, df_clas_res2, df_eq_total2 = stats2
                    for i, s in enumerate(lista_stats2):
                        df_temp_cf = df_eq_total2[(df_eq_total2['Season']==s['temp'])].copy()
                        df_casa = df_temp_cf[df_temp_cf['HomeTeam']==s['equipo']]
                        df_fuera = df_temp_cf[df_temp_cf['AwayTeam']==s['equipo']]
                        def g_e_p2(df_x, es_casa):
                            if df_x.empty: return 0,0,0
                            if es_casa:
                                g = (df_x['FTHG']>df_x['FTAG']).sum()
                                p = (df_x['FTHG']<df_x['FTAG']).sum()
                            else:
                                g = (df_x['FTAG']>df_x['FTHG']).sum()
                                p = (df_x['FTAG']<df_x['FTHG']).sum()
                            e = len(df_x)-g-p
                            return int(g),int(e),int(p)
                        g_c,e_c,p_c = g_e_p2(df_casa, True)
                        g_f,e_f,p_f = g_e_p2(df_fuera, False)
                        df_r = df_temp_cf.sort_values('Date')
                        seq = []
                        for _, r in df_r.iterrows():
                            es_c = r['HomeTeam']==s['equipo']
                            seq.append('G' if (r['FTHG']>r['FTAG'] if es_c else r['FTAG']>r['FTHG']) else 'P' if (r['FTHG']<r['FTAG'] if es_c else r['FTAG']<r['FTHG']) else 'E')
                        max_g = max_p = cur_g = cur_p = 0
                        for x in seq:
                            if x=='G': cur_g+=1; max_g=max(max_g,cur_g)
                            else: cur_g=0
                            if x=='P': cur_p+=1; max_p=max(max_p,cur_p)
                            else: cur_p=0
                        df_1p_calc = df_temp_cf.copy()
                        total_gol_1p = df_1p_calc['HTHG'] + df_1p_calc['HTAG']
                        am_1p = (df_1p_calc['HTHG'] > 0) & (df_1p_calc['HTAG'] > 0)
                        g05_1p = (total_gol_1p > 0.5).sum()
                        g1_1p = (total_gol_1p > 1).sum()
                        si1p = am_1p.sum()
                        total_1p = len(df_1p_calc)
                        pct_g05 = round(g05_1p/total_1p*100) if total_1p else 0
                        pct_g1 = round(g1_1p/total_1p*100) if total_1p else 0
                        pct_si1p = round(si1p/total_1p*100) if total_1p else 0

                        st.markdown(f"""
                        <div style='background:#e0f2fe;padding:8px 10px;border-left:4px solid #0369a1;margin:6px 0 0 0;font-family:monospace;font-size:10px;line-height:1.4'>
                        <b style='font-size:12px'>{s['equipo'].title()} | {s['temp']}</b><br>
                        <b>{s['total']}PJ</b> -> <span style='color:#0f8105;font-weight:900'>{s['n_g']}G {s['pct_g']}%</span> | <span style='color:#b45309;font-weight:900'>{s['n_e']}E {s['pct_e']}%</span> | <span style='color:#dc2626;font-weight:900'>{s['n_p']}P {s['pct_p']}%</span><br>
                        <span style='font-size:9px;color:#000'>Casa: <span style='color:#0f8105'>{g_c}G</span> <span style='color:#b45309'>{e_c}E</span> <span style='color:#dc2626'>{p_c}P</span> | Fuera: <span style='color:#0f8105'>{g_f}G</span> <span style='color:#b45309'>{e_f}E</span> <span style='color:#dc2626'>{p_f}P</span></span><br>
                        <b>Goles:</b> {int(s['gf_tot'])}GF {int(s['gc_tot'])}GC | Prom: {s['gf_avg']:.2f}-{s['gc_avg']:.2f} | AM:{s['am']}/{s['total']} ({round(s['am']/s['total']*100)}%) | Over2.5:{s['over25']}/{s['total']} ({round(s['over25']/s['total']*100)}%)<br>
                        <b>GStats 1P:</b> G1T>0.5: {g05_1p}/{total_1p} ({pct_g05}%) | >1: {g1_1p}/{total_1p} ({pct_g1}%)<br>
                        <b>Si1P:</b> {si1p}/{total_1p} ({pct_si1p}%)<br>
                        <b>Stats:</b> {s['hs']:.1f}T | {s['hst']:.1f}TP | {s['hf']:.1f}F | {s['hc']:.1f}C | {s['hy']:.1f}A | {s['hr']:.1f}R<br>
                        <b>Racha:</b> Mejor <span style='color:#0f8105;font-weight:900'>{max_g}G</span> | Peor <span style='color:#dc2626;font-weight:900'>{max_p}P</span><br>
                        <b>Pos final:</b> <span style='color:#4B0082;font-weight:900'>{s['pos_final']}º</span> | <b>Pts final:</b> <span style='color:#4B0082;font-weight:900'>{s['pts_final']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        key_j2 = f"ver_jor_{s['equipo']}_{s['temp']}_eq2"
                        if key_j2 not in st.session_state:
                            st.session_state[key_j2] = False
                        with st.container(border=True):
                            st.markdown(f"**Jornadas {s['equipo'].title()} {s['temp']} ({s['total']})**")
                            if not st.session_state[key_j2]:
                                if st.button(f"Cargar partidos {s['equipo'].title()}", key=f"btn_{key_j2}", type="primary", use_container_width=True):
                                    st.session_state[key_j2] = True
                                    st.rerun()
                            else:
                                c1,c2 = st.columns([1,3])
                                if c1.button("Ocultar", key=f"hide_{key_j2}"):
                                    st.session_state[key_j2] = False
                                    st.rerun()
                                c2.caption(f"{s['equipo'].title()} | {s['temp']}")
                                st.markdown(f"<div style='background:#fff;border:1px solid #ddd;padding:6px;max-height:500px;overflow-y:auto'>{s['jors_html']}</div>", unsafe_allow_html=True)

        if st.button("Cerrar resumen", key="cerrar_resumen"):
            st.session_state.resumen_buscado = False
            st.rerun()

# ==================== DESPLEGABLE DATOS - INDEPENDIENTE CON FILTROS PROPIOS - V2 RÁPIDO Y COMPATIBLE ====================
with st.expander("📋 DATOS", expanded=False):
    # Filtros propios, independientes de todo lo demas - NO TOCA df global
    if 'datos_cargado' not in st.session_state:
        st.session_state.datos_cargado = False
    if 'datos_liga_sel' not in st.session_state:
        st.session_state.datos_liga_sel = []
    if 'datos_temp_sel' not in st.session_state:
        st.session_state.datos_temp_sel = []

    st.caption("Filtro independiente - no afecta al resto de la app | v2 más rápido, misma lógica")
    c1, c2, c3 = st.columns([2,2,1])
    try:
        ligas_datos_disp = sorted(df['League'].dropna().unique())
    except:
        ligas_datos_disp = sorted(df_original['League'].dropna().unique())
    try:
        temps_datos_disp = sorted(df['Season'].dropna().unique())
    except:
        temps_datos_disp = sorted(df_original['Season'].dropna().unique())

    liga_datos_sel = c1.multiselect("Liga", ligas_datos_disp, default=st.session_state.datos_liga_sel, key="filtro_datos_liga_v2")
    temp_datos_sel = c2.multiselect("Temporada", temps_datos_disp, default=st.session_state.datos_temp_sel, key="filtro_datos_temp_v2")
    limite_filas = c3.number_input("Filas", 100, 10000, 2000, step=500, key="limite_datos_v2")

    col_btn1, col_btn2 = st.columns([1,3])
    if col_btn1.button("Cargar", key="btn_cargar_datos_v2", type="primary"):
        st.session_state.datos_liga_sel = liga_datos_sel
        st.session_state.datos_temp_sel = temp_datos_sel
        st.session_state.datos_cargado = True
        st.rerun()
    if col_btn2.button("Limpiar", key="btn_limpiar_datos_v2"):
        st.session_state.datos_cargado = False
        st.session_state.datos_liga_sel = []
        st.session_state.datos_temp_sel = []
        st.rerun()

    if st.session_state.datos_cargado:
        try:
            _df_base = df if 'df' in globals() else df_original
            if liga_datos_sel:
                _df_base = _df_base[_df_base['League'].isin(liga_datos_sel)]
            if temp_datos_sel:
                _df_base = _df_base[_df_base['Season'].isin(temp_datos_sel)]
            
            total = len(_df_base)
            _df_show = _df_base.head(limite_filas)
            
            st.caption(f"Mostrando {len(_df_show)} de {total} partidos | Ligas: {', '.join(liga_datos_sel) if liga_datos_sel else 'Todas'} | Temps: {', '.join(temp_datos_sel) if temp_datos_sel else 'Todas'}")
            
            # CAMBIO 1: dataframe nativo (100x más rápido que text_area con 30k lineas)
            st.dataframe(_df_show, use_container_width=True, height=600)

            # CAMBIO 2: preparamos el texto en minúsculas SOLO de lo filtrado y con límite, no de todo
            _txt_bruto = _df_show.to_csv(index=False, sep='|').lower()
            
            # Boton copiar optimizado
            import json
            _txt_json = json.dumps(_txt_bruto)
            components.html(f"""
                <div style="margin:8px 0">
                    <button id="btn_copy_datos" style="
                        background:#0A2342;color:#fff;border:none;
                        padding:10px 18px;border-radius:8px;
                        font-size:14px;font-weight:700;
                        width:100%;cursor:pointer;
                    ">📋 Copiar al portapapeles ({len(_df_show)} filas)</button>
                    <div id="copy_msg" style="font-size:11px;font-family:monospace;margin-top:4px;color:#0f8105;display:none">¡Copiado!</div>
                </div>
                <script>
                    const btn = document.getElementById('btn_copy_datos');
                    const msg = document.getElementById('copy_msg');
                    const texto = {_txt_json};
                    btn.addEventListener('click', async () => {{
                        try {{
                            await navigator.clipboard.writeText(texto);
                            msg.style.display = 'block';
                            btn.innerText = '✅ ¡Copiado!';
                            setTimeout(()=>{{ msg.style.display='none'; btn.innerText='📋 Copiar al portapapeles ({len(_df_show)} filas)'; }}, 2000);
                        }} catch(e) {{
                            const ta = document.createElement('textarea');
                            ta.value = texto;
                            document.body.appendChild(ta);
                            ta.select();
                            document.execCommand('copy');
                            document.body.removeChild(ta);
                            msg.style.display = 'block';
                            btn.innerText = '✅ ¡Copiado!';
                            setTimeout(()=>{{ msg.style.display='none'; btn.innerText='📋 Copiar al portapapeles ({len(_df_show)} filas)'; }}, 2000);
                        }}
                    }});
                </script>
            """, height=90)
            
            # AÑADIDO: descarga directa sin pasar por portapapeles (mucho más rápido en móvil)
            st.download_button("📥 Descargar filtrado CSV", _txt_bruto.encode('utf-8'), file_name="datos_filtrados.csv", mime="text/csv", use_container_width=True, key="dl_datos_v2")
            
            st.text_area("datos_bruto_independiente", value=_txt_bruto, height=250, key="datos_bruto_v5_indep", label_visibility="collapsed")
        except Exception as _e:
            st.error(f"error: {_e}")
    else:
        st.info("Selecciona Liga/Temporada y dale a Cargar")
# ==================== FIN DATOS INDEPENDIENTE V2 ====================
