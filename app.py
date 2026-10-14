import streamlit as st
import pandas as pd
import pathlib
import re
import unicodedata
import numpy as np
import matplotlib.pyplot as plt
import io, base64

st.set_page_config(page_title="Lite Rapido + Local", layout="wide")
# --- FIX SCROLL MOVIL - QUITA REINICIO AL TOCAR BORDE ARRIBA + FIX SCROLL EXPANDER PREDICCION ---
st.markdown("""
<style>
html, body {
    overscroll-behavior-y: contain!important;
    touch-action: pan-y;
    -webkit-overflow-scrolling: touch;
}
[data-testid="stAppViewContainer"] {
    overscroll-behavior-y: contain!important;
}
[data-testid="stHeader"] {
    overscroll-behavior: none!important;
}
div[data-testid="stExpanderDetails"] {
    max-height: none!important;
    overflow-y: visible!important;
    overflow: visible!important;
    -webkit-overflow-scrolling: auto!important;
    touch-action: auto!important;
    overscroll-behavior: auto!important;
    overscroll-behavior-y: auto!important;
}
iframe {
    touch-action: auto!important;
    overscroll-behavior: auto!important;
}
#btn-top-float {
    position: fixed!important;
    bottom: 20px!important;
    right: 20px!important;
    z-index: 999999!important;
    background: #0A2342!important;
    color: white!important;
    border: none!important;
    border-radius: 50%!important;
    width: 56px!important;
    height: 56px!important;
    font-size: 26px!important;
    font-weight: 900!important;
    cursor: pointer!important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4)!important;
    display: none;
}
#btn-top-float:hover { background: #0f8105!important; }
#top-ancla { position: absolute; top: 0; }
</style>
<div id="top-ancla"></div>
<button id="btn-top-float" onclick="window.scrollTo({top:0, behavior:'smooth'})">↑</button>
<script>
// bloquea pull-to-refresh solo en el body, no dentro de expanders/iframes
let startY = 0;
let isInsideExpander = false;
document.addEventListener('touchstart', e => {
    startY = e.touches[0].clientY;
    isInsideExpander =!!e.target.closest('[data-testid="stExpanderDetails"], iframe');
}, {passive: true});
document.addEventListener('touchmove', e => {
    if (isInsideExpander) return;
    const currentY = e.touches[0].clientY;
    const diff = currentY - startY;
    if (window.scrollY <= 0 && diff > 50) {
        e.preventDefault();
    }
}, {passive: false});
window.addEventListener('scroll', function() {
    const btn = document.getElementById('btn-top-float');
    if (btn) btn.style.display = window.scrollY > 400? 'block' : 'none';
});
</script>
""", unsafe_allow_html=True)
# --- UTILS ---
MAPA_NORMALIZACION = {
    "Pusamania Borneo": "PUSAMANIA BORNEO",
    "Dewa United": "DEWA UNITED",
    "Persebaya Surabaya": "PERSEBAYA SURABAYA",
    "Persita": "PERSITA",
    "PSS Sleman": "PSS SLEMAN",
    "Bali United": "BALI UNITED",
    "Persija": "PERSIJA",
    "PSIM Yogyakarta": "PSIM YOGYAKARTA",
    "PSM Makassar": "PSM MAKASSAR",
    "Garudayaksa": "GARUDAYAKSA",
    "Persepam Madura Utd": "PERSEPAM MADURA UTD",
    "Arema FC": "AREMA FC",
    "Persijap": "PERSIJAP",
    "Bhayangkara FC": "BHAYANGKARA FC",
    "Persik Kediri": "PERSIK KEDIRI",
    "Persib Bandung": "PERSIB BANDUNG",
    "KUCHING FA": "Kuching FA",
    "JOHOR DARUL TAKZIM FC": "Johor Darul Takzim FC",
    "KELANTAN RED WARRIOR FC": "Kelantan Red Warrior FC",
    "KUALA LUMPUR FA": "Kuala Lumpur FA",
    "IMIGRESEN": "Imigresen",
    "PENANG": "Penang",
    "SELANGOR": "Selangor",
    "SABAH FA": "Sabah FA",
    "TERENGGANU": "Terengganu",
    "MELAKA": "Melaka",
    "DPMM FC BRUNEI": "DPMM FC Brunei",
    "NEGERI SEMBILAN": "Negeri Sembilan",
    "CASTELLON": "CASTELLÓN",
    "SPVGG GREUTHER FURTH": "SPVGG GREUTHER FÜRTH",
    "1. FC NURNBERG": "1. FC NÜRNBERG",
    "BAYERN MUNCHEN": "BAYERN MÜNCHEN",
    "RAAL LA LOUVIERE": "RAAL LA LOUVIÈRE",
    "VFL OSNABRUCK": "VFL OSNABRÜCK",
    "MUGLASPOR": "MUĞLASPOR",
    "Real Madrid II": "REAL MADRID II",
    "Teruel": "TERUEL",
}
_MAPA_UPPER = {k.upper(): v for k, v in MAPA_NORMALIZACION.items()}

def normaliza(s):
    if pd.isna(s): return ""
    raw = str(s).strip()
    if raw in MAPA_NORMALIZACION:
        return MAPA_NORMALIZACION[raw]
    up = raw.upper()
    if up in _MAPA_UPPER:
        return _MAPA_UPPER[up]
    return up

def normaliza_fuzzy(s):
    n = normaliza(s)
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'^\d+\.?\s*', '', n)
    for pref in ['FC ','CF ','SC ','SV ','REAL ','CLUB ','DEPORTIVO ','CLUB ATLETICO ','AL-','AL ']:
        if n.startswith(pref):
            n = n[len(pref):].strip()
    return n.strip()

@st.cache_data(show_spinner=False, max_entries=500)
def plot_momentum_base64_cached(fixture_id, titulo, n_points):
    # usa globals para no pasar dataframes gigantes al cache
    mom_data = momentum_by_id.get(fixture_id, [])
    if not mom_data:
        # busca por teams key que es "HOME___AWAY"
        for k,v in momentum_by_teams.items():
            if fixture_id in k:
                mom_data = v
                break
    if not mom_data:
        return ""
    try:
        mins = [int(m.get('minute',0)) for m in mom_data][::2] # cada 2 min = mitad de barras = 2x rapido
        vals = [float(m.get('momentumValue',0)) for m in mom_data][::2]
        fig, ax = plt.subplots(figsize=(5,1.6), dpi=100) # mas pequeño = 3x rapido
        colors = ['#e74c3c' if v>=0 else '#3498db' for v in vals]
        ax.bar(mins, vals, color=colors, width=1.2, alpha=0.9)
        ax.axhline(0, color='black', linewidth=0.6)
        ax.set_xlim(-1, 100)
        ax.set_title(titulo, fontsize=8, fontweight='bold')
        ax.tick_params(labelsize=5)
        ax.set_xticks([])
        fig.tight_layout(pad=0.3)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        return f"<img src='data:image/png;base64,{b64}' style='width:100%;max-width:380px;margin:4px 0;border:1px solid #ddd'/>"
    except:
        return ""

def plot_momentum_base64(mom_data, goles_list, titulo=""):
    # wrapper compat para que no pete nada de lo que ya tienes
    if not mom_data:
        return ""
    try:
        fid = str(goles_list[0].get('fixture_id','')) if goles_list else titulo
        return plot_momentum_base64_cached(titulo, titulo, len(mom_data))
    except:
        return plot_momentum_base64_cached(titulo, titulo, len(mom_data))

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

@st.cache_data(show_spinner=False)
def cargar_momentum_lite():
    f_parquet = BASE / "base_momentum.parquet"
    f_pkl = BASE / "base_momentum.pkl"
    dm = None
    if f_parquet.exists():
        dm = pd.read_parquet(f_parquet)
    elif f_pkl.exists():
        dm = pd.read_pickle(f_pkl)
    else:
        return {}, {}
    mom_by_id = {}
    mom_by_teams = {}
    try:
        for fid, g in dm.groupby('fixture_id'):
            fid_c = str(fid).split('.')[0]
            g_sorted = g.sort_values('minute')
            recs = g_sorted.to_dict('records')
            mom_by_id[fid_c] = recs
            if not g_sorted.empty:
                h_raw = str(g_sorted.iloc[0].get('home',''))
                a_raw = str(g_sorted.iloc[0].get('away',''))
                hn = normaliza_fuzzy(h_raw)
                an = normaliza_fuzzy(a_raw)
                if hn and an:
                    mom_by_teams[(hn, an)] = recs
                    mom_by_teams[(an, hn)] = recs
    except:
        pass
    return mom_by_id, mom_by_teams

df = cargar_todo_lite()
eventos = cargar_goles_lite()
momentum_by_id, momentum_by_teams = cargar_momentum_lite()
if df.empty:
    st.error("No CSVs encontrados en /mnt/data")
    st.stop()

# --- UI ---
if 'show_partidos' not in st.session_state:
    st.session_state.show_partidos = False

filtros = st.expander("FILTROS", expanded=True)
with filtros:
    if st.button("Ocultar partidos" if st.session_state.show_partidos else "Mostrar partidos", key="toggle_partidos", use_container_width=True):
        st.session_state.show_partidos = not st.session_state.show_partidos
        st.rerun()

ligas = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []
c1,c2,c3,c4d = filtros.columns(4)
with c1: liga_sel = st.selectbox("Liga", ["Todas"] + ligas)
df_f = df if liga_sel == "Todas" else df[df['League'] == liga_sel]
# FIX TEMPORADA NUEVA J1/J2 - solo J-League empieza 07/08/2026 (K League NO)
if not df_f.empty and 'Date' in df_f.columns:
    try:
        mask_new = df_f['League'].astype(str).str.contains('J1 League|J2 League', case=False, na=False)
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

# Equipo lista más rápida - FIX DEDUP POR NORMALIZA
if not df_f.empty:
    seen = {}
    for t in pd.concat([df_f['HomeTeam'], df_f['AwayTeam']]).dropna().astype(str):
        n = normaliza(t)
        if n not in seen:
            seen[n] = t.upper() # fuerza UPPER -> AREMA FC = Arema FC
    equipos = sorted(seen.values())
else:
    equipos = []

with c2: eq1 = st.selectbox("Equipo 1", ["Ninguno"] + equipos)
with c3: eq1_loc = st.selectbox("Eq1 Condición", ["Todos","Local","Visitante"], key="eq1loc")
c4,c5 = filtros.columns(2)
with c4: eq2 = st.selectbox("Equipo 2", ["Ninguno"] + [e for e in equipos if normaliza(e)!= normaliza(eq1)])
with c5: eq2_loc = st.selectbox("Eq2 Condición", ["Todos","Local","Visitante"], key="eq2loc")

# --- BUSCADOR POR % ---
c6,c7,c8 = filtros.columns([2,1,1])
with c6:
    filtro_tipo = st.selectbox("Filtro %", ["Ninguno","Ambos SI","Ambos NO","Over 2.5","Under 2.5","Corners Over 9.5","Corners Under 9.5","Amarillas Over 4.5","Amarillas Under 4.5","Tiros Puerta Over 8.5","Tiros Puerta Under 8.5","Tiros Totales Over 24.5","Tiros Totales Under 24.5","Faltas Over 24.5","Faltas Under 24.5","Gana","Pierde","Empata","GanaEmpata","GanaPierde","PierdeEmpata"], key="filtro_tipo")
with c7:
    filtro_pct = st.number_input("% mínimo", min_value=0, max_value=100, value=60, step=5, key="filtro_pct")
with c8:
    modo_stats = st.selectbox("Detalle stats", ["ON","OFF"], key="modo_stats")

c9,c_min1,c_min2 = filtros.columns([1,1,1])
with c9:
    modo_jugadores = st.selectbox("JUGADORES", ["ON","OFF"], key="jugadores")
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

