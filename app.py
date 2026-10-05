import streamlit as st
import pandas as pd
import pathlib
import re
import unicodedata
import numpy as np
import matplotlib.pyplot as plt
import io, base64

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
window.addEventListener('scroll', function() {
    const btn = document.getElementById('btn-top-float');
    if (btn) btn.style.display = window.scrollY > 400? 'block' : 'none';
});
</script>
""", unsafe_allow_html=True)
# --- UTILS ---
def normaliza(s):
    if pd.isna(s): return ""
    n = unicodedata.normalize('NFKD', str(s)).encode('ASCII','ignore').decode('ASCII')
    return n.upper().strip()

def normaliza_fuzzy(s):
    n = normaliza(s)
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'\bII\b|\bAM\b|\bRESERVAS\b|\bB\b', '', n)
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
    modo_stats = st.selectbox("Detalle stats", ["OFF","ON"], key="modo_stats")

c9,c_min1,c_min2 = filtros.columns([1,1,1])
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

            if hy is not None or ay is not None:
                extra += f" <span style='color:#b8860b'>Amarillas Local {hy if hy is not None else '-'} - Visitante {ay if ay is not None else '-'}</span><br>"
            if hr is not None or ar is not None:
                extra += f" <span style='color:#FF0000'>Rojas Local {hr if hr is not None else '-'} - Visitante {ar if ar is not None else '-'}</span><br>"
            if hc is not None or ac is not None:
                extra += f" <span style='color:#1E90FF'>Corners Local {hc if hc is not None else '-'} - Visitante {ac if ac is not None else '-'}</span><br>"
            if hst is not None or ast is not None:
                extra += f" <span style='color:#0066cc'>Tiros Puerta Local {hst if hst is not None else '-'} - Visitante {ast if ast is not None else '-'}</span><br>"
            if hs is not None or _as is not None:
                extra += f" <span style='color:#004080'>Tiros Totales Local {hs if hs is not None else '-'} - Visitante {_as if _as is not None else '-'}</span><br>"
            if hf is not None or af is not None:
                extra += f" <span style='color:#666'>Faltas Local {hf if hf is not None else '-'} - Visitante {af if af is not None else '-'}</span><br>"
            if hsv is not None or asv is not None:
                extra += f" <span style='color:#008080'>Paradas Local {hsv if hsv is not None else '-'} - Visitante {asv if asv is not None else '-'}</span><br>"
            if hp is not None or ap is not None:
                extra += f" <span style='color:#2E8B57'>Pases Local {hp if hp is not None else '-'} - Visitante {ap if ap is not None else '-'}</span><br>"
            if hpos is not None or apos is not None:
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
    return f"<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #333;line-height:1.2;max-width:380px;margin:0 auto'><div style='text-align:left;color:{col_j};font-weight:900'>|Jornada {j}| {h} vs {a}</div><div style='text-align:center;font-weight:900;word-break:break-word'>{extra}</div><div style='text-align:center;font-weight:900;margin-top:4px'><span style='background:#0A2342;color:#fff;padding:2px 10px;border-radius:3px'>Final {hg}-{ag}</span></div><div style='text-align:center;color:#666;font-weight:700;font-size:10px;margin-top:2px'>[1ª parte {hthg}-{htag}]</div><div style='color:#000;white-space:normal;word-break:break-word;line-height:1.1;margin-top:3px'>{txt_mins}</div>{mom_html}</div>"

eq_refs_orig = [e for e in [eq1, eq2] if e!= "Ninguno"]
eq_refs_norm = [normaliza(e) for e in eq_refs_orig]

html = ""

if not st.session_state.show_partidos:
    st.info("👁 Partidos ocultos - dale a Mostrar partidos. Usa el botón ↑ flotante abajo a la derecha para subir.")

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
            t_norm = normaliza(team)
            for _, rr in d_team_valid.iterrows():
                if cumple(rr.to_dict(), t_norm):
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
            d_team_cumple = d_team_full[d_team_full.apply(lambda rr: cumple(rr.to_dict(), normaliza(team)), axis=1)]
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
        import streamlit.components.v1 as components
        bloque_copy = f"""
        <div>
            <button onclick="copyPartidos()" id="btnCopyPartidos" style="position:sticky;top:0;z-index:99999;width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px;">📋 COPIAR PARTIDOS</button>
            <div id="targetPartidos">{html}</div>
        </div>
        <script>
        function copyPartidos(){{
            var txt = document.getElementById('targetPartidos').innerText;
            navigator.clipboard.writeText(txt).then(()=>{{
                var b = document.getElementById('btnCopyPartidos');
                b.innerText = '✓ COPIADO';
                b.style.background = '#0f8105';
                setTimeout(()=>{{ b.innerText='📋 COPIAR PARTIDOS'; b.style.background='#0A2342'; }},1200);
            }});
        }}
        </script>
        """
        components.html(bloque_copy, height=900, scrolling=True)
    else:
        st.info("Selecciona equipo")

st.caption(f"Base: {BASE} | Registros: {len(df)} | Goles: {len(eventos)} | Momentum: {len(momentum_by_id)} partidos | Filtro: {filtro_tipo} {filtro_pct}%")

if st.button("Ocultar partidos 2" if st.session_state.show_partidos else "Mostrar partidos 2", key="toggle_partidos_2", use_container_width=True):
    st.session_state.show_partidos = not st.session_state.show_partidos
    st.rerun()
##########################################
##########################################
with st.expander("momentum JSON - copiar para IA", expanded=False):
    st.markdown('<div id="mom-only"></div>', unsafe_allow_html=True)
    try:
        import json as _json
        import html as _html
        import streamlit.components.v1 as components

        all_recs = []
        for recs in momentum_by_id.values():
            if recs:
                all_recs.extend(recs)

        def safe_str(v):
            if v is None: return ""
            try:
                if pd.isna(v): return ""
            except: pass
            s = str(v).strip()
            if s.lower() == "nan": return ""
            return s

        comps_mom = sorted(set([safe_str(r.get('competition')) for r in all_recs if safe_str(r.get('competition'))]))
        if not comps_mom:
            comps_mom = sorted([safe_str(x) for x in df['League'].dropna().unique().tolist()]) if 'League' in df.columns else []
        c1_m, c2_m = st.columns(2)
        with c1_m:
            comp_sels = st.multiselect("Competicion momentum", comps_mom, default=[], key="comp_mom_json", placeholder="Todas")

        # --- PRECACHE para no recalcular fuzzy 1000 veces ---
        if 'fuzzy_cache' not in st.session_state:
            st.session_state.fuzzy_cache = {}
        def fast_fuzzy(s):
            if s not in st.session_state.fuzzy_cache:
                st.session_state.fuzzy_cache[s] = normaliza_fuzzy(s)
            return st.session_state.fuzzy_cache[s]

        equipos_mom_set = set()
        if not comp_sels:
            for rec in all_recs:
                h = safe_str(rec.get('home')); a = safe_str(rec.get('away'))
                if h: equipos_mom_set.add(h)
                if a: equipos_mom_set.add(a)
        else:
            comp_set = set(comp_sels)
            for rec in all_recs:
                if safe_str(rec.get('competition')) not in comp_set:
                    continue
                h = safe_str(rec.get('home')); a = safe_str(rec.get('away'))
                if h: equipos_mom_set.add(h)
                if a: equipos_mom_set.add(a)
        equipos_mom = sorted(equipos_mom_set)
        with c2_m:
            eq_sels_mom = st.multiselect("Equipo momentum", equipos_mom, default=[], key="eq_mom_json", placeholder="Todos")

        # FILTRO ULTRA RAPIDO - sin to_datetime, sin fuzzy repetido
        fixtures_filtrados = []
        eq_fuzzy_set = set(fast_fuzzy(x) for x in eq_sels_mom) if eq_sels_mom else set()
        eq_raw_set = set(eq_sels_mom) if eq_sels_mom else set()
        comp_set2 = set(comp_sels) if comp_sels else None

        for fid, recs in momentum_by_id.items():
            if not recs: continue
            r0 = recs[0]
            c0 = safe_str(r0.get('competition'))
            if comp_set2 and c0 not in comp_set2:
                continue
            h = safe_str(r0.get('home')); a = safe_str(r0.get('away'))
            if eq_raw_set:
                if h not in eq_raw_set and a not in eq_raw_set:
                    if fast_fuzzy(h) not in eq_fuzzy_set and fast_fuzzy(a) not in eq_fuzzy_set:
                        continue
            label = f"{h} VS {a} - {fid} - {c0}"
            fixtures_filtrados.append((fid, label, r0, h, a, c0, recs))

        fixtures_filtrados = sorted(fixtures_filtrados, key=lambda x: x[1], reverse=True)[:100]

        if not fixtures_filtrados:
            st.info("No hay momentum para ese filtro")
        else:
            if 'selected_moms' not in st.session_state:
                st.session_state.selected_moms = set()

            st.markdown(f"<div style='font-family:monospace;font-size:11px;font-weight:900;margin:6px 0'>{len(fixtures_filtrados)} partidos | Seleccionados: {len(st.session_state.selected_moms)}</div>", unsafe_allow_html=True)

            col_all1, col_all2, col_all3 = st.columns(3)
            with col_all1:
                if st.button(" Todo", key="sel_all_mom_v2", use_container_width=True):
                    for fid,_,_,_,_,_,_ in fixtures_filtrados:
                        fid_s = str(fid)
                        st.session_state.selected_moms.add(fid_s)
                        st.session_state[f"chk_{fid_s}"] = True
                    st.rerun()
            with col_all2:
                if st.button(" Limpiar", key="clear_all_mom_v2", use_container_width=True):
                    st.session_state.selected_moms = set()
                    for fid,_,_,_,_,_,_ in fixtures_filtrados:
                        st.session_state[f"chk_{str(fid)}"] = False
                    if 'big_copy_text' in st.session_state:
                        del st.session_state.big_copy_text
                    if 'big_copy_text_wa' in st.session_state:
                        del st.session_state.big_copy_text_wa
                    st.rerun()
            with col_all3:
                if st.button(f" JSON {len(st.session_state.selected_moms)}", type="primary", key="copy_sel_mom_v2", use_container_width=True):
                    combined = []
                    for fid, _, r0, h0, a0, comp0, recs_show in fixtures_filtrados:
                        if str(fid) not in st.session_state.selected_moms:
                            continue
                        recs_show = sorted(recs_show, key=lambda x: int(x.get('minute',0)))
                        vals = [round(float(x.get('momentumValue',0)),3) for x in recs_show]
                        json_out = {
                            "match": f"{h0} vs {a0}",
                            "id": str(fid),
                            "home": h0,
                            "away": a0,
                            "competition": comp0,
                            "legend": f"+ = {h0} (home) dominates, - = {a0} (away) dominates, value -1 to 1, index = minute 0-{len(vals)-1}",
                            "momentum": vals,
                            "count": len(vals)
                        }
                        combined.append(_json.dumps(json_out, separators=(',',':'), ensure_ascii=False))
                    if combined:
                        st.session_state.big_copy_text = "\n\n".join(combined)
                        st.rerun()

            if 'big_copy_text_wa' in st.session_state and st.session_state.big_copy_text_wa:
                txt_esc_wa = _html.escape(st.session_state.big_copy_text_wa)
                html_big_wa = f"""
                <div>
                    <textarea id="big_txt_wa" style="width:100%;height:200px;font-family:monospace;font-size:11px;">{txt_esc_wa}</textarea>
                    <button onclick="navigator.clipboard.writeText(document.getElementById('big_txt_wa').value).then(()=>{{document.getElementById('msg_big_wa').innerText='✓ COPIADO WA '+document.getElementById('big_txt_wa').value.length+' chars';}})"
                            style="width:100%;background:#0f8105;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;margin-top:6px;">📱 COPIAR FORMATO WHATSAPP ({len(st.session_state.big_copy_text_wa)} chars = {len(st.session_state.selected_moms)} partidos)</button>
                    <div id="msg_big_wa" style="font-family:monospace;font-weight:900;color:#0f8105;margin-top:4px;">9 partidos por mensaje WA (4.096 limite) / 156 (65k)</div>
                </div>
                """
                components.html(html_big_wa, height=280, scrolling=True)

            if 'big_copy_text' in st.session_state and st.session_state.big_copy_text:
                txt_esc = _html.escape(st.session_state.big_copy_text)
                html_big = f"""
                <div>
                    <textarea id="big_txt" style="width:100%;height:200px;font-family:monospace;font-size:11px;">{txt_esc}</textarea>
                    <button onclick="navigator.clipboard.writeText(document.getElementById('big_txt').value).then(()=>{{document.getElementById('msg_big').innerText='✓ COPIADO '+document.getElementById('big_txt').value.length+' chars';}})"
                            style="width:100%;background:#0f8105;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;margin-top:6px;">📋 COPIAR TODO ({len(st.session_state.big_copy_text)} chars)</button>
                    <div id="msg_big" style="font-family:monospace;font-weight:900;color:#0f8105;margin-top:4px;"></div>
                </div>
                """
                components.html(html_big, height=280, scrolling=True)

            st.markdown("---")
            for fid, label, r0, h0, a0, comp0, recs_show in fixtures_filtrados:
                fid_str = str(fid)
                checked = fid_str in st.session_state.selected_moms
                col_chk, col_lab, col_btn = st.columns([0.6, 3.5, 1])
                with col_chk:
                    new_val = st.checkbox("", value=checked, key=f"chk_{fid_str}")
                    if new_val!= checked:
                        if new_val:
                            st.session_state.selected_moms.add(fid_str)
                        else:
                            st.session_state.selected_moms.discard(fid_str)
                        st.rerun()
                with col_lab:
                    st.markdown(f"<div style='font-family:monospace;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'><b>{_html.escape(label)}</b><br><span style='font-size:10px;color:#666'>{h0} vs {a0} - {len(recs_show)} pts</span></div>", unsafe_allow_html=True)
                with col_btn:
                    recs_s = sorted(recs_show, key=lambda x: int(x.get('minute',0)))
                    vals = [round(float(x.get('momentumValue',0)),3) for x in recs_s]
                    json_out = {"match": f"{h0} vs {a0}","id": str(fid),"home": h0,"away": a0,"competition": comp0,"legend": f"+ = {h0} (home) dominates, - = {a0} (away) dominates, value -1 to 1, index = minute 0-{len(vals)-1}","momentum": vals,"count": len(vals)}
                    j_str = _json.dumps(json_out, separators=(',',':'), ensure_ascii=False)
                    html_one = f"""<textarea id="txt_{fid_str}" style="position:absolute;left:-9999px">{_html.escape(j_str)}</textarea><button onclick="navigator.clipboard.writeText(document.getElementById('txt_{fid_str}').value).then(()=>{{let b=document.getElementById('btn_{fid_str}'); b.innerText='✓'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText='COPIAR'; b.style.background='#0A2342';}},1000);}})" id="btn_{fid_str}" style="background:#0A2342;color:white;border:none;border-radius:4px;padding:4px 6px;font-weight:900;font-size:9px;cursor:pointer;width:100%">COPIAR</button>"""
                    components.html(html_one, height=35, scrolling=False)

    except Exception as e:
        st.error(f"Error momentum JSON: {e}")
#########################################
with st.expander("JORNADAS FIX - vista rapida", expanded=False):
    # --- PERSISTENCIA REAL 8 HORAS (URL) ---
    if "ligas_fix" not in st.session_state:
        st.session_state.ligas_fix = st.query_params.get_all("ligas_fix")
    if "equipos_fix" not in st.session_state:
        st.session_state.equipos_fix = st.query_params.get_all("equipos_fix")
    if "min_desde_fix" not in st.session_state:
        st.session_state.min_desde_fix = st.query_params.get("min_desde_fix", "")
    if "min_hasta_fix" not in st.session_state:
        st.session_state.min_hasta_fix = st.query_params.get("min_hasta_fix", "")

    if st.button("🧹 Limpiar FIX", key="btn_limpiar_fix", use_container_width=True):
        for k in ["ligas_fix","equipos_fix","min_desde_fix","min_hasta_fix"]:
            if k in st.session_state:
                del st.session_state[k]
        for k in ["ligas_fix","equipos_fix","min_desde_fix","min_hasta_fix"]:
            if k in st.query_params:
                del st.query_params[k]
        st.rerun()

    c_liga_fix, c_eq_fix = st.columns(2)
    with c_liga_fix:
        ligas_fix_sel = st.multiselect("Ligas FIX", ligas, default=st.session_state.ligas_fix, key="ligas_fix", placeholder="Todas")
        st.query_params["ligas_fix"] = ligas_fix_sel
    # base segun ligas seleccionadas
    if ligas_fix_sel:
        df_base_fix = df[df['League'].isin(ligas_fix_sel)]
    else:
        df_base_fix = df

    # lista equipos dedup igual que tu filtro original
    seen_fix = {}
    for t in pd.concat([df_base_fix['HomeTeam'], df_base_fix['AwayTeam']]).dropna().astype(str):
        n = normaliza(t)
        if n not in seen_fix:
            seen_fix[n] = t.upper()
    equipos_fix_lista = sorted(seen_fix.values())

    with c_eq_fix:
        equipos_fix_sel = st.multiselect("Equipos FIX", equipos_fix_lista, default=st.session_state.equipos_fix, key="equipos_fix", placeholder="Elige 1 o mas")
        st.query_params["equipos_fix"] = equipos_fix_sel
        st.query_params["min_desde_fix"] = st.session_state.min_desde_fix
        st.query_params["min_hasta_fix"] = st.session_state.min_hasta_fix

    c_min_fix1, c_min_fix2 = st.columns(2)
    with c_min_fix1:
        min_desde_fix_raw = st.text_input("MIN DESDE FIX", key="min_desde_fix", placeholder="-")
    with c_min_fix2:
        min_hasta_fix_raw = st.text_input("MIN HASTA FIX", key="min_hasta_fix", placeholder="-")

    def _parse_min_fix(v):
        try:
            if v is None or str(v).strip() in ["", "-", "–", "—"]:
                return None
            return int(str(v).strip().replace("'", ""))
        except:
            return None
    MIN_DESDE_FIX = _parse_min_fix(min_desde_fix_raw)
    MIN_HASTA_FIX = _parse_min_fix(min_hasta_fix_raw)

    partidos_fix_copy = []

    if not equipos_fix_sel:
        st.info("Selecciona al menos 1 liga y 1 equipo en FIX")
    else:
        for nombre_eq in equipos_fix_sel:
            norm_eq = normaliza(nombre_eq)
            df_team = df_base_fix[(df_base_fix['HomeTeam'].apply(lambda x: normaliza(x)==norm_eq)) | (df_base_fix['AwayTeam'].apply(lambda x: normaliza(x)==norm_eq))]
            if df_team.empty:
                continue
            st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:2px 6px;margin:6px 0 2px 0;font-size:10px;line-height:1.1'>{nombre_eq.upper()}</div>", unsafe_allow_html=True)
            jornadas = sorted(df_team['Jornada'].dropna().unique(), reverse=True)[:15]
            for j in jornadas:
                st.markdown(f"<div style='font-family:monospace;font-weight:700;color:#0A2342;margin:4px 0 0 0;font-size:10px;line-height:1.1'>J{int(j)}</div>", unsafe_allow_html=True)
                d_j = df_team[df_team['Jornada']==j].sort_values('Date', ascending=False)
                html_lineas = ""
                for _, r in d_j.iterrows():
                    fid = str(r.get('fixture_id','')).split('.')[0]
                    # FILTRO MIN FIX independiente - solo partidos con gol en ese tramo
                    if MIN_DESDE_FIX is not None or MIN_HASTA_FIX is not None:
                        _tiene = False
                        for _ev in eventos.get(fid, []):
                            if 'Missed' in _ev.get('tipo',''): continue
                            _mm = _ev.get('m', -1)
                            if MIN_DESDE_FIX is not None and _mm < MIN_DESDE_FIX: continue
                            if MIN_HASTA_FIX is not None and _mm > MIN_HASTA_FIX: continue
                            _tiene = True
                            break
                        if not _tiene:
                            continue
                    h = str(r.get('HomeTeam','')).strip(); a = str(r.get('AwayTeam','')).strip()
                    try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                    except: hg=0; ag=0
                    hn = normaliza(h); an = normaliza(a)
                    if norm_eq == hn: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#8B4513"
                    elif norm_eq == an: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#8B4513"
                    else: col_main = "#000"
                    mins_1t = []; mins_2t = []
                    for ev in sorted(eventos.get(fid, []), key=lambda x: x['m']):
                        if MIN_DESDE_FIX is not None and ev.get('m',-1) < MIN_DESDE_FIX: continue
                        if MIN_HASTA_FIX is not None and ev.get('m',-1) > MIN_HASTA_FIX: continue
                        if 'Missed' in ev.get('tipo',''): continue
                        m = ev['m']; team_ev = ev['team']; tipo = ev.get('tipo','')
                        benef = an if 'Own Goal' in tipo and team_ev == hn else hn if 'Own Goal' in tipo else team_ev
                        es_mio = norm_eq in benef
                        col_min = col_main if es_mio else "#000"
                        peso = "font-weight:900;" if es_mio else "font-weight:700;"
                        span = f"<span style='color:{col_min};{peso}'> {m}'</span>"
                        if m <= 45: mins_1t.append(span)
                        else: mins_2t.append(span)
                    if mins_1t and mins_2t: mins_html = "".join(mins_1t) + "<span style='color:#000;font-weight:900;margin:0 4px'>|</span>" + "".join(mins_2t)
                    else: mins_html = "".join(mins_1t + mins_2t)
                    try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                    except: hthg=0; htag=0
                    def res_eq(gf, gc):
                        if gf > gc: return "G"
                        if gf == gc: return "E"
                        return "P"
                    if norm_eq == hn: r1 = res_eq(hthg, htag); rF = res_eq(hg, ag)
                    elif norm_eq == an: r1 = res_eq(htag, hthg); rF = res_eq(ag, hg)
                    else: r1="E"; rF="E"
                    estado_1p_final = f"{r1}/{rF}"
                    # --- SUBRAYA EQUIPO SELECCIONADO ---
                    if norm_eq == hn:
                        h_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"
                        a_txt = a
                    elif norm_eq == an:
                        h_txt = h
                        a_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
                    else:
                        h_txt = h
                        a_txt = a
                    html_lineas += f"<span style='color:{col_main};font-family:monospace;font-size:9px;font-weight:700;white-space:nowrap;margin-right:10px;line-height:1.1'>{h_txt} {hg}-{ag} {a_txt}{mins_html}<span style='color:#fff;background:{col_main};padding:0 4px;border-radius:2px;margin-left:5px'>{estado_1p_final}</span></span>"
                    # --- PARA COPIAR LIMPIO SIN HTML ---
                    m1 = []; m2 = []
                    for evc in sorted(eventos.get(fid, []), key=lambda x: x['m']):
                        if MIN_DESDE_FIX is not None and evc.get('m',-1) < MIN_DESDE_FIX: continue
                        if MIN_HASTA_FIX is not None and evc.get('m',-1) > MIN_HASTA_FIX: continue
                        if 'Missed' in evc.get('tipo',''): continue
                        mm = evc.get('m',0)
                        if mm <= 45: m1.append(f"{mm}'")
                        else: m2.append(f"{mm}'")
                    if m1 and m2: mins_txt = " ".join(m1) + "| " + " ".join(m2)
                    else: mins_txt = " ".join(m1 + m2)
                    partidos_fix_copy.append(f"J{int(j)}|{h} {hg}-{ag} {a} {mins_txt}{estado_1p_final}")

                st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas}</div>", unsafe_allow_html=True)

        # --- BOTON COPIAR FIX - SOLO BOTON ---
        if partidos_fix_copy:
            import html as _html
            lineas_final = []
            for eq in equipos_fix_sel:
                lineas_final.append(f"{eq}")
            last_j = ""
            for item in partidos_fix_copy:
                if "|" not in item: continue
                j_part, resto = item.split("|",1)
                if j_part != last_j:
                    lineas_final.append(j_part)
                    last_j = j_part
                lineas_final.append(resto.strip())
            texto_final = "\n".join(lineas_final)
            safe_txt = _html.escape(texto_final)
            import streamlit.components.v1 as components
            components.html(f"""
            <textarea id="txt_fix" style="position:absolute;left:-9999px;top:-9999px;">{safe_txt}</textarea>
            <button onclick="navigator.clipboard.writeText(document.getElementById('txt_fix').value).then(()=>{{let b=document.getElementById('btn_fix_copy'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText='📋 COPIAR FIX'; b.style.background='#0A2342'}},1200)}})"
            id="btn_fix_copy"
            style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;">
             COPIAR FIX
            </button>
            """, height=55, scrolling=False)
            # --- DESPLEGABLE INDEPENDIENTE MOMENTUM/ESTADISTICAS ---

##########################################
# BLOQUE INDEPENDIENTE - MOMENTUM / ESTADISTICAS PARA IA - SIN ERROR 400
##########################################
# BLOQUE V6 - FINAL SIMPLE - PEGA URL Y GENERA - COPIA REAL
##########################################
with st.expander("MOMENTUM LIVE - PEGAR URL Y COPIAR", expanded=False):
    import requests, re, json, html
    import streamlit.components.v1 as components

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

    def get_momentum_from_url(url):
        url = url.strip()
        eid = None
        home = "local"
        away = "visitante"
        mt = re.search(r'/partido/futbol/([^/]+)/([^/]+)/', url)
        if mt:
            def clean(s):
                s = re.sub(r'-[A-Za-z0-9]{6,8}$','',s)
                return s.replace('-',' ').title().strip()
            away = clean(mt.group(1))
            home = clean(mt.group(2))
        m_mid = re.search(r'[?&]mid=([A-Za-z0-9]{6,12})', url, re.I)
        if m_mid:
            eid = m_mid.group(1)
        else:
            m = re.search(r'/partido/futbol/[^/]+/([A-Za-z0-9]{8,12})/', url)
            if m:
                eid = m.group(1)
        if not eid:
            return None, "No encuentro ?mid= en la URL. Pega la URL completa: ...?mid=ML4DjdZa"
        try:
            import time as _tt
            api = f"https://13.ds.lsapp.eu/pq_graphql?_hash=mmts&eventId={eid}&providerId=7&_t={int(_tt.time())}"
            r = requests.get(api, headers={"User-Agent": UA, "Referer":"https://www.flashscore.es/", "Cache-Control":"no-cache", "Pragma":"no-cache"}, timeout=12)
            if r.status_code!=200:
                return None, f"Error {r.status_code} - Flashscore bloquea Streamlit Cloud. Ejecuta la app en local y si funcionara"
            data = r.json()
            entries = data.get("data",{}).get("findMatchMomentumStatsByMatchId",{}).get("momentum",{}).get("entries",[])
            if not entries:
                return None, "Sin momentum aun - partido no empezado"
            vals = [round(float(e.get("momentumValue",0)),3) for e in entries]
            return {"eid":eid, "vals":vals, "home":home, "away":away}, None
        except Exception as e:
            return None, str(e)

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
