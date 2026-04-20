import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

# Tu ID de Google Sheets
ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/edit?usp=sharing"

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Orbitron:wght@400;900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(188, 57, 253, 0.25) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.25) 0%, transparent 50%);
            color: #f0f0f0; font-family: 'Rajdhani', sans-serif;
        }}
        .main-logo {{
            font-family: 'Orbitron', sans-serif; font-size: 60px; font-weight: 900; 
            text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 10px; margin-bottom: 20px;
        }}
        .glass-panel {{
            background: rgba(255, 255, 255, 0.05); border-radius: 15px; 
            padding: 25px; border-left: 5px solid #00d4ff; backdrop-filter: blur(10px);
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(spreadsheet=URL_HOJA, worksheet=sheet_name, ttl=0)
    except Exception as e:
        return pd.DataFrame()

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f: config = yaml.load(f, Loader=SafeLoader)
except: config = {'credentials': {'usernames': {}}}

auth = stauth.Authenticate(config['credentials'], "nova_p", "nova_k", 30)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Entrar", "👤 Nuevo Usuario"])
    with t1: auth.login(location='main')
    with t2:
        if auth.register_user(location='main'):
            with open('config_pro.yaml', 'w') as f: yaml.dump(config, f)
            st.success("Usuario registrado.")
else:
    with st.sidebar:
        st.markdown(f"### {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📦 INVENTARIO", "💰 COTIZADOR PRO", "📝 PEDIDOS", "📊 DASHBOARD"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- SECCIÓN: INVENTARIO ---
    if menu == "📦 INVENTARIO":
        st.subheader("📦 Control de Stock")
        
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("add_material"):
            c1, c2, c3 = st.columns(3)
            cat = c1.selectbox("Categoría", ["Material Base", "Insumo"])
            nom = c1.text_input("Nombre (ej. Gorra)")
            tip = c2.text_input("Tipo de Material")
            col = c2.text_input("Color")
            tal = c3.text_input("Talle")
            can = c3.number_input("Cantidad", min_value=0.0)
            
            submit = st.form_submit_button("💾 GUARDAR MATERIAL")
            
            if submit:
                try:
                    df_actual = get_data("Inventario")
                    nueva_f = pd.DataFrame([{
                        "Categoría": cat, "Nombre": nom, "Tipo Material": tip, 
                        "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": "u"
                    }])
                    
                    if df_actual.empty:
                        df_final = nueva_f
                    else:
                        df_final = pd.concat([df_actual, nueva_f], ignore_index=True)
                    
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=df_final)
                    st.success("✅ ¡Guardado!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error técnico: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        df_inv = get_data("Inventario")
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)

    # --- SECCIÓN: COTIZADOR ---
    elif menu == "💰 COTIZADOR PRO":
        st.subheader("💰 Calculadora")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        costo = st.number_input("Costo materiales $", min_value=0.0)
        margen = st.slider("Ganancia %", 0, 400, 100)
        precio = costo * (1 + margen/100)
        st.markdown(f"<h1 style='text-align:center; color:#bc39fd;'>PRECIO: ${precio:,.2f}</h1>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- SECCIÓN: PEDIDOS ---
    elif menu == "📝 PEDIDOS":
        st.subheader("📝 Registrar Venta")
        with st.form("form_p"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Monto $")
            if st.form_submit_button("REGISTRAR"):
                try:
                    df_p = get_data("Pedidos")
                    n_p = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Monto": mon}])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, n_p], ignore_index=True))
                    st.success("Pedido guardado")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- SECCIÓN: DASHBOARD ---
    elif menu == "📊 DASHBOARD":
        df_p = get_data("Pedidos")
        if not df_p.empty:
            st.metric("Total Ventas", f"${df_p['Monto'].sum():,.2f}")
            st.dataframe(df_p, use_container_width=True)
