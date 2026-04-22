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

# ==========================================
# 1. ESTILOS GLOBALES (VISIBILIDAD Y NEÓN)
# ==========================================
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');

        /* Fondo Negro Absoluto */
        .stApp, [data-testid="stHeader"], .main { background-color: #000000 !important; }
        [data-testid="stSidebar"] { 
            background-color: #050505 !important; 
            border-right: 1px solid #1a1a1a !important; 
        }

        /* Texto Blanco Forzado */
        h1, h2, h3, p, span, label, div { color: white !important; }

        /* Estilo de Botones del Menú */
        div[role="radiogroup"] label {
            background: #0d0d0d !important;
            border: 1px solid #1a1a1a !important;
            padding: 15px 20px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            transition: 0.3s all ease;
        }
        div[role="radiogroup"] label:hover {
            border-color: #00d4ff !important;
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
            transform: translateX(5px);
        }
        div[role="radiogroup"] label p { font-weight: 700 !important; color: #888 !important; }
        div[role="radiogroup"] label:hover p { color: white !important; }
    </style>
''', unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR Y LOGO (LÍNEA 177 CORREGIDA)
# ==========================================
with st.sidebar:
    # EL LOGO CON EFECTO NEÓN (Aquí es donde daba el error de indentación)
    st.write(f'''
        <div style="text-align: center; margin: 20px 0 40px 0;">
            <h1 style="
                font-family: 'Orbitron', sans-serif; 
                font-size: 38px; 
                font-weight: 700;
                color: #FFFFFF !important;
                text-shadow: 0 0 20px #00d4ff, 0 0 5px #ffffff; 
                margin: 0;
            ">
                NOVA INK<span style="color: #00d4ff !important;">.</span>
            </h1>
        </div>
    ''', unsafe_allow_html=True)
    
    # Menú de Navegación Único
    menu = st.radio("", [
        "📊 DASHBOARD", 
        "🛍️ PEDIDOS", 
        "📦 STOCK", 
        "📜 HISTORIAL", 
        "💰 COTIZADOR"
    ], key="nav_nova_ink_final")
    
    st.write("---")

# ==========================================
# 3. LÓGICA DEL DASHBOARD (CEROS FORZADOS)
# ==========================================
if "DASHBOARD" in menu:
    # 1. Aseguramos que las variables existan en 0
    v_pedidos = 0
    v_monto = 0.0
    
    # 2. Tu lógica para cargar datos (Mantenla aquí)
    try:
        # Aquí usa tus variables reales, ejemplo: if not df_act.empty...
        if 'df_act' in locals() and not df_act.empty:
            v_pedidos = len(df_act)
            v_monto = df_act['Monto'].sum()
    except:
        pass # Si falla, se quedan en 0

    # 3. Renderizado de Tarjetas Visuales (Estilo Imagen 3)
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f'''
            <div style="background: linear-gradient(145deg, #111, #050505); border: 1px solid #222; padding: 35px; border-radius: 20px; text-align: center;">
                <p style="color: #666 !important; font-size: 12px; font-weight: bold; letter-spacing: 2px; margin: 0;">PEDIDOS ACTIVOS</p>
                <h2 style="font-family: 'Orbitron', sans-serif; font-size: 45px; color: white !important; margin: 10px 0 0 0;">{v_pedidos}</h2>
            </div>
        ''', unsafe_allow_html=True)
        
    with col2:
        st.write(f'''
            <div style="background: linear-gradient(145deg, #111, #050505); border: 1px solid #222; padding: 35px; border-radius: 20px; text-align: center;">
                <p style="color: #666 !important; font-size: 12px; font-weight: bold; letter-spacing: 2px; margin: 0;">BALANCE PENDIENTE</p>
                <h2 style="font-family: 'Orbitron', sans-serif; font-size: 45px; color: #00d4ff !important; margin: 10px 0 0 0;">${v_monto:,.0f}</h2>
            </div>
        ''', unsafe_allow_html=True)

    st.write("---")

# --- 2. TU LÓGICA DE CONFIGURACIÓN (TAL CUAL LA ENVIASTE) ---
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

# --- 3. LOGIN Y REGISTRO (ESTRUCTURA ORIGINAL) ---
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

# --- 4. APLICACIÓN PRINCIPAL (REPLICA EXACTA DE TU LÓGICA) ---
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
    # LOGO NOVA INK CON EFECTO NEÓN (Línea 94 corregida)
    st.write(f'''
        <div style="text-align: center; padding: 20px 0; margin-bottom: 10px;">
            <h1 style="
                font-family: 'Orbitron', sans-serif; 
                font-size: 35px; 
                font-weight: 700;
                color: #FFFFFF !important; 
                text-shadow: 0 0 15px #00d4ff, 0 0 30px #00d4ff;
                margin: 0;
            ">
                NOVA INK<span style="color: #00d4ff !important;">.</span>
            </h1>
        </div>
    ''', unsafe_allow_html=True)
    
    # Menú Único (Asegúrate de que este sea el único st.radio de tu app)
    menu = st.radio("", [
        "📊 DASHBOARD", 
        "🛍️ PEDIDOS", 
        "📦 STOCK", 
        "📜 HISTORIAL", 
        "💰 COTIZADOR"
    ], key="nav_nova_ink")

        # SECCIÓN DASHBOARD (Tus métricas pero con estilo de la imagen)
        if "DASHBOARD" in menu:
    # 1. Lógica ultra-segura para los ceros
    try:
        # Reemplaza 'df_act' por tu variable real de pedidos activos
        v_pedidos = len(df_act) if ('df_act' in locals() or 'df_act' in globals()) else 0
        v_monto = df_act['Monto'].sum() if ('df_act' in locals() or 'df_act' in globals()) else 0
    except:
        v_pedidos, v_monto = 0, 0

    # 2. Renderizado con Estilos Forzados (Inline)
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f'''
            <div style="background: #0d0d0d; border: 1px solid #222; padding: 30px; border-radius: 15px; text-align: center;">
                <p style="color: #666 !important; font-family: sans-serif; font-size: 12px; font-weight: bold; letter-spacing: 2px; margin: 0;">PEDIDOS ACTIVOS</p>
                <h2 style="color: #FFFFFF !important; font-family: 'Orbitron', sans-serif; font-size: 45px; margin: 10px 0 0 0;">{v_pedidos}</h2>
            </div>
        ''', unsafe_allow_html=True)
        
    with col2:
        st.write(f'''
            <div style="background: #0d0d0d; border: 1px solid #222; padding: 30px; border-radius: 15px; text-align: center;">
                <p style="color: #666 !important; font-family: sans-serif; font-size: 12px; font-weight: bold; letter-spacing: 2px; margin: 0;">BALANCE PENDIENTE</p>
                <h2 style="color: #00d4ff !important; font-family: 'Orbitron', sans-serif; font-size: 45px; margin: 10px 0 0 0;">${v_monto:,.0f}</h2>
            </div>
        ''', unsafe_allow_html=True)
    
    st.write("---")

        # SECCIÓN GESTIÓN PEDIDOS (REPLICA EXACTA DE TUS TABS Y FORMULARIOS)
        elif menu == "GESTIÓN PEDIDOS":
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
                    # (Aquí seguiría el resto de tu lógica de modificar...)

        # SECCIÓN STOCK (TU LÓGICA ORIGINAL)
        elif menu == "STOCK":
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)
            with st.expander("➕ AGREGAR MATERIAL"):
                with st.form("add_s"):
                    c1, c2 = st.columns(2)
                    cat, nom, tip = c1.text_input("Categoría"), c1.text_input("Nombre"), c1.text_input("Tipo")
                    tal, col, can, uni = c2.text_input("Talle"), c2.text_input("Color"), c2.number_input("Cantidad"), c2.text_input("Unidad")
                    if st.form_submit_button("CARGAR"):
                        ws_i.append_row([cat, nom, tip, tal, col, can, uni]); st.rerun()

        # SECCIÓN HISTORIAL Y COTIZADOR (REPLICA EXACTA)
        elif menu == "HISTORIAL":
            df_h = pd.DataFrame(ws_p.get_all_records())
            if not df_h.empty:
                df_v = df_h[df_h['Estado'] == 'Vendido']
                st.write("### Ventas Finalizadas")
                st.table(df_v)

        elif menu == "COTIZADOR":
            c1, c2 = st.columns(2)
            ins = c1.number_input("Insumos $")
            hrs = c1.number_input("Horas Trabajo")
            v_h = c1.number_input("Valor Hora $", value=2000.0)
            mrg = c2.slider("% Ganancia", 0, 400, 100)
            total = (ins + (hrs * v_h)) * (1 + mrg/100)
            st.title(f"Sugerido: ${total:,.2f}")