# --- FILTRO VECTORIZADO - FIX POR NORMALIZA ---
def filtrar_equipo(dframe, equipo, condicion):
    if equipo == "Ninguno" or dframe.empty:
        return dframe.iloc[0:0] if equipo!= "Ninguno" else dframe
    n_eq = normaliza(equipo)
    # usa columna pre-calculada si existe
    if 'HomeNorm' in dframe.columns:
        if condicion == "Local":
            return dframe[dframe['HomeNorm']==n_eq]
        if condicion == "Visitante":
            return dframe[dframe['AwayNorm']==n_eq]
        return dframe[(dframe['HomeNorm']==n_eq) | (dframe['AwayNorm']==n_eq)]
    # fallback por si es un df sin HomeNorm
    if condicion == "Local":
        return dframe[dframe['HomeTeam'].apply(lambda x: normaliza(x)==n_eq)]
    if condicion == "Visitante":
        return dframe[dframe['AwayTeam'].apply(lambda x: normaliza(x)==n_eq)]
    return dframe[(dframe['HomeTeam'].apply(lambda x: normaliza(x)==n_eq)) | (dframe['AwayTeam'].apply(lambda x: normaliza(x)==n_eq))]

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
            if ern == hn and hg == ag: col = "#8B4513"
            if ern == an and hg == ag: col = "#8B4513"
    else:
        if hg == ag:
            col = "#8B4513"

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
            filtro_activo = (MIN_DESDE is not None or MIN_HASTA is not None)
            en_rango = (MIN_DESDE is None or m >= MIN_DESDE) and (MIN_HASTA is None or m <= MIN_HASTA)
            # ahora color del gol = color del resultado si es mi equipo, no subrayado
            color_gol = col if es_mio else "#000"
            deco = ""
            if filtro_activo and en_rango:
                bold = "font-weight:900;"
                gris = "background:#D3D3D3; border-radius:3px; padding:1px 4px;"
            else:
                bold = ""
                gris = ""
            extra_style = f"{deco} {bold}"
            if mj == "ON" and gol_ab:
                extra_jug = f' "{gol_ab}"' + (f' ({asi_ab})' if asi_ab else '')
            else:
                extra_jug = ""
            min_txt = f"<span style='font-size:12px; {bold} {gris}'>{m}'</span>"
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

    # separador 1T/2T linea continua gris flojita ancho completo
    sep_1t = "<div style='display:flex;align-items:center;gap:8px;margin:6px 0'><div style='flex:1;height:1px;background:#D3D3D3'></div><span style='color:#A9A9A9;font-weight:900;font-size:9px;white-space:nowrap'>1T</span><div style='flex:1;height:1px;background:#D3D3D3'></div></div>"
    sep_2t = "<div style='display:flex;align-items:center;gap:8px;margin:6px 0'><div style='flex:1;height:1px;background:#D3D3D3'></div><span style='color:#A9A9A9;font-weight:900;font-size:9px;white-space:nowrap'>2T</span><div style='flex:1;height:1px;background:#D3D3D3'></div></div>"
    if mins_1t and mins_2t:
        txt_mins = sep_1t + "".join(mins_1t) + sep_2t + "".join(mins_2t)
    elif mins_1t:
        txt_mins = sep_1t + "".join(mins_1t)
    elif mins_2t:
        txt_mins = sep_2t + "".join(mins_2t)
    else:
        txt_mins = "-"

    # --- MOMENTUM DESACTIVADO TOTAL - CERO GRAFICAS ---
    mom_html = ""

    # Si hay filtro MIN y no hay goles en ese rango, no renderizar - DESACTIVADO para no limitar
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

        # --- ROJAS AUTO DESACTIVADO ---

        if ms == "ON":
            hy = _iv(r.get('HY')); ay = _iv(r.get('AY'))
            hr = _iv(r.get('HR')); ar = _iv(r.get('AR'))
            hc = _iv(r.get('HC')); ac = _iv(r.get('AC'))
            hst = _iv(r.get('HST')); ast = _iv(r.get('AST'))
            hs = _iv(r.get('HS')); _as = _iv(r.get('AS'))
            hf = _iv(r.get('HF')); af = _iv(r.get('AF'))
            hsv = _iv(r.get('HomeSaves')); asv = _iv(r.get('AwaySaves'))

            hp = _iv(r.get('HomePasses')); ap = _iv(r.get('AwayPasses'))
            hpos = _iv(r.get('HomePos')); apos = _iv(r.get('AwayPos'))

            if (hy is not None or ay is not None) and ((hy or 0) + (ay or 0) > 0):
                extra += f" <span style='color:#b8860b'>Amarillas Local {hy if hy is not None else '-'} - Visitante {ay if ay is not None else '-'}</span><br>"
            if (hr is not None or ar is not None) and ((hr or 0) + (ar or 0) > 0):
                extra += f" <span style='color:#FF0000'>Rojas Local {hr if hr is not None else '-'} - Visitante {ar if ar is not None else '-'}</span><br>"
            if (hc is not None or ac is not None) and ((hc or 0) + (ac or 0) > 0):
                extra += f" <span style='color:#1E90FF'>Corners Local {hc if hc is not None else '-'} - Visitante {ac if ac is not None else '-'}</span><br>"
            if (hst is not None or ast is not None) and ((hst or 0) + (ast or 0) > 0):
                extra += f" <span style='color:#0066cc'>Tiros Puerta Local {hst if hst is not None else '-'} - Visitante {ast if ast is not None else '-'}</span><br>"
            if (hs is not None or _as is not None) and ((hs or 0) + (_as or 0) > 0):
                extra += f" <span style='color:#004080'>Tiros Totales Local {hs if hs is not None else '-'} - Visitante {_as if _as is not None else '-'}</span><br>"
            if (hf is not None or af is not None) and ((hf or 0) + (af or 0) > 0):
                extra += f" <span style='color:#666'>Faltas Local {hf if hf is not None else '-'} - Visitante {af if af is not None else '-'}</span><br>"
            if (hsv is not None or asv is not None) and ((hsv or 0) + (asv or 0) > 0):
                extra += f" <span style='color:#008080'>Paradas Local {hsv if hsv is not None else '-'} - Visitante {asv if asv is not None else '-'}</span><br>"
            if (hp is not None or ap is not None) and ((hp or 0) + (ap or 0) > 0):
                extra += f" <span style='color:#2E8B57'>Pases Local {hp if hp is not None else '-'} - Visitante {ap if ap is not None else '-'}</span><br>"
            if (hpos is not None or apos is not None) and ((hpos or 0) + (apos or 0) > 0):
                extra += f" <span style='color:#8B4513'>Posesion Local {hpos if hpos is not None else '-'}% - Visitante {apos if apos is not None else '-'}%</span><br>"
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

    col_j = "#0A2342"
    # --- TODA LA LINEA COLOREADA + SUBRAYADO EQUIPO FILTRO ---
    h_norm_chk = normaliza(h)
    a_norm_chk = normaliza(a)
    col_line = col_j
    h_html = h
    a_html = a
    if current_eq_norm:
        col_line = col
        if h_norm_chk == current_eq_norm:
            h_html = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"
        elif a_norm_chk == current_eq_norm:
            a_html = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
    return f"<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #333;line-height:1.2;max-width:380px;margin:0 auto'><div style='text-align:left;color:{col_line};font-weight:900'>|Jornada {j}| {h_html} vs {a_html}</div><div style='text-align:center;font-weight:900;word-break:break-word'>{extra}</div><div style='text-align:center;font-weight:900;margin-top:4px'><span style='background:#0A2342;color:#fff;padding:2px 10px;border-radius:3px'>Final {hg}-{ag}</span></div><div style='text-align:center;color:#666;font-weight:700;font-size:10px;margin-top:2px'>[1ª parte {hthg}-{htag}]</div><div style='color:#000;white-space:normal;word-break:break-word;line-height:1.1;margin-top:3px'>{txt_mins}</div>{mom_html}</div>"

eq_refs_orig = [e for e in [eq1, eq2] if e!= "Ninguno"]
eq_refs_norm = [normaliza(e) for e in eq_refs_orig]

html = ""

# mensaje ocultos borrado

# MODO FILTRO POR % - PRIORITARIO
if st.session_state.show_partidos and filtro_tipo!= "Ninguno":
    def get_val(r, keys):
        for k in keys:
            if k in r and pd.notna(r.get(k)):
                try: return float(r.get(k))
                except: pass
        return None
    def cumple(r, team_norm=None):
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
        # --- NUEVOS: resultado relativo al equipo ---
        if team_norm is not None:
            hn = normaliza(r.get('HomeTeam','')); an = normaliza(r.get('AwayTeam',''))
            if team_norm == hn: gf, gc = hg, ag
            elif team_norm == an: gf, gc = ag, hg
            else: return False
            if filtro_tipo == "Gana": return gf > gc
            if filtro_tipo == "Pierde": return gf < gc
            if filtro_tipo == "Empata": return gf == gc
            if filtro_tipo == "GanaEmpata": return gf >= gc
            if filtro_tipo == "GanaPierde": return gf != gc
            if filtro_tipo == "PierdeEmpata": return gf <= gc
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
            jornadas_ok = []
            t_norm = normaliza(team)
            for _, rr in d_team_valid.iterrows():
                if cumple(rr.to_dict(), t_norm):
                    c_ok+=1
                    try: jornadas_ok.append(int(float(rr.get('Jornada',0))))
                    except: pass
            pct = (c_ok / len(d_team_valid) * 100) if len(d_team_valid)>0 else 0
            if pct >= filtro_pct:
                calificados.append((team, loc_cond, pct, len(d_team_valid), c_ok, sorted(set(jornadas_ok))))

        calificados = sorted(calificados, key=lambda x: x[2], reverse=True)

    if not calificados:
        st.info(f"Ningún equipo cumple {filtro_tipo} >= {filtro_pct}%")
    else:
        # --- HEADER RESUMEN POR LIGA ---
        from collections import defaultdict
        resumen = defaultdict(list)
        for team, loc_cond, pct, total, ok, jors_list in calificados:
            try:
                liga_r = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)]['League'].mode().iloc[0]
            except:
                liga_r = liga_sel
            resumen[liga_r].append((team, pct, ok, total, jors_list))
        header_html = "<div style='font-family:monospace;background:#fff;color:#000;padding:8px;border-radius:6px;margin:6px 0;font-size:11px;border:1px solid #000'>"
        for liga_name in sorted(resumen.keys()):
            header_html += f"<div style='font-weight:900;margin-top:6px;color:#000;text-decoration:underline'>{liga_name}:</div>"
            for team_r, pct_r, ok_r, tot_r, jors_r in sorted(resumen[liga_name], key=lambda x: x[1], reverse=True):
                j_str = ", ".join([f"J{j}" for j in jors_r]) if jors_r else ""
                header_html += f"<div style='margin-left:10px;color:#000'>{team_r} {ok_r}/{tot_r} -> {j_str} {pct_r:.0f}%</div>"
        header_html += "</div>"
        html_partidos = ""
        for team, loc_cond, pct, total, ok, jors in calificados:
            d_team_full = filtrar_equipo(df_f, team, loc_cond)
            d_team_cumple = d_team_full[d_team_full.apply(lambda rr: cumple(rr.to_dict(), normaliza(team)), axis=1)]
            d_team_cumple = d_team_cumple.sort_values(['Jornada','Date'], ascending=[False, False]).head(20)
            try:
                liga_team = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)]['League'].mode().iloc[0]
            except:
                liga_team = liga_sel
            color_pct = "#0f8105" if pct>=70 else "#0A2342"
            html_partidos += f"<div style='font-family:monospace;font-weight:900;background:{color_pct};color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{team} {loc_cond} - {liga_team} | {filtro_tipo} {pct:.0f}% ({ok}/{total})</div>"
            for _, r in d_team_cumple.iterrows():
                html_partidos += fmt_rapido(r.to_dict(), [normaliza(team)], normaliza(team), team)
        html = header_html + html_partidos
        # --- FIX COPIAR FILTRO - SOLO PARTIDOS ---
        if html_partidos:
            import streamlit.components.v1 as components
            bloque_copy_filtro = f"""
            <div>
                <button onclick="copyFiltro()" id="btnCopyFiltro" style="position:sticky;top:0;z-index:99999;width:100%;background:#0f8105;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px;">📋 COPIAR PARTIDOS ({len(calificados)} equipos)</button>
                {header_html}
                <div id="targetFiltro">{html_partidos}</div>
            </div>
            <script>
            function copyFiltro(){{
                var txt = document.getElementById('targetFiltro').innerText;
                navigator.clipboard.writeText(txt).then(()=>{{
                    var b = document.getElementById('btnCopyFiltro');
                    b.innerText = '✓ COPIADO';
                    b.style.background = '#0A2342';
                    setTimeout(()=>{{ b.innerText=' COPIAR FILTRO ({len(calificados)} equipos)'; b.style.background='#0f8105'; }},1200);
                }});
            }}
            </script>
            """
            components.html(bloque_copy_filtro, height=900, scrolling=True)

