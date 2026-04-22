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

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp { background: #05000a; background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%); }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; margin-bottom: 20px; }
    </style>
''', unsafe_allow_html=True)

# --- 2. CARGA DE CONFIGURACIÓN ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'}}
        with open("config_pro.yaml", 'w') as f:
            yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f:
        return yaml.load(f, Loader=SafeLoader)

config = load_config()

# --- 3. SISTEMA DE AUTENTICACIÓN ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

# LOGIN DIRECTO (Sin Tabs para evitar el error de visualización)
name, authentication_status, username = authenticator.login('Login', 'main')

if st.session_state["authentication_status"] is False:
    st.error('Usuario o contraseña incorrectos')
    if st.button("¿No tienes cuenta? Regístrate aquí"):
        st.session_state["mostrar_registro"] = True

elif st.session_state["authentication_status"] is None:
    st.info('Ingresa tus credenciales para acceder.')
    # Opción de registro por si es la primera vez
    with st.expander("📝 ¿ERES NUEVO? REGÍSTRATE AQUÍ"):
        try:
            if authenticator.register_user('Registrar usuario', location='main'):
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('¡Usuario creado! Ahora ingresa tus datos arriba.')
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. APP PRINCIPAL ---
elif st.session_state["authentication_status"]:
    
    @st.cache_resource
    def get_gspread_client():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"Error de credenciales: {e}")
            st.stop()

    try:
        client = get_gspread_client()
        SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
        sh = client.open_by_key(SHEET_ID)
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("MENÚ", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    # CONTENIDO SEGÚN MENÚ
    if menu == "📊 DASHBOARD":
        df_p = pd.DataFrame(ws_p.get_all_records())
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            v = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            g = df_p['Gasto_Prod'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("VENTAS", f"${v:,.2f}")
            c2.metric("COSTOS", f"${g:,.2f}")
            c3.metric("UTILIDAD", f"${v - g:,.2f}")

    elif menu == "📦 STOCK":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.expander("➕ AGREGAR"):
            with st.form("add"):
                cat, nom = st.text_input("Categoría"), st.text_input("Nombre")
                can = st.number_input("Cantidad", min_value=0.0)
                if st.form_submit_button("Guardar"):
                    ws_i.append_row([cat, nom, "", "", "", can, ""])
                    st.rerun()
        st.dataframe(df_inv)

    elif menu == "📝 NUEVO PEDIDO":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.form("new"):
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon = st.number_input("Monto $")
            mat = st.selectbox("Material", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad", min_value=0.1)
            if st.form_submit_button("REGISTRAR"):
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                nueva = float(df_inv.at[idx, 'Cantidad']) - can_u
                ws_i.update_cell(idx+2, 6, nueva)
                ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, "", mon, "Producción", 0, ""])
                st.success("Hecho"); st.rerun()

    elif menu == "💰 COTIZADOR":
        costo = st.number_input("Inversión $")
        st.title(f"Sugerido (100%): ${costo * 2:,.2f}")
