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

# --- 1. MOTOR VISUAL CORREGIDO (FONDO NEGRO + LOGIN VISIBLE) ---
st.set_page_config(page_title="NOVA INK", layout="wide")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* FONDO NEGRO TOTAL */
        .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
            background-color: #000000 !important;
        }

        /* ARREGLO PARA QUE EL LOGIN SEA VISIBLE */
        .stTextInput label, .stButton button p, .stMarkdown p, stInfo {
            color: white !important;
        }
        input {
            background-color: #111 !important;
            color: white !important;
            border: 1px solid #333 !important;
        }

        /* LOGO NOVA INK. */
        .logo-container { text-align: center; padding: 20px 0; }
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 50px; color: white; letter-spacing: -2px;
        }
        .logo-text span { color: #00d4ff; text-shadow: 0 0 15px #00d4ff; }

        /* MENÚ LATERAL: CELDAS DE LUZ */
        div[role="radiogroup"] label {
            background-color: #111 !important;
            border: 1px solid #222 !important;
            padding: 15px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            transition: 0.3s all ease !important;
        }
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0px 0px 20px rgba(0, 212, 255, 0.4) !important;
            transform: translateX(5px) !important;
        }
        div[role="radiogroup"] label p {
            color: #888 !important; font-weight: 700 !important;
        }
        div[role="radiogroup"] label:hover p { color: white !important; }

        /* TARJETAS DEL DASHBOARD */
        .glass-card {
            background: linear-gradient(145deg, #151515, #050505);
            border: 1px solid #222;
            padding: 40px;
            border-radius: 20px;
            text-align: center;
        }
    </style>
''', unsafe_allow_html=True)

st.markdown('<div class="logo-container"><div class="logo-text">NOVA INK<span>.</span></div></div>', unsafe_allow_html=True)

# --- 2. TU CONFIGURACIÓN DE USUARIOS (INTACTA) ---
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
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. PROCESO DE LOGIN ---
# Importante: location='main' para que veas el formulario en el centro
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is None:
    st.warning("Por favor, introduce tus credenciales.")
elif st.session_state.get("authentication_status") is False:
    st.error("Usuario/Contraseña incorrectos")
elif st.session_state["authentication_status"]:

    # --- 4. APLICACIÓN PRINCIPAL (TU LÓGICA DE GOOGLE SHEETS) ---
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
            st.write(f"Bienvenido, {st.session_state['name']}")
            menu = st.radio("", ["DASHBOARD", "PRODUCTOS Y PRECIOS", "STOCK", "NUEVO PEDIDO", "HISTORIAL", "MODIFICAR PEDIDO"])
            authenticator.logout('Cerrar Sesión', 'sidebar')

        if menu == "DASHBOARD":
            df_p = pd.DataFrame(ws_p.get_all_records())
            if not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_act = df_p[df_p['Estado'] != 'Vendido']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'''<div class="glass-card">
                        <p style="color:#666; font-size:12px; letter-spacing:2px;">PEDIDOS ACTIVOS</p>
                        <h1 style="color:white; font-family:'Orbitron'; font-size:55px;">{len(df_act)}</h1>
                    </div>''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''<div class="glass-card">
                        <p style="color:#666; font-size:12px; letter-spacing:2px;">BALANCE</p>
                        <h1 style="color:#bc39fd; font-family:'Orbitron'; font-size:55px;">${df_act['Monto'].sum():,.0f}</h1>
                    </div>''', unsafe_allow_html=True)
            else:
                st.write("No hay datos en la hoja de Pedidos.")

        # Aquí siguen tus otras secciones (STOCK, HISTORIAL, etc.) tal cual las tenías.
        elif menu == "STOCK":
            st.write("### Inventario Actual")
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st)
