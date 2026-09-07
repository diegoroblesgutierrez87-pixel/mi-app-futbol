import streamlit as st
import pandas as pd
import pathlib
import re
import unicodedata
import numpy as np

st.set_page_config(page_title="Lite Rapido + Local", layout="wide")

# --- UTILS ---
def normaliza(s):
    if pd.isna(s): return ""
    n = unicodedata.normalize('NFKD', str(s)).encode('ASCII','ignore').decode('ASCII')
    return n.upper().strip()

def abreviar_equipo(nombre):
    n = normaliza(nombre)
    if not n or n == "NAN": return "XXX"
    if 'ATLETICO' in n: return 'ATM'
    if 'BILBAO' in n or 'ATHLETIC' in n: return 'ATH'
    for pref in ['FC ','REAL ','CLUB ','DEPORTIVO ','CLUB ATLETICO ']:
        if n.startswith(pref):
            n = n[len(pref):].strip()
            break
    return (n.split()[0][:3] if n.split() else "XXX").upper()

def get_base():
    for p in [pathlib.Path("/mnt/data"), pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
        if (p / "europa_actual.csv").exists():
            return p
    return pathlib.Path("/mnt/data")

BASE = get_base()

@st.cache_data(show_spinner=False)
def cargar_todo_lite():
    files = ["europa_actual.csv","din1_suec1_26_27.csv","asia_actual_j1j2k1k2csl1.csv","arabia_actual.csv","sudamerica_actual.csv"]
    dfs=[]
    for fn in files:
        f = BASE / fn
        if f.exists() and f.stat().st_size > 100:
            d = pd.read_csv(f, on_bad_lines='skip', engine='c', low_memory=False)
            if 'Date' in d.columns:
                d['Date'] = pd.to_datetime(d['Date'], dayfirst=True, errors='coerce')
            dfs.append(d)
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
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
    files = ["goles_actual.csv","goles_arabia_actual.csv","goles_sudamerica_actual.csv"]
    ev = {}
    for fn in files:
        f = BASE / fn
        if not f.exists(): continue
        try:
            dg = pd.read_csv(f, dtype=str, on_bad_lines='skip', engine='python')
            for fid, g in dg.groupby('fixture_id'):
                fid_c = str(fid).split('.')[0]
                lista = []
                for _, r in g.iterrows():
                    try:
                        m = int(float(str(r.get('minuto','0')).split('+')[0] or 0))
                        team = normaliza(r.get('equipo',''))
                        if not team: continue
                        lista.append({"m": m, "team": team})
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
c1,c2,c3 = st.columns(3)
with c1: liga_sel = st.selectbox("Liga", ["Todas"] + ligas)
df_f = df if liga_sel == "Todas" else df[df['League'] == liga_sel]

# Equipo lista más rápida
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
c6,c7 = st.columns(2)
with c6:
    filtro_tipo = st.selectbox("Filtro %", ["Ninguno","Ambos SI","Ambos NO","Over 2.5","Under 2.5"], key="filtro_tipo")
with c7:
    filtro_pct = st.slider("% mínimo", 0, 100, 60, 5, key="filtro_pct")

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
    hab = str(r.get('HomeAbbr', abreviar_equipo(h)))[:3].upper()
    aab = str(r.get('AwayAbbr', abreviar_equipo(a)))[:3].upper()
    try: hg = int(float(r.get('FTHG',0) or 0)); ag = int(float(r.get('FTAG',0) or 0))
    except: hg = 0; ag = 0

    col = "#0A2342"
    if eq_refs_norm:
        hn = normaliza(h); an = normaliza(a)
        for ern in eq_refs_norm:
            if ern == hn and hg > ag: col = "#0f8105"
            if ern == an and ag > hg: col = "#0f8105"
            if ern == hn and hg < ag: col = "#f31818"
            if ern == an and ag < hg: col = "#f31818"

    mins_html = []
    try:
        fid = str(r.get('fixture_id','')).split('.')[0]
        for ev in eventos.get(fid, []):
            m = ev['m']; team = ev['team']
            es_mio = any(ern in team or team in ern for ern in eq_refs_norm) if eq_refs_norm else False
            if es_mio:
                mins_html.append(f"<span style='color:#8A2BE2;font-weight:900'>{m}'</span>")
            else:
                mins_html.append(f"<span style='color:#000'>{m}'</span>")
    except: pass

    if not mins_html:
        ms = re.findall(r"(\d+)'", str(r.get('Goles_Todo_HTML','') or ''))
        mins_html = [f"<span style='color:#000'>{x}'</span>" for x in ms]

    txt_mins = " ".join(mins_html) if mins_html else "-"

    # FIX L/V - ahora sí usa el equipo del bloque
    loc_tag = ""
    if current_eq_orig:
        if r.get('HomeTeam','') == current_eq_orig: loc_tag = " (L)"
        elif r.get('AwayTeam','') == current_eq_orig: loc_tag = " (V)"

    return f"<div style='font-family:monospace;font-size:11px;padding:4px 2px;border-bottom:1px solid #eee'><span style='color:{col};font-weight:900'>|J{j}| {hab} {hg}-{ag} {aab}{loc_tag}</span> <span style='color:#000'>| {txt_mins}</span></div>"

eq_refs_orig = [e for e in [eq1, eq2] if e!= "Ninguno"]
eq_refs_norm = [normaliza(e) for e in eq_refs_orig]

html = ""

# MODO FILTRO POR % - PRIORITARIO
if filtro_tipo!= "Ninguno":
    def cumple(r):
        try:
            hg = int(float(r.get('FTHG',0) or 0)); ag = int(float(r.get('FTAG',0) or 0))
        except: return False, False, False
        ambos_si = hg>0 and ag>0
        ambos_no = not ambos_si
        over = (hg+ag) > 2.5
        under = not over
        if filtro_tipo == "Ambos SI": return ambos_si, True, True
        if filtro_tipo == "Ambos NO": return ambos_no, True, True
        if filtro_tipo == "Over 2.5": return over, True, True
        if filtro_tipo == "Under 2.5": return under, True, True
        return False, False, False

    equipos_a_chequear = equipos if liga_sel!="Todas" else sorted(pd.unique(pd.concat([df['HomeTeam'], df['AwayTeam']]).dropna()).tolist())

    calificados = []
    for team in equipos_a_chequear:
        d_team = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)]
        if len(d_team) < 3: continue
        c_ok = 0
        for _, rr in d_team.iterrows():
            ok,_,_ = cumple(rr.to_dict())
            if ok: c_ok+=1
        pct = (c_ok / len(d_team) * 100) if len(d_team)>0 else 0
        if pct >= filtro_pct:
            calificados.append((team, pct, len(d_team), c_ok))

    calificados = sorted(calificados, key=lambda x: x[1], reverse=True)

    if not calificados:
        st.info(f"Ningún equipo cumple {filtro_tipo} >= {filtro_pct}%")
    else:
        for team, pct, total, ok in calificados:
            d_team = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)].sort_values(['Jornada','Date'], ascending=[False, False]).head(20)
            # cabecera con % en verde/rojo
            color_pct = "#0f8105" if pct>=70 else "#0A2342"
            html += f"<div style='font-family:monospace;font-weight:900;background:{color_pct};color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{team} | {filtro_tipo} {pct:.0f}% ({ok}/{total})</div>"
            for _, r in d_team.iterrows():
                # usa tu mismo fmt_rapido pero pasando solo ese equipo como ref
                html += fmt_rapido(r.to_dict(), [normaliza(team)], normaliza(team), team)
        st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)

