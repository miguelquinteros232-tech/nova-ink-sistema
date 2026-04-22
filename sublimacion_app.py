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

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="NOVA OS", layout="wide")

# --- 2. MOTOR VISUAL "LUMINAL FLOW" (ESTILO IMAGEN 3) ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* FONDO NEGRO PURO */
        .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
            background-color: #0a0a0a !important;
        }
        header, footer { visibility: hidden; }

        /* LOGO "NOVA INK." */
        .logo-container { text-align: center; padding: 20px 0; }
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 50px; color: white; letter-spacing: -2px;
        }
        .logo-text span { color: #00d4ff; text-shadow: 0 0 15px #00d4ff; }

        /* MENÚ LATERAL: CELDA DE LUZ (HOVER) */
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: #151515 !important;
            border: 1px solid #252525 !important;
            padding: 15px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            transition: all 0.3s ease !important;
            display: flex !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0px 0px 20px rgba(0, 212, 255, 0.4) !important;
            background-color: #1a1a1a !important;
            transform: translateX(8px) !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label p {
            color: #888 !important; font-weight: 700 !important;
            text-transform: uppercase !important; font-size: 13px !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:hover p { color: white !important; }

        /* TARJETAS DEL DASHBOARD */
        .glass-card {
            background: linear-gradient(145deg, #181818, #0c0c0c);
            border: 1px solid #222;
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            transition: 0.4s ease;
        }
        .glass-card:hover {
            border-color: #00d4ff;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.2);
            transform: translateY(-5px);
        }
    </style>
''', unsafe_allow_html=True)

# --- 3. LÓGICA DE AUTENTICACIÓN (Tu código original simplificado) ---
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'}, 'preauthorized': {'emails': []}}
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f: yaml.dump(initial_config, f)
    with open(file_path) as f: return yaml.load(f, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# Mostrar logo siempre arriba
st.markdown('<div class="logo-container"><div class="logo-text">NOVA INK<span>.</span></div></div>', unsafe_allow_html=True)

name, authentication_status, username = authenticator.login(location='main')

if st.session_state["authentication_status"] is False:
    st.error("Usuario/Contraseña incorrectos")
elif st.session_state["authentication_status"] is None:
    st.info("Inicia sesión para continuar")
    # Aquí iría tu bloque de Registro si lo deseas...
elif st.session_state["authentication_status"]:

    # CONEXIÓN GOOGLE SHEETS
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
    
    # --- MENÚ LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.markdown(f"<h3 style='color:white; text-align:center;'>Hola, {st.session_state['name']}</h3>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 GESTIÓN PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"])
        st.write("---")
        authenticator.logout('Cerrar Sesión', 'sidebar')

    # --- NAVEGACIÓN DE SECCIONES ---
    if menu == "📊 DASHBOARD":
        ws_p = sh.worksheet("Pedidos")
        df_p = pd.DataFrame(ws_p.get_all_records())
        
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_act = df_p[df_p['Estado'] != 'Vendido']
            
            # EL DASHBOARD DE LA IMAGEN 3 (SOLO 2 CAMPOS)
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'''
                    <div class="glass-card">
                        <p style="color: #666; font-size: 14px; letter-spacing: 2px;">PEDIDOS ACTIVOS</p>
                        <h1 style="color: white; font-family: 'Orbitron'; font-size: 55px; margin: 15px 0;">{len(df_act)}</h1>
                        <div style="width: 40px; height: 2px; background: #00d4ff; margin: 0 auto; box-shadow: 0 0 10px #00d4ff;"></div>
                    </div>
                ''', unsafe_allow_html=True)
            with c2:
                st.markdown(f'''
                    <div class="glass-card">
                        <p style="color: #666; font-size: 14px; letter-spacing: 2px;">BALANCE PENDIENTE</p>
                        <h1 style="color: #bc39fd; font-family: 'Orbitron'; font-size: 55px; margin: 15px 0;">${df_act['Monto'].sum():,.0f}</h1>
                        <div style="width: 40px; height: 2px; background: #bc39fd; margin: 0 auto; box-shadow: 0 0 10px #bc39fd;"></div>
                    </div>
                ''', unsafe_allow_html=True)
            
            # Lista de detalles abajo
            st.write("---")
            for i, r in df_act.iterrows():
                with st.expander(f"🕒 {r['Cliente']} - {r['Producto']}"):
                    st.write(f"**Detalle:** {r['Detalle']} | **Monto:** ${r['Monto']}")
                    if st.button("FINALIZAR VENTA", key=f"f_{i}"):
                        ws_p.update_cell(i+2, 7, "Vendido"); st.rerun()

    elif menu == "📦 STOCK":
        # Aquí va tu código de Stock original...
        st.subheader("Control de Inventario")
        df_st = pd.DataFrame(sh.worksheet("Inventario").get_all_records())
        st.dataframe(df_st, use_container_width=True)

    # ... Resto de tus secciones (HISTORIAL, COTIZADOR)
