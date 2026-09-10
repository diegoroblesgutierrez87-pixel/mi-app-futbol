import streamlit as st
import pandas as pd
import pathlib
import re
import unicodedata
import numpy as np

st.set_page_config(page_title="Lite Rapido + Local", layout="wide")
# --- FIX SCROLL MOVIL - QUITA REINICIO AL TOCAR BORDE ARRIBA ---
st.markdown("""
<style>
html, body {
    overscroll-behavior-y: contain!important;
    overscroll-behavior: none!important;
    touch-action: pan-y;
    -webkit-overflow-scrolling: touch;
}
[data-testid="stAppViewContainer"] {
    overscroll-behavior-y: contain!important;
    overscroll-behavior: none!important;
}
[data-testid="stHeader"] {
    overscroll-behavior: none!important;
}
</style>
<script>
// bloquea pull-to-refresh en movil
let startY = 0;
document.addEventListener('touchstart', e => {
    startY = e.touches[0].clientY;
}, {passive: false});
document.addEventListener('touchmove', e => {
    const currentY = e.touches[0].clientY;
    const diff = currentY - startY;
    if (window.scrollY <= 0 && diff > 0) {
        e.preventDefault();
    }
}, {passive: false});
</script>
""", unsafe_allow_html=True)
# --- UTILS ---
def normaliza(s):
    if pd.isna(s): return ""
    n = unicodedata.normalize('NFKD', str(s)).encode('ASCII','ignore').decode('ASCII')
    return n.upper().strip()

def abreviar_equipo(nombre):
    n = normaliza(nombre)
    if not n or n == "NAN": return "XXX"
    if 'KAISERSLAUTERN' in n: return 'KAI'
    if 'DARMSTADT' in n: return 'DAR'
    if 'ATLETICO' in n: return 'ATM'
    if 'BILBAO' in n or 'ATHLETIC' in n: return 'ATH'
    if 'QADISIYAH' in n: return 'QAD'
    if 'DIRIYAH' in n: return 'DIR'
    # quita "1. ", "2. " del inicio
    n = re.sub(r'^\d+\.?\s*', '', n)
    # quita prefijos feos
    for pref in ['FC ','REAL ','CLUB ','DEPORTIVO ','CLUB ATLETICO ','SV ','CF ','SC ','AL ']:
        if n.startswith(pref):
            n = n[len(pref):].strip()
    if n.startswith('AL-'):
        n = n[3:].strip()
    parts = n.split()
    if not parts: return "XXX"
    # si quedó "FC KAISERSLAUTERN", usa la 2da palabra
    if parts[0] in ['FC','CF','SC','SV'] and len(parts) > 1:
        return parts[1][:3].upper()
    if '-' in parts[0]:
        return parts[0].split('-')[-1][:3].upper()
    return parts[0][:3].upper()

