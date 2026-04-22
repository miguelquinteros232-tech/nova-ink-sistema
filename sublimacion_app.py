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

import streamlit as st
import pandas as pd

# --- 2. TU LÓGICA DE CONFIGURACIÓN (MANTENIDA) ---
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

# --- INYECCIÓN DE ESTILO "IMAGEN 3" (NUEVO) ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;600&display=swap');
        
        /* Fondo y Sidebar */
        .stApp { background-color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1a1a1a !important; }
        
        /* Botones de Menú Estilo Premium */
        div[role="radiogroup"] label {
            background: #0d0d0d !important;
            border: 1px solid #1a1a1a !important;
            padding: 15px 20px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            transition: 0.3s all ease-in-out;
        }
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
            transform: translateX(5px);
        }
        div[role="radiogroup"] label p { color: #888 !important; font-weight: 600 !important; font-size: 14px !important; }
        div[role="radiogroup"] [aria-checked="true"] label { border-left: 5px solid #00d4ff !important; border-color: #1a1a1a !important; }
        div[role="radiogroup"] [aria-checked="true"] label p { color: #ffffff !important; }

        /* Estilo de Tablas y Dataframes */
        .stDataFrame { border: 1px solid #1a1a1a !important; border-radius: 10px !important; }
    </style>
''', unsafe_allow_html=True)

# --- 3. LOGIN Y REGISTRO ---
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

# --- 4. APLICACIÓN PRINCIPAL ---
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
            # LOGO NOVA INK MEJORADO
            st.write(f'''
                <div style="text-align: center; padding: 30px 0; margin-bottom: 20px;">
                    <h1 style="font-family: 'Orbitron', sans-serif; font-size: 38px; color: #FFFFFF !important; text-shadow: 0 0 20px #00d4ff; margin: 0;">
                        NOVA INK<span style="color: #00d4ff !important;">.</span>
                    </h1>
                    <p style="color: #444; font-size: 10px; letter-spacing: 3px; margin-top: -5px;">MANAGEMENT SYSTEM</p>
                </div>
            ''', unsafe_allow_html=True)
            
            menu = st.radio("", ["📊 DASHBOARD", "🛍️ PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"], key="nav_nova_ink")

        # SECCIÓN DASHBOARD (Estilo Imagen 3 Mejorado)
        if "📊 DASHBOARD" in menu:
            try:
                # Tu lógica de datos se mantiene igual
                df_p = pd.DataFrame(ws_p.get_all_records())
                df_act = df_p[df_p['Estado'] != 'Vendido'] if not df_p.empty else pd.DataFrame()
                v_pedidos = len(df_act)
                v_monto = pd.to_numeric(df_act['Monto'], errors='coerce').sum()
            except:
                v_pedidos, v_monto = 0, 0

            col1, col2 = st.columns(2)
            with col1:
                st.write(f'''
                    <div style="background: linear-gradient(145deg, #0d0d0d, #050505); border: 1px solid #1a1a1a; padding: 35px; border-radius: 20px; text-align: center; box-shadow: 10px 10px 20px #030303;">
                        <p style="color: #666 !important; font-family: 'Inter'; font-size: 11px; font-weight: bold; letter-spacing: 2px; margin: 0; text-transform: uppercase;">Pedidos Activos</p>
                        <h2 style="color: #FFFFFF !important; font-family: 'Orbitron'; font-size: 50px; margin: 10px 0 0 0;">{v_pedidos}</h2>
                    </div>
                ''', unsafe_allow_html=True)
                
            with col2:
                st.write(f'''
                    <div style="background: linear-gradient(145deg, #0d0d0d, #050505); border: 1px solid #1a1a1a; padding: 35px; border-radius: 20px; text-align: center; box-shadow: 10px 10px 20px #030303;">
                        <p style="color: #666 !important; font-family: 'Inter'; font-size: 11px; font-weight: bold; letter-spacing: 2px; margin: 0; text-transform: uppercase;">Balance Pendiente</p>
                        <h2 style="color: #00d4ff !important; font-family: 'Orbitron'; font-size: 50px; margin: 10px 0 0 0;">${v_monto:,.0f}</h2>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.write("###")
            if not df_act.empty:
                st.dataframe(df_act, use_container_width=True)

        # --- RESTO DE SECCIONES (Siguen funcionando igual) ---
        elif menu == "🛍️ PEDIDOS":
            # Aquí va tu lógica de pedidos (mantenida)
            st.title("Gestión de Pedidos")
            
        elif menu == "📦 STOCK":
            # Aquí va tu lógica de stock (mantenida)
            st.title("Inventario")

        # ... (Mantener el resto de elif exactamente como los tienes)
