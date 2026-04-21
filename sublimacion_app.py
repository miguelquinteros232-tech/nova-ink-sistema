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
        .stMetric { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }
    </style>
''', unsafe_allow_html=True)

# --- 2. FUNCIONES DE CONFIGURACIÓN ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_a'}}
        with open("config_pro.yaml", 'w') as f:
            yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f:
        return yaml.load(f, Loader=SafeLoader)

# --- 3. AUTENTICACIÓN ---
config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t1:
        authenticator.login(location='main')
    with t2:
        try:
            if authenticator.register_user(location='main'):
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('Registrado. Inicia sesión.')
        except Exception as e:
            st.error(f"Error al registrar: {e}")

# --- 4. APP PRINCIPAL ---
elif st.session_state["authentication_status"]:
    
    @st.cache_resource
    def get_gspread_client():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            # Verificación de existencia de secrets
            if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
                st.error("Faltan los Secrets de 'gsheets' en Streamlit Cloud.")
                st.stop()
            
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            # Reparar saltos de línea en la clave privada
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"Error procesando credenciales: {e}")
            st.stop()

    try:
        client = get_gspread_client()
        SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
        sh = client.open_by_key(SHEET_ID)
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")
    except Exception as e:
        if "Permission" in str(e):
            st.error("❌ ERROR DE PERMISOS")
            st.info(f"Comparte el Excel con: `{st.secrets['connections']['gsheets']['client_email']}`")
        else:
            st.error(f"❌ Error de Conexión: {e}")
        st.stop()

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df_p = pd.DataFrame(ws_p.get_all_records())
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            v = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            g = df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS", f"${v:,.2f}")
            c2.metric("GASTOS", f"${g:,.2f}")
            c3.metric("UTILIDAD", f"${v - g:,.2f}")

            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '⚙️'} {r['ID']} - {r['Cliente']}"):
                    if bloqueado: st.info("Registro cerrado.")
                    else:
                        with st.form(f"e_{i}"):
                            n_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            n_mon = st.number_input("Precio $", value=float(r['Monto']))
                            if st.form_submit_button("Actualizar"):
                                ws_p.update_cell(i+2, 7, n_est)
                                ws_p.update_cell(i+2, 6, n_mon)
                                st.rerun()

    # --- STOCK ---
    elif menu == "📦 STOCK":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.expander("➕ AGREGAR MATERIAL"):
            with st.form("add_st"):
                c1, c2 = st.columns(2)
                cat, nom = c1.text_input("Categoría"), c1.text_input("Nombre")
                tip, tal = c2.text_input("Tipo"), c2.text_input("Talle")
                col, can = c1.text_input("Color"), c2.number_input("Cantidad", min_value=0.0)
                uni = c2.text_input("Unidad")
                if st.form_submit_button("Guardar"):
                    ws_i.append_row([cat, nom, tip, tal, col, can, uni])
                    st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.form("new_order"):
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio $"), st.number_input("Costo $")
            mat = st.selectbox("Material", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad", min_value=0.1)
            if st.form_submit_button("REGISTRAR"):
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                nueva = float(df_inv.at[idx, 'Cantidad']) - can_u
                ws_i.update_cell(idx+2, 6, nueva)
                ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, "", mon, "Producción", gas, ""])
                st.success("Registrado correctamente"); time.sleep(1); st.rerun()

    # --- COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        costo = st.number_input("Costo $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")

elif st.session_state["authentication_status"] is False:
    st.error('Usuario o contraseña incorrectos')
