import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Pronóstico SAVC - Gestión de Turnos", layout="wide")

def login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.title("🔐 Acceso Sistema Pronóstico")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if "passwords" in st.secrets and u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Credenciales incorrectas")
        return False
    return True

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_ABR = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TURNOS = ["Mañana (06-15)", "Tarde (15-24)"]

def crear_pdf(df_final, mes_nombre, anio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    t_pdf = f"CRONOGRAMA PRONOSTICADORES - {mes_nombre.upper()} {anio}"
    pdf.cell(190, 10, t_pdf.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(31, 73, 125) # Azul oscuro para Pronóstico
    pdf.set_text_color(255, 255, 255)
    pdf.cell(50, 10, "FECHA", border=1, align="C", fill=True)
    pdf.cell(70, 10, "MANANA (06-15)", border=1, align="C", fill=True)
    pdf.cell(70, 10, "TARDE (15-24)", border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    f_p = False
    for _, r in df_final.iterrows():
        pdf.set_fill_color(245, 245, 245)
        f_val = str(r['Fecha']).encode('latin-1', 'replace').decode('latin-1')
        m_val = str(r['Mañana (06-15)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        t_val = str(r['Tarde (15-24)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(50, 8, f_val, border=1, align="C", fill=f_p)
        pdf.cell(70, 8, m_val, border=1, align="C", fill=f_p)
        pdf.cell(70, 8, t_val, border=1, align="C", fill=f_p)
        pdf.ln()
        f_p = not f_p
    return pdf.output(dest='S').encode('latin-1', 'ignore')

if login():
    st.sidebar.header("⚡ Panel de Control")
    m_nom = st.sidebar.selectbox("Mes a planificar", MESES_ES, index=datetime.now().month - 1)
    m_nro = MESES_ES.index(m_nom) + 1
    a_nro = st.sidebar.number_input("Año", value=2026)
    
    st.sidebar.divider()
    L_M = st.sidebar.number_input("Límite mensual (Hs)", value=130)
    C_S = st.sidebar.slider("Tope semanal (Hs)", 20, 60, 48)
    MAX_SEG = st.sidebar.number_input("Máximo días seguidos", value=5)

    # Equipo Pronóstico
    empleados = ["Jones", "Wiertz", "Sánchez"]
    
    cfg = {}
    for e in empleados:
        with st.sidebar.expander(f"👤 {e}"):
            lic_in = st.date_input(f"Licencia/Afectación {e}", value=[], key=f"l_{e}")
            ff = st.multiselect(f"Francos fijos:", range(1, 32), key=f"f_{e}")
            pref = st.radio("Preferencia:", ["Ambos", "Solo Mañana", "Solo Tarde"], key=f"p_{e}", horizontal=True)
            bl = []
            c1, c2 = st.columns(2)
            for i, d_n in enumerate(DIAS_ES):
                col = c1 if i < 4 else c2
                if col.checkbox(f"{d_n} M", key=f"m_{e}_{d_n}"): bl.append((d_n, TURNOS[0]))
                if col.checkbox(f"{d_n} T", key=f"t_{e}_{d_n}"): bl.append((d_n, TURNOS[1]))
            fl = []
            if len(lic_in) == 2:
                fl = pd.date_range(start=lic_in[0], end=lic_in[1]).date
            cfg[e] = {"lic": fl, "fra": ff, "blo": bl, "pref": pref}

    if st.button("🚀 GENERAR CRONOGRAMA PRONÓSTICO"):
        n_d = calendar.monthrange(a_nro, m_nro)[1]
        cron, h_t, h_s = [], {e: 0 for e in empleados}, {e: 0 for e in empleados}
        seguidos = {e: 0 for e in empleados}
        t_ayer, s_act = None, None

        for d in range(1, n_d + 1):
            f_dt = datetime(a_nro, m_nro, d)
            idx_s, n_dia = f_dt.weekday(), DIAS_ES[f_dt.weekday()]
            i_sem = f_dt.isocalendar()[1]
            if i_sem != s_act:
                h_s, s_act = {e: 0 for e in empleados}, i_sem
            
            hs_v = 18 if idx_s >= 5 else 9
            f_str = f"{DIAS_ABR[idx_s]} {f_dt.strftime('%d/%m/%Y')}"
            h_hoy = [] 
            
            for t in TURNOS:
                cand = []
                for e in empleados:
                    es_lic = f_dt.date() in cfg[e]["lic"]
                    es_fra = d in cfg[e]["fra"]
                    es_blo = (n_dia, t) in cfg[e]["blo"]
                    ya_trabajo_hoy = e in h_hoy
                    desc_min = not (t == TURNOS[0] and e == t_ayer)
                    
                    l_m = h_t[e] + hs_v <= L_M
                    l_s = h_s[e] + hs_v <= C_S
                    l_seg = seguidos[e] < MAX_SEG
                    
                    p_ok = True
                    if cfg[e]["pref"] == "Solo Mañana" and t != TURNOS[0]: p_ok = False
                    if cfg[e]["pref"] == "Solo Tarde" and t != TURNOS[1]: p_ok = False
                    
                    if not any([es_lic, es_fra, es_blo, ya_trabajo_hoy]) and desc_min and l_m and l_s and l_seg and p_ok:
                        cand.append(e)
                
                # Sorteo por el que menos horas tiene acumuladas
                cand.sort(key=lambda x: h_t[x])
                el = cand[0] if cand else "[VACANTE]"
                cron.append({"n": d, "Fecha": f_str, "Turno": t, "Empleado": el})
                
                if el != "[VACANTE]":
                    h_t[el], h_s[el] = h_t[el] + hs_v, h_s[el] + hs_v
                    h_hoy.append(el)
                    seguidos[el] += 1
                    if t == TURNOS[1]: t_ayer = el
                else:
                    if t == TURNOS[1]: t_ayer = None
            
            for e in empleados:
                if e not in h_hoy: seguidos[e] = 0

        if len(cron) > 0:
            df = pd.DataFrame(cron)
            df_c = df.pivot_table(index=['n', 'Fecha'], columns='Turno', values='Empleado', aggfunc='first').reset_index()
            df_c = df_c.sort_values('n').drop(columns='n')
            st.subheader(f"Vista Previa Planilla: {m_nom}")
            st.dataframe(df_c, use_container_width=True)
            
            p_bytes = crear_pdf(df_c, m_nom, a_nro)
            st.download_button(label="📥 Descargar PDF Pronosticadores", data=p_bytes, file_name=f"Turnos_Pronostico_{m_nom}.pdf", mime="application/pdf")
            
            st.divider()
            st.subheader("📊 Control de Carga Horaria")
            cols = st.columns(len(empleados))
            for i, e in enumerate(empleados):
                cols[i].metric(e, f"{h_t[e]} hs")
                cols[i].progress(min(h_t[e]/L_M, 1.0))