def get_base():
    # 1 - si hay parquet nuevo en el repo, usa repo
    for p in [pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
        if (p / "base_partidos.parquet").exists():
            return p
    # 2 - si no, busca csv
    for p in [pathlib.Path("/mnt/data"), pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
        if (p / "europa_actual.csv").exists():
            return p
    return pathlib.Path("/mnt/data")

BASE = get_base()

@st.cache_data(show_spinner=False)
def cargar_todo_lite():
    f_parquet = BASE / "base_partidos.parquet"
    f_pkl = BASE / "base_partidos.pkl"
    if f_parquet.exists():
        df = pd.read_parquet(f_parquet)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    elif f_pkl.exists():
        df = pd.read_pickle(f_pkl)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    else:
        files = ["europa_actual.csv","din1_suec1_26_27.csv","asia_actual_j1j2k1k2csl1.csv","arabia_actual.csv","sudamerica_actual.csv","asia_4ligas_con_israel_2026.csv"]
        dfs=[]
        for fn in files:
            fp = BASE / fn
            if fp.exists() and fp.stat().st_size > 100:
                d = pd.read_csv(fp, on_bad_lines='skip', engine='c')
                if 'Date' in d.columns:
                    d['Date'] = pd.to_datetime(d['Date'], dayfirst=True, errors='coerce')
                dfs.append(d)
        df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if 'Season' in df.columns:
        df['Season'] = df['Season'].astype(str)
    if 'fixture_id' in df.columns and not df.empty:
        df = df.sort_values('Date').drop_duplicates(subset=['fixture_id'], keep='last')

    if 'Jornada' not in df.columns and not df.empty:
        df = df.sort_values(['League','Season','Date']).copy()
        df['Jornada'] = 0
        for (l,s), g in df.groupby(['League','Season'], sort=False):
            g_sorted = g.sort_values('Date')
            n_teams = 20
            if 'HomeTeam' in g_sorted.columns:
                teams = pd.unique(pd.concat([g_sorted['HomeTeam'], g_sorted['AwayTeam']]).dropna())
                n_teams = len(teams)
            ppj = max(n_teams // 2, 1)
            idxs = g_sorted.index.to_numpy()
            df.loc[idxs,'Jornada'] = (np.arange(len(idxs)) // ppj) + 1

    if 'HomeAbbr' not in df.columns and 'HomeTeam' in df.columns:
        df['HomeAbbr'] = df['HomeTeam'].apply(abreviar_equipo)
        df['AwayAbbr'] = df['AwayTeam'].apply(abreviar_equipo)
    return df

@st.cache_data(show_spinner=False)
def cargar_goles_lite():
    f_parquet = BASE / "base_goles.parquet"
    f_pkl = BASE / "base_goles.pkl"
    if f_parquet.exists():
        dg_all = pd.read_parquet(f_parquet)
    elif f_pkl.exists():
        dg_all = pd.read_pickle(f_pkl)
    else:
        files = ["goles_actual.csv","goles_arabia_actual.csv","goles_sudamerica_actual.csv","goles_asia_4ligas_con_israel_2026.csv"]
        dfs=[]
        for fn in files:
            f = BASE / fn
            if f.exists() and f.stat().st_size > 100:
                dfs.append(pd.read_csv(f, dtype=str, on_bad_lines='skip', engine='c'))
        dg_all = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    ev = {}
    if dg_all.empty:
        return ev
    try:
        for fid, g in dg_all.groupby('fixture_id'):
            fid_c = str(fid).split('.')[0]
            lista = []
            for _, r in g.iterrows():
                try:
                    m = int(float(str(r.get('minuto','0')).split('+')[0] or 0))
                    team = normaliza(r.get('equipo',''))
                    if not team: continue
                    gol = str(r.get('goleador','')).strip()
                    asi = str(r.get('asistente','')).strip()
                    if gol.lower() == 'nan': gol = ""
                    if asi.lower() == 'nan': asi = ""
                    abbr = abreviar_equipo(team)
                    tipo = str(r.get('tipo','Normal Goal')).strip()
                    lista.append({"m": m, "team": team, "gol": gol, "asi": asi, "abbr": abbr, "tipo": tipo})
                except: continue
            if lista:
                ev[fid_c] = sorted(lista, key=lambda x: x['m'])
    except: pass
    return ev

df = cargar_todo_lite()
eventos = cargar_goles_lite()
if df.empty:
    st.error("No CSVs encontrados en /mnt/data")
    st.stop()

# --- UI ---
ligas = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []
c1,c2,c3,c4d = st.columns(4)
with c1: liga_sel = st.selectbox("Liga", ["Todas"] + ligas)
df_f = df if liga_sel == "Todas" else df[df['League'] == liga_sel]
# FIX TEMPORADA NUEVA J1/J2 - solo J-League empieza 07/08/2026 (K League NO)
if not df_f.empty and 'Date' in df_f.columns:
    try:
        mask_new = df_f['League'].astype(str).str.contains('J1 League|J2 League|K League', case=False, na=False)
mask_new = df_f['League'].astype(str).str.contains('J1 League|J2 League|K2 League', case=False, na=False)
        if mask_new.any():
            df_f.loc[mask_new, 'Date'] = pd.to_datetime(df_f.loc[mask_new, 'Date'], dayfirst=True, errors='coerce')
            df_f = df_f[~mask_new | (df_f['Date'] >= pd.to_datetime('2026-08-07'))]
            # RECALCULA JORNADA SOLO PARA ESAS LIGAS
            df_f = df_f.sort_values(['League','Date']).copy()
            for l_name in df_f[mask_new]['League'].dropna().unique():
                g_mask = df_f['League'] == l_name
                g_s = df_f[g_mask].sort_values('Date')
                idxs = g_s.index.to_numpy()
                n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                ppj = max(n_teams // 2, 1)
                df_f.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1
    except:
        pass

# --- FILTRO FECHA POR LIGA ---
# saca las fechas que realmente existen en esa liga
if not df_f.empty and 'Date' in df_f.columns:
    # solo fechas validas
    fechas_dt = pd.to_datetime(df_f['Date'], dayfirst=True, errors='coerce').dropna()
    fechas_unicas = sorted(fechas_dt.dt.date.unique(), reverse=True) # mas reciente primero
    fechas_str = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_unicas]
else:
    fechas_unicas = []
    fechas_str = ["Todas"]

with c4d:
    fecha_sel_str = st.selectbox("Desde fecha", fechas_str, key="fecha_desde")

# filtra df_f desde esa fecha en adelante
if fecha_sel_str != "Todas" and fechas_unicas:
    try:
        fecha_sel_date = pd.to_datetime(fecha_sel_str, dayfirst=True).date()
        mask_fecha = pd.to_datetime(df_f['Date'], dayfirst=True, errors='coerce').dt.date >= fecha_sel_date
        df_f = df_f[mask_fecha]
    except:
        pass

# Equipo lista más rápida - DESPUES del filtro de fecha para que solo salgan equipos de ese rango
if not df_f.empty:
    equipos = sorted(pd.unique(pd.concat([df_f['HomeTeam'], df_f['AwayTeam']]).dropna()).tolist())
else:
    equipos = []

with c2: eq1 = st.selectbox("Equipo 1", ["Ninguno"] + equipos)
with c3: eq1_loc = st.selectbox("Eq1 Condición", ["Todos","Local","Visitante"], key="eq1loc")
c4,c5 = st.columns(2)
with c4: eq2 = st.selectbox("Equipo 2", ["Ninguno"] + [e for e in equipos if e!= eq1])
with c5: eq2_loc = st.selectbox("Eq2 Condición", ["Todos","Local","Visitante"], key="eq2loc")

# --- BUSCADOR POR % ---
c6,c7,c8 = st.columns([2,1,1])
with c6:
    filtro_tipo = st.selectbox("Filtro %", ["Ninguno","Ambos SI","Ambos NO","Over 2.5","Under 2.5","Corners Over 9.5","Corners Under 9.5","Amarillas Over 4.5","Amarillas Under 4.5","Tiros Puerta Over 8.5","Tiros Puerta Under 8.5","Tiros Totales Over 24.5","Tiros Totales Under 24.5","Faltas Over 24.5","Faltas Under 24.5"], key="filtro_tipo")
with c7:
    filtro_pct = st.number_input("% mínimo", min_value=0, max_value=100, value=60, step=5, key="filtro_pct")
with c8:
    modo_stats = st.selectbox("Detalle stats", ["OFF","ON"], key="modo_stats")

c9,c10,c_min1,c_min2 = st.columns([1,1,1,1])
with c9:
    modo_jugadores = st.selectbox("JUGADORES", ["OFF","ON"], key="jugadores")
with c_min1:
    min_desde_raw = st.text_input("MIN DESDE", key="min_desde", placeholder="-")
with c_min2:
    min_hasta_raw = st.text_input("MIN HASTA", key="min_hasta", placeholder="-")

def parse_min(v):
    try:
        if v is None or str(v).strip() in ["", "-", "–", "—"]:
            return None
        return int(str(v).strip().replace("'", ""))
    except:
        return None

MIN_DESDE = parse_min(min_desde_raw)
MIN_HASTA = parse_min(min_hasta_raw)

# --- FILTRO VECTORIZADO ---
def filtrar_equipo(dframe, equipo, condicion):
    if equipo == "Ninguno" or dframe.empty:
        return dframe.iloc[0:0] if equipo!= "Ninguno" else dframe
    if condicion == "Local": return dframe[dframe['HomeTeam'] == equipo]
    if condicion == "Visitante": return dframe[dframe['AwayTeam'] == equipo]
    return dframe[(dframe['HomeTeam'] == equipo) | (dframe['AwayTeam'] == equipo)]

if eq1!= "Ninguno" and eq2!= "Ninguno":
    df_eq1 = filtrar_equipo(df_f, eq1, eq1_loc)
    df_eq2 = filtrar_equipo(df_f, eq2, eq2_loc)
    modo_doble = True
elif eq1!= "Ninguno":
    df_mostrar = filtrar_equipo(df_f, eq1, eq1_loc)
    modo_doble = False
elif eq2!= "Ninguno":
    df_mostrar = filtrar_equipo(df_f, eq2, eq2_loc)
    modo_doble = False
else:
    df_mostrar = df_f
    modo_doble = False

def fmt_rapido(r, eq_refs_norm, current_eq_norm, current_eq_orig):
    j = int(r.get('Jornada',0) or 0)
    h = str(r.get('HomeTeam','')); a = str(r.get('AwayTeam',''))
    hab = h.strip()
    aab = a.strip()
    try: hg = int(float(r.get('FTHG',0) or 0)); ag = int(float(r.get('FTAG',0) or 0))
    except: hg = 0; ag = 0
    try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
    except: hthg = 0; htag = 0

    col = "#0A2342"
    if eq_refs_norm:
        hn = normaliza(h); an = normaliza(a)
        for ern in eq_refs_norm:
            if ern == hn and hg > ag: col = "#0f8105"
            if ern == an and ag > hg: col = "#0f8105"
            if ern == hn and hg < ag: col = "#f31818"
            if ern == an and ag < hg: col = "#f31818"
            if ern == hn and hg == ag: col = "#FFA500"
            if ern == an and hg == ag: col = "#FFA500"
    else:
        if hg == ag:
            col = "#FFA500"

    mins_1t = []
    mins_2t = []
    marc_h, marc_a = 0, 0
    try:
        fid = str(r.get('fixture_id','')).split('.')[0]
        home_abbr_fix = str(r.get('HomeAbbr','')).strip().upper()
        for ev in eventos.get(fid, []):
            m = ev['m']; team = ev['team']
            gol = ev.get('gol',''); asi = ev.get('asi','')
            h_norm = normaliza(r.get('HomeTeam','')); a_norm = normaliza(r.get('AwayTeam',''))
            if team == h_norm:
                abbr = r.get('HomeAbbr') or abreviar_equipo(r.get('HomeTeam',''))
            elif team == a_norm:
                abbr = r.get('AwayAbbr') or abreviar_equipo(r.get('AwayTeam',''))
            else:
                abbr = ev.get('abbr') or abreviar_equipo(team)
            if not abbr or abbr == "XXX":
                abbr = "A."
            tipo_ev = ev.get('tipo','Normal Goal')
            es_fallado = 'Missed' in tipo_ev
            es_propia = 'Own Goal' in tipo_ev

            if not es_fallado:
                if es_propia:
                    # gol en propia: cuenta para el rival
                    if team == h_norm:
                        marc_a += 1
                    else:
                        marc_h += 1
                else:
                    if team == h_norm:
                        marc_h += 1
                    else:
                        marc_a += 1
            alterador = f" {marc_h}-{marc_a}"
            if es_fallado:
                alterador = f" {marc_h}-{marc_a} [PEN FALLADO]"

            # --- NO filtrar goles aquí, el filtro de partido se hace fuera ---

            es_mio = any(ern in team or team in ern for ern in eq_refs_norm) if eq_refs_norm else False
            mj = globals().get('modo_jugadores', 'OFF')
            def abrev(n):
                s = str(n).strip()
                if not s or s.lower() == 'nan': return ""
                p = s.split()
                if len(p) == 1: return p[0]
                return f"{p[0][0]}. {p[-1]}"
            gol_raw = str(gol).strip()
            asi_raw = str(asi).strip()
            if gol_raw.lower() == 'nan': gol_raw = ""
            if asi_raw.lower() == 'nan': asi_raw = ""
            gol_ab = abrev(gol_raw).upper()
            asi_ab = abrev(asi_raw).lower()

            # si no hay goleador, no intentes pintar "" ()
            if mj == "ON" and gol_raw and gol_ab:
                txt_extra = f' "{gol_ab}" ({asi_ab})({abbr}){alterador}' if asi_ab else f' "{gol_ab}" ({abbr}){alterador}'
            else:
                txt_extra = f'({abbr}){alterador}'

            if not txt_extra.strip():
                txt_extra = f'({abbr}){alterador}'

            is_local = (team == h_norm)
            es_mio = any(ern in team or team in ern for ern in eq_refs_norm) if eq_refs_norm else False
            en_rango = (MIN_DESDE is None or m >= MIN_DESDE) and (MIN_HASTA is None or m <= MIN_HASTA) and (MIN_DESDE is not None or MIN_HASTA is not None)
            # filtro minuto = rotulado gris + negrita, equipo seleccionado = subrayado, color siempre negro
            color_gol = "#000"
            deco = "text-decoration:underline; text-underline-offset:3px; text-decoration-thickness:1.5px;" if es_mio else ""
            bold = "font-weight:900;" if en_rango else ""
            gris = "background:#D3D3D3; border-radius:3px; padding:1px 4px;" if en_rango else ""
            extra_style = f"{deco} {bold} {gris}"
            if mj == "ON" and gol_ab:
                extra_jug = f' "{gol_ab}"' + (f' ({asi_ab})' if asi_ab else '')
            else:
                extra_jug = ""
            min_txt = f"<span style='font-size:12px; {bold} {deco} {gris}'>{m}'</span>"
            if is_local:
                html_gol = f"<div style='text-align:left; color:{color_gol}; {extra_style} margin:0; padding:0; line-height:1.0; font-size:11px'>{min_txt} {alterador.strip()}{extra_jug}</div>"
            else:
                html_gol = f"<div style='text-align:right; color:{color_gol}; {extra_style} margin:0; padding:0; line-height:1.0; font-size:11px'>{min_txt} {alterador.strip()}{extra_jug}</div>"
            if m <= 45:
                mins_1t.append(html_gol)
            else:
                mins_2t.append(html_gol)
    except: pass

    if not mins_1t and not mins_2t:
        ms = re.findall(r"(\d+)'", str(r.get('Goles_Todo_HTML','') or ''))
        for x in ms:
            try:
                m_int = int(x)
                if m_int <= 45:
                    mins_1t.append(f"<span style='color:#000'>{x}'</span>")
                else:
                    mins_2t.append(f"<span style='color:#000'>{x}'</span>")
            except:
                mins_1t.append(f"<span style='color:#000'>{x}'</span>")

    # goles ultra comprimidos sin hueco
    if mins_1t and mins_2t:
        txt_mins = "<div style='color:#333;font-weight:900;font-size:9px;line-height:1.0;margin:0;padding:0'>--- 1T ---</div>" + "".join(mins_1t) + "<div style='color:#333;font-weight:900;font-size:9px;line-height:1.0;margin:0;padding:0'>--- 2T ---</div>" + "".join(mins_2t)
    elif mins_1t:
        txt_mins = "<div style='color:#333;font-weight:900;font-size:9px;line-height:1.0;margin:0;padding:0'>--- 1T ---</div>" + "".join(mins_1t)
    elif mins_2t:
        txt_mins = "<div style='color:#333;font-weight:900;font-size:9px;line-height:1.0;margin:0;padding:0'>--- 2T ---</div>" + "".join(mins_2t)
    else:
        txt_mins = "-"

    # Si hay filtro MIN y no hay goles en ese rango, no renderizar
    try:
        md_f = globals().get('MIN_DESDE', None)
        mh_f = globals().get('MIN_HASTA', None)
        if (md_f is not None or mh_f is not None) and txt_mins == "-":
            return ""
    except:
        pass

    # FIX L/V - ahora sí usa el equipo del bloque
    loc_tag = ""
    if current_eq_orig:
        if r.get('HomeTeam','') == current_eq_orig: loc_tag = " (L)"
        elif r.get('AwayTeam','') == current_eq_orig: loc_tag = " (V)"

    # extra stats - ON muestra todo diferenciado con color / OFF normal
    extra = ""
    try:
        def _iv(v):
            try:
                if v is None or pd.isna(v): return None
                return int(float(v))
            except: return None

        if 'modo_stats' in locals() or 'modo_stats' in globals():
            ms = modo_stats
        else:
            ms = "OFF"

        # --- ROJAS AUTO SIEMPRE ---
        hr_auto = _iv(r.get('HR'))
        ar_auto = _iv(r.get('AR'))
        if hr_auto is not None and hr_auto > 0:
            extra += f" <span style='color:#FF0000;font-weight:900'>[HR{hr_auto}]</span>"
        if ar_auto is not None and ar_auto > 0:
            extra += f" <span style='color:#FF4500;font-weight:900'>[AR{ar_auto}]</span>"

        if ms == "ON":
            hy = _iv(r.get('HY')); ay = _iv(r.get('AY'))
            hr = _iv(r.get('HR')); ar = _iv(r.get('AR'))
            hc = _iv(r.get('HC')); ac = _iv(r.get('AC'))
            hst = _iv(r.get('HST')); ast = _iv(r.get('AST'))
            hs = _iv(r.get('HS')); _as = _iv(r.get('AS'))
            hf = _iv(r.get('HF')); af = _iv(r.get('AF'))

            hp = _iv(r.get('HomePasses')); ap = _iv(r.get('AwayPasses'))
            hpos = _iv(r.get('HomePos')); apos = _iv(r.get('AwayPos'))

            if hy is not None or ay is not None:
                extra += f" <span style='color:#b8860b'>[HY{hy if hy is not None else '-'}]</span> <span style='color:#DAA520'>[AY{ay if ay is not None else '-'}]</span>"
            if hr is not None or ar is not None:
                extra += f" <span style='color:#FF0000'>[HR{hr if hr is not None else '-'}]</span> <span style='color:#FF4500'>[AR{ar if ar is not None else '-'}]</span>"
            if hc is not None or ac is not None:
                extra += f" <span style='color:#1E90FF'>[HC{hc if hc is not None else '-'}]</span> <span style='color:#4682B4'>[AC{ac if ac is not None else '-'}]</span>"
            if hst is not None or ast is not None:
                extra += f" <span style='color:#0066cc'>[HST{hst if hst is not None else '-'}]</span> <span style='color:#0099FF'>[AST{ast if ast is not None else '-'}]</span>"
            if hs is not None or _as is not None:
                extra += f" <span style='color:#004080'>[HS{hs if hs is not None else '-'}]</span> <span style='color:#5A8AC0'>[AS{_as if _as is not None else '-'}]</span>"
            if hf is not None or af is not None:
                extra += f" <span style='color:#666'>[HF{hf if hf is not None else '-'}]</span> <span style='color:#999'>[AF{af if af is not None else '-'}]</span>"
            if hp is not None or ap is not None:
                extra += f" <span style='color:#2E8B57'>[HP{hp if hp is not None else '-'}]</span> <span style='color:#3CB371'>[AP{ap if ap is not None else '-'}]</span>"
            if hpos is not None or apos is not None:
                extra += f" <span style='color:#8B4513'>[POS{hpos if hpos is not None else '-'}-{apos if apos is not None else '-'}]</span>"
        else:
            # OFF - comportamiento original tuyo
            if "Corners" in filtro_tipo:
                hc = r.get('HC'); ac = r.get('AC')
                if hc is not None and ac is not None and pd.notna(hc) and pd.notna(ac):
                    tot_c = int(float(hc)+float(ac))
                    extra += f" <span style='color:#555'>[{tot_c}c]</span>"
            if "Amarillas" in filtro_tipo:
                hy = r.get('HY'); ay = r.get('AY')
                if hy is not None and ay is not None and pd.notna(hy) and pd.notna(ay):
                    tot_y = int(float(hy)+float(ay))
                    extra += f" <span style='color:#b8860b'>[{tot_y}y]</span>"
            if "Tiros Puerta" in filtro_tipo:
                hst = r.get('HST'); ast = r.get('AST')
                if hst is not None and ast is not None and pd.notna(hst) and pd.notna(ast):
                    tot_sot = int(float(hst)+float(ast))
                    extra += f" <span style='color:#0066cc'>[{tot_sot}tp]</span>"
            if "Tiros Totales" in filtro_tipo:
                hs = r.get('HS'); _as = r.get('AS')
                if hs is not None and _as is not None and pd.notna(hs) and pd.notna(_as):
                    tot_s = int(float(hs)+float(_as))
                    extra += f" <span style='color:#0066cc'>[{tot_s}t]</span>"
            if "Faltas" in filtro_tipo:
                hf = r.get('HF'); af = r.get('AF')
                if hf is not None and af is not None and pd.notna(hf) and pd.notna(af):
                    tot_f = int(float(hf)+float(af))
                    extra += f" <span style='color:#888'>[{tot_f}f]</span>"
    except: pass

    # G/E/P del equipo seleccionado: 1P / FINAL
    def res_eq(gf, gc):
        if gf > gc: return "G"
        if gf == gc: return "E"
        return "P"

    es_local = current_eq_orig and r.get('HomeTeam','') == current_eq_orig
    es_visit = current_eq_orig and r.get('AwayTeam','') == current_eq_orig

    if es_local:
        r1 = res_eq(hthg, htag)
        rF = res_eq(hg, ag)
        btts_txt = f"{r1}/{rF}"
    elif es_visit:
        r1 = res_eq(htag, hthg)
        rF = res_eq(ag, hg)
        btts_txt = f"{r1}/{rF}"
    else:
        btts = hg > 0 and ag > 0
        btts_txt = "G/G" if btts else "NG/NG"

    hab_u = f"<u style='text-decoration-thickness:2px;text-underline-offset:3px'>{hab}</u>" if eq_refs_norm and normaliza(h) in eq_refs_norm else hab
    aab_u = f"<u style='text-decoration-thickness:2px;text-underline-offset:3px'>{aab}</u>" if eq_refs_norm and normaliza(a) in eq_refs_norm else aab
    return f"<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #333;line-height:1.4;word-wrap:break-word;overflow-wrap:anywhere;white-space:normal;text-align:center;max-width:380px;margin:0 auto'><span style='color:{col};font-weight:900'>|J{j}| {btts_txt}{loc_tag}</span>{extra}<br><span style='color:{col};font-weight:900'>{hab_u} [ {hg}-{ag} ] {aab_u}</span><br><span style='color:#555;font-weight:700'>{hab} [ {hthg}-{htag} ] {aab}</span><br><div style='color:#000;white-space:normal;word-break:break-word;line-height:1.1'>{txt_mins}</div></div>"

eq_refs_orig = [e for e in [eq1, eq2] if e!= "Ninguno"]
eq_refs_norm = [normaliza(e) for e in eq_refs_orig]

html = ""

# MODO FILTRO POR % - PRIORITARIO
if filtro_tipo!= "Ninguno":
    def get_val(r, keys):
        for k in keys:
            if k in r and pd.notna(r.get(k)):
                try: return float(r.get(k))
                except: pass
        return None
    def cumple(r):
        try: hg = int(float(r.get('FTHG',0) or 0)); ag = int(float(r.get('FTAG',0) or 0))
        except: hg=0; ag=0
        hc = get_val(r, ['HC']) or 0; ac = get_val(r, ['AC']) or 0
        tot_c = get_val(r, ['Corners','TotalCorners'])
        if tot_c is None: tot_c = hc + ac
        hy = get_val(r, ['HY']) or 0; ay = get_val(r, ['AY']) or 0
        tot_y = get_val(r, ['YellowCards'])
        if tot_y is None: tot_y = hy + ay
        hst = get_val(r, ['HST']) or 0; ast = get_val(r, ['AST']) or 0
        tot_sot = get_val(r, ['SOT'])
        if tot_sot is None: tot_sot = hst + ast
        hs = get_val(r, ['HS']) or 0; _as = get_val(r, ['AS']) or 0
        tot_s = get_val(r, ['Shots'])
        if tot_s is None: tot_s = hs + _as
        hf = get_val(r, ['HF']) or 0; af = get_val(r, ['AF']) or 0
        tot_f = get_val(r, ['Fouls'])
        if tot_f is None: tot_f = hf + af
        if filtro_tipo == "Ambos SI": return hg>0 and ag>0
        if filtro_tipo == "Ambos NO": return not (hg>0 and ag>0)
        if filtro_tipo == "Over 2.5": return (hg+ag) > 2.5
        if filtro_tipo == "Under 2.5": return (hg+ag) < 2.5
        if filtro_tipo == "Corners Over 9.5": return tot_c > 9.5
        if filtro_tipo == "Corners Under 9.5": return tot_c < 9.5 and tot_c>0
        if filtro_tipo == "Amarillas Over 4.5": return tot_y > 4.5
        if filtro_tipo == "Amarillas Under 4.5": return tot_y <= 4.5
        if filtro_tipo == "Tiros Puerta Over 8.5": return tot_sot > 8.5
        if filtro_tipo == "Tiros Puerta Under 8.5": return tot_sot < 8.5 and tot_sot>0
        if filtro_tipo == "Tiros Totales Over 24.5": return tot_s > 24.5
        if filtro_tipo == "Tiros Totales Under 24.5": return tot_s < 24.5 and tot_s>0
        if filtro_tipo == "Faltas Over 24.5": return tot_f > 24.5
        if filtro_tipo == "Faltas Under 24.5": return tot_f < 24.5 and tot_f>0
        return False

    columnas = set(df_f.columns)
    hay_datos = True
    if "Corners" in filtro_tipo and not ({"HC","AC","Corners"}.intersection(columnas)):
        st.warning(f"⚠️ {liga_sel} no tiene corners"); hay_datos=False
    if "Amarillas" in filtro_tipo and not ({"HY","AY"}.intersection(columnas)):
        st.warning(f"⚠️ {liga_sel} no tiene amarillas"); hay_datos=False

    if hay_datos:
        equipos_con_loc = []
        if eq1!= "Ninguno":
            equipos_con_loc.append((eq1, eq1_loc))
        if eq2!= "Ninguno":
            equipos_con_loc.append((eq2, eq2_loc))

        if equipos_con_loc:
            equipos_a_chequear = equipos_con_loc
        else:
            base_eq = equipos if liga_sel!="Todas" else sorted(pd.unique(pd.concat([df['HomeTeam'], df['AwayTeam']]).dropna()).tolist())
            equipos_a_chequear = [(t, "Todos") for t in base_eq]

        calificados = []
        for team, loc_cond in equipos_a_chequear:
            d_team = filtrar_equipo(df_f, team, loc_cond)
            if len(d_team) < 1:
                continue
            # para filtros de stats, excluye partidos sin dato para no penalizar %
            if "Corners" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HC'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AC'], errors='coerce').fillna(0)) > 0]
            elif "Amarillas" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HY'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AY'], errors='coerce').fillna(0)) > 0]
            elif "Tiros Puerta" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HST'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AST'], errors='coerce').fillna(0)) > 0]
            elif "Tiros Totales" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HS'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AS'], errors='coerce').fillna(0)) > 0]
            elif "Faltas" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HF'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AF'], errors='coerce').fillna(0)) > 0]
            else:
                d_team_valid = d_team
            if len(d_team_valid) < 1:
                continue
            c_ok = 0
            for _, rr in d_team_valid.iterrows():
                if cumple(rr.to_dict()):
                    c_ok+=1
            pct = (c_ok / len(d_team_valid) * 100) if len(d_team_valid)>0 else 0
            if pct >= filtro_pct:
                calificados.append((team, loc_cond, pct, len(d_team_valid), c_ok))

        calificados = sorted(calificados, key=lambda x: x[2], reverse=True)

    if not calificados:
        st.info(f"Ningún equipo cumple {filtro_tipo} >= {filtro_pct}%")
    else:
        for team, loc_cond, pct, total, ok in calificados:
            d_team_full = filtrar_equipo(df_f, team, loc_cond)
            d_team_cumple = d_team_full[d_team_full.apply(lambda rr: cumple(rr.to_dict()), axis=1)]
            d_team_cumple = d_team_cumple.sort_values(['Jornada','Date'], ascending=[False, False]).head(20)
            try:
                liga_team = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)]['League'].mode().iloc[0]
            except:
                liga_team = liga_sel
            color_pct = "#0f8105" if pct>=70 else "#0A2342"
            html += f"<div style='font-family:monospace;font-weight:900;background:{color_pct};color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{team} {loc_cond} - {liga_team} | {filtro_tipo} {pct:.0f}% ({ok}/{total})</div>"
            for _, r in d_team_cumple.iterrows():
                html += fmt_rapido(r.to_dict(), [normaliza(team)], normaliza(team), team)
        st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)

