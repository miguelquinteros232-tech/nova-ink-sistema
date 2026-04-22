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
st.set_page_config(page_title="NOVA INK - OS", layout="wide")
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp { background: #05000a; }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; margin-bottom: 20px; }
    </style>
''', unsafe_allow_html=True)

# --- 2. CARGA DE CONFIGURACIÓN ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'}}
        with open("config_pro.yaml", 'w') as f: yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

# --- 3. LOGIN ---
authenticator.login(location='main')

if st.session_state.get("authentication_status") is False:
    st.error('Usuario o contraseña incorrectos')
elif st.session_state.get("authentication_status") is None:
    st.info('Ingresa tus datos.')
    with st.expander("📝 REGISTRARSE"):
        if authenticator.register_user(location='main'):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f, default_flow_style=False)
            st.success('Registrado.')

# --- 4. APP PRINCIPAL ---
elif st.session_state.get("authentication_status"):
    
    @st.cache_resource
    def get_gspread_client():
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        return gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))

    try:
        client = get_gspread_client()
        sh = client.open_by_key("11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8")
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

    with st.sidebar:
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    # --- FUNCIÓN RECUPERADA: DASHBOARD EDITABLE ---
    if menu == "📊 DASHBOARD":
        data = ws_p.get_all_records()
        df_p = pd.DataFrame(data) if data else pd.DataFrame()
        
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            v, g = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum(), df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("VENTAS", f"${v:,.2f}")
            c2.metric("COSTOS", f"${g:,.2f}")
            c3.metric("UTILIDAD", f"${v - g:,.2f}")

            st.write("### Gestión de Pedidos Activos")
            for i, r in df_p.iterrows():
                with st.expander(f"{r['Estado']} | {r['Cliente']} - {r['Producto']}"):
                    with st.form(f"edit_{i}"):
                        new_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                        new_mon = st.number_input("Precio $", value=float(r['Monto']))
                        if st.form_submit_button("Actualizar"):
                            ws_p.update_cell(i+2, 7, new_est) # Estado
                            ws_p.update_cell(i+2, 6, new_mon) # Monto
                            st.rerun()

    # --- FUNCIÓN RECUPERADA: STOCK DETALLADO ---
    elif menu == "📦 STOCK":
        data_i = ws_i.get_all_records()
        df_inv = pd.DataFrame(data_i)
        st.dataframe(df_inv, use_container_width=True)
        with st.expander("➕ AGREGAR MATERIAL"):
            with st.form("add"):
                c1, c2 = st.columns(2)
                cat, nom = c1.text_input("Categoría"), c1.text_input("Nombre")
                can, uni = c2.number_input("Cantidad"), c2.text_input("Unidad (Mts/Un)")
                if st.form_submit_button("Guardar"):
                    ws_i.append_row([cat, nom, "", "", "", can, uni])
                    st.rerun()

    # --- FUNCIÓN RECUPERADA: PEDIDO CON DESCUENTO ---
    elif menu == "📝 NUEVO PEDIDO":
        data_i = ws_i.get_all_records()
        df_inv = pd.DataFrame(data_i)
        
        with st.form("new"):
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio $"), st.number_input("Costo $")
            mat_sel = st.selectbox("Material a usar", df_inv['Nombre'].tolist() if not df_inv.empty else ["Sin Stock"])
            can_usar = st.number_input("Cantidad a descontar", min_value=0.0)
            
            if st.form_submit_button("REGISTRAR PEDIDO"):
                # 1. Descuento automático en Google Sheets
                if mat_sel != "Sin Stock":
                    idx = df_inv[df_inv['Nombre'] == mat_sel].index[0]
                    nueva_cant = float(df_inv.at[idx, 'Cantidad']) - can_usar
                    ws_i.update_cell(idx+2, 6, nueva_cant)
                
                # 2. Guardar el pedido
                ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, "", mon, "Producción", gas, ""])
                st.success("✅ Pedido creado y Stock actualizado."); time.sleep(1); st.rerun()

    elif menu == "💰 COTIZADOR":
        inv = st.number_input("Inversión $")
        st.title(f"Sugerido: ${inv * 2:,.2f}")
