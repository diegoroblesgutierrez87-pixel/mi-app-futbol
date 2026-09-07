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
    for p in [pathlib.Path("/mnt/data"), pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
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

def fmt_rapido(r, eq_refs):
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
    # fix L/V por bloque
    equipo_bloque = eq_refs[0] if len(eq_refs)==1 else current_eq
    loc_tag = " (L)" if r.get('HomeTeam','')==equipo_bloque else " (V)" if r.get('AwayTeam','')==equipo_bloque else ""
    return f"<div style='font-family:monospace;font-size:11px;padding:4px 2px;border-bottom:1px solid #000'><span style='color:{col};font-weight:900'>|J{j}| {hab} {hg}-{ag} {aab}{loc_tag}</span> <span style='color:#000'>| {txt_mins}</span></div>"

eq_refs=[e for e in [eq1,eq2] if e!="Ninguno"]
html=""

if modo_doble:
    for eq, df_eq, cond in [(eq1, df_eq1, eq1_loc), (eq2, df_eq2, eq2_loc)]:
        df_eq = df_eq.sort_values(['Jornada','Date'], ascending=[False, False]).head(30) if not df_eq.empty else df_eq
        html+=f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{eq} {cond} | {len(df_eq)}</div>"
        for _,r in df_eq.iterrows(): html+=fmt_rapido(r.to_dict(), eq_refs)
else:
    df_mostrar = df_mostrar.sort_values(['Jornada','Date'], ascending=[False, False]).head(60) if not df_mostrar.empty else df_mostrar
    if eq_refs:
        cond_txt = eq1_loc if eq1!="Ninguno" else eq2_loc
        html+=f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:6px 0 2px 0'>{eq_refs[0]} {cond_txt} | {len(df_mostrar)}</div>"
    for _,r in df_mostrar.iterrows(): html+=fmt_rapido(r.to_dict(), eq_refs)

if (modo_doble and (not df_eq1.empty or not df_eq2.empty)) or (not modo_doble and not df_mostrar.empty):
    st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
else:
    st.info("Selecciona equipo")

st.caption(f"Sigue volando - Local/Visitante es solo un filtro vectorizado, no añade lag")
