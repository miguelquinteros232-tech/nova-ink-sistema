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

# --- 1. CONFIGURACIÓN DE PÁGINA (DEBE SER LO PRIMERO) ---
st.set_page_config(page_title="Nova Ink - Sistema", layout="wide")

# --- 2. CONFIGURACIÓN DE AUTH (LÓGICA ORIGINAL) ---
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

# --- 3. ESTILO VISUAL REPLICADO DE LA IMAGEN ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');
        
        /* Fondo Negro en toda la App */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #000000 !important;
        }

        /* Sidebar Oscuro y Borde */
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background-color: #050505 !important;
            border-right: 1px solid #1a1a1a !important;
        }

        /* Títulos y textos generales */
        h1, h2, h3, p, span, label { 
            color: white !important; 
            font-family: 'Inter', sans-serif;
        }

        /* --- ESTILO DE BOTONES DE NAVEGACIÓN (RADIO) --- */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
            gap: 12px !important;
            padding: 0 !important;
        }

        /* Cada botón del menú */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
            background: #0d0d0d !important;
            border: 1px solid #1a1a1a !important;
            padding: 15px 20px !important;
            border-radius: 12px !important;
            margin-bottom: 5px !important;
            transition: all 0.3s ease-in-out !important;
            cursor: pointer !important;
            width: 100% !important;
        }

        /* Efecto al pasar el mouse (Hover) */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            transform: translateX(5px) !important;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.1) !important;
        }

        /* Botón SELECCIONADO (Azul Neón) */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] label {
            border: 1.5px solid #00d4ff !important;
            background: rgba(0, 212, 255, 0.05) !important;
        }

        /* Texto del botón seleccionado */
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] label p {
            color: #00d4ff !important;
            font-weight: bold !important;
            text-shadow: 0 0 8px rgba(0, 212, 255, 0.4) !important;
        }

        /* Limpieza de elementos nativos de Streamlit */
        [data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"] { display: none !important; }
        [data-testid="stSidebar"] .stRadio label [data-testid="stCheckbox"] { display: none !important; }

        /* Tarjetas de Dashboard estilo Billing */
        .metric-card {
            background: linear-gradient(145deg, #0d0d0d, #050505);
            border: 1px solid #222;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
        }
    </style>
''', unsafe_allow_html=True)

# --- 4. LOGIN Y REGISTRO (LÓGICA ORIGINAL) ---
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Inicia sesión o regístrate para gestionar Nova Ink.")
    with st.expander("📝 REGISTRO"):
        with st.form("registro_manual"):
            new_email = st.text_input("Correo electrónico")
            new_username = st.text_input("Nombre de Usuario")
            new_name = st.text_input("Nombre Completo")
            new_password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("REGISTRAR"):
                if new_email and new_username and new_password:
                    hashed_password = stauth.Hasher([new_password]).generate()[0]
                    config['credentials']['usernames'][new_username] = {
                        'email': new_email, 'name': new_name, 'password': hashed_password
                    }
                    with open("config_pro.yaml", 'w') as f: yaml.dump(config, f, default_flow_style=False)
                    st.success("Usuario creado."); time.sleep(1); st.rerun()

# --- 5. APLICACIÓN PRINCIPAL (TU LÓGICA CON EL NUEVO ESTILO) ---
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
            # LOGO NOVA INK ESTILO IMAGEN
            st.write(f'''
                <div style="text-align: center; padding: 20px 0; margin-bottom: 10px;">
                    <h1 style="font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #FFFFFF !important; text-shadow: 0 0 15px #00d4ff;">
                        NOVA INK<span style="color: #00d4ff !important;">.</span>
                    </h1>
                </div>
            ''', unsafe_allow_html=True)
            
            menu = st.radio("", ["📊 DASHBOARD", "🛍️ PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"], key="nav_nova")
            st.write("---")
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # --- SECCIONES (LÓGICA INTACTA) ---
        if "📊 DASHBOARD" in menu:
            try:
                data_p = ws_p.get_all_records()
                df_p = pd.DataFrame(data_p)
                df_p.columns = [str(c).strip() for c in df_p.columns]
                df_act = df_p[df_p['Estado'] != 'Vendido'] if not df_p.empty else pd.DataFrame()
                df_vendidos = df_p[df_p['Estado'] == 'Vendido'] if not df_p.empty else pd.DataFrame()
                v_monto = pd.to_numeric(df_vendidos['Monto'], errors='coerce').sum()
            except:
                v_monto, df_act = 0, pd.DataFrame()

            col1, col2 = st.columns(2)
            with col1:
                st.write(f'<div class="metric-card"><p style="color: #666; font-size: 12px; font-weight: bold; letter-spacing: 2px;">PEDIDOS ACTIVOS</p><h2 style="font-family: Orbitron; font-size: 45px;">{len(df_act)}</h2></div>', unsafe_allow_html=True)
            with col2:
                st.write(f'<div class="metric-card"><p style="color: #666; font-size: 12px; font-weight: bold; letter-spacing: 2px;">VENTAS REALIZADAS</p><h2 style="color: #00d4ff; font-family: Orbitron; font-size: 45px;">${v_monto:,.0f}</h2></div>', unsafe_allow_html=True)
            
            st.write("### 🔍 GESTIÓN RÁPIDA")
            if not df_act.empty:
                for i, row in df_act.iterrows():
                    with st.expander(f"🔹 {row.get('Cliente', 'S/N')} | {row.get('Producto', 'S/P')}"):
                        c1, c2 = st.columns(2)
                        if c1.button("✅ VENDIDO", key=f"v_{i}"):
                            ws_p.update_cell(i+2, 7, "Vendido"); st.rerun()
                        if c2.button("❌ ELIMINAR", key=f"d_{i}"):
                            ws_p.delete_rows(i+2); st.rerun()
            else:
                st.info("Sin pedidos activos.")

        # Aquí continuarían las demás secciones (PEDIDOS, STOCK, etc.) manteniendo tu lógica original.
        elif "🛍️ PEDIDOS" in menu:
            st.write("## Gestión de Pedidos")
            # (...) resto de tu código original
