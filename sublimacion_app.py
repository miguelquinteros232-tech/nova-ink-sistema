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

# --- 1. CONFIGURACIÓN DE PÁGINA (ESTO DEBE IR PRIMERO) ---
st.set_page_config(page_title="Nova Ink", layout="wide", initial_sidebar_state="expanded")

# --- 2. INYECCIÓN DE ESTILO FORZADA (EL DISEÑO DE LA IMAGEN) ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');
        
        /* Forzar fondo negro en toda la app */
        .stApp {
            background-color: #000000 !important;
        }

        /* Sidebar: Negro profundo y borde sutil */
        [data-testid="stSidebar"] {
            background-color: #050505 !important;
            border-right: 1px solid #1a1a1a !important;
        }

        /* Títulos en blanco con fuente Orbitron */
        h1, h2, h3, h4, h5, h6, .stMarkdown p {
            color: #ffffff !important;
            font-family: 'Inter', sans-serif;
        }

        /* ESTILO DE LOS BOTONES DEL MENÚ (RADIO) */
        /* Contenedor principal de los botones */
        div[role="radiogroup"] {
            gap: 10px !important;
            padding-top: 20px !important;
        }

        /* Cada botón individual */
        div[role="radiogroup"] label {
            background-color: #0d0d0d !important;
            border: 1px solid #1a1a1a !important;
            border-radius: 10px !important;
            padding: 12px 20px !important;
            transition: all 0.3s ease !important;
            margin-bottom: 5px !important;
        }

        /* Cuando pasas el mouse por encima */
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            transform: translateX(5px) !important;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.2) !important;
        }

        /* Cuando el botón está seleccionado */
        div[role="radiogroup"] [aria-checked="true"] label {
            border: 1px solid #00d4ff !important;
            background-color: rgba(0, 212, 255, 0.05) !important;
        }

        /* Texto del botón seleccionado */
        div[role="radiogroup"] [aria-checked="true"] label p {
            color: #00d4ff !important;
            font-weight: bold !important;
            text-shadow: 0 0 5px rgba(0, 212, 255, 0.5) !important;
        }

        /* Ocultar los círculos feos de los radio buttons */
        div[role="radiogroup"] [data-testid="stWidgetLabel"] { display: none !important; }
        div[role="radiogroup"] label [data-testid="stCheckbox"] { display: none !important; }
        
        /* Tarjetas del Dashboard */
        .metric-container {
            background: linear-gradient(145deg, #0d0d0d, #050505) !important;
            border: 1px solid #222 !important;
            padding: 25px !important;
            border-radius: 15px !important;
            text-align: center !important;
        }
    </style>
''', unsafe_allow_html=True)

# --- 3. LÓGICA DE CONFIGURACIÓN ---
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

# --- 4. LOGIN ---
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Inicia sesión en Nova Ink.")
    # (El bloque de registro se mantiene igual...)
    with st.expander("📝 REGISTRO"):
        with st.form("reg"):
            ne, nu, nn, np = st.text_input("Email"), st.text_input("User"), st.text_input("Nombre"), st.text_input("Pass", type="password")
            if st.form_submit_button("REGISTRAR"):
                hashed = stauth.Hasher([np]).generate()[0]
                config['credentials']['usernames'][nu] = {'email': ne, 'name': nn, 'password': hashed}
                with open("config_pro.yaml", 'w') as f: yaml.dump(config, f)
                st.success("OK"); st.rerun()

# --- 5. APP PRINCIPAL ---
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
            # TÍTULO ESTILO LOGO
            st.markdown(f'''
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="font-family: 'Orbitron'; font-size: 30px; letter-spacing: 2px;">
                        NOVA INK<span style="color: #00d4ff;">.</span>
                    </h1>
                </div>
            ''', unsafe_allow_html=True)
            
            menu = st.radio("", ["📊 DASHBOARD", "🛍️ PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"], key="nav")
            st.write("---")
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # --- SECCIONES ---
        if "📊 DASHBOARD" in menu:
            try:
                df_p = pd.DataFrame(ws_p.get_all_records())
                df_p.columns = [str(c).strip() for c in df_p.columns]
                df_act = df_p[df_p['Estado'] != 'Vendido']
                df_vend = df_p[df_p['Estado'] == 'Vendido']
                v_monto = pd.to_numeric(df_vend['Monto'], errors='coerce').sum()
            except:
                v_monto, df_act = 0, pd.DataFrame()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="metric-container"><p style="color:#666; font-size:12px; font-weight:bold;">PEDIDOS ACTIVOS</p><h2>{len(df_act)}</h2></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-container"><p style="color:#666; font-size:12px; font-weight:bold;">VENTAS REALIZADAS</p><h2 style="color:#00d4ff;">${v_monto:,.0f}</h2></div>', unsafe_allow_html=True)
            
            st.write("### 🔍 Gestión Pendientes")
            if not df_act.empty:
                for i, row in df_act.iterrows():
                    with st.expander(f"🔹 {row.get('Cliente', 'S/N')} - {row.get('Producto', 'S/P')}"):
                        c1, c2 = st.columns(2)
                        if c1.button("✅ VENDIDO", key=f"v_{i}"):
                            ws_p.update_cell(i+2, 7, "Vendido"); st.rerun()
                        if c2.button("❌ BORRAR", key=f"d_{i}"):
                            ws_p.delete_rows(i+2); st.rerun()

        # (Aquí siguen el resto de tus secciones de Pedidos, Stock, etc. sin cambios en la lógica)
        elif "🛍️ PEDIDOS" in menu:
            st.write("### Gestión de Pedidos")
            # ... resto de tu código de pedidos ...
