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

# --- 1. ESTILO "HARD-CODED" (PARA FORZAR LA APARIENCIA DE LA IMAGEN) ---
st.set_page_config(page_title="NOVA INK", layout="wide")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* FONDO NEGRO TOTAL */
        .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
            background-color: #000000 !important;
        }
        header, footer { visibility: hidden; }

        /* LOGO NOVA INK. */
        .logo-container { text-align: center; padding: 20px 0; }
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 50px; color: white; letter-spacing: -2px;
        }
        .logo-text span { color: #00d4ff; text-shadow: 0 0 15px #00d4ff; }

        /* MENU LATERAL: FORZAR ILUMINACIÓN */
        /* Este selector es más agresivo para atrapar tus opciones actuales */
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: #111111 !important;
            border: 1px solid #222 !important;
            padding: 15px !important;
            border-radius: 12px !important;
            margin-bottom: 8px !important;
            transition: 0.3s all ease !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0px 0px 20px rgba(0, 212, 255, 0.4) !important;
            transform: translateX(5px) !important;
            background-color: #161616 !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label p {
            color: #888 !important; font-weight: 700 !important;
            font-family: 'Inter', sans-serif !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:hover p {
            color: white !important;
        }

        /* DASHBOARD: TARJETAS DE LA IMAGEN */
        .glass-card {
            background: linear-gradient(145deg, #151515, #050505);
            border: 1px solid #222;
            padding: 35px;
            border-radius: 20px;
            text-align: center;
            transition: 0.4s ease;
        }
        .glass-card:hover {
            border-color: #00d4ff;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.2);
        }
    </style>
''', unsafe_allow_html=True)

# Logo siempre visible arriba
st.markdown('<div class="logo-container"><div class="logo-text">NOVA INK<span>.</span></div></div>', unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN DE USUARIOS (TU LÓGICA) ---
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'}}
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f: yaml.dump(initial_config, f)
    with open(file_path) as f:
        cfg = yaml.load(f, Loader=SafeLoader)
        return cfg if cfg else initial_config

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. LOGIN ---
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Inicia sesión para gestionar Nova Ink.")
    # (Aquí va tu bloque de registro tal cual lo tenías)

elif st.session_state["authentication_status"]:
    # CONEXIÓN GSHEETS (TU LÓGICA)
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
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")

        with st.sidebar:
            st.markdown(f"<p style='color:white; text-align:center;'>Usuario: {st.session_state['name']}</p>", unsafe_allow_html=True)
            # RADIO SIN TÍTULO PARA QUE EL CSS FUNCIONE
            menu = st.radio("", ["DASHBOARD", "GESTIÓN PEDIDOS", "STOCK", "HISTORIAL", "COTIZADOR"])
            st.write("---")
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # --- A. DASHBOARD (SOLO PEDIDOS Y BALANCE) ---
        if menu == "DASHBOARD":
            df_p = pd.DataFrame(ws_p.get_all_records())
            if not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_act = df_p[df_p['Estado'] != 'Vendido']
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'''<div class="glass-card">
                        <p style="color:#666; font-size:12px; letter-spacing:2px;">PEDIDOS ACTIVOS</p>
                        <h1 style="color:white; font-family:'Orbitron'; font-size:50px; margin:10px 0;">{len(df_act)}</h1>
                        <div style="width:40px; height:2px; background:#00d4ff; margin:0 auto;"></div>
                    </div>''', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'''<div class="glass-card">
                        <p style="color:#666; font-size:12px; letter-spacing:2px;">BALANCE PENDIENTE</p>
                        <h1 style="color:#bc39fd; font-family:'Orbitron'; font-size:50px; margin:10px 0;">${df_act['Monto'].sum():,.0f}</h1>
                        <div style="width:40px; height:2px; background:#bc39fd; margin:0 auto;"></div>
                    </div>''', unsafe_allow_html=True)
                
                # Lista de pedidos debajo
                st.write("### Tareas Pendientes")
                for i, r in df_act.iterrows():
                    with st.expander(f"📦 {r['Cliente']} - {r['Producto']}"):
                        st.write(f"Estado: {r['Estado']} | Pago: {r['Notas']}")
                        if st.button("FINALIZAR VENTA", key=f"f_{i}"):
                            ws_p.update_cell(i+2, 7, "Vendido"); st.rerun()

        # --- SECCIONES RESTANTES (MANTIENEN TU LÓGICA) ---
        elif menu == "STOCK":
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)
            # ... resto de tu código de stock ...

        # ... (Agrega aquí el resto de tus bloques: GESTIÓN PEDIDOS, HISTORIAL, etc. tal cual los tenías)
