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

# --- 2. CONFIGURACIÓN DE AUTH (TU LÓGICA ORIGINAL) ---
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

# --- INYECCIÓN DE ESTILO "IMAGEN 3" (SIN TOCAR LÓGICA) ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1a1a1a !important; }
        h1, h2, h3, p, span, label { color: white !important; }
        
        /* Botones del Menú Lateral */
        div[role="radiogroup"] label {
            background: #0d0d0d !important; border: 1px solid #1a1a1a !important;
            padding: 15px 20px !important; border-radius: 12px !important; margin-bottom: 10px !important;
            transition: 0.3s all ease;
        }
        div[role="radiogroup"] label:hover { border-color: #00d4ff !important; transform: translateX(5px); }
        div[role="radiogroup"] [aria-checked="true"] label { border-left: 5px solid #00d4ff !important; border-color: #1a1a1a !important; }
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

# --- 4. APLICACIÓN PRINCIPAL (TU CÓDIGO ÍNTEGRO) ---
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
            # LOGO NOVA INK
            st.write(f'''
                <div style="text-align: center; padding: 20px 0; margin-bottom: 10px;">
                    <h1 style="font-family: 'Orbitron', sans-serif; font-size: 35px; font-weight: 700; color: #FFFFFF !important; text-shadow: 0 0 15px #00d4ff; margin: 0;">
                        NOVA INK<span style="color: #00d4ff !important;">.</span>
                    </h1>
                </div>
            ''', unsafe_allow_html=True)
            
            menu = st.radio("", ["📊 DASHBOARD", "🛍️ PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"], key="nav_nova_ink")

        # --- SECCIÓN DASHBOARD ---
        if "DASHBOARD" in menu:
            try:
                df_p = pd.DataFrame(ws_p.get_all_records())
                df_act = df_p[df_p['Estado'] != 'Vendido'] if not df_p.empty else pd.DataFrame()
                v_pedidos = len(df_act)
                v_monto = pd.to_numeric(df_act['Monto'], errors='coerce').sum()
            except:
                v_pedidos, v_monto = 0, 0

            col1, col2 = st.columns(2)
            with col1:
                st.write(f'''
                    <div style="background: linear-gradient(145deg, #0d0d0d, #050505); border: 1px solid #222; padding: 30px; border-radius: 15px; text-align: center;">
                        <p style="color: #666 !important; font-size: 12px; font-weight: bold; letter-spacing: 2px; margin: 0;">PEDIDOS ACTIVOS</p>
                        <h2 style="color: #FFFFFF !important; font-family: 'Orbitron'; font-size: 45px; margin: 10px 0 0 0;">{v_pedidos}</h2>
                    </div>
                ''', unsafe_allow_html=True)
            with col2:
                st.write(f'''
                    <div style="background: linear-gradient(145deg, #0d0d0d, #050505); border: 1px solid #222; padding: 30px; border-radius: 15px; text-align: center;">
                        <p style="color: #666 !important; font-size: 12px; font-weight: bold; letter-spacing: 2px; margin: 0;">BALANCE PENDIENTE</p>
                        <h2 style="color: #00d4ff !important; font-family: 'Orbitron'; font-size: 45px; margin: 10px 0 0 0;">${v_monto:,.0f}</h2>
                    </div>
                ''', unsafe_allow_html=True)
            st.write("---")

        # --- SECCIÓN PEDIDOS (TAL CUAL LA ENVIASTE) ---
        elif "PEDIDOS" in menu:
            tab1, tab2 = st.tabs(["NUEVO PEDIDO", "MODIFICAR EXISTENTE"])
            df_inv = pd.DataFrame(ws_i.get_all_records())
            
            with tab1:
                with st.form("n_p"):
                    c1, c2 = st.columns(2)
                    cli = c1.text_input("Cliente")
                    prd = c1.text_input("Producto")
                    det = c2.text_area("Descripción")
                    pago = c2.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"])
                    mon = st.number_input("Precio Final $")
                    mat = st.selectbox("Insumo a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                    can = st.number_input("Cantidad a restar", min_value=0.0)
                    if st.form_submit_button("REGISTRAR"):
                        idx = df_inv[df_inv['Nombre'] == mat].index[0]
                        ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                        ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                        st.success("Registrado."); st.rerun()
            
            with tab2:
                df_p = pd.DataFrame(ws_p.get_all_records())
                if not df_p.empty:
                    sel = st.selectbox("Seleccionar Pedido", df_p['Cliente'] + " - " + df_p['Producto'])

        # --- SECCIÓN STOCK (RECUPERADOS TODOS LOS CAMPOS) ---
        elif "STOCK" in menu:
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)
            with st.expander("➕ AGREGAR MATERIAL"):
                with st.form("add_s"):
                    c1, c2 = st.columns(2)
                    cat = c1.text_input("Categoría")
                    nom = c1.text_input("Nombre")
                    tip = c1.text_input("Tipo")
                    tal = c2.text_input("Talle")
                    col = c2.text_input("Color")
                    can = c2.number_input("Cantidad")
                    uni = c2.text_input("Unidad")
                    if st.form_submit_button("CARGAR"):
                        ws_i.append_row([cat, nom, tip, tal, col, can, uni]); st.rerun()

        # --- SECCIÓN HISTORIAL ---
        elif "HISTORIAL" in menu:
            df_h = pd.DataFrame(ws_p.get_all_records())
            if not df_h.empty:
                df_v = df_h[df_h['Estado'] == 'Vendido']
                st.write("### Ventas Finalizadas")
                st.table(df_v)

        # --- SECCIÓN COTIZADOR ---
        elif "COTIZADOR" in menu:
            c1, c2 = st.columns(2)
            ins = c1.number_input("Insumos $")
            hrs = c1.number_input("Horas Trabajo")
            v_h = c1.number_input("Valor Hora $", value=2000.0)
            mrg = c2.slider("% Ganancia", 0, 400, 100)
            total = (ins + (hrs * v_h)) * (1 + mrg/100)
            st.title(f"Sugerido: ${total:,.2f}")
