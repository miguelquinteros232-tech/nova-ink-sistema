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
        .stApp { background: #05000a; }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; margin-bottom: 20px; }
        .stMetric { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }
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

# --- 3. ACCESO ---
authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Ingresa al sistema para operar.")
    with st.expander("📝 REGISTRO"):
        if authenticator.register_user(location='main'):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f, default_flow_style=False)
            st.success('Registrado correctamente.')

# --- 4. APP PRINCIPAL ---
else:
    @st.cache_resource
    def get_db():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = dict(st.secrets["connections"]["gsheets"])
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
            client = gspread.authorize(Credentials.from_service_account_info(creds, scopes=scope))
            sh = client.open_by_key("11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8")
            return sh.worksheet("Pedidos"), sh.worksheet("Inventario"), None
        except Exception as e:
            return None, None, str(e)

    ws_p, ws_i, error = get_db()

    if error:
        st.error(f"❌ Error de Conexión: {error}")
        st.stop()

    with st.sidebar:
        menu = st.radio("MENÚ", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    # --- DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df_p = pd.DataFrame(ws_p.get_all_records())
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            v, g = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum(), df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS", f"${v:,.2f}")
            c2.metric("GASTOS", f"${g:,.2f}")
            c3.metric("NETO", f"${v - g:,.2f}")

            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '⚙️'} {r['ID']} - {r['Cliente']}"):
                    if bloqueado: st.info("Pedido finalizado.")
                    else:
                        with st.form(f"f_{i}"):
                            n_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            n_mon = st.number_input("Precio $", value=float(r['Monto']))
                            if st.form_submit_button("Actualizar"):
                                ws_p.update_cell(i+2, 7, n_est)
                                ws_p.update_cell(i+2, 6, n_mon)
                                st.rerun()

    # --- STOCK ---
    elif menu == "📦 STOCK":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        st.dataframe(df_inv, use_container_width=True)
        with st.expander("➕ AGREGAR"):
            with st.form("add"):
                cat, nom = st.text_input("Categoría"), st.text_input("Nombre")
                can, uni = st.number_input("Cantidad"), st.text_input("Unidad")
                if st.form_submit_button("Guardar"):
                    ws_i.append_row([cat, nom, "", "", "", can, uni])
                    st.rerun()

    # --- NUEVO PEDIDO (CON DESCUENTO DE STOCK) ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.form("new"):
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio Cobrado $"), st.number_input("Costo Material $")
            mat = st.selectbox("Insumo", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad a usar", min_value=0.0)
            
            if st.form_submit_button("REGISTRAR"):
                # Restar del Excel de Inventario
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                nueva = float(df_inv.at[idx, 'Cantidad']) - can_u
                ws_i.update_cell(idx+2, 6, nueva)
                # Guardar en Pedidos
                ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, "", mon, "Producción", gas, ""])
                st.success("✅ Pedido y Stock actualizados."); time.sleep(1); st.rerun()

    # --- COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        costo = st.number_input("Costo $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
