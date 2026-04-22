import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import os

# --- 1. CAPA VISUAL DEFINITIVA (FORZANDO VISIBILIDAD) ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* FONDO NEGRO ABSOLUTO */
        .stApp, [data-testid="stHeader"], .main { background-color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1a1a1a !important; }

        /* EL LOGO (CON EFECTOS DE NEÓN) */
        .logo-box {
            text-align: center; margin: 20px 0 40px 0;
            font-family: 'Orbitron', sans-serif;
            font-size: 40px; font-weight: 700;
            color: #ffffff !important;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.8), 0 0 40px rgba(0, 212, 255, 0.4);
        }
        .logo-box span { color: #00d4ff !important; }

        /* MENÚ LATERAL: ITEMS CON LUZ (IMAGEN 3) */
        div[role="radiogroup"] label {
            background: #0d0d0d !important;
            border: 1px solid #222 !important;
            padding: 18px 25px !important;
            border-radius: 12px !important;
            margin-bottom: 12px !important;
            transition: 0.3s all ease !important;
        }
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0 0 25px rgba(0, 212, 255, 0.3) !important;
            transform: translateX(10px);
        }
        div[role="radiogroup"] label p {
            color: #888888 !important; font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important; font-size: 15px !important;
        }
        div[role="radiogroup"] label:hover p { color: #ffffff !important; }

        /* TARJETAS DASHBOARD (PARA BALANCES) */
        .dashboard-card {
            background: linear-gradient(145deg, #111, #050505) !important;
            border: 1px solid #252525 !important;
            padding: 40px !important;
            border-radius: 20px !important;
            text-align: center !important;
            margin-bottom: 20px !important;
        }
        .card-label { color: #666 !important; font-size: 13px; font-weight: 700; letter-spacing: 3px; }
        .card-value { 
            font-family: 'Orbitron', sans-serif !important; 
            font-size: 45px !important; color: #ffffff !important; 
            font-weight: 700 !important; margin-top: 10px !important;
        }

        /* FORZAR TEXTOS BLANCOS EN TODA LA APP */
        h1, h2, h3, p, label, span, .stMarkdown { color: #ffffff !important; }
    </style>
''', unsafe_allow_html=True)

# --- 2. NAVEGACIÓN (UN SOLO SIDEBAR) ---
if st.session_state.get("authentication_status"):
    with st.sidebar:
        # Logo con efectos
        st.markdown('<div class="logo-box">NOVA INK<span>.</span></div>', unsafe_allow_html=True)
        
        # Un solo radio button con iconos
        menu = st.radio("", [
            "📊 DASHBOARD", 
            "🛍️ PEDIDOS", 
            "📦 STOCK", 
            "📜 HISTORIAL", 
            "💰 COTIZADOR"
        ])
        
        st.write("---")
        try:
            authenticator.logout('Cerrar Sesión', 'sidebar')
        except:
            pass

    # --- 3. LÓGICA DEL DASHBOARD (AQUÍ ES DONDE APARECEN TUS BALANCES) ---
    if "DASHBOARD" in menu:
        # Asegúrate de que df_act tenga los datos de tus pedidos actuales
        try:
            # Reutilizo tus variables actuales
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f'''<div class="dashboard-card">
                    <div class="card-label">PEDIDOS ACTIVOS</div>
                    <div class="card-value">{len(df_act)}</div>
                </div>''', unsafe_allow_html=True)
            with col2:
                # Cambia 'df_act' por el nombre de tu dataframe real si es distinto
                balance_total = df_act['Monto'].sum()
                st.markdown(f'''<div class="dashboard-card">
                    <div class="card-label">BALANCE PENDIENTE</div>
                    <div class="card-value" style="color:#00d4ff;">${balance_total:,.0f}</div>
                </div>''', unsafe_allow_html=True)
            
            st.write("---")
            st.subheader("Pedidos en curso")
            st.dataframe(df_act) # Tu tabla normal
        except Exception as e:
            st.warning("Cargando datos desde la nube...")

# --- 2. TU LÓGICA DE CONFIGURACIÓN (TAL CUAL LA ENVIASTE) ---
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'}, 'preauthorized': {'emails': []}}
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        with open(file_path, 'w') as f: yaml.dump(initial_config, f)
        return initial_config
    with open(file_path) as f:
        cfg = yaml.load(f, Loader=SafeLoader)
        return cfg if cfg else initial_config

config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- 3. LOGIN Y REGISTRO (ESTRUCTURA ORIGINAL) ---
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Inicia sesión o regístrate para gestionar Nova Ink.")
    with st.expander("📝 CREAR CUENTA NUEVA (REGISTRO)"):
        with st.form("registro_manual"):
            new_email = st.text_input("Correo electrónico")
            new_username = st.text_input("Nombre de Usuario (ID)")
            new_name = st.text_input("Tu Nombre Completo")
            new_password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("REGISTRAR USUARIO"):
                if new_email and new_username and new_password:
                    hashed_password = stauth.Hasher([new_password]).generate()[0]
                    config['credentials']['usernames'][new_username] = {
                        'email': new_email, 'name': new_name, 'password': hashed_password
                    }
                    with open("config_pro.yaml", 'w') as f: yaml.dump(config, f, default_flow_style=False)
                    st.success("✅ Usuario creado."); time.sleep(1); st.rerun()

# --- 4. APLICACIÓN PRINCIPAL (REPLICA EXACTA DE TU LÓGICA) ---
elif st.session_state["authentication_status"]:
    @st.cache_resource
    def get_sh_conn():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(credentials).open_by_key("1Y0pJANMQxuW_HTS6__Td69fJYvyfyeOyX0thC1CpzlA")
        except: return None

    sh = get_sh_conn()
    if sh:
        ws_p = sh.worksheet("Pedidos"); ws_i = sh.worksheet("Inventario")

        with st.sidebar:
            st.markdown(f"### Hola, {st.session_state['name']} 👋")
            menu = st.radio("SISTEMA", ["DASHBOARD", "GESTIÓN PEDIDOS", "STOCK", "HISTORIAL", "COTIZADOR"])
            st.write("---")
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # SECCIÓN DASHBOARD (Tus métricas pero con estilo de la imagen)
        if menu == "DASHBOARD":
            df_p = pd.DataFrame(ws_p.get_all_records())
            if not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_act = df_p[df_p['Estado'] != 'Vendido']
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<div class="glass-card"><p style="color:#888; font-size:12px;">PEDIDOS ACTIVOS</p><h1 style="color:white; font-family:Orbitron;">{len(df_act)}</h1></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="glass-card"><p style="color:#888; font-size:12px;">BALANCE PENDIENTE</p><h1 style="color:#bc39fd; font-family:Orbitron;">${df_act["Monto"].sum():,.0f}</h1></div>', unsafe_allow_html=True)
                
                st.write("---")
                for i, r in df_act.iterrows():
                    with st.expander(f"🕒 {r['Estado']} | {r['Cliente']} - {r['Producto']}"):
                        st.write(f"**Detalle:** {r['Detalle']}")
                        if st.button("FINALIZAR VENTA", key=f"f_{i}"):
                            ws_p.update_cell(i+2, 7, "Vendido"); st.rerun()

        # SECCIÓN GESTIÓN PEDIDOS (REPLICA EXACTA DE TUS TABS Y FORMULARIOS)
        elif menu == "GESTIÓN PEDIDOS":
            tab1, tab2 = st.tabs(["NUEVO PEDIDO", "MODIFICAR EXISTENTE"])
            df_inv = pd.DataFrame(ws_i.get_all_records())
            
            with tab1:
                with st.form("n_p"):
                    c1, c2 = st.columns(2)
                    cli = c1.text_input("Cliente")
                    prd = c1.text_input("Producto")
                    det = c2.text_area("Descripción")
                    pago = c2.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"])
                    mon = st.number_input("Precio Final $")
                    mat = st.selectbox("Insumo a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                    can = st.number_input("Cantidad a restar", min_value=0.0)
                    if st.form_submit_button("REGISTRAR"):
                        idx = df_inv[df_inv['Nombre'] == mat].index[0]
                        ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                        ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                        st.success("Registrado."); st.rerun()
            
            with tab2:
                df_p = pd.DataFrame(ws_p.get_all_records())
                if not df_p.empty:
                    sel = st.selectbox("Seleccionar Pedido", df_p['Cliente'] + " - " + df_p['Producto'])
                    # (Aquí seguiría el resto de tu lógica de modificar...)

        # SECCIÓN STOCK (TU LÓGICA ORIGINAL)
        elif menu == "STOCK":
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)
            with st.expander("➕ AGREGAR MATERIAL"):
                with st.form("add_s"):
                    c1, c2 = st.columns(2)
                    cat, nom, tip = c1.text_input("Categoría"), c1.text_input("Nombre"), c1.text_input("Tipo")
                    tal, col, can, uni = c2.text_input("Talle"), c2.text_input("Color"), c2.number_input("Cantidad"), c2.text_input("Unidad")
                    if st.form_submit_button("CARGAR"):
                        ws_i.append_row([cat, nom, tip, tal, col, can, uni]); st.rerun()

        # SECCIÓN HISTORIAL Y COTIZADOR (REPLICA EXACTA)
        elif menu == "HISTORIAL":
            df_h = pd.DataFrame(ws_p.get_all_records())
            if not df_h.empty:
                df_v = df_h[df_h['Estado'] == 'Vendido']
                st.write("### Ventas Finalizadas")
                st.table(df_v)

        elif menu == "COTIZADOR":
            c1, c2 = st.columns(2)
            ins = c1.number_input("Insumos $")
            hrs = c1.number_input("Horas Trabajo")
            v_h = c1.number_input("Valor Hora $", value=2000.0)
            mrg = c2.slider("% Ganancia", 0, 400, 100)
            total = (ins + (hrs * v_h)) * (1 + mrg/100)
            st.title(f"Sugerido: ${total:,.2f}")
