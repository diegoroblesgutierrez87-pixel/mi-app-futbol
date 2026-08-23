
with st.expander("📥 Descargas 26/27 - FIX + AUTO GITHUB", expanded=False):

    # --- PAUSA / CONTINUAR SOLO PARA ESTE BOTON 26/27 ---
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

    if st.button("Ligas 26/27 - FIX TOTAL 1P/2P + GOLES + MINUTOS", use_container_width=True, key="btn_1esp_2627_FIX_TOTAL_V5"):
        import requests as _req, time, pathlib, pandas as pd, os, json
        try: API_KEY = str(st.secrets["API_KEY"]).strip()
        except: st.error("Falta API_KEY en Secrets"); st.stop()

        try:
            rr = _req.get("https://v3.football.api-sports.io/status", headers={"x-apisports-key": API_KEY}, timeout=15)
            q = rr.json()['response']['requests']
            quedan = int(q['limit_day'] - q['current'])
            if quedan < 100:
                st.error(f"⛔ Solo {quedan}/7500 - espera 02:00 Madrid"); st.stop()
        except: pass

        MAPA_2627 = {
            "Bundesliga": 78, "2. Bundesliga": 79, "Bundesliga Femenina": 82,
            "Saudi Professional League": 307, "Saudi First Division League": 308,
            "Bundesliga Austria": 218, "2. Liga Austria": 219,
            "Super League": 207, "Challenge League": 208, "Premier League Bahrein": 400,
            "Jupiler Pro League": 144, "Challenger Pro League": 145,
            "Chinese Super League": 169, "China League One": 170, "Cyprus League": 318,
            "K League 1": 292, "K League 2": 293, "Superliga Dinamarca": 119, "UAE League": 301,
            "Premiership Escocia": 179, "LaLiga EA Sports": 140, "LaLiga Hypermotion": 141,
            "Primera Federacion G1": 435, "Primera Federacion G2": 436, "Liga F": 148,
            "Ligue 1": 61, "Ligue 2": 62, "Super League Grecia": 197, "Super League 2 Grecia": 196,
            "Premier League": 39, "Championship": 40, "WSL": 44, "WSL 2": 45,
            "Serie A Italia": 135, "Serie B Italia": 136, "J1 League": 98, "J2 League": 99,
            "Eredivisie": 88, "Eerste Divisie": 89, "Liga Portugal": 94, "Liga Portugal 2": 95,
            "Taça de Portugal": 96, "Süper Lig": 203, "1. Lig": 204,
        }
        TEMPORADA = 2026
        BASE = pathlib.Path(__file__).parent
        FILE_CUR = BASE / "partidos_2627_actual.csv"
        FILE_GOLES = BASE / "goles_2627_actual.csv"
        FILE_JUG = BASE / "jugadores_2627_actual.csv"
        PROG_FILE = BASE / "progreso_2627_fix.json"

        def _esta_completo(rd):
            if not rd: return False
            if int(float(rd.get('HS',0) or 0))==0 and int(float(rd.get('HC',0) or 0))==0 and int(float(rd.get('HomePasses',0) or 0))==0:
                return False
            for c in ['HomePasses','HST','HC','HomePos','B365H']:
                v = rd.get(c,0)
                if str(v).strip() in ['','0','0.0','0%','None','nan'] or (c.startswith('B365') and float(str(v).replace('%','') or 0)<=1):
                    return False
            return True

        fids_existentes = set()
        map_fid_to_row = {}
        goles_fids = set()
        if FILE_CUR.exists() and FILE_CUR.stat().st_size>0:
            try:
                d = pd.read_csv(FILE_CUR, on_bad_lines='skip', engine='python')
                if 'fixture_id' in d.columns:
                    fids_existentes.update(d['fixture_id'].dropna().astype(str).tolist())
                    for _, r in d.iterrows():
                        try: map_fid_to_row[str(r['fixture_id'])] = r.to_dict()
                        except: pass
            except: pass
        if FILE_GOLES.exists() and FILE_GOLES.stat().st_size>0:
            try:
                dg = pd.read_csv(FILE_GOLES, on_bad_lines='skip', engine='python')
                if 'fixture_id' in dg.columns:
                    goles_fids.update(dg['fixture_id'].dropna().astype(str).tolist())
            except: pass

        liga_start_idx = 0
        if PROG_FILE.exists():
            try:
                prog_data = json.loads(PROG_FILE.read_text(encoding='utf-8'))
                liga_start_idx = int(prog_data.get("liga_idx",0))
            except: liga_start_idx = 0

        st.session_state.pausa_2627 = False
        req=[0]
        prog=st.progress(0.0, text="Iniciando 26/27...")
        nuevos_p, nuevos_g, nuevos_j = [], [], []
        lista_ligas = list(MAPA_2627.items())

        for idx_liga in range(liga_start_idx, len(lista_ligas)):
            nom, lid = lista_ligas[idx_liga]
            prog.progress(idx_liga/len(lista_ligas), text=f"{nom} | req:{req[0]} | fids:{len(fids_existentes)}")

            # CHECK PAUSA AL INICIO DE CADA LIGA
            if st.session_state.pausa_2627:
                try: PROG_FILE.write_text(json.dumps({"liga_idx": idx_liga}), encoding='utf-8')
                except: pass
                st.warning(f"⏸ Pausado en {nom}. Dale a ▶ Continuar 26/27 para seguir.")
                st.stop()

            try:
                time.sleep(0.35)
                r = _req.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": API_KEY}, params={"league": lid, "season": TEMPORADA}, timeout=30)
                req[0]+=1
                fixtures = r.json().get("response", [])
            except: continue

            for fx in fixtures:
                # CHECK PAUSA EN CADA PARTIDO
                if st.session_state.pausa_2627:
                    try: PROG_FILE.write_text(json.dumps({"liga_idx": idx_liga}), encoding='utf-8')
                    except: pass
                    st.warning(f"⏸ Pausado en {nom} | {fx['teams']['home']['name']} vs {fx['teams']['away']['name']}")
                    st.stop()

                if fx["fixture"]["status"]["short"] not in ["FT","AET","PEN"]: continue
                fid = str(fx["fixture"]["id"])
                if fid in fids_existentes:
                    completo = _esta_completo(map_fid_to_row.get(fid, {}))
                    total_goles = (fx["goals"]["home"] or 0) + (fx["goals"]["away"] or 0)
                    falta_gol = total_goles>0 and fid not in goles_fids
                    if completo and not falta_gol: continue
                    fids_existentes.discard(fid)

                date_str = pd.to_datetime(fx["fixture"]["date"][:10]).strftime("%d/%m/%Y")
                home = normaliza(fx["teams"]["home"]["name"])
                away = normaliza(fx["teams"]["away"]["name"])
                ft_h, ft_a = fx["goals"]["home"] or 0, fx["goals"]["away"] or 0
                ht_h, ht_a = fx["score"]["halftime"]["home"] or 0, fx["score"]["halftime"]["away"] or 0

                row = {
                    "Date":date_str,"League":nom,"Season":f"{TEMPORADA}/{TEMPORADA+1}","HomeTeam":home,"AwayTeam":away,
                    "FTHG":ft_h,"FTAG":ft_a,"HTHG":ht_h,"HTAG":ht_a,"FTR":"H" if ft_h>ft_a else "A" if ft_a>ft_h else "D",
                    "B365H":0,"B365D":0,"B365A":0,"HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0,
                    "HomePasses":0,"AwayPasses":0,"HomeSaves":0,"AwaySaves":0,"HomePos":0,"AwayPos":0,
                    "HS_1P":0,"AS_1P":0,"HST_1P":0,"AST_1P":0,"HF_1P":0,"AF_1P":0,"HC_1P":0,"AC_1P":0,"HY_1P":0,"AY_1P":0,"HR_1P":0,"AR_1P":0,"HomePasses_1P":0,"AwayPasses_1P":0,"HomePos_1P":0,"AwayPos_1P":0,
                    "HS_2P":0,"AS_2P":0,"HST_2P":0,"AST_2P":0,"HF_2P":0,"AF_2P":0,"HC_2P":0,"AC_2P":0,"HY_2P":0,"AY_2P":0,"HR_2P":0,"AR_2P":0,"HomePasses_2P":0,"AwayPasses_2P":0,"HomePos_2P":0,"AwayPos_2P":0,
                    "fixture_id": fx["fixture"]["id"]
                }

                try:
                    time.sleep(0.35); rs=_req.get("https://v3.football.api-sports.io/fixtures/statistics", headers={"x-apisports-key": API_KEY}, params={"fixture": fx["fixture"]["id"]}, timeout=20); req[0]+=1
                    if rs.status_code==200 and len(rs.json().get("response",[]))==2:
                        for j, td in enumerate(rs.json()["response"]):
                            sd={s["type"]: s["value"] for s in td["statistics"] if s["value"] is not None}
                            passes = sd.get("Total passes") or sd.get("Passes accurate") or 0
                            pos = str(sd.get("Ball Possession","")).replace("%","") or 0
                            if j==0:
                                row["HS"]=sd.get("Total Shots",0) or 0; row["HST"]=sd.get("Shots on Goal",0) or 0; row["HF"]=sd.get("Fouls",0) or 0; row["HC"]=sd.get("Corner Kicks",0) or 0; row["HY"]=sd.get("Yellow Cards",0) or 0; row["HR"]=sd.get("Red Cards",0) or 0; row["HomePasses"]=passes; row["HomePos"]=pos; row["HomeSaves"]=sd.get("Goalkeeper Saves",0) or 0
                            else:
                                row["AS"]=sd.get("Total Shots",0) or 0; row["AST"]=sd.get("Shots on Goal",0) or 0; row["AF"]=sd.get("Fouls",0) or 0; row["AC"]=sd.get("Corner Kicks",0) or 0; row["AY"]=sd.get("Yellow Cards",0) or 0; row["AR"]=sd.get("Red Cards",0) or 0; row["AwayPasses"]=passes; row["AwayPos"]=pos; row["AwaySaves"]=sd.get("Goalkeeper Saves",0) or 0
                except: pass
                if row["HS"]==0 and row["HC"]==0 and row["HomePasses"]==0: continue

                try:
                    time.sleep(0.35); rh=_req.get("https://v3.football.api-sports.io/fixtures/statistics", headers={"x-apisports-key": API_KEY}, params={"fixture": fx["fixture"]["id"], "half":"true"}, timeout=20); req[0]+=1
                    if rh.status_code==200:
                        for td in rh.json().get("response",[]):
                            is_home = td["team"]["id"]==fx["teams"]["home"]["id"]
                            raw_half = str(td.get("half","") or td.get("period","")).lower()
                            if "1" in raw_half or "first" in raw_half: suf="_1P"
                            elif "2" in raw_half or "second" in raw_half: suf="_2P"
                            else: continue
                            sd={s["type"]: s["value"] for s in td["statistics"] if s["value"] is not None}
                            passes = sd.get("Total passes") or sd.get("Passes accurate") or 0
                            pos = str(sd.get("Ball Possession","")).replace("%","") or 0
                            if is_home:
                                row[f"HS{suf}"]=sd.get("Total Shots",0) or 0; row[f"HST{suf}"]=sd.get("Shots on Goal",0) or 0; row[f"HC{suf}"]=sd.get("Corner Kicks",0) or 0; row[f"HF{suf}"]=sd.get("Fouls",0) or 0; row[f"HY{suf}"]=sd.get("Yellow Cards",0) or 0; row[f"HR{suf}"]=sd.get("Red Cards",0) or 0; row[f"HomePasses{suf}"]=passes; row[f"HomePos{suf}"]=pos
                            else:
                                row[f"AS{suf}"]=sd.get("Total Shots",0) or 0; row[f"AST{suf}"]=sd.get("Shots on Goal",0) or 0; row[f"AC{suf}"]=sd.get("Corner Kicks",0) or 0; row[f"AF{suf}"]=sd.get("Fouls",0) or 0; row[f"AY{suf}"]=sd.get("Yellow Cards",0) or 0; row[f"AR{suf}"]=sd.get("Red Cards",0) or 0; row[f"AwayPasses{suf}"]=passes; row[f"AwayPos{suf}"]=pos
                except: pass

                try:
                    time.sleep(0.35); ro=_req.get("https://v3.football.api-sports.io/odds", headers={"x-apisports-key": API_KEY}, params={"fixture": fx["fixture"]["id"], "bookmaker": 8}, timeout=20); req[0]+=1
                    if ro.status_code==200:
                        for bet in ro.json().get("response",[{}])[0].get("bookmakers",[{}])[0].get("bets",[]):
                            if bet["name"]=="Match Winner":
                                for v in bet["values"]:
                                    if v["value"]=="Home": row["B365H"]=float(v["odd"])
                                    elif v["value"]=="Draw": row["B365D"]=float(v["odd"])
                                    elif v["value"]=="Away": row["B365A"]=float(v["odd"])
                except: pass

                try:
                    time.sleep(0.35); re_=_req.get("https://v3.football.api-sports.io/fixtures/events", headers={"x-apisports-key": API_KEY}, params={"fixture": fx["fixture"]["id"]}, timeout=20); req[0]+=1
                    if re_.status_code==200:
                        for ev in re_.json().get("response", []):
                            if ev["type"]=="Goal":
                                nuevos_g.append({"Date":date_str,"League":nom,"HomeTeam":home,"AwayTeam":away,"minuto":ev["time"]["elapsed"],"parte":"1P" if (ev["time"]["elapsed"] or 0)<=45 else "2P","goleador":ev["player"]["name"],"asistente":ev["assist"]["name"] or "","equipo":normaliza(ev["team"]["name"]),"tipo":ev["detail"],"fixture_id": fx["fixture"]["id"]})
                except: pass

                try:
                    time.sleep(0.35); rp=_req.get("https://v3.football.api-sports.io/fixtures/players", headers={"x-apisports-key": API_KEY}, params={"fixture": fx["fixture"]["id"]}, timeout=20); req[0]+=1
                    if rp.status_code==200:
                        for team_data in rp.json().get("response",[]):
                            for pl in team_data.get("players",[]):
                                p=pl.get("player",{}); s=pl.get("statistics",[{}])[0]
                                nuevos_j.append({"Date":date_str,"League":nom,"HomeTeam":home,"AwayTeam":away,"jugador":p.get("name"),"equipo":normaliza(team_data["team"]["name"]),"minutos":s.get("games",{}).get("minutes") or 0,"fixture_id": fx["fixture"]["id"]})
                except: pass

                nuevos_p.append(row); fids_existentes.add(fid); map_fid_to_row[fid]=row
                if len(nuevos_p)>=1:
                    pd.DataFrame(nuevos_p).to_csv(FILE_CUR, mode='a', header=not FILE_CUR.exists() or FILE_CUR.stat().st_size==0, index=False); nuevos_p=[]
                    if nuevos_g: pd.DataFrame(nuevos_g).to_csv(FILE_GOLES, mode='a', header=not FILE_GOLES.exists() or FILE_GOLES.stat().st_size==0, index=False); nuevos_g=[]
                    if nuevos_j: pd.DataFrame(nuevos_j).to_csv(FILE_JUG, mode='a', header=not FILE_JUG.exists() or FILE_JUG.stat().st_size==0, index=False); nuevos_j=[]

            try: PROG_FILE.write_text(json.dumps({"liga_idx": idx_liga+1}), encoding='utf-8')
            except: pass

        if nuevos_p: pd.DataFrame(nuevos_p).to_csv(FILE_CUR, mode='a', header=not FILE_CUR.exists() or FILE_CUR.stat().st_size==0, index=False)
        if nuevos_g: pd.DataFrame(nuevos_g).to_csv(FILE_GOLES, mode='a', header=not FILE_GOLES.exists() or FILE_GOLES.stat().st_size==0, index=False)
        if nuevos_j: pd.DataFrame(nuevos_j).to_csv(FILE_JUG, mode='a', header=not FILE_JUG.exists() or FILE_JUG.stat().st_size==0, index=False)

        try:
            if FILE_CUR.exists():
                df_all=pd.read_csv(FILE_CUR, on_bad_lines='skip'); df_all=df_all.drop_duplicates(subset=['fixture_id'], keep='last'); df_all.to_csv(FILE_CUR, index=False)
        except: pass
        if PROG_FILE.exists():
            try: os.remove(PROG_FILE)
            except: pass

        st.success(f"✅ 26/27 {req[0]} req | FIX TOTAL OK | 1P/2P + goles + minutos"); st.cache_data.clear(); time.sleep(1); st.rerun()
