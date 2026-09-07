import streamlit as st
import pandas as pd, pathlib, re, unicodedata
import numpy as np

st.set_page_config(page_title="Lite Rapido + Local", layout="wide")

def normaliza(s):
    import unicodedata
    n = unicodedata.normalize('NFKD', str(s)).encode('ASCII','ignore').decode('ASCII')
    return n.upper().strip()
def abreviar_equipo(nombre):
    n = normaliza(nombre)
    if 'ATLETICO' in n: return 'ATM'
    if 'BILBAO' in n or 'ATHLETIC' in n: return 'ATH'
    for pref in ['FC ','REAL ','CLUB ','DEPORTIVO ']:
        if n.startswith(pref): n = n[len(pref):]
    return (n.split()[0][:3] if n.split() else "XXX").upper()

def get_base():
    for p in [pathlib.Path("/mnt/data"), pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve(), pathlib.Path("/mount/src/mi-app-futbol")]:
        if (p / "europa_actual.csv").exists(): return p
    return pathlib.Path("/mnt/data")
BASE = get_base()

@st.cache_data(show_spinner=False)
def cargar_todo_lite():
    files = ["europa_actual.csv","din1_suec1_26_27.csv","asia_actual_j1j2k1k2csl1.csv","arabia_actual.csv","sudamerica_actual.csv"]
    dfs=[]
    for fn in files:
        f=BASE/fn
        if f.exists() and f.stat().st_size>100:
            d=pd.read_csv(f, on_bad_lines='skip', engine='c', low_memory=False)
            if 'Date' in d.columns: d['Date']=pd.to_datetime(d['Date'], dayfirst=True, errors='coerce')
            dfs.append(d)
    df=pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if 'Season' in df.columns: df['Season']=df['Season'].astype(str)
    if 'fixture_id' in df.columns and not df.empty:
        df=df.sort_values('Date').drop_duplicates(subset=['fixture_id'], keep='last')
    if not df.empty and 'Jornada' not in df.columns:
        df=df.sort_values(['League','Season','Date']).copy()
        df['Jornada']=0
        for (l,s),g in df.groupby(['League','Season'], sort=False):
            g_sorted=g.sort_values('Date')
            n_teams=len(pd.unique(g_sorted[['HomeTeam','AwayTeam']].values.ravel())) if 'HomeTeam' in g_sorted.columns else 20
            ppj=max(n_teams//2,1)
            idxs=g_sorted.index.to_numpy()
            df.loc[idxs,'Jornada']=(np.arange(len(idxs))//ppj)+1
    if 'HomeAbbr' not in df.columns and 'HomeTeam' in df.columns:
        df['HomeAbbr']=df['HomeTeam'].apply(abreviar_equipo)
        df['AwayAbbr']=df['AwayTeam'].apply(abreviar_equipo)
    return df

@st.cache_data(show_spinner=False)
def cargar_goles_lite():
    files=["goles_actual.csv","goles_arabia_actual.csv","goles_sudamerica_actual.csv"]
    ev={}
    for fn in files:
        f=BASE/fn
        if not f.exists(): continue
        try:
            dg=pd.read_csv(f, dtype=str, on_bad_lines='skip', engine='python')
            for fid,g in dg.groupby('fixture_id'):
                fid_c=str(fid).split('.')[0]
                lista=[]
                for _,r in g.iterrows():
                    try:
                        m=int(float(str(r.get('minuto','0')).split('+')[0] or 0))
                        team=str(r.get('equipo','')).strip()
                        if not team: continue
                        lista.append({"m":m,"team":normaliza(team)})
                    except: continue
                if lista: ev[fid_c]=sorted(lista, key=lambda x:x['m'])
        except: pass
    return ev

df = cargar_todo_lite()
eventos = cargar_goles_lite()
if df.empty: st.error("No CSVs"); st.stop()

# DESPLEGABLES
ligas = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []
c1,c2,c3 = st.columns(3)
with c1: liga_sel = st.selectbox("Liga", ["Todas"]+ligas)
df_f = df if liga_sel=="Todas" else df[df['League']==liga_sel]
equipos = sorted(pd.unique(df_f[['HomeTeam','AwayTeam']].values.ravel())) if not df_f.empty else []

with c2: eq1 = st.selectbox("Equipo 1", ["Ninguno"]+equipos)
with c3: eq1_loc = st.selectbox("Eq1 Condición", ["Todos","Local","Visitante"], key="eq1loc")

c4,c5 = st.columns(2)
with c4: eq2 = st.selectbox("Equipo 2", ["Ninguno"]+[e for e in equipos if e!=eq1])
with c5: eq2_loc = st.selectbox("Eq2 Condición", ["Todos","Local","Visitante"], key="eq2loc")

# FILTRO VECTORIZADO - ESTO NO PETA
def filtrar_equipo(dframe, equipo, condicion):
    if equipo=="Ninguno" or dframe.empty: return dframe.iloc[0:0] if equipo!="Ninguno" else dframe
    if condicion=="Local": return dframe[dframe['HomeTeam']==equipo]
    if condicion=="Visitante": return dframe[dframe['AwayTeam']==equipo]
    return dframe[(dframe['HomeTeam']==equipo)|(dframe['AwayTeam']==equipo)]

if eq1!="Ninguno" and eq2!="Ninguno":
    df_eq1 = filtrar_equipo(df_f, eq1, eq1_loc)
    df_eq2 = filtrar_equipo(df_f, eq2, eq2_loc)
    modo_doble = True
elif eq1!="Ninguno":
    df_mostrar = filtrar_equipo(df_f, eq1, eq1_loc)
    modo_doble = False
elif eq2!="Ninguno":
    df_mostrar = filtrar_equipo(df_f, eq2, eq2_loc)
    modo_doble = False
else:
    df_mostrar = df_f
    modo_doble = False

# --- BLOQUE CORREGIDO + BUSCADOR ---
def fmt_rapido(r, eq_refs, current_eq=None):
    j=int(r.get('Jornada',0) or 0)
    h=str(r.get('HomeTeam','')); a=str(r.get('AwayTeam',''))
    hab=str(r.get('HomeAbbr',abreviar_equipo(h)))[:3].upper()
    aab=str(r.get('AwayAbbr',abreviar_equipo(a)))[:3].upper()
    try: hg=int(float(r.get('FTHG',0) or 0)); ag=int(float(r.get('FTAG',0) or 0))
    except: hg=0; ag=0
    col="#0A2342"
    if eq_refs:
        hn=normaliza(h); an=normaliza(a)
        for er in eq_refs:
            ern=normaliza(er)
            if ern==hn and hg>ag: col="#0f8105"
            if ern==an and ag>hg: col="#0f8105"
            if ern==hn and hg<ag: col="#f31818"
            if ern==an and ag<hg: col="#f31818"
    mins=[]
    try:
        fid=str(r.get('fixture_id','')).split('.')[0]
        for ev in eventos.get(fid,[]):
            m=ev['m']; team=ev['team']
            es_mio=any(normaliza(er) in team or team in normaliza(er) for er in eq_refs) if eq_refs else False
            mins.append(f"<span style='color:#8A2BE2;font-weight:900'>{m}'</span>" if es_mio else f"<span style='color:#000'>{m}'</span>")
    except: pass
    if not mins:
        ms=re.findall(r"(\d+)'", str(r.get('Goles_Todo_HTML','') or ''))
        mins=[f"<span style='color:#000'>{x}'</span>" for x in ms]
    txt_mins=" ".join(mins) if mins else "-"
    equipo_bloque = current_eq if current_eq is not None else (eq_refs[0] if eq_refs else "")
    if equipo_bloque:
        if r.get('HomeTeam','')==equipo_bloque: loc_tag=" (L)"
        elif r.get('AwayTeam','')==equipo_bloque: loc_tag=" (V)"
        else: loc_tag=""
    else:
        loc_tag=""
    return f"<div style='font-family:monospace;font-size:11px;padding:4px 2px;border-bottom:1px solid #000'><span style='color:{col};font-weight:900'>|J{j}| {hab} {hg}-{ag} {aab}{loc_tag}</span> <span style='color:#000'>| {txt_mins}</span></div>"

def fmt_corto(r):
    j=int(r.get('Jornada',0) or 0)
    try: hg=int(float(r.get('FTHG',0))); ag=int(float(r.get('FTAG',0)))
    except: hg=0; ag=0
    return f"|J{j}| {hg}-{ag}"

# Asegurar columnas BTTS y OVER sin tocar carga original
for _df in [df_f] + ([df_eq1, df_eq2] if modo_doble else [df_mostrar]):
    if not _df.empty and 'BTTS' not in _df.columns and 'FTHG' in _df.columns:
        _df['BTTS'] = (pd.to_numeric(_df['FTHG'], errors='coerce').fillna(0)>0) & (pd.to_numeric(_df['FTAG'], errors='coerce').fillna(0)>0)
        _df['OVER25'] = (pd.to_numeric(_df['FTHG'], errors='coerce').fillna(0)+pd.to_numeric(_df['FTAG'], errors='coerce').fillna(0))>2.5

# BUSCADOR
st.divider()
b1,b2,b3 = st.columns(3)
with b1: filtro_btts = st.selectbox("Ambos marcan", ["Todos","BTTS Si","BTTS No"])
with b2: filtro_over = st.selectbox("Goles", ["Todos","Over 2.5","Under 2.5"])
with b3: pct_min = st.slider("% mínimo", 0, 100, 70)

def cumple_filtro(dframe):
    dfx=dframe
    if filtro_btts=="BTTS Si": dfx=dfx[dfx['BTTS']==True]
    if filtro_btts=="BTTS No": dfx=dfx[dfx['BTTS']==False]
    if filtro_over=="Over 2.5": dfx=dfx[dfx['OVER25']==True]
    if filtro_over=="Under 2.5": dfx=dfx[dfx['OVER25']==False]
    return dfx

eq_refs=[e for e in [eq1,eq2] if e!="Ninguno"]
texto_portapapeles=""
html=""

if modo_doble:
    for eq, df_eq, cond in [(eq1, df_eq1, eq1_loc), (eq2, df_eq2, eq2_loc)]:
        total=len(df_eq)
        if total==0: continue
        df_cumple = cumple_filtro(df_eq) if (filtro_btts!="Todos" or filtro_over!="Todos") else df_eq
        cumple=len(df_cumple)
        pct = round(cumple/total*100,1) if total else 0
        if pct < pct_min: continue
        df_cumple = df_cumple.sort_values(['Jornada','Date'], ascending=[False, False])
        partidos_str = " ".join([fmt_corto(r.to_dict() if hasattr(r,'to_dict') else r) for _,r in df_cumple.iterrows()])
        linea = f"{eq} {cond} {pct}% ({cumple}/{total} {filtro_btts} {filtro_over}): {partidos_str}"
        texto_portapapeles += linea + "\n\n"
        color = "#0f8105" if pct>=70 else "#f39c12" if pct>=50 else "#f31818"
        html+=f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px;margin:8px 0 2px 0;display:flex;justify-content:space-between'><span>{eq} {cond} | {pct}% ({cumple}/{total})</span><span style='background:{color};padding:2px 6px;border-radius:4px'>{pct}%</span></div>"
        html+=f"<div style='font-family:monospace;font-size:12px;padding:6px;border:1px solid #000;margin-bottom:10px'>{partidos_str if partidos_str else 'Ninguno cumple'}</div>"
else:
    df_base = df_mostrar
    total=len(df_base)
    if total>0:
        df_cumple = cumple_filtro(df_base) if (filtro_btts!="Todos" or filtro_over!="Todos") else df_base
        cumple=len(df_cumple)
        pct = round(cumple/total*100,1) if total else 0
        eq_nombre = eq1 if eq1!="Ninguno" else eq2 if eq2!="Ninguno" else "TODOS"
        cond_txt = eq1_loc if eq1!="Ninguno" else eq2_loc if eq2!="Ninguno" else "Todos"
        if pct >= pct_min:
            df_cumple = df_cumple.sort_values(['Jornada','Date'], ascending=[False, False])
            partidos_str = " ".join([fmt_corto(r.to_dict() if hasattr(r,'to_dict') else r) for _,r in df_cumple.iterrows()])
            linea = f"{eq_nombre} {cond_txt} {pct}% ({cumple}/{total} {filtro_btts} {filtro_over}): {partidos_str}"
            texto_portapapeles = linea
            color = "#0f8105" if pct>=70 else "#f39c12" if pct>=50 else "#f31818"
            html+=f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px;margin:6px 0 2px 0;display:flex;justify-content:space-between'><span>{eq_nombre} {cond_txt} | {pct}% ({cumple}/{total})</span><span style='background:{color};padding:2px 6px;border-radius:4px'>{pct}%</span></div>"
            html+=f"<div style='font-family:monospace;font-size:12px;padding:6px;border:1px solid #000'>{partidos_str}</div>"
        else:
            html=f"<div style='font-family:monospace;padding:10px;background:#ffe0e0'>No cumple % mínimo: {eq_nombre} tiene {pct}% y pides {pct_min}%</div>"
            texto_portapapeles = f"{eq_nombre} NO CUMPLE {pct_min}% -> tiene {pct}% ({cumple}/{total})"

if html:
    st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
else:
    st.info("Ningún equipo cumple el % mínimo con esos filtros")

if texto_portapapeles:
    st.divider()
    st.code(texto_portapapeles, language="text")
    st.components.v1.html(f"""
    <button onclick="navigator.clipboard.writeText(`{texto_portapapeles.replace('`','').replace(chr(92),chr(92)+chr(92))}`)"
    style="background:#0A2342;color:#fff;padding:10px 20px;border:none;border-radius:6px;font-weight:900;cursor:pointer;width:100%">
    📋 COPIAR AL PORTAPAPELES
    </button>
    """, height=50)

st.caption(f"Sigue volando - Buscador vectorizado, no añade lag")
