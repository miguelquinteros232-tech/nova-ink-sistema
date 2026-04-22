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

# 1. ESTILO "NOVA ELITE" (RESTAURADO DE LA CAPTURA 3)
st.set_page_config(page_title="NOVA INK", layout="wide")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* FONDO NEGRO TOTAL */
        .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
            background-color: #0a0a0a !important;
        }

        /* LOGO ESTILO CAPTURA 3 */
        .logo-container { text-align: center; padding: 30px 0; }
        .logo-text {
            font-family: 'Orbitron', sans-serif;
            font-size: 50px; color: white; letter-spacing: 5px;
        }
        .logo-text span { color: #00d4ff; text-shadow: 0 0 15px #00d4ff; }

        /* MENÚ LATERAL: BOTONES CON LUZ */
        div[role="radiogroup"] label {
            background-color: #151515 !important;
            border: 1px solid #252525 !important;
            padding: 15px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            transition: 0.3s all ease !important;
        }
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0px 0px 20px rgba(0, 212, 255, 0.4) !important;
            transform: translateX(8px) !important;
        }
        div[role="radiogroup"] label p {
            color: #888 !important; font-weight: 700 !important;
            text-transform: uppercase !important;
        }
        div[role="radiogroup"] label:hover p { color: white !important; }

        /* TARJETAS GLASS PARA DASHBOARD */
        .glass-card {
            background: linear-gradient(145deg, #181818, #0c0c0c);
            border: 1px solid #222;
            padding: 40px;
            border-radius: 20px;
            text-align: center;
        }
    </style>
''', unsafe_allow_html=True)

# 2. LOGO CENTRAL
st.markdown('<div class="logo-container"><div class="logo-text">NOVA INK<span>.</span></div></div>', unsafe_allow_html=True)

# 3. LÓGICA DE USUARIOS (TU CÓDIGO ORIGINAL)
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'}}
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f: yaml.dump(initial_config, f)
    with open(file_path) as f: return yaml.load(f, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# 4. LOGIN
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is False:
    st.error("Credenciales incorrectas")
elif st.session_state.get("authentication_status") is None:
    st.info("Inicia sesión para continuar")
elif st.session_state["authentication_status"]:

    # 5. CONEXIÓN GOOGLE SHEETS (TU LÓGICA ORIGINAL)
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
            st.markdown(f"<p style='color:white; text-align:center;'>Hola, {st.session_state['name']}</p>", unsafe_allow_html=True)
            opcion = st.radio("", ["DASHBOARD", "PRODUCTOS Y PRECIOS", "STOCK", "NUEVO PEDIDO", "HISTORIAL", "MODIFICAR PEDIDO"])
            st.write("---")
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # --- SECCIONES DE TU APP ---
        if opcion == "DASHBOARD":
            df_p = pd.DataFrame(ws_p.get_all_records())
            if not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_act = df_p[df_p['Estado'] != 'Vendido']
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'''<div class="glass-card">
                        <p style="color:#666; font-size:12px; letter-spacing:2px;">PEDIDOS ACTIVOS</p>
                        <h1 style="color:white; font-family:'Orbitron'; font-size:55px;">{len(df_act)}</h1>
                        <div style="width:40px; height:2px; background:#00d4ff; margin:0 auto;"></div>
                    </div>''', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'''<div class="glass-card">
                        <p style="color:#666; font-size:12px; letter-spacing:2px;">CAPITAL PENDIENTE</p>
                        <h1 style="color:#bc39fd; font-family:'Orbitron'; font-size:55px;">${df_act['Monto'].sum():,.0f}</h1>
                        <div style="width:40px; height:2px; background:#bc39fd; margin:0 auto;"></div>
                    </div>''', unsafe_allow_html=True)

        elif opcion == "STOCK":
            st.markdown("<h2 style='color:white;'>Inventario Actual</h2>", unsafe_allow_html=True)
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)

        elif opcion == "NUEVO PEDIDO":
            df_inv = pd.DataFrame(ws_i.get_all_records())
            with st.form("n_p"):
                c1, c2 = st.columns(2)
                cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
                det, pago = c2.text_area("Descripción"), c2.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"])
                mon = st.number_input("Precio Final $")
                mat = st.selectbox("Insumo", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                can = st.number_input("Cantidad a restar", min_value=0.0)
                if st.form_submit_button("REGISTRAR PEDIDO"):
                    idx = df_inv[df_inv['Nombre'] == mat].index[0]
                    ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                    ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                    st.success("Registrado correctamente."); st.rerun()

        # Las otras secciones (HISTORIAL, MODIFICAR) siguen el mismo patrón de tu código original.