##############boton 2
#######################
###########################
    if st.button("Ligas 22/23 a 25/26 -> CSV VIEJO (solo resultado + 1P/2P)", use_container_width=True, key="btn_2226_A_CSV_VIEJO_SOLO_RES_FINAL_V2"):
        import requests as _req, time, pathlib, pandas as pd, os
        try: 
            API_KEY = str(st.secrets["API_KEY"]).strip()
        except: 
            st.error("Falta API_KEY en Secrets")
            st.stop()

        MAPA_2627 = {
            "Bundesliga": 78, "2. Bundesliga": 79, "Bundesliga Femenina": 82,
            "Saudi Professional League": 307, "Saudi First Division League": 308,
            "Bundesliga Austria": 218, "2. Liga Austria": 219,
            "Super League": 207, "Challenge League": 208, "Premier League Bahrein": 400,
            "Jupiler Pro League": 144, "Challenger Pro League": 145,
            "Chinese Super League": 169, "China League One": 170, "Cyprus League": 318,
            "K League 1": 292, "K League 2": 293, "Superliga Dinamarca": 119, "UAE League": 301,
            "Premiership Escocia": 179, "LaLiga EA Sports": 140, "LaLiga Hypermotion": 141,
            "Primera Federacion G1": 435, "Primera Federacion G2": 436, "Liga F": 148,
            "Ligue 1": 61, "Ligue 2": 62, "Super League Grecia": 197, "Super League 2 Grecia": 196,
            "Premier League": 39, "Championship": 40, "WSL": 44, "WSL 2": 45,
            "Serie A Italia": 135, "Serie B Italia": 136, "J1 League": 98, "J2 League": 99,
            "Eredivisie": 88, "Eerste Divisie": 89, "Liga Portugal": 94, "Liga Portugal 2": 95,
            "Taça de Portugal": 96, "Süper Lig": 203, "1. Lig": 204,
        }

        mapa_unifica_viejo = {
            'Jupiler':'Jupiler Pro League',
            'LaLiga':'LaLiga EA Sports',
            'LaLiga2':'LaLiga Hypermotion',
            'Premier':'Premier League',
            'Eredivisie':'Eredivisie'
        }

        TEMPORADAS = [2022, 2023, 2024, 2025]
        BASE = pathlib.Path(__file__).parent
        FILE_VIEJO = BASE / "ligas_2122_a_2627_SIN_DUPLICADOS.csv"

        existentes = set()
        if FILE_VIEJO.exists() and FILE_VIEJO.stat().st_size > 0:
            try:
                d = pd.read_csv(FILE_VIEJO, on_bad_lines='skip', engine='python')
                d["Date"] = pd.to_datetime(d["Date"], dayfirst=True, errors='coerce').dt.strftime("%d/%m/%Y")
                d["HomeTeam"] = d["HomeTeam"].astype(str).apply(normaliza)
                d["AwayTeam"] = d["AwayTeam"].astype(str).apply(normaliza)
                d["League"] = d["League"].astype(str).replace(mapa_unifica_viejo)
                d["Season"] = d["Season"].astype(str)
                existentes.update(zip(d["Date"], d["HomeTeam"], d["AwayTeam"], d["League"], d["Season"]))
            except:
                pass

        prog = st.progress(0.0, text="Iniciando 22/23 a 25/26...")
        total = len(MAPA_2627) * len(TEMPORADAS)
        step = 0
        nuevos_total = 0
        req_gastados = 0

        for nom, lid in MAPA_2627.items():
            for Y in TEMPORADAS:
                step += 1
                prog.progress(step/total, text=f"[{step}/{total}] {nom} {Y} | Nuevos: {nuevos_total} | Req: {req_gastados}")

                try:
                    time.sleep(0.4)
                    r = _req.get(
                        "https://v3.football.api-sports.io/fixtures",
                        headers={"x-apisports-key": API_KEY},
                        params={"league": lid, "season": Y},
                        timeout=30
                    )
                    req_gastados += 1
                except:
                    continue

                if r.status_code != 200:
                    continue

                fixtures = [f for f in r.json().get("response",[]) if f["fixture"]["status"]["short"] in ["FT","AET","PEN"]]
                if not fixtures:
                    continue

                nuevos_liga = []
                for fx in fixtures:
                    date_str = pd.to_datetime(fx["fixture"]["date"][:10]).strftime("%d/%m/%Y")
                    home = normaliza(fx["teams"]["home"]["name"])
                    away = normaliza(fx["teams"]["away"]["name"])
                    season_str = f"{Y}/{Y+1}"
                    key = (date_str, home, away, nom, season_str)
                    if key in existentes:
                        continue

                    ft_h = fx["goals"]["home"] or 0
                    ft_a = fx["goals"]["away"] or 0
                    ht_h = fx["score"]["halftime"]["home"] or 0
                    ht_a = fx["score"]["halftime"]["away"] or 0

                    row = {
                        "Date": date_str,
                        "League": nom,
                        "Season": season_str,
                        "HomeTeam": home,
                        "AwayTeam": away,
                        "FTHG": ft_h,
                        "FTAG": ft_a,
                        "HTHG": ht_h,
                        "HTAG": ht_a,
                        "FTR": "H" if ft_h > ft_a else "A" if ft_a > ft_h else "D",
                        "B365H": 0, "B365D": 0, "B365A": 0,
                        "HS": 0, "AS": 0, "HST": 0, "AST": 0, "HF": 0, "AF": 0, "HC": 0, "AC": 0,
                        "HY": 0, "AY": 0, "HR": 0, "AR": 0,
                        "fixture_id": fx["fixture"]["id"]
                    }
                    nuevos_liga.append(row)
                    existentes.add(key)

                if nuevos_liga:
                    pd.DataFrame(nuevos_liga).to_csv(
                        FILE_VIEJO,
                        mode='a',
                        header=not FILE_VIEJO.exists() or FILE_VIEJO.stat().st_size == 0,
                        index=False
                    )
                    nuevos_total += len(nuevos_liga)

        try:
            if FILE_VIEJO.exists():
                df_all = pd.read_csv(FILE_VIEJO, on_bad_lines='skip', engine='python')
                df_all["Date"] = pd.to_datetime(df_all["Date"], dayfirst=True, errors='coerce').dt.strftime("%d/%m/%Y")
                df_all["League"] = df_all["League"].astype(str).replace(mapa_unifica_viejo)
                df_all = df_all.drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League','Season'], keep='last')
                df_all.to_csv(FILE_VIEJO, index=False)
        except Exception as e:
            st.warning(f"Dedup error: {e}")

        st.success(f"✅ CSV VIEJO 22/23-25/26: {nuevos_total} nuevos | {req_gastados} requests")
        try: 
            push_csv_a_github(str(FILE_VIEJO), "ligas_2122_a_2627_SIN_DUPLICADOS.csv")
        except: pass

        st.cache_data.clear()
        time.sleep(1)
        st.rerun()
###################################################
