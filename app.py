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
@st.cache_data(show_spinner=False)
def cargar_todo_lite():
    files = ["europa_actual.csv","din1_suec1_26_27.csv","asia_actual_j1j2k1k2csl1.csv","arabia_actual.csv","sudamerica_actual.csv","asia_4ligas_actual_2026.csv","asia_5ligas_actual_2026.csv"]
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
c1,c2,c3,c4d = st.columns(4)
with c1: liga_sel = st.selectbox("Liga", ["Todas"] + ligas)
df_f = df if liga_sel == "Todas" else df[df['League'] == liga_sel]

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

    col = "#0A2342"
    if eq_refs_norm:
        hn = normaliza(h); an = normaliza(a)
        for ern in eq_refs_norm:
            if ern == hn and hg > ag: col = "#0f8105"
            if ern == an and ag > hg: col = "#0f8105"
            if ern == hn and hg < ag: col = "#f31818"
            if ern == an and ag < hg: col = "#f31818"

    mins_1t = []
    mins_2t = []
    try:
        fid = str(r.get('fixture_id','')).split('.')[0]
        for ev in eventos.get(fid, []):
            m = ev['m']; team = ev['team']
            es_mio = any(ern in team or team in ern for ern in eq_refs_norm) if eq_refs_norm else False
            html_gol = f"<span style='color:#8A2BE2;font-weight:900'>{m}'</span>" if es_mio else f"<span style='color:#000'>{m}'</span>"
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

    # separador visual 1T | 2T
    if mins_1t and mins_2t:
        txt_mins = " ".join(mins_1t) + " <span style='color:#999;font-weight:900'>|</span> " + " ".join(mins_2t)
    elif mins_1t:
        txt_mins = " ".join(mins_1t)
    elif mins_2t:
        txt_mins = "<span style='color:#999'>-</span> <span style='color:#999;font-weight:900'>|</span> " + " ".join(mins_2t)
    else:
        txt_mins = "-"

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

    return f"<div style='font-family:monospace;font-size:11px;padding:4px 2px;border-bottom:1px solid #eee'><span style='color:{col};font-weight:900'>|J{j}| {hab} {hg}-{ag} {aab}{loc_tag}</span>{extra} <span style='color:#000'>| {txt_mins}</span></div>"

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
            c_ok = 0
            for _, rr in d_team.iterrows():
                if cumple(rr.to_dict()):
                    c_ok+=1
            pct = (c_ok / len(d_team) * 100) if len(d_team)>0 else 0
            if pct >= filtro_pct:
                calificados.append((team, loc_cond, pct, len(d_team), c_ok))

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
