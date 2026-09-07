import streamlit as st
import pandas as pd, pathlib, re, unicodedata, os
import numpy as np

st.set_page_config(page_title="Lite Rapido", layout="wide")

def normaliza(s):
    try:
        n = unicodedata.normalize('NFKD', str(s)).encode('ASCII','ignore').decode('ASCII')
        return n.upper().strip()
    except:
        return str(s).upper().strip()

def abreviar_equipo(nombre):
    n = normaliza(nombre)
    if 'ATLETICO' in n: return 'ATM'
    if 'BILBAO' in n or 'ATHLETIC' in n: return 'ATH'
    for pref in ['FC ','REAL ','CLUB ','DEPORTIVO ']:
        if n.startswith(pref): n = n[len(pref):]
    parts = n.split()
    return (parts[0][:3] if parts else "XXX").upper()

def get_base():
    # busca CSVs en /mnt/data (cuando pruebas aquí) y en la carpeta del script (cuando lo subes a Streamlit)
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
        f=BASE/fn
        if f.exists() and f.stat().st_size>100:
            try:
                d=pd.read_csv(f, on_bad_lines='skip', engine='c', low_memory=False)
                if 'Date' in d.columns:
                    d['Date']=pd.to_datetime(d['Date'], dayfirst=True, errors='coerce')
                dfs.append(d)
            except Exception as e:
                st.warning(f"Error {fn}: {e}")
    if not dfs:
        return pd.DataFrame()
    df=pd.concat(dfs, ignore_index=True)
    df['Season']=df['Season'].astype(str) if 'Season' in df.columns else "2025"
    # limpia duplicados
    if 'fixture_id' in df.columns:
        df=df.sort_values('Date').drop_duplicates(subset=['fixture_id'], keep='last')
    # jornada vectorizada (el fix que te quita los segundos)
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
                if lista:
                    ev[fid_c]=sorted(lista, key=lambda x:x['m'])
        except: pass
    return ev

df = cargar_todo_lite()
eventos = cargar_goles_lite()

if df.empty:
    st.error(f"No encontré CSVs en {BASE}. Sube los 8 CSVs a la misma carpeta que app.py")
    st.stop()

# 3 desplegables
ligas = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []
liga_sel = st.selectbox("Liga", ["Todas"]+ligas)

df_f = df if liga_sel=="Todas" else df[df['League']==liga_sel]

equipos = sorted(pd.unique(df_f[['HomeTeam','AwayTeam']].values.ravel())) if not df_f.empty else []
eq1 = st.selectbox("Equipo 1", ["Ninguno"]+equipos)
eq2 = st.selectbox("Equipo 2", ["Ninguno"]+[e for e in equipos if e!=eq1])

if eq1!="Ninguno" and eq2!="Ninguno":
    mask = (df_f['HomeTeam'].isin([eq1,eq2])) | (df_f['AwayTeam'].isin([eq1,eq2]))
    df_mostrar = df_f[mask]
elif eq1!="Ninguno":
    df_mostrar = df_f[(df_f['HomeTeam']==eq1) | (df_f['AwayTeam']==eq1)]
elif eq2!="Ninguno":
    df_mostrar = df_f[(df_f['HomeTeam']==eq2) | (df_f['AwayTeam']==eq2)]
else:
    df_mostrar = df_f

df_mostrar = df_mostrar.sort_values(['Jornada','Date'], ascending=[False, False]).head(60) if not df_mostrar.empty else df_mostrar

def fmt_rapido(r, eq_refs):
    j=int(r.get('Jornada',0) or 0)
    h=str(r.get('HomeTeam','')); a=str(r.get('AwayTeam',''))
    hab=str(r.get('HomeAbbr',abreviar_equipo(h)))[:3].upper()
    aab=str(r.get('AwayAbbr',abreviar_equipo(a)))[:3].upper()
    try:
        hg=int(float(r.get('FTHG',0) or 0)); ag=int(float(r.get('FTAG',0) or 0))
    except:
        hg=0; ag=0
    col = "#0A2342"
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
        evs=eventos.get(fid,[])
        for ev in evs:
            m=ev['m']
            team=ev['team']
            es_mio=False
            for er in eq_refs:
                if normaliza(er) in team or team in normaliza(er) or team.split()[0] in normaliza(er):
                    es_mio=True
            if eq_refs and es_mio:
                mins.append(f"<span style='color:#8A2BE2;font-weight:900'>{m}'</span>")
            else:
                mins.append(f"<span style='color:#000'>{m}'</span>")
    except: pass
    if not mins:
        raw=str(r.get('Goles_Todo_HTML','') or '')
        ms=re.findall(r"(\d+)'", raw)
        mins=[f"<span style='color:#000'>{x}'</span>" for x in ms]
    txt_mins=" ".join(mins) if mins else "-"
    return f"<div style='font-family:monospace;font-size:11px;padding:4px 2px;border-bottom:1px solid #000'><span style='color:{col};font-weight:900'>|J{j}| {hab} {hg}-{ag} {aab}</span> <span style='color:#000'>| {txt_mins}</span></div>"

eq_refs=[e for e in [eq1,eq2] if e!="Ninguno"]

html=""
if eq1!="Ninguno" and eq2!="Ninguno":
    for eq in [eq1,eq2]:
        df_eq=df_mostrar[(df_mostrar['HomeTeam']==eq)|(df_mostrar['AwayTeam']==eq)].sort_values(['Jornada','Date'], ascending=[False,False]) if not df_mostrar.empty else df_mostrar
        html+=f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{eq} | {len(df_eq)}</div>"
        for _,r in df_eq.iterrows():
            html+=fmt_rapido(r.to_dict(), eq_refs)
else:
    if eq_refs:
        html+=f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:6px 0 2px 0'>{eq_refs[0]} | {len(df_mostrar)} partidos</div>"
    for _,r in df_mostrar.iterrows():
        html+=fmt_rapido(r.to_dict(), eq_refs)

if not df_mostrar.empty:
    st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
else:
    st.info("Selecciona liga y equipo")

st.caption(f"CSV base: {BASE} | {len(df)} partidos totales | {len(eventos)} partidos con goles | Liga: {liga_sel}")