else:
    # MODO NORMAL (tu logica original intacta)
    if modo_doble:
        for eq_orig, df_eq in [(eq1, df_eq1), (eq2, df_eq2)]:
            cond = eq1_loc if eq_orig == eq1 else eq2_loc
            # FIX MIN en modo doble
            try:
                if MIN_DESDE is not None or MIN_HASTA is not None:
                    fids_v = set()
                    for fid_c, evs_c in eventos.items():
                        for ev_c in evs_c:
                            mm_c = ev_c.get('m', -1)
                            if MIN_DESDE is not None and mm_c < MIN_DESDE: continue
                            if MIN_HASTA is not None and mm_c > MIN_HASTA: continue
                            fids_v.add(str(fid_c))
                            break
                    df_eq = df_eq[df_eq['fixture_id'].astype(str).str.split('.').str[0].isin(fids_v)]
            except:
                pass
            df_eq = df_eq.sort_values(['Jornada','Date'], ascending=[False, False]).head(30) if not df_eq.empty else df_eq
            html += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:8px 0 2px 0;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:4px'>{eq_orig} {cond} | {len(df_eq)}</div>"
            eq_norm_single = normaliza(eq_orig)
            for _, r in df_eq.iterrows():
                html += fmt_rapido(r.to_dict(), [eq_norm_single], eq_norm_single, eq_orig)
    else:
        # Pre-filtro por MIN para que el contador sea real
        df_filtrada_min = df_mostrar.copy()
        try:
            if MIN_DESDE is not None or MIN_HASTA is not None:
                fids_validos = set()
                for fid_check, evs_check in eventos.items():
                    for ev_c in evs_check:
                        if 'Missed' in ev_c.get('tipo',''): continue
                        mm_c = ev_c.get('m', -1)
                        if MIN_DESDE is not None and mm_c < MIN_DESDE: continue
                        if MIN_HASTA is not None and mm_c > MIN_HASTA: continue
                        fids_validos.add(str(fid_check))
                        break
                df_filtrada_min = df_mostrar[df_mostrar['fixture_id'].astype(str).str.split('.').str[0].isin(fids_validos)]
        except:
            pass

        df_mostrar = df_filtrada_min.sort_values(['Jornada','Date'], ascending=[False, False]) if not df_filtrada_min.empty else df_filtrada_min
        if eq_refs_orig:
            cond_txt = eq1_loc if eq1!= "Ninguno" else eq2_loc
            html += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:6px 0 2px 0;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:4px'>{eq_refs_orig[0]} {cond_txt} | {len(df_mostrar)}</div>"
        for _, r in df_mostrar.iterrows():
            # --- FILTRO POR MINUTO A NIVEL PARTIDO ---
            try:
                if MIN_DESDE is not None or MIN_HASTA is not None:
                    fid_f = str(r.get('fixture_id','')).split('.')[0]
                    evs = eventos.get(fid_f, [])
                    tiene = False
                    for ev in evs:
                        mm = ev.get('m', -1)
                        if MIN_DESDE is not None and mm < MIN_DESDE: continue
                        if MIN_HASTA is not None and mm > MIN_HASTA: continue
                        tiene = True
                        break
                    if not tiene:
                        continue
            except:
                pass

            curr_norm = eq_refs_norm[0] if eq_refs_norm else ""
            curr_orig = eq_refs_orig[0] if eq_refs_orig else ""
            html += fmt_rapido(r.to_dict(), eq_refs_norm, curr_norm, curr_orig)

    if (modo_doble and (not df_eq1.empty or not df_eq2.empty)) or (not modo_doble and not df_mostrar.empty):
        st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
    else:
        st.info("Selecciona equipo")

st.caption(f"Base: {BASE} | Registros: {len(df)} | Goles indexados: {len(eventos)} | Filtro: {filtro_tipo} {filtro_pct}%")
