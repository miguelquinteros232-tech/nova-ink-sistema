import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. IDENTIDAD VISUAL (BLOQUEADA PARA QUE NO SE BORRE) ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")

URL_LOGO_REAL = "https://i.postimg.cc/85M9m9zV/nova-ink-logo.png" 

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: clamp(35px, 9vw, 75px); text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 12px; filter: drop-shadow(0 0 15px #bc39fd);
            margin-bottom: 25px; font-weight: 900;
        }}
        .stApp::after {{
            content: ""; position: fixed; bottom: 40px; right: 40px;
            width: 250px; height: 250px; background-image: url("{URL_LOGO_REAL}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.08; pointer-events: none; z-index: 0;
        }}
        /* Estilo de métricas neón */
        [data-testid="stMetricValue"] {{ font-family: 'Orbitron'; color: #00d4ff !important; }}
    </style>
''', unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

config = load_config()
auth = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t1: auth.login(location='main')
    with t2:
        if auth.register_user(location='main'):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f)
            st.success('Registrado.')
else:
    # --- 3. CONEXIÓN REFORZADA ---
    # Usamos st.connection pero forzamos el refresco de caché para evitar el PermissionError persistente
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Extraemos el ID de la hoja directamente para evitar fallos de URL
    # Tu ID es: 11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8
    SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD (BALANCE Y LÓGICA DE CIERRE) ---
    if menu == "📊 DASHBOARD":
    try:
        # Forzamos la lectura limpia
        df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
        
        if df_p is not None and not df_p.empty:
            # Limpiar nombres de columnas por si tienen espacios invisibles
            df_p.columns = df_p.columns.str.strip()
            
            # Verificación de columnas críticas
            columnas_necesarias = ['Estado', 'Monto', 'Gasto_Prod']
            if all(col in df_p.columns for col in columnas_necesarias):
                ventas = pd.to_numeric(df_p[df_p['Estado'] == 'Vendido']['Monto'], errors='coerce').sum()
                gastos = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("INGRESOS", f"${ventas:,.2f}")
                c2.metric("GASTOS", f"${gastos:,.2f}")
                c3.metric("NETO", f"${ventas - gastos:,.2f}")
            else:
                st.error(f"Faltan columnas en 'Pedidos'. Encontradas: {list(df_p.columns)}")
                st.info("Asegúrate de tener: ID, Fecha, Cliente, Producto, Detalle, Monto, Estado, Gasto_Prod, Descripcion")
        else:
            st.warning("La hoja 'Pedidos' está vacía o no se pudo leer.")
            
    except Exception as e:
        st.error(f"Error específico: {e}")

    # --- B. STOCK (ESTRUCTURA SOLICITADA) ---
    elif menu == "📦 STOCK":
        df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
        with st.form("add_inv"):
            st.subheader("Cargar Material")
            c1, c2 = st.columns(2)
            cat = c1.text_input("Categoría")
            nom = c1.text_input("Nombre")
            tip = c2.text_input("Tipo Material")
            tal = c2.text_input("Talle/Medida")
            col = c1.text_input("Color")
            can = c2.number_input("Cantidad", min_value=0)
            uni = c2.text_input("Unidad")
            if st.form_submit_button("Guardar"):
                nuevo = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": tip, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": uni}])
                conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- C. NUEVO PEDIDO (RESTA DE STOCK AUTOMÁTICA) ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
        with st.form("new_order"):
            st.subheader("Registrar Orden")
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio $"), st.number_input("Gasto Prod $")
            mat = st.selectbox("Material usado", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad usada", min_value=1)
            det = st.text_area("Detalles")
            if st.form_submit_button("CREAR"):
                # 1. Restar Stock
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                df_inv.at[idx, 'Cantidad'] -= can_u
                conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=df_inv)
                # 2. Guardar Pedido
                df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
                nuevo_p = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": det, "Monto": mon, "Estado": "Producción", "Gasto_Prod": gas, "Descripcion": ""}])
                conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                st.success("Hecho."); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora")
        costo = st.number_input("Inversión $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
