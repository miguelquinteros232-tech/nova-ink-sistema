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

# 1. ARMADURA VISUAL (CSS AGRESIVO)
st.set_page_config(page_title="NOVA INK", layout="wide")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* Fondo Negro Absoluto */
        .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
            background-color: #000000 !important;
        }
        header, footer { visibility: hidden; }

        /* Logo Nova Ink */
        .logo-container { text-align: center; padding: 20px 0; }
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 50px; color: white; letter-spacing: -2px;
        }
        .logo-text span { color: #00d4ff; text-shadow: 0 0 15px #00d4ff; }

        /* MENU LATERAL: CELDAS DE LUZ */
        [data-testid="stSidebarNav"] { display: none; } /* Ocultamos nav default si existe */
        
        div[role="radiogroup"] label {
            background-color: #111 !important;
            border: 1px solid #222 !important;
            padding: 20px !important;
            border-radius: 12px !important;
            margin-bottom: 12px !important;
            transition: 0.3s all ease-in-out !important;
            display: flex !important;
        }

        /* EL BRILLO CIAN DE LA IMAGEN */
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0 0 25px rgba(0, 212, 255, 0.4) !important;
            transform: translateX(10px) !important;
            background: #181818 !important;
        }

        div[role="radiogroup"] label p {
            color: #888 !important; 
            font-family: 'Inter' !important;
            font-weight: 700 !important;
            font-size: 14px !important;
        }

        div[role="radiogroup"] label:hover p { color: white !important; }

        /* DASHBOARD: TARJETAS GLASS */
        .glass-card {
            background: linear-gradient(145deg, #151515, #050505);
            border: 1px solid #222;
            padding: 45px;
            border-radius: 20px;
            text-align: center;
            transition: 0.5s;
        }
        .glass-card:hover {
            border-color: #00d4ff;
            box-shadow: 0 0 40px rgba(0, 212, 255, 0.2);
            transform: translateY(-5px);
        }
    </style>
''', unsafe_allow_html=True)

# 2. LOGO
st.markdown('<div class="logo-container"><div class="logo-text">NOVA INK<span>.</span></div></div>', unsafe_allow_html=True)

# 3. CONFIGURACIÓN (Tu lógica original)
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'}}
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f: yaml.dump(initial_config, f)
    with open(file_path) as f: return yaml.load(f, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

name, authentication_status, username = authenticator.login(location='main')

if authentication_status:
    # CONEXIÓN (Tu lógica original)
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
            st.markdown("<br>", unsafe_allow_html=True)
            # USAMOS EL RADIO SIN TEXTO PARA FORZAR EL CSS
            menu = st.radio("", ["DASHBOARD", "PRODUCTOS", "STOCK", "HISTORIAL", "COTIZADOR"])
            st.write("---")
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # 4. DASHBOARD: SOLO PEDIDOS ACTIVOS Y BALANCE
        if menu == "DASHBOARD":
            df_p = pd.DataFrame(ws_p.get_all_records())
            if not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_act = df_p[df_p['Estado'] != 'Vendido']
                
                st.markdown("<br>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f'''
                        <div class="glass-card">
                            <p style="color: #666; font-size: 14px; letter-spacing: 2px;">PEDIDOS ACTIVOS</p>
                            <h1 style="color: white; font-family: 'Orbitron'; font-size: 60px; margin: 15px 0;">{len(df_act)}</h1>
                            <div style="width: 50px; height: 2px; background: #00d4ff; margin: 0 auto; box-shadow: 0 0 10px #00d4ff;"></div>
                        </div>
                    ''', unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f'''
                        <div class="glass-card">
                            <p style="color: #666; font-size: 14px; letter-spacing: 2px;">BALANCE</p>
                            <h1 style="color: #bc39fd; font-family: 'Orbitron'; font-size: 60px; margin: 15px 0;">${df_act['Monto'].sum():,.0f}</h1>
                            <div style="width: 50px; height: 2px; background: #bc39fd; margin: 0 auto; box-shadow: 0 0 10px #bc39fd;"></div>
                        </div>
                    ''', unsafe_allow_html=True)
            
            # (Aquí puedes poner la tabla de pedidos si quieres debajo de las tarjetas)

        # 5. RESTO DE SECCIONES (Tu lógica intacta)
        elif menu == "STOCK":
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)

        # Aquí pega el resto de tus secciones (GESTIÓN PEDIDOS, etc.)
