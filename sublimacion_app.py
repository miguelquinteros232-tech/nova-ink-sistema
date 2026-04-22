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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NOVA INK - OS", layout="wide")

# --- 2. CARGA DE CONFIGURACIÓN ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'}}
        with open("config_pro.yaml", 'w') as f: yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. LOGIN ---
authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Por favor, inicia sesión para conectar con la base de datos.")
    if st.session_state.get("authentication_status") is False:
        st.error('Usuario/Contraseña incorrectos')

# --- 4. APP PRINCIPAL ---
else:
    # FUNCIÓN DE CONEXIÓN CON LIMPIEZA DE CACHÉ
    def conectar_google():
        try:
            # Forzamos que Streamlit no use datos viejos
            st.cache_resource.clear() 
            
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            gc = gspread.authorize(credentials)
            
            # ID de tu hoja
            sh = gc.open_by_key("11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8")
            return sh.worksheet("Pedidos"), sh.worksheet("Inventario")
        except Exception as e:
            return None, str(e)

    ws_p, error = conectar_google()

    if ws_p is None:
        st.error(f"❌ Error de Conexión: {error}")
        st.warning("⚠️ PASO FINAL: Ve a Google Cloud Console y asegúrate de que la 'Google Drive API' esté ACTIVADA para este proyecto. A veces solo activamos 'Google Sheets API' y gspread necesita ambas.")
        if st.button("🔄 REINTENTAR CONEXIÓN"):
            st.rerun()
        st.stop()

    # --- RESTO DEL SISTEMA (DASHBOARD, STOCK, ETC.) ---
    ws_i = error # En el return exitoso, el segundo valor no es un error
    # (Aquí sigue el código de Dashboard, Stock y Pedidos que ya tienes configurado)
    
    st.sidebar.success("✅ Conectado a Base de Datos")
    menu = st.sidebar.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
    authenticator.logout('Cerrar Sesión', 'sidebar')
    
    # ... (Copia aquí las funciones de Dashboard, Stock y Pedidos del código anterior)
