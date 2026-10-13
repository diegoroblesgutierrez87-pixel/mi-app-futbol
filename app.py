    if not partidos_sel and not tiene_manuales:
        st.caption("Selecciona partido futuro o equipo manual")
    else:
        # --- PARA CADA PARTIDO FUTURO ELEGIDO, PINTA HISTORIAL DE LOS 2 EQUIPOS ---
        partidos_pred_copy = [] # para boton copiar