elif st.session_state.show_partidos:
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

        df_mostrar = df_filtrada_min.sort_values(['Date','Jornada'], ascending=[False, False]) if not df_filtrada_min.empty else df_filtrada_min
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
        import streamlit.components.v1 as components
        import html as _html
        safe_html = _html.escape(html)
        # FIX HUECO GIGANTE BLANCO - FILTROS
        h_dinamica = min(5000, max(600, len(html)//10))
        total_partidos_btn = (len(df_eq1) + len(df_eq2)) if modo_doble else len(df_mostrar)
        bloque_copy = f"""
        <div>
            <button onclick="copyPartidos()" id="btnCopyPartidos" style="position:sticky;top:0;z-index:99999;width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px;">📋 COPIAR PARTIDOS ({total_partidos_btn} partidos)</button>
            <div id="targetPartidos">{html}</div>
        </div>
        <script>
        function copyPartidos(){{
            var txt = document.getElementById('targetPartidos').innerText;
            navigator.clipboard.writeText(txt).then(()=>{{
                var b = document.getElementById('btnCopyPartidos');
                b.innerText = '✓ COPIADO';
                b.style.background = '#0f8105';
                setTimeout(()=>{{ b.innerText='📋 COPIAR PARTIDOS ({total_partidos_btn} partidos)'; b.style.background='#0A2342'; }},1500);
            }});
        }}
        </script>
        """
        components.html(bloque_copy, height=h_dinamica, scrolling=True)
    else:
        st.info("Selecciona equipo")

# caption base borrado

if st.button("Ocultar partidos 2" if st.session_state.show_partidos else "Mostrar partidos 2", key="toggle_partidos_2", use_container_width=True):
    st.session_state.show_partidos = not st.session_state.show_partidos
    st.rerun()
##########################################
##########################################

##########################################
with st.expander("MOMENTUM LIVE - PEGAR URL Y COPIAR", expanded=False):
    import requests, re, json, html
    import streamlit.components.v1 as components

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

    def get_momentum_from_url(url):
        url = url.strip()
        eid = None
        m_mid = re.search(r'[?&]mid=([A-Za-z0-9]{6,12})', url, re.I)
        if m_mid:
            eid = m_mid.group(1)
        else:
            m = re.search(r'/partido/futbol/[^/]+/([A-Za-z0-9]{8,12})/', url)
            if m:
                eid = m.group(1)
        if not eid:
            return None, "No encuentro ?mid= en la URL. Pega la URL completa: ...?mid=ML4DjdZa"
        # FIX REAL HOME/AWAY - no fiarse de la URL
        home = "Local"
        away = "Visitante"
        try:
            r_html = requests.get(url, headers={"User-Agent": UA, "Referer":"https://www.flashscore.es/"}, timeout=8)
            htxt = r_html.text
            mh = re.search(r'duelParticipant__home[^>]*>.*?duelParticipant__name[^>]*>([^<]+)</', htxt, re.S)
            ma = re.search(r'duelParticipant__away[^>]*>.*?duelParticipant__name[^>]*>([^<]+)</', htxt, re.S)
            if mh and ma:
                home = re.sub(r'<.*?>','', mh.group(1)).strip().title()
                away = re.sub(r'<.*?>','', ma.group(1)).strip().title()
            else:
                mt2 = re.search(r'<meta property="og:title" content="([^"]+?)\s*-\s*([^"]+?)\s*\|', htxt)
                if mt2:
                    home = mt2.group(1).strip().title()
                    away = mt2.group(2).strip().title()
        except:
            pass
        if home == "Local":
            mt = re.search(r'/partido/futbol/([^/]+)/([^/]+)/', url)
            if mt:
                def clean(s):
                    s = re.sub(r'-[A-Za-z0-9]{6,8}$','',s)
                    return s.replace('-',' ').title().strip()
                away = clean(mt.group(1))
                home = clean(mt.group(2))
        try:
            import time as _tt
            api = f"https://13.ds.lsapp.eu/pq_graphql?_hash=mmts&eventId={eid}&providerId=7&_t={int(_tt.time())}"
            r = requests.get(api, headers={"User-Agent": UA, "Referer":"https://www.flashscore.es/", "Cache-Control":"no-cache", "Pragma":"no-cache"}, timeout=12)
            if r.status_code!=200:
                return None, f"Error {r.status_code} - Flashscore bloquea Streamlit Cloud. Ejecuta la app en local y si funcionara"
            data = r.json()
            root = data.get("data",{}).get("findMatchMomentumStatsByMatchId",{})
            entries = root.get("momentum",{}).get("entries",[])
            if not entries:
                return None, "Sin momentum aun - partido no empezado"
            vals = [round(float(e.get("momentumValue",0)),3) for e in entries]
            # FIX REAL HOME: el local de verdad es el primer slug de la URL
            def clean_slug(s):
                s = re.sub(r'-[A-Za-z0-9]{6,}$','',s).replace('-',' ').title().strip()
                return s
            m_url = re.search(r'/partido/futbol/([^/]+)/([^/]+)/', url)
            if m_url:
                real_home_url = clean_slug(m_url.group(1))
                real_away_url = clean_slug(m_url.group(2))
            else:
                real_home_url, real_away_url = home, away

            # si la API dice que el home es España pero en la URL el primero es Croacia, invierte todo
            api_home = (root.get("homeParticipant",{}).get("name") or home or "").lower()
            if real_home_url.lower() not in api_home and real_away_url.lower() in api_home:
                # esta al reves -> invierte momentum
                vals = [-v for v in vals]
                home, away = real_home_url, real_away_url
            else:
                home, away = real_home_url, real_away_url

            return {"eid":eid, "vals":vals, "home":home.title(), "away":away.title()}, None
        except Exception as e:
            return None, str(e)

    if st.button("🧹 LIMPIAR MOMENTUMS", key="v6_clear"):
        for i in range(15):
            if f"v6_url_{i}" in st.session_state:
                del st.session_state[f"v6_url_{i}"]
        st.rerun()
    st.caption("URL con ?mid= - 15 huecos para directo")
    urls = []
    for i in range(15):
        u = st.text_input(f"P{i+1}", value="https://www.flashscore.es/partido/futbol/cd-tenerife-IHv6nz80/cordoba-cf-CWuejruc/?mid=ML4DjdZa" if i==0 else "", key=f"v6_url_{i}", placeholder=f"Partido {i+1} ?mid=")
        urls.append(u)

    auto = st.checkbox("🔄 Auto-actualizar cada 60s", value=False, key="v6_auto")
    btn = st.button("⚡ GENERAR 15 MOMENTUMS", key="v6_btn", use_container_width=True)

    if btn or auto:
        todo = []
        for idx, url in enumerate(urls):
            if not url.strip():
                continue
            with st.spinner(f"P{idx+1}..."):
                res, err = get_momentum_from_url(url)
                if err:
                    st.error(f"P{idx+1} {err}")
                else:
                    vals = res["vals"]
                    eid = res["eid"]
                    reducido = {"id":eid,"home":res.get("home","local"),"away":res.get("away","visit"),"momentum":vals,"count":len(vals)}
                    todo.append(reducido)
                    j_str = json.dumps(reducido, separators=(',',':'))
                    j_esc = html.escape(j_str)
                    st.success(f"P{idx+1} OK {eid} {len(vals)} mins")
                    copy_html = f"""
                    <div style="font-family:monospace">
                        <textarea id="json_{idx}" style="width:100%;height:60px;font-size:10px;font-family:monospace;border:1px solid #ccc;border-radius:6px;padding:4px">{j_esc}</textarea>
                        <button onclick="navigator.clipboard.writeText(document.getElementById('json_{idx}').value).then(()=>{{document.getElementById('msg_{idx}').innerText='✅ P{idx+1} COPIADO'}})" 
                        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:8px;font-weight:900;cursor:pointer;margin-top:4px">📋 COPIAR P{idx+1}</button>
                        <div id="msg_{idx}" style="font-weight:900;color:#0f8105;text-align:center;font-size:11px"></div>
                    </div>
                    """
                    components.html(copy_html, height=110)
        if todo:
            mega = html.escape(json.dumps(todo, separators=(',',':')))
            mega_html = f"""
            <textarea id="mega" style="width:100%;height:90px;font-size:10px;font-family:monospace;border:2px solid #0A2342;border-radius:6px;padding:6px">{mega}</textarea>
            <button onclick="navigator.clipboard.writeText(document.getElementById('mega').value).then(()=>{{document.getElementById('mega_msg').innerText='✅ MEGA 15 COPIADO'}})" 
            style="width:100%;background:#0f8105;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;margin-top:6px">📋 COPIAR LOS {len(todo)} JUNTOS PARA IA</button>
            <div id="mega_msg" style="font-weight:900;color:#0f8105;text-align:center"></div>
            """
            components.html(mega_html, height=160)
            

with st.expander(" PREDICCION - PARTIDOS FUTUROS + HISTORIAL FIX", expanded=False):
    import pathlib

    @st.cache_data(show_spinner=False)
    def cargar_futuro():
        p = pathlib.Path("/mnt/data/Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv")
        if not p.exists():
            # busca en la carpeta del repo
            for q in [pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
                if (q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv").exists():
                    p = q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv"
                    break
        if not p.exists():
            return pd.DataFrame()
        df_fut = pd.read_csv(p, on_bad_lines='skip')
        df_fut['Date'] = pd.to_datetime(df_fut['Date'], errors='coerce')
        return df_fut

    df_futuro = cargar_futuro()
    if df_futuro.empty:
        st.warning("No encuentro Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv en /mnt/data")
        st.stop()

    # --- PERSISTENCIA 48H DISCO - FIX BORRADO REFRESCO ---
    import json, time
    FILE_PERSIST_PRED = pathlib.Path(__file__).parent.resolve() / ".persist_pred_48h.json"
    TTL_48H = 48 * 3600
    def _load_persist_48h():
        if not FILE_PERSIST_PRED.exists():
            return {}
        try:
            if time.time() - FILE_PERSIST_PRED.stat().st_mtime > TTL_48H:
                FILE_PERSIST_PRED.unlink(missing_ok=True)
                return {}
            with open(FILE_PERSIST_PRED, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    def _save_persist_48h():
        try:
            data = {
                "ligas_pred": st.session_state.get("ligas_pred", []),
                "fecha_pred": st.session_state.get("fecha_pred", "Todas"),
                "min_desde_pred": st.session_state.get("min_desde_pred", ""),
                "min_hasta_pred": st.session_state.get("min_hasta_pred", ""),
                "partidos_pred_sel": st.session_state.get("partidos_pred_sel", []),
                "eq_manual_1": st.session_state.get("eq_manual_1", []),
                "eq_manual_2": st.session_state.get("eq_manual_2", []),
                "cond_manual_1": st.session_state.get("cond_manual_1", "TODOS"),
                "cond_manual_2": st.session_state.get("cond_manual_2", "TODOS"),
                "cond_loc_pred": st.session_state.get("cond_loc_pred", "Local en casa / Visitante fuera"),
                "filtro_ht_ft_unico_2026_v9": st.session_state.get("filtro_ht_ft_unico_2026_v9", []),
            }
            with open(FILE_PERSIST_PRED, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    _persist = _load_persist_48h()
    if "ligas_pred" not in st.session_state:
        st.session_state.ligas_pred = _persist.get("ligas_pred") or st.query_params.get_all("ligas_pred")
    if "fecha_pred" not in st.session_state:
        st.session_state.fecha_pred = _persist.get("fecha_pred") or st.query_params.get("fecha_pred", "Todas")
    if "min_desde_pred" not in st.session_state:
        st.session_state.min_desde_pred = _persist.get("min_desde_pred") or st.query_params.get("min_desde_pred", "")
    if "min_hasta_pred" not in st.session_state:
        st.session_state.min_hasta_pred = _persist.get("min_hasta_pred") or st.query_params.get("min_hasta_pred", "")
    if "partidos_pred_sel" not in st.session_state:
        st.session_state.partidos_pred_sel = _persist.get("partidos_pred_sel") or st.query_params.get_all("partidos_pred_sel")
    if "eq_manual_1" not in st.session_state:
        st.session_state.eq_manual_1 = _persist.get("eq_manual_1") or st.query_params.get_all("eq_manual_1")
    if "eq_manual_2" not in st.session_state:
        st.session_state.eq_manual_2 = _persist.get("eq_manual_2") or st.query_params.get_all("eq_manual_2")
    if "cond_manual_1" not in st.session_state:
        st.session_state.cond_manual_1 = _persist.get("cond_manual_1") or st.query_params.get("cond_manual_1", "TODOS")
    if "cond_manual_2" not in st.session_state:
        st.session_state.cond_manual_2 = _persist.get("cond_manual_2") or st.query_params.get("cond_manual_2", "TODOS")
    if "cond_loc_pred" not in st.session_state:
        st.session_state.cond_loc_pred = _persist.get("cond_loc_pred") or st.query_params.get("cond_loc_pred", "Local en casa / Visitante fuera")
    if "filtro_ht_ft_unico_2026_v9" not in st.session_state:
        st.session_state.filtro_ht_ft_unico_2026_v9 = _persist.get("filtro_ht_ft_unico_2026_v9") or st.query_params.get_all("filtro_ht_ft_unico_2026_v9")

    if st.button(" LIMPIAR TODO EL BLOQUE PREDICCION", key="btn_limpiar_pred", use_container_width=True):
        for k in ["ligas_pred","fecha_pred","min_desde_pred","min_hasta_pred","partidos_pred_sel","eq_manual_1","eq_manual_2","cond_manual_1","cond_manual_2","filtro_ht_ft_unico_2026_v9","cond_loc_pred"]:
            if k in st.session_state:
                del st.session_state[k]
        for k in ["ligas_pred","fecha_pred","min_desde_pred","min_hasta_pred"]:
            if k in st.query_params:
                del st.query_params[k]
        try:
            FILE_PERSIST_PRED.unlink(missing_ok=True)
        except:
            pass
        st.rerun()

    # --- GUARDA AUTOMATICO 48H ---
    _save_persist_48h()

    # --- 2 EQUIPOS MANUALES PARA CARTAGENA / ANTEQUERA - EUROPA ONLY 2.529 vs 5.264 ---
    @st.cache_data(show_spinner=False)
    def cargar_base_europa():
        p_par = pathlib.Path("base_partidos_europa.parquet")
        if not p_par.exists():
            p_par = pathlib.Path(__file__).parent.resolve() / "base_partidos_europa.parquet"
        g_par = pathlib.Path("base_goles_europa.parquet")
        if not g_par.exists():
            g_par = pathlib.Path(__file__).parent.resolve() / "base_goles_europa.parquet"
        df_e = pd.read_parquet(p_par) if p_par.exists() else pd.DataFrame()
        if not df_e.empty:
            df_e['Date'] = pd.to_datetime(df_e['Date'], errors='coerce')
            df_e = df_e.sort_values(['League','Season','Date']).copy()
            # FIX JORNADA POR LIGA + TEMPORADA - NO SOLO LIGA
            df_e['Jornada'] = 0
            for (l_name, s_name), g_s in df_e.groupby(['League','Season'], sort=False):
                g_s = g_s.sort_values('Date')
                idxs = g_s.index.to_numpy()
                n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                ppj = max(n_teams // 2, 1)
                df_e.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1
        df_g = pd.read_parquet(g_par) if g_par.exists() else pd.DataFrame()
        ev = {}
        if not df_g.empty:
            df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            df_g['m'] = pd.to_numeric(df_g.get('minuto', 0), errors='coerce').fillna(0).astype(int)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo',''))} for _, r in sub.iterrows()]
        return df_e, ev

    df_europa, eventos_europa = cargar_base_europa()
    df = df_europa
    eventos = eventos_europa

    # --- FILTROS ARRIBA - SOLO EUROPA ---
    ligas_fut_all = sorted(df_futuro['League_CSV'].dropna().unique().tolist())
    # filtra solo ligas que tienen historial en base_europa
    if not df_europa.empty and 'League' in df_europa.columns:
        ligas_europa_set = set(df_europa['League'].dropna().astype(str).tolist())
        ligas_fut = [l for l in ligas_fut_all if any(normaliza(l) == normaliza(le) or normaliza(l) in normaliza(le) or normaliza(le) in normaliza(l) for le in ligas_europa_set)]
        # si por nombre no matchea, deja solo palabras clave europeas
        if not ligas_fut:
            keywords_eu = ["Eliteserien","Eredivisie","Bundesliga","LaLiga","Premier","Serie A","Ligue","Pro League","First League Bulgaria","Super Lig","Ekstraklasa","Primeira Liga"]
            ligas_fut = [l for l in ligas_fut_all if any(k.lower() in l.lower() for k in keywords_eu)]
    else:
        ligas_fut = ligas_fut_all

    c_lp1, c_lp2, c_lp3, c_lp4 = st.columns([2,1,1,1])
    with c_lp4:
        cond_loc_pred = st.selectbox("Filtro", ["TODOS","equipo local solamente partidos de local","equipo visitante solamente sus partidos de visitante","Local en casa / Visitante fuera"], index=3, key="cond_loc_pred")
        res_1p_tipo = st.selectbox("Resultado 1ªP", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_1p_tipo_pred")
        opciones_res = [f"{a}-{b}_1ªP" for a in range(5) for b in range(5)] + [f"{a}-{b}_2ªP" for a in range(5) for b in range(5)]
        resultados_pred_sel = st.multiselect("Resultado 1ªP / 2ªP", opciones_res, default=[], key="filtro_ht_ft_unico_2026_v9", placeholder="Ej: 0-0_1ªP")
        overs_sel = st.multiselect("Overs / Unders por parte", ["1P >0.5","1P >1.5","1P >2.5","2P >0.5","2P >1.5","2P >2.5"], default=[], key="overs_unders_pred", placeholder="Ej: 1P >0.5")

    lista_hist_equipos = sorted(pd.concat([df['HomeTeam'], df['AwayTeam']]).dropna().astype(str).unique().tolist())

    if st.button("🧹 Limpiar solo manuales", key="btn_limpiar_solo_manuales", use_container_width=True):
        for k in ["eq_manual_1","eq_manual_2"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    c_man1, c_man2 = st.columns(2)
    with c_man1:
        equipos_manuales_1 = st.multiselect("Equipos manuales 1", lista_hist_equipos, default=[], key="eq_manual_1", placeholder="Ej: Cartagena, Burgos...")
        cond_manual_1 = st.selectbox("Cond manual 1", ["TODOS","solo local","solo visitante"], key="cond_manual_1")
    with c_man2:
        equipos_manuales_2 = st.multiselect("Equipos manuales 2", lista_hist_equipos, default=[], key="eq_manual_2", placeholder="Ej: Antequera, Marbella...")
        cond_manual_2 = st.selectbox("Cond manual 2", ["TODOS","solo local","solo visitante"], key="cond_manual_2")
    import streamlit.components.v1 as _comp_morado
    _comp_morado.html("""
    <script>
    const MOR = ["Equipos manuales 1","Equipos manuales 2"];
    function paintMor(){
      parent.document.querySelectorAll('label').forEach(l=>{
        if(MOR.some(t=>l.innerText.includes(t))){
          l.style.setProperty('color','#7B2CBF','important');
          l.style.setProperty('font-weight','900','important');
        }
      });
    }
    paintMor();
    setInterval(paintMor, 500);
    </script>
    """, height=0)

    with c_lp1:
        ligas_pred_sel = st.multiselect("Ligas futuras", ligas_fut, default=st.session_state.ligas_pred, key="ligas_pred", placeholder="Todas las ligas")
    with c_lp2:
        # fechas reales que hay en el futuro
        df_base_pred = df_futuro if not ligas_pred_sel else df_futuro[df_futuro['League_CSV'].isin(ligas_pred_sel)]
        fechas_pred = sorted(df_base_pred['Date'].dropna().dt.date.unique())
        fechas_pred_str = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_pred]
        fecha_pred_sel = st.selectbox("Fecha desde", fechas_pred_str, index=fechas_pred_str.index(st.session_state.fecha_pred) if st.session_state.fecha_pred in fechas_pred_str else 0, key="fecha_pred")
    with c_lp3:
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            min_desde_pred_raw = st.text_input("MIN DESDE", key="min_desde_pred", placeholder="-")
        with c_m2:
            min_hasta_pred_raw = st.text_input("MIN HASTA", key="min_hasta_pred", placeholder="-")
        import streamlit.components.v1 as _comp_blue
        _comp_blue.html("""
        <script>
        const BLUES = ["MIN DESDE","MIN HASTA"];
        function paintBlue(){
          parent.document.querySelectorAll('label').forEach(l=>{
            if(BLUES.some(t=>l.innerText.includes(t))){
              l.style.setProperty('color','#1E3A8A','important');
              l.style.setProperty('font-weight','900','important');
            }
          });
        }
        paintBlue();
        setInterval(paintBlue, 500);
        </script>
        """, height=0)

    def _parse_min_pred(v):
        try:
            if v is None or str(v).strip() in ["", "-", "–", "—"]: return None
            return int(str(v).strip().replace("'", ""))
        except: return None
    MIN_DESDE_PRED = _parse_min_pred(min_desde_pred_raw)
    MIN_HASTA_PRED = _parse_min_pred(min_hasta_pred_raw)

    # filtra base por fecha
    if fecha_pred_sel!= "Todas":
        try:
            f_date = pd.to_datetime(fecha_pred_sel, dayfirst=True).date()
            df_base_pred = df_base_pred[df_base_pred['Date'].dt.date >= f_date]
        except: pass

    df_base_pred = df_base_pred.sort_values('Date').head(1000)

    # --- SELECTOR AUTOMATICO PARTIDO FUTURO -> EQUIPO1 VS EQUIPO2 ---
    # formato: "10/10 | 2. Bundesliga | Magdeburg vs Hannover"
    opciones_partidos = []
    for _, r in df_base_pred.iterrows():
        try:
            fecha_s = r['Date'].strftime("%d/%m")
            liga_s = str(r['League_CSV'])[:15]
            h = str(r['HomeTeam']).strip()
            a = str(r['AwayTeam']).strip()
            fid = str(r.get('fixture_id',''))
            opciones_partidos.append(f"{fecha_s} | {liga_s} | {h} vs {a} | {fid}")
        except: continue

    partidos_sel = []
    if not opciones_partidos:
        st.info("No hay partidos futuros con ese filtro")
    else:
        partidos_sel = st.multiselect("Elige partido futuro (auto-carga equipos)", opciones_partidos, key="partidos_pred_sel", placeholder="Ej: Magdeburg vs Hannover - se cargan los 2 equipos solos")
    # --- PINTA EN ROJO LOS 4 LABELS + MARRON OVERS ---
    import streamlit.components.v1 as _comp_red
    _comp_red.html("""
    <script>
    const REDS = ["Resultado 1ªP","Resultado 1ªP / 2ªP","Filtro","Elige partido futuro"];
    const BROWNS = ["Overs / Unders"];
    function paint(){
      parent.document.querySelectorAll('label').forEach(l=>{
        if(REDS.some(t=>l.innerText.includes(t))){
          l.style.setProperty('color','red','important');
          l.style.setProperty('font-weight','900','important');
        }
        if(BROWNS.some(t=>l.innerText.includes(t))){
          l.style.setProperty('color','#8B4513','important');
          l.style.setProperty('font-weight','900','important');
        }
      });
    }
    paint();
    setInterval(paint, 500);
    </script>
    """, height=0)
##########

    partidos_pred_copy = []
    tiene_manuales = (len(equipos_manuales_1) > 0 or len(equipos_manuales_2) > 0)

    if not partidos_sel and not tiene_manuales:
        st.caption("Selecciona partido futuro o equipo manual")
    else:
        # --- PARA CADA PARTIDO FUTURO ELEGIDO, PINTA HISTORIAL DE LOS 2 EQUIPOS ---
        partidos_pred_copy = [] # para boton copiar
        partidos_a_iterar = partidos_sel if partidos_sel else ["MANUAL | Manual | Manual vs Manual | 0"]

        for partido_str in partidos_a_iterar:
            try:
                # saca home y away del string
                partes = partido_str.split("|")
                teams_part = partes[2].strip() if len(partes)>=3 else ""
                if " vs " in teams_part:
                    h_fut, a_fut = [x.strip() for x in teams_part.split(" vs ")]
                else:
                    continue
            except: continue

            st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 FUTURO: {h_fut} vs {a_fut} | {partes[0].strip()}</div>", unsafe_allow_html=True)

        if "MANUAL" in partido_str:
            equipos_a_mostrar = []
            if 'equipos_manuales_1' in locals() and equipos_manuales_1: equipos_a_mostrar.extend(equipos_manuales_1)
            if 'equipos_manuales_2' in locals() and equipos_manuales_2: equipos_a_mostrar.extend(equipos_manuales_2)
        else:
            equipos_a_mostrar = [h_fut, a_fut]
            if 'equipos_manuales_1' in locals() and equipos_manuales_1: equipos_a_mostrar.extend(equipos_manuales_1)
            if 'equipos_manuales_2' in locals() and equipos_manuales_2: equipos_a_mostrar.extend(equipos_manuales_2)
        for nombre_eq in equipos_a_mostrar:
            norm_eq = normaliza(nombre_eq)
            eq_up = nombre_eq.upper().strip()
            # tu base ya es todo MAYUSCULAS y sin variantes internas, no hace falta apply
            df_team = df[(df['HomeTeam'].astype(str).str.upper().str.strip() == eq_up) | (df['AwayTeam'].astype(str).str.upper().str.strip() == eq_up)]
            # fallback si viene con acento en futuro (Beşiktaş vs BESIKTAS)
            if df_team.empty:
                df_team = df[(df['HomeTeam'].apply(lambda x: normaliza(x)==norm_eq)) | (df['AwayTeam'].apply(lambda x: normaliza(x)==norm_eq))]
            # --- FILTRO LOCAL / VISITANTE FIX - CORREGIDO + COMBINADO - FAST ---
            if cond_loc_pred == "equipo local solamente partidos de local" and nombre_eq == h_fut:
                df_team = df_team[df_team['HomeTeam'].astype(str).str.upper().str.strip() == eq_up]
            elif cond_loc_pred == "equipo visitante solamente sus partidos de visitante" and nombre_eq == a_fut:
                df_team = df_team[df_team['AwayTeam'].astype(str).str.upper().str.strip() == eq_up]
            elif cond_loc_pred == "Local en casa / Visitante fuera":
                if nombre_eq == h_fut:
                    df_team = df_team[df_team['HomeTeam'].astype(str).str.upper().str.strip() == eq_up]
                elif nombre_eq == a_fut:
                    df_team = df_team[df_team['AwayTeam'].astype(str).str.upper().str.strip() == eq_up]
            # --- FILTRO PARA MANUALES CARTAGENA / ANTEQUERA - FAST ---
            if 'equipos_manuales_1' in locals() and nombre_eq in equipos_manuales_1:
                if cond_manual_1 == "solo local":
                    df_team = df_team[df_team['HomeTeam'].astype(str).str.upper().str.strip() == eq_up]
                elif cond_manual_1 == "solo visitante":
                    df_team = df_team[df_team['AwayTeam'].astype(str).str.upper().str.strip() == eq_up]
            if 'equipos_manuales_2' in locals() and nombre_eq in equipos_manuales_2:
                if cond_manual_2 == "solo local":
                    df_team = df_team[df_team['HomeTeam'].astype(str).str.upper().str.strip() == eq_up]
                elif cond_manual_2 == "solo visitante":
                    df_team = df_team[df_team['AwayTeam'].astype(str).str.upper().str.strip() == eq_up]
            # jornadas recientes - con huecos - FAST: base para J15,J14,J13 ANTES de filtrar por 0-0 / Overs
            df_team_base_pred = df_team.copy()
            if 'resultados_pred_sel' in locals() and resultados_pred_sel or 'filtro_ht_ft_unico_2026_v9' in st.session_state and st.session_state.get('filtro_ht_ft_unico_2026_v9'):
                sel = st.session_state.get('filtro_ht_ft_unico_2026_v9', resultados_pred_sel if 'resultados_pred_sel' in locals() else [])
                set_1p = set(); set_2p = set()
                for s in sel:
                    if "_1ªP" in s:
                        try: a,b = s.replace("_1ªP","").split("-"); set_1p.add((int(a),int(b)))
                        except: pass
                    if "_2ªP" in s:
                        try: a,b = s.replace("_2ªP","").split("-"); set_2p.add((int(a),int(b)))
                        except: pass
                if set_1p or set_2p:
                    def _cumple_res_pred(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        if set_1p and (hthg_, htag_) in set_1p: return True
                        if set_2p and (hg_, ag_) in set_2p: return True
                        return False
                    df_team = df_team[df_team.apply(_cumple_res_pred, axis=1)]

            # --- FILTRO OVERS / UNDERS POR PARTE ---
            if 'overs_sel' in locals() and overs_sel:
                def _cumple_overs_pred(rr):
                    try:
                        hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                        hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                    except:
                        return False
                    g1 = hthg_ + htag_
                    g2 = (hg_ + ag_) - g1
                    if g2 < 0: g2 = 0
                    for o in overs_sel:
                        if o == "1P >0.5" and not (g1 > 0.5): return False
                        if o == "1P >1.5" and not (g1 > 1.5): return False
                        if o == "1P >2.5" and not (g1 > 2.5): return False
                        if o == "2P >0.5" and not (g2 > 0.5): return False
                        if o == "2P >1.5" and not (g2 > 1.5): return False
                        if o == "2P >2.5" and not (g2 > 2.5): return False
                    return True
                df_team = df_team[df_team.apply(_cumple_overs_pred, axis=1)]

            # --- FILTRO 1ªP TIPO EMPATE / GANA / PIERDE ---
            if 'res_1p_tipo' in locals() and res_1p_tipo != "TODOS":
                def _cumple_1p_tipo(rr):
                    try:
                        hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                    except: return False
                    hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                    if norm_eq == hn_:
                        r_ = "GANA" if hthg_ > htag_ else "EMPATE" if hthg_ == htag_ else "PIERDE"
                    elif norm_eq == an_:
                        r_ = "GANA" if htag_ > hthg_ else "EMPATE" if htag_ == hthg_ else "PIERDE"
                    else:
                        return False
                    if res_1p_tipo == "EMPATE": return r_ == "EMPATE"
                    if res_1p_tipo == "GANA": return r_ == "GANA"
                    if res_1p_tipo == "PIERDE": return r_ == "PIERDE"
                    if res_1p_tipo == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                    if res_1p_tipo == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                    if res_1p_tipo == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                    return True
                df_team = df_team[df_team.apply(_cumple_1p_tipo, axis=1)]

            if df_team.empty:
                st.caption(f"{nombre_eq} - sin historial en base actual")
                continue

            st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:2px 6px;margin:6px 0 2px 0;font-size:10px'>{nombre_eq.upper()}</div>", unsafe_allow_html=True)
            if 'Jornada' not in df_team_base_pred.columns:
                df_team_base_pred['Jornada'] = 1
            if 'Jornada' not in df_team.columns:
                df_team['Jornada'] = df_team_base_pred['Jornada'] if 'Jornada' in df_team_base_pred.columns else 1
            # FIX ORDEN JORNADAS J9->J1 REAL
            df_team_base_pred = df_team_base_pred.sort_values(['Jornada','Date'], ascending=[False, False])
            df_team = df_team.sort_values(['Jornada','Date'], ascending=[False, False]) if not df_team.empty else df_team
            jornadas = sorted(df_team_base_pred['Jornada'].dropna().unique(), reverse=True)[:15]
            sel_txt = ", ".join(sel) if 'sel' in locals() and sel else ""
            for j in jornadas:
                d_j_ok = df_team[df_team['Jornada']==j].sort_values('Date', ascending=False) if not df_team.empty and 'Jornada' in df_team.columns else pd.DataFrame()
                es_hueco = d_j_ok.empty
                if es_hueco:
                    # HUECO VACIO - sin ningun texto del otro partido
                    st.markdown(f"<div style='font-family:monospace;font-weight:700;color:#aaa;margin:4px 0 0 0;font-size:10px'>J{int(j)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='line-height:1.15;margin:0 0 6px 0;padding:0'></div>", unsafe_allow_html=True)
                    continue
                else:
                    st.markdown(f"<div style='font-family:monospace;font-weight:700;color:#0A2342;margin:4px 0 0 0;font-size:10px'>J{int(j)}</div>", unsafe_allow_html=True)
                d_j = d_j_ok
                html_lineas = ""
                for _, r in d_j.iterrows():
                    fid = str(r.get('fixture_id','')).split('.')[0]

                    # FILTRO MINUTO PREDICCION
                    if MIN_DESDE_PRED is not None or MIN_HASTA_PRED is not None:
                        _tiene = False
                        for _ev in eventos.get(fid, []):
                            if 'Missed' in _ev.get('tipo',''): continue
                            _mm = _ev.get('m', -1)
                            if MIN_DESDE_PRED is not None and _mm < MIN_DESDE_PRED: continue
                            if MIN_HASTA_PRED is not None and _mm > MIN_HASTA_PRED: continue
                            _tiene = True
                            break
                        if not _tiene:
                            continue

                    h = str(r.get('HomeTeam','')).strip(); a = str(r.get('AwayTeam','')).strip()
                    try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                    except: hg=0; ag=0
                    h_up = h.upper().strip(); a_up = a.upper().strip()
                    h_norm_r = normaliza(h); a_norm_r = normaliza(a)
                    if norm_eq == h_norm_r: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#8B4513"
                    elif norm_eq == a_norm_r: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#8B4513"
                    else: col_main = "#000"
                    hn = h_norm_r; an = a_norm_r

                    try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                    except: hthg=0; htag=0
                    ht_str = f"[{hthg}-{htag}]"
                    ht_html = f"<span style='color:#0A2342;font-weight:900;background:#E8E8E8;border-radius:3px;padding:0 4px;margin:0 3px'>{ht_str}</span>"

                    mins_1t = []; mins_2t = []
                    filtro_act = (MIN_DESDE_PRED is not None or MIN_HASTA_PRED is not None)
                    for ev in sorted(eventos.get(fid, []), key=lambda x: x['m']):
                        if 'Missed' in ev.get('tipo',''): continue
                        m = ev.get('m',-1); team_ev = ev['team']
                        benef = an if 'Own Goal' in ev.get('tipo','') and team_ev == hn else hn if 'Own Goal' in ev.get('tipo','') else team_ev
                        es_mio = norm_eq in benef
                        col_min = col_main if es_mio else "#000"
                        peso = "font-weight:900;" if es_mio else "font-weight:700;"
                        en_rango = (MIN_DESDE_PRED is None or m >= MIN_DESDE_PRED) and (MIN_HASTA_PRED is None or m <= MIN_HASTA_PRED)
                        if filtro_act and en_rango:
                            span = f"<span style='color:{col_min};{peso};background:#D3D3D3;border-radius:3px;padding:1px 4px;margin-right:2px'> {m}'</span>"
                        else:
                            span = f"<span style='color:{col_min};{peso};margin-right:2px'> {m}'</span>"
                        if m <= 45: mins_1t.append(span)
                        else: mins_2t.append(span)

                    if mins_1t and mins_2t: mins_html = "".join(mins_1t) + ht_html + "<span style='color:#000;font-weight:900;margin:0 4px'>|</span>" + "".join(mins_2t)
                    elif mins_1t: mins_html = "".join(mins_1t) + ht_html
                    elif mins_2t: mins_html = ht_html + "<span style='color:#000;font-weight:900;margin:0 4px'>|</span>" + "".join(mins_2t)
                    else: mins_html = ht_html
                    def res_eq_pred(gf, gc): return "G" if gf>gc else "E" if gf==gc else "P"
                    if norm_eq == hn: r1 = res_eq_pred(hthg, htag); rF = res_eq_pred(hg, ag)
                    elif norm_eq == an: r1 = res_eq_pred(htag, hthg); rF = res_eq_pred(ag, hg)
                    else: r1="E"; rF="E"
                    estado = f"{r1}/{rF}"

                    if norm_eq == h_norm_r:
                        h_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"; a_txt = a
                    elif norm_eq == a_norm_r:
                        h_txt = h; a_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
                    else:
                        h_txt = h; a_txt = a

                    html_lineas += f"<span style='color:{col_main};font-family:monospace;font-size:9px;font-weight:700;white-space:nowrap;margin-right:10px;line-height:1.1'>{h_txt} {hg}-{ag} {a_txt}{mins_html}<span style='color:#fff;background:{col_main};padding:0 4px;border-radius:2px;margin-left:5px'>{estado}</span></span>"

                    # para copiar
                    m1 = []; m2 = []
                    for evc in sorted(eventos.get(fid, []), key=lambda x: x['m']):
                        if MIN_DESDE_PRED is not None and evc.get('m',-1) < MIN_DESDE_PRED: continue
                        if MIN_HASTA_PRED is not None and evc.get('m',-1) > MIN_HASTA_PRED: continue
                        if 'Missed' in evc.get('tipo',''): continue
                        mm = evc.get('m',0)
                        if mm <= 45: m1.append(f"{mm}'")
                        else: m2.append(f"{mm}'")
                    if m1 and m2: mins_txt = " ".join(m1) + f"{ht_str} " + " ".join(m2)
                    elif m1: mins_txt = " ".join(m1) + f"{ht_str}"
                    elif m2: mins_txt = f"{ht_str} " + " ".join(m2)
                    else: mins_txt = f"{ht_str}"
                    partidos_pred_copy.append(f"J{int(j)}|{h} {hg}-{ag} {a} {mins_txt}{estado}")

                st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas}</div>", unsafe_allow_html=True)

    # --- BOTON COPIAR PREDICCION ---
    if partidos_pred_copy:
        import html as _html
        texto_final = "\n".join(partidos_pred_copy[:200])
        safe_txt = _html.escape(texto_final)
        import streamlit.components.v1 as components
        components.html(f"""
        <textarea id="txt_pred" style="position:absolute;left:-9999px;top:-9999px;">{safe_txt}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_pred').value).then(()=>{{let b=document.getElementById('btn_pred_copy'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText=' COPIAR PREDICCION'; b.style.background='#0A2342'}},1200)}})"
        id="btn_pred_copy"
        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;">
         COPIAR PREDICCION ({len(partidos_sel)} partidos futuros)
        </button>
        """, height=55, scrolling=False)
        




with st.expander(" PREDICCION RESTO - SUDAMERICA + ASIA + MLS", expanded=False):
    @st.cache_data(show_spinner=False)
    def cargar_base_resto():
        p_par = pathlib.Path("base_partidos_resto.parquet")
        if not p_par.exists():
            p_par = pathlib.Path(__file__).parent.resolve() / "base_partidos_resto.parquet"
        g_par = pathlib.Path("base_goles_resto.parquet")
        if not g_par.exists():
            g_par = pathlib.Path(__file__).parent.resolve() / "base_goles_resto.parquet"
        df_e = pd.read_parquet(p_par) if p_par.exists() else pd.DataFrame()
        if not df_e.empty:
            df_e['Date'] = pd.to_datetime(df_e['Date'], errors='coerce')
            df_e = df_e.sort_values(['League','Season','Date']).copy()
            df_e['Jornada'] = 0
            for (l_name, s_name), g_s in df_e.groupby(['League','Season'], sort=False):
                g_s = g_s.sort_values('Date')
                idxs = g_s.index.to_numpy()
                n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                ppj = max(n_teams // 2, 1)
                df_e.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1
        df_g = pd.read_parquet(g_par) if g_par.exists() else pd.DataFrame()
        ev = {}
        if not df_g.empty:
            df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            df_g['m'] = pd.to_numeric(df_g.get('minuto', 0), errors='coerce').fillna(0).astype(int)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo',''))} for _, r in sub.iterrows()]
        return df_e, ev

    df_resto, eventos_resto = cargar_base_resto()
    df_r = df_resto
    eventos_r = eventos_resto

    if df_r.empty:
        st.warning("No encuentro base_partidos_resto.parquet")
        st.stop()

    # --- FILTROS SOLO RESTO ---
    ligas_fut_all_r = sorted(df_futuro['League_CSV'].dropna().unique().tolist())
    if not df_r.empty and 'League' in df_r.columns:
        ligas_resto_set = set(df_r['League'].dropna().astype(str).tolist())
        ligas_fut_r = [l for l in ligas_fut_all_r if any(normaliza(l) == normaliza(le) or normaliza(l) in normaliza(le) or normaliza(le) in normaliza(l) for le in ligas_resto_set)]
        if not ligas_fut_r:
            # si no matchea por nombre exacto, filtra por keywords resto
            keywords_resto = ["J1 League","J2 League","K League","CSL","A-League","Liga MX","MLS","Brasileirao","Primera Division Argentina","Primera A Colombia","Primera Division Chile","Liga 1 Peru","Serie A Ecuador","Liga Pro"]
            ligas_fut_r = [l for l in ligas_fut_all_r if any(k.lower() in l.lower() for k in keywords_resto)]
    else:
        ligas_fut_r = ligas_fut_all_r

    c1r,c2r,c3r,c4r = st.columns([2,1,1,1])
    with c1r:
        ligas_pred_sel_r = st.multiselect("Ligas futuras RESTO", ligas_fut_r, default=[], key="ligas_pred_resto", placeholder="J1, K1, CSL, MLS, Brasil...")
    with c2r:
        df_base_pred_r = df_futuro if not ligas_pred_sel_r else df_futuro[df_futuro['League_CSV'].isin(ligas_pred_sel_r)]
        fechas_pred_r = sorted(df_base_pred_r['Date'].dropna().dt.date.unique())
        fechas_pred_str_r = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_pred_r]
        fecha_pred_sel_r = st.selectbox("Fecha desde RESTO", fechas_pred_str_r, key="fecha_pred_resto")
    with c3r:
        c_m1r, c_m2r = st.columns(2)
        with c_m1r:
            min_desde_pred_raw_r = st.text_input("MIN DESDE R", key="min_desde_pred_resto", placeholder="-")
        with c_m2r:
            min_hasta_pred_raw_r = st.text_input("MIN HASTA R", key="min_hasta_pred_resto", placeholder="-")
    with c4r:
        cond_loc_pred_r = st.selectbox("Filtro R", ["TODOS","equipo local solamente partidos de local","equipo visitante solamente sus partidos de visitante","Local en casa / Visitante fuera"], index=3, key="cond_loc_pred_resto")
        res_1p_tipo_r = st.selectbox("Resultado 1ªP R", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_1p_tipo_pred_resto")
        opciones_res_r = [f"{a}-{b}_1ªP" for a in range(5) for b in range(5)] + [f"{a}-{b}_2ªP" for a in range(5) for b in range(5)]
        resultados_pred_sel_r = st.multiselect("Resultado 1ªP / 2ªP R", opciones_res_r, default=[], key="filtro_ht_ft_resto", placeholder="Ej: 0-0_1ªP")
        overs_sel_r = st.multiselect("Overs / Unders R", ["1P >0.5","1P >1.5","1P >2.5","2P >0.5","2P >1.5","2P >2.5"], default=[], key="overs_unders_pred_resto", placeholder="Ej: 1P >0.5")

    # --- EQUIPOS MANUALES RESTO - AÑADIDO (igual que EUROPA) ---
    lista_hist_equipos_resto = sorted(pd.concat([df_r['HomeTeam'], df_r['AwayTeam']]).dropna().astype(str).unique().tolist())
    if st.button("🧹 Limpiar solo manuales", key="btn_limpiar_solo_manuales_resto", use_container_width=True):
        for k in ["eq_manual_1_resto","eq_manual_2_resto"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
    c_man1_r, c_man2_r = st.columns(2)
    with c_man1_r:
        equipos_manuales_1_r = st.multiselect("Equipos manuales 1", lista_hist_equipos_resto, default=[], key="eq_manual_1_resto", placeholder="Ej: Bahia, Flamengo...")
        cond_manual_1_r = st.selectbox("Cond manual 1", ["TODOS","solo local","solo visitante"], key="cond_manual_1_resto")
    with c_man2_r:
        equipos_manuales_2_r = st.multiselect("Equipos manuales 2", lista_hist_equipos_resto, default=[], key="eq_manual_2_resto", placeholder="Ej: Mirassol, Palmeiras...")
        cond_manual_2_r = st.selectbox("Cond manual 2", ["TODOS","solo local","solo visitante"], key="cond_manual_2_resto")

    def _parse_min_pred_r(v):
        try:
            if v is None or str(v).strip() in ["", "-", "–", "—"]: return None
            return int(str(v).strip().replace("'", ""))
        except: return None
    MIN_DESDE_PRED_R = _parse_min_pred_r(min_desde_pred_raw_r)
    MIN_HASTA_PRED_R = _parse_min_pred_r(min_hasta_pred_raw_r)

    if fecha_pred_sel_r!= "Todas":
        try:
            f_date_r = pd.to_datetime(fecha_pred_sel_r, dayfirst=True).date()
            df_base_pred_r = df_base_pred_r[df_base_pred_r['Date'].dt.date >= f_date_r]
        except: pass

    df_base_pred_r = df_base_pred_r.sort_values('Date').head(1000)

    opciones_partidos_r = []
    for _, r in df_base_pred_r.iterrows():
        try:
            fecha_s = r['Date'].strftime("%d/%m")
            liga_s = str(r['League_CSV'])[:15]
            h = str(r['HomeTeam']).strip()
            a = str(r['AwayTeam']).strip()
            fid = str(r.get('fixture_id',''))
            opciones_partidos_r.append(f"{fecha_s} | {liga_s} | {h} vs {a} | {fid}")
        except: continue

    partidos_sel_r = []
    if not opciones_partidos_r:
        st.info("No hay partidos futuros RESTO con ese filtro")
    else:
        partidos_sel_r = st.multiselect("Elige partido futuro RESTO", opciones_partidos_r, key="partidos_pred_sel_resto", placeholder="Ej: Kashima vs Urawa - J1")

    partidos_pred_copy_r = []
    # FIX MANUALES AUNQUE NO HAYA FUTURO SELECCIONADO
    manuales_extra_r = []
    if 'equipos_manuales_1_r' in locals() and equipos_manuales_1_r: manuales_extra_r.extend(equipos_manuales_1_r)
    if 'equipos_manuales_2_r' in locals() and equipos_manuales_2_r: manuales_extra_r.extend(equipos_manuales_2_r)

    if not partidos_sel_r and not manuales_extra_r:
        st.caption("Selecciona partido futuro RESTO")
    else:
        partidos_pred_copy_r = []
        partidos_a_iterar_r = partidos_sel_r if partidos_sel_r else ["MANUAL_ONLY| | " + " vs ".join(manuales_extra_r[:2]) + " | 0"]

        for partido_str_r in partidos_a_iterar_r:
            try:
                partes_r = partido_str_r.split("|")
                teams_part_r = partes_r[2].strip() if len(partes_r)>=3 else ""
                if " vs " in teams_part_r:
                    h_fut_r, a_fut_r = [x.strip() for x in teams_part_r.split(" vs ")]
                else:
                    continue
            except: continue

            if "MANUAL_ONLY" in partido_str_r:
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 MANUAL RESTO: {', '.join(manuales_extra_r)}</div>", unsafe_allow_html=True)
                equipos_a_mostrar_r = manuales_extra_r
            else:
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 FUTURO RESTO: {h_fut_r} vs {a_fut_r} | {partes_r[0].strip()}</div>", unsafe_allow_html=True)
                equipos_a_mostrar_r = [h_fut_r, a_fut_r]
                if 'equipos_manuales_1_r' in locals() and equipos_manuales_1_r: equipos_a_mostrar_r.extend(equipos_manuales_1_r)
                if 'equipos_manuales_2_r' in locals() and equipos_manuales_2_r: equipos_a_mostrar_r.extend(equipos_manuales_2_r)

            for nombre_eq_r in equipos_a_mostrar_r:
                norm_eq_r = normaliza(nombre_eq_r)
                eq_up_r = nombre_eq_r.upper().strip()
                df_team_r = df_r[(df_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r) | (df_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r)]
                if df_team_r.empty:
                    df_team_r = df_r[(df_r['HomeTeam'].apply(lambda x: normaliza(x)==norm_eq_r)) | (df_r['AwayTeam'].apply(lambda x: normaliza(x)==norm_eq_r))]

                # --- FIX FILTRO LOCAL/VISITANTE RESPETA COND MANUAL 1/2 ---
                es_manual_1 = 'equipos_manuales_1_r' in locals() and nombre_eq_r in equipos_manuales_1_r
                es_manual_2 = 'equipos_manuales_2_r' in locals() and nombre_eq_r in equipos_manuales_2_r

                if es_manual_1:
                    if cond_manual_1_r == "solo local":
                        df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_manual_1_r == "solo visitante":
                        df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                elif es_manual_2:
                    if cond_manual_2_r == "solo local":
                        df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_manual_2_r == "solo visitante":
                        df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                else:
                    # equipos de futuro - respeta Filtro R
                    if cond_loc_pred_r == "equipo local solamente partidos de local":
                        df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_loc_pred_r == "equipo visitante solamente sus partidos de visitante":
                        df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_loc_pred_r == "Local en casa / Visitante fuera":
                        if nombre_eq_r == h_fut_r:
                            df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                        elif nombre_eq_r == a_fut_r:
                            df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]

                df_team_base_pred_r = df_team_r.copy()
                if resultados_pred_sel_r:
                    set_1p_r = set(); set_2p_r = set()
                    for s in resultados_pred_sel_r:
                        if "_1ªP" in s:
                            try: a,b = s.replace("_1ªP","").split("-"); set_1p_r.add((int(a),int(b)))
                            except: pass
                        if "_2ªP" in s:
                            try: a,b = s.replace("_2ªP","").split("-"); set_2p_r.add((int(a),int(b)))
                            except: pass
                    if set_1p_r or set_2p_r:
                        def _cumple_res_pred_r(rr):
                            try:
                                hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                                hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                            except: return False
                            if set_1p_r and (hthg_, htag_) in set_1p_r: return True
                            if set_2p_r and (hg_, ag_) in set_2p_r: return True
                            return False
                        df_team_r = df_team_r[df_team_r.apply(_cumple_res_pred_r, axis=1)]

                if overs_sel_r:
                    def _cumple_overs_pred_r(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        g1 = hthg_ + htag_
                        g2 = (hg_ + ag_) - g1
                        if g2 < 0: g2 = 0
                        for o in overs_sel_r:
                            if o == "1P >0.5" and not (g1 > 0.5): return False
                            if o == "1P >1.5" and not (g1 > 1.5): return False
                            if o == "1P >2.5" and not (g1 > 2.5): return False
                            if o == "2P >0.5" and not (g2 > 0.5): return False
                            if o == "2P >1.5" and not (g2 > 1.5): return False
                            if o == "2P >2.5" and not (g2 > 2.5): return False
                        return True
                    df_team_r = df_team_r[df_team_r.apply(_cumple_overs_pred_r, axis=1)]

                if res_1p_tipo_r!= "TODOS":
                    def _cumple_1p_tipo_r(rr):
                        try:
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        if norm_eq_r == hn_:
                            r_ = "GANA" if hthg_ > htag_ else "EMPATE" if hthg_ == htag_ else "PIERDE"
                        elif norm_eq_r == an_:
                            r_ = "GANA" if htag_ > hthg_ else "EMPATE" if htag_ == hthg_ else "PIERDE"
                        else:
                            return False
                        if res_1p_tipo_r == "EMPATE": return r_ == "EMPATE"
                        if res_1p_tipo_r == "GANA": return r_ == "GANA"
                        if res_1p_tipo_r == "PIERDE": return r_ == "PIERDE"
                        if res_1p_tipo_r == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                        if res_1p_tipo_r == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                        if res_1p_tipo_r == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        return True
                    df_team_r = df_team_r[df_team_r.apply(_cumple_1p_tipo_r, axis=1)]

                if df_team_r.empty:
                    st.caption(f"{nombre_eq_r} - sin historial en base RESTO")
                    continue

                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:2px 6px;margin:6px 0 2px 0;font-size:10px'>{nombre_eq_r.upper()}</div>", unsafe_allow_html=True)
                if 'Jornada' not in df_team_base_pred_r.columns:
                    df_team_base_pred_r['Jornada'] = 1
                if 'Jornada' not in df_team_r.columns:
                    df_team_r['Jornada'] = 1
                df_team_base_pred_r = df_team_base_pred_r.sort_values(['Jornada','Date'], ascending=[False, False])
                df_team_r = df_team_r.sort_values(['Jornada','Date'], ascending=[False, False]) if not df_team_r.empty else df_team_r
                jornadas_r = sorted(df_team_base_pred_r['Jornada'].dropna().unique(), reverse=True)[:15]
                for j in jornadas_r:
                    d_j_ok_r = df_team_r[df_team_r['Jornada']==j].sort_values('Date', ascending=False) if not df_team_r.empty and 'Jornada' in df_team_r.columns else pd.DataFrame()
                    if d_j_ok_r.empty:
                        st.markdown(f"<div style='font-family:monospace;font-weight:700;color:#aaa;margin:4px 0 0 0;font-size:10px'>J{int(j)}</div>", unsafe_allow_html=True)
                        continue
                    else:
                        st.markdown(f"<div style='font-family:monospace;font-weight:700;color:#0A2342;margin:4px 0 0 0;font-size:10px'>J{int(j)}</div>", unsafe_allow_html=True)
                    d_j_r = d_j_ok_r
                    html_lineas_r = ""
                    for _, r in d_j_r.iterrows():
                        fid = str(r.get('fixture_id','')).split('.')[0]
                        if MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None:
                            _tiene = False
                            for _ev in eventos_r.get(fid, []):
                                if 'Missed' in _ev.get('tipo',''): continue
                                _mm = _ev.get('m', -1)
                                if MIN_DESDE_PRED_R is not None and _mm < MIN_DESDE_PRED_R: continue
                                if MIN_HASTA_PRED_R is not None and _mm > MIN_HASTA_PRED_R: continue
                                _tiene = True
                                break
                            if not _tiene:
                                continue
                        h = str(r.get('HomeTeam','')).strip(); a = str(r.get('AwayTeam','')).strip()
                        try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                        except: hg=0; ag=0
                        h_norm_r = normaliza(h); a_norm_r = normaliza(a)
                        if norm_eq_r == h_norm_r: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#8B4513"
                        elif norm_eq_r == a_norm_r: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#8B4513"
                        else: col_main = "#000"
                        try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                        except: hthg=0; htag=0
                        ht_str = f"[{hthg}-{htag}]"
                        ht_html = f"<span style='color:#0A2342;font-weight:900;background:#E8E8E8;border-radius:3px;padding:0 4px;margin:0 3px'>{ht_str}</span>"
                        mins_1t = []; mins_2t = []
                        filtro_act = (MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None)
                        for ev in sorted(eventos_r.get(fid, []), key=lambda x: x['m']):
                            if 'Missed' in ev.get('tipo',''): continue
                            m = ev.get('m',-1); team_ev = ev['team']
                            es_mio = norm_eq_r in team_ev
                            col_min = col_main if es_mio else "#000"
                            peso = "font-weight:900;" if es_mio else "font-weight:700;"
                            en_rango = (MIN_DESDE_PRED_R is None or m >= MIN_DESDE_PRED_R) and (MIN_HASTA_PRED_R is None or m <= MIN_HASTA_PRED_R)
                            if filtro_act and en_rango:
                                span = f"<span style='color:{col_min};{peso};background:#D3D3D3;border-radius:3px;padding:1px 4px;margin-right:2px'> {m}'</span>"
                            else:
                                span = f"<span style='color:{col_min};{peso};margin-right:2px'> {m}'</span>"
                            if m <= 45: mins_1t.append(span)
                            else: mins_2t.append(span)
                        if mins_1t and mins_2t: mins_html = "".join(mins_1t) + ht_html + "<span style='color:#000;font-weight:900;margin:0 4px'>|</span>" + "".join(mins_2t)
                        elif mins_1t: mins_html = "".join(mins_1t) + ht_html
                        elif mins_2t: mins_html = ht_html + "<span style='color:#000;font-weight:900;margin:0 4px'>|</span>" + "".join(mins_2t)
                        else: mins_html = ht_html
                        def res_eq_pred(gf, gc): return "G" if gf>gc else "E" if gf==gc else "P"
                        if norm_eq_r == h_norm_r: r1 = res_eq_pred(hthg, htag); rF = res_eq_pred(hg, ag)
                        elif norm_eq_r == a_norm_r: r1 = res_eq_pred(htag, hthg); rF = res_eq_pred(ag, hg)
                        else: r1="E"; rF="E"
                        estado = f"{r1}/{rF}"
                        if norm_eq_r == h_norm_r:
                            h_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"; a_txt = a
                        elif norm_eq_r == a_norm_r:
                            h_txt = h; a_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
                        else:
                            h_txt = h; a_txt = a
                        html_lineas_r += f"<span style='color:{col_main};font-family:monospace;font-size:9px;font-weight:700;white-space:nowrap;margin-right:10px;line-height:1.1'>{h_txt} {hg}-{ag} {a_txt}{mins_html}<span style='color:#fff;background:{col_main};padding:0 4px;border-radius:2px;margin-left:5px'>{estado}</span></span>"
                        m1 = []; m2 = []
                        for evc in sorted(eventos_r.get(fid, []), key=lambda x: x['m']):
                            if MIN_DESDE_PRED_R is not None and evc.get('m',-1) < MIN_DESDE_PRED_R: continue
                            if MIN_HASTA_PRED_R is not None and evc.get('m',-1) > MIN_HASTA_PRED_R: continue
                            if 'Missed' in evc.get('tipo',''): continue
                            mm = evc.get('m',0)
                            if mm <= 45: m1.append(f"{mm}'")
                            else: m2.append(f"{mm}'")
                        if m1 and m2: mins_txt = " ".join(m1) + f"{ht_str} " + " ".join(m2)
                        elif m1: mins_txt = " ".join(m1) + f"{ht_str}"
                        elif m2: mins_txt = f"{ht_str} " + " ".join(m2)
                        else: mins_txt = f"{ht_str}"
                        partidos_pred_copy_r.append(f"J{int(j)}|{h} {hg}-{ag} {a} {mins_txt}{estado}")
                    st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas_r}</div>", unsafe_allow_html=True)

    if partidos_pred_copy_r:
        import html as _html
        texto_final_r = "\n".join(partidos_pred_copy_r[:200])
        safe_txt_r = _html.escape(texto_final_r)
        import streamlit.components.v1 as components
        components.html(f"""
        <textarea id="txt_pred_r" style="position:absolute;left:-9999px;top:-9999px;">{safe_txt_r}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_pred_r').value).then(()=>{{let b=document.getElementById('btn_pred_copy_r'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText=' COPIAR PREDICCION RESTO'; b.style.background='#0A2342'}},1200)}})"
        id="btn_pred_copy_r"
        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;">
         COPIAR PREDICCION RESTO ({len(partidos_sel_r)} partidos)
        </button>
        """, height=55, scrolling=False)

with st.expander("GOLES HT / GOLES 75-90", expanded=False):
    st.caption("Filtra equipos que en sus últimos 5 partidos, 3 cumplen y mínimo 2 seguidos")

    ligas_g = sorted(df['League'].dropna().unique().tolist()) if 'League' in df.columns else []
    c_liga_g, c_eq_g, c_cond_g, c_ht, c_7590 = st.columns([2,2,1,1,1])
    with c_liga_g:
        ligas_sel_g = st.multiselect("Ligas", ligas_g, default=[], key="ligas_g_ht", placeholder="Todas")
    df_base_g = df if not ligas_sel_g else df[df['League'].isin(ligas_sel_g)]

    # equipos de esas ligas
    if not df_base_g.empty:
        seen_g = {}
        for t in pd.concat([df_base_g['HomeTeam'], df_base_g['AwayTeam']]).dropna().astype(str):
            n = normaliza(t)
            if n not in seen_g:
                seen_g[n] = t.upper()
        equipos_g = sorted(seen_g.values())
    else:
        equipos_g = []

    with c_eq_g:
        equipos_sel_g = st.multiselect("Equipos", equipos_g, default=[], key="eq_g_ht", placeholder="Todos")
    with c_cond_g:
        cond_g_sel = st.selectbox("Condición", ["TODOS","LOCAL","VISITANTE"], index=0, key="cond_g_ht")
    with c_ht:
        goles_ht_sel = st.selectbox("GOLES HT 25-45", ["NO","SI"], index=0, key="goles_ht_25_45")
    with c_7590:
        goles_7590_sel = st.selectbox("GOLES 75-90", ["NO","SI"], index=0, key="goles_75_90")

    check_ht = (goles_ht_sel == "SI")
    check_75 = (goles_7590_sel == "SI")

    if not check_ht and not check_75:
        st.info("Activa SI en GOLES HT o en GOLES 75-90")
    else:
        def cumple_fixture(fid_str, need_ht, need_75, hthg=None, htag=None, hg=None, ag=None):
            has_ht = False
            has_75 = False
            # FALLBACK HT: si hay gol en 1ª parte [1-1] cuenta aunque no tenga minuto 25-45
            if need_ht and hthg is not None and htag is not None:
                if (hthg + htag) > 0:
                    has_ht = True
            # FALLBACK 75-90: si hay eventos los chequea, si no, mira si hubo gol en 2ª parte
            evs = eventos.get(str(fid_str).split('.')[0], [])
            for ev in evs:
                if 'Missed' in ev.get('tipo',''): continue
                m = ev.get('m', -1)
                if 25 <= m <= 45:
                    has_ht = True
                if 75 <= m <= 90:
                    has_75 = True
            if need_ht and need_75:
                # si no hay minuto 75-90 pero hay gol en 2ª parte y no hay eventos, lo aceptamos
                if not has_75 and not evs and hg is not None and hthg is not None:
                    if ((hg + ag) - (hthg + htag)) > 0:
                        has_75 = True
                return has_ht and has_75
            if need_ht:
                return has_ht
            if need_75:
                if not has_75 and not evs and hg is not None and hthg is not None:
                    if ((hg + ag) - (hthg + htag)) > 0:
                        has_75 = True
                return has_75
            return False

        # equipos a chequear
        if equipos_sel_g:
            equipos_a_check = equipos_sel_g
        else:
            equipos_a_check = equipos_g

        html_g = ""
        calificados_g = 0
        resumen_ligas_g = {}
        for team_g in equipos_a_check:
            n_team = normaliza(team_g)
            df_t = df_base_g[(df_base_g['HomeTeam'].apply(lambda x: normaliza(x)==n_team)) | (df_base_g['AwayTeam'].apply(lambda x: normaliza(x)==n_team))]
            if cond_g_sel == "LOCAL":
                df_t = df_t[df_t['HomeTeam'].apply(lambda x: normaliza(x)==n_team)]
            elif cond_g_sel == "VISITANTE":
                df_t = df_t[df_t['AwayTeam'].apply(lambda x: normaliza(x)==n_team)]
            if df_t.empty:
                continue
            df_t = df_t.sort_values('Date', ascending=False).head(5)
            if len(df_t) < 5:
                continue
            checks = []
            for _, r in df_t.iterrows():
                fid = str(r.get('fixture_id','')).split('.')[0]
                try: _hthg = int(float(r.get('HTHG',0) or 0)); _htag = int(float(r.get('HTAG',0) or 0))
                except: _hthg=0; _htag=0
                try: _hg = int(float(r.get('FTHG',0) or 0)); _ag = int(float(r.get('FTAG',0) or 0))
                except: _hg=0; _ag=0
                checks.append(cumple_fixture(fid, check_ht, check_75, _hthg, _htag, _hg, _ag))
            cnt = sum(checks)
            tiene_2_seg = any(checks[i] and checks[i+1] for i in range(len(checks)-1))
            if cnt >= 3 and tiene_2_seg:
                calificados_g += 1
                try:
                    liga_team_g = df_t['League'].mode().iloc[0] if 'League' in df_t.columns else "Liga"
                except:
                    liga_team_g = "Liga"
                if liga_team_g not in resumen_ligas_g:
                    resumen_ligas_g[liga_team_g] = []
                resumen_ligas_g[liga_team_g].append((team_g, cnt))
                html_g += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:10px 0 2px 0'>{team_g} | {cnt}/5 cumplen 25-45:{check_ht} 75-90:{check_75} | 2 seguidos: SI</div>"
                for idx, (_, r) in enumerate(df_t.iterrows()):
                    fid = str(r.get('fixture_id','')).split('.')[0]
                    ok = checks[idx]
                    col = "#0f8105" if ok else "#f31818"
                    label = "OK" if ok else "NO"
                    h = str(r.get('HomeTeam','')); a = str(r.get('AwayTeam',''))
                    try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                    except: hg=0; ag=0
                    try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                    except: hthg=0; htag=0
                    ht_txt = f"[{hthg}-{htag}]"
                    ht_html = f"<span style='background:#E8E8E8;color:#0A2342;font-weight:900;border-radius:3px;padding:0 4px;margin:0 3px'>{ht_txt}</span>"
                    # subraya equipo seleccionado
                    if normaliza(h) == normaliza(team_g):
                        h_show = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"
                        a_show = a
                    elif normaliza(a) == normaliza(team_g):
                        h_show = h
                        a_show = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
                    else:
                        h_show = h; a_show = a
                    mins_rel = []
                    for ev in eventos.get(fid, []):
                        m = ev.get('m',-1)
                        if 'Missed' in ev.get('tipo',''): continue
                        if (check_ht and 25 <= m <= 45) or (check_75 and 75 <= m <= 90):
                            mins_rel.append(f"<span style='background:#D3D3D3;border-radius:3px;padding:1px 4px;margin-right:2px;font-weight:900'>{m}'</span>")
                    mins_txt = "".join(mins_rel) if mins_rel else "-"
                    html_g += f"<div style='font-family:monospace;font-size:11px;padding:3px 4px;border-bottom:1px solid #ddd;color:{col}'>{'✔' if ok else '✘'} [{label}] {h_show} {hg}-{ag} {a_show} | {ht_html} Goles filtro: {mins_txt} | {pd.to_datetime(r.get('Date')).strftime('%d/%m/%Y') if pd.notna(r.get('Date')) else ''}</div>"

        # --- LISTADO RESUMEN POR LIGA ---
        html_listado_g = "<div style='font-family:monospace;background:#fff;color:#000;padding:8px;border-radius:6px;margin:6px 0;font-size:11px;border:1px solid #000'>"
        for liga_name in sorted(resumen_ligas_g.keys()):
            html_listado_g += f"<div style='font-weight:900;margin-top:6px;color:#000;text-decoration:underline'>{liga_name}:</div>"
            lineas = []
            for team_r, cnt_r in sorted(resumen_ligas_g[liga_name], key=lambda x: x[1], reverse=True):
                lineas.append(f"{team_r} ({cnt_r} veces)")
            html_listado_g += f"<div style='margin-left:10px;color:#000'>{' - '.join(lineas)}</div>"
        html_listado_g += "</div>"

        if calificados_g == 0:
            st.info(f"Ningún equipo cumple 3/5 con 2 seguidos (25-45={check_ht} 75-90={check_75})")
        else:
            import streamlit.components.v1 as components
            bloque = f"""
            <style>
            html, body {{
                overscroll-behavior: auto!important;
                touch-action: pan-y!important;
                -webkit-overflow-scrolling: touch!important;
                overflow-y: auto!important;
            }}
            div, button {{
                touch-action: pan-y!important;
            }}
            </style>
            <div style="touch-action: pan-y; -webkit-overflow-scrolling: touch;">
                <button onclick="navigator.clipboard.writeText(document.getElementById('targetG').innerText).then(()=>{{let b=document.getElementById('btnG_top'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText='📋 COPIAR GOLES HT 75-90 ({calificados_g})'; b.style.background='#0A2342'}},1200)}})" id='btnG_top' style='width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px'>📋 COPIAR GOLES HT 75-90 ({calificados_g})</button>
                <div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:6px;margin-bottom:6px'>EQUIPOS QUE CUMPLEN: {calificados_g}</div>
                <div id='targetG' style="touch-action: pan-y;">{html_listado_g}{html_g}</div>
                <button onclick="navigator.clipboard.writeText(document.getElementById('targetG').innerText).then(()=>{{let b=document.getElementById('btnG'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText='📋 COPIAR GOLES HT 75-90 ({calificados_g})'; b.style.background='#0A2342'}},1200)}})" id='btnG' style='width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;margin-top:8px'>📋 COPIAR GOLES HT 75-90 ({calificados_g})</button>
            </div>
            """
            h_g = min(5000, max(800, (len(html_g)+len(html_listado_g))//10))
            components.html(bloque, height=h_g, scrolling=False)