else:
    # MODO NORMAL (tu logica original intacta)
    if modo_doble:
        for eq_orig, df_eq in [(eq1, df_eq1), (eq2, df_eq2)]:
            cond = eq1_loc if eq_orig == eq1 else eq2_loc
            df_eq = df_eq.sort_values(['Jornada','Date'], ascending=[False, False]).head(30) if not df_eq.empty else df_eq
            html += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{eq_orig} {cond} | {len(df_eq)}</div>"
            eq_norm_single = normaliza(eq_orig)
            for _, r in df_eq.iterrows():
                html += fmt_rapido(r.to_dict(), eq_refs_norm, eq_norm_single, eq_orig)
    else:
        df_mostrar = df_mostrar.sort_values(['Jornada','Date'], ascending=[False, False]).head(60) if not df_mostrar.empty else df_mostrar
        if eq_refs_orig:
            cond_txt = eq1_loc if eq1!= "Ninguno" else eq2_loc
            html += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:6px 0 2px 0'>{eq_refs_orig[0]} {cond_txt} | {len(df_mostrar)}</div>"
        for _, r in df_mostrar.iterrows():
            curr_norm = eq_refs_norm[0] if eq_refs_norm else ""
            curr_orig = eq_refs_orig[0] if eq_refs_orig else ""
            html += fmt_rapido(r.to_dict(), eq_refs_norm, curr_norm, curr_orig)

    if (modo_doble and (not df_eq1.empty or not df_eq2.empty)) or (not modo_doble and not df_mostrar.empty):
        st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
    else:
        st.info("Selecciona equipo")

st.caption(f"Base: {BASE} | Registros: {len(df)} | Goles indexados: {len(eventos)} | Filtro: {filtro_tipo} {filtro_pct}%")
