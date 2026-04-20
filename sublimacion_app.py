import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/edit?usp=sharing"
SLOGAN = "CALIDAD QUE DEJA HUELLA"

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Orbitron:wght@900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 20% 20%, rgba(188, 57, 253, 0.12) 0%, transparent 50%);
        }}
        .stApp::after {{
            content: "{SLOGAN}";
            position: fixed; bottom: 40px; right: 40px;
            font-size: 50px; font-family: 'Orbitron';
            color: rgba(255, 255, 255, 0.02); transform: rotate(-10deg);
            pointer-events: none; z-index: 0;
        }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: 55px; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 8px; filter: drop-shadow(0 0 8px #bc39fd);
            margin-bottom: 30px;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try:
        return conn.read(spreadsheet=URL_HOJA, worksheet=sheet, ttl=0)
    except:
        return pd.DataFrame()

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f: config = yaml.load(f, Loader=SafeLoader)
except: config = {'credentials': {'usernames': {}}}

auth = stauth.Authenticate(config['credentials'], "nova_p", "nova_k", 30)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    auth.login(location='main')
else:
    with st.sidebar:
        st.write(f"### Operador: {st.session_state['name']}")
        menu = st.radio("NAVEGACIÓN", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        auth.logout('Salir', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df = get_data("Pedidos")
        if not df.empty:
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Totales", f"${df['Monto'].sum():,.2f}")
            c2.metric("Pedidos Pendientes", len(df[df['Estado'] != 'Vendido']))
            
            # Gráfico de Ventas
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df_v = df.groupby(df['Fecha'].dt.strftime('%m-%Y'))['Monto'].sum().reset_index()
            fig = px.bar(df_v, x='Fecha', y='Monto', title="Historial Mensual", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            st.write("---")
            st.subheader("📋 Gestión y Edición")
            for i, r in df.iterrows():
                with st.expander(f"ORDEN #{r['ID']} - {r['Cliente']} ({r['Estado']})"):
                    if r['Estado'] == "Vendido":
                        st.info("🔒 Registro bloqueado: Ya fue marcado como Vendido.")
                        st.write(f"**Descripción:** {r.get('Descripción', 'Sin detalles')}")
                    else:
                        with st.form(f"form_ed_{i}"):
                            nc = st.text_input("Cliente", value=r['Cliente'])
                            nm = st.number_input("Monto", value=float(r['Monto']))
                            ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], 
                                            index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nd = st.text_area("Descripción", value=r.get('Descripción', ''))
                            if st.form_submit_button("Guardar Cambios"):
                                df.at[i, 'Cliente'], df.at[i, 'Monto'], df.at[i, 'Estado'], df.at[i, 'Descripción'] = nc, nm, ne, nd
                                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                                st.rerun()

    # --- 📦 STOCK ---
    elif menu == "📦 STOCK":
        st.subheader("Inventario de Materiales")
        df_i = get_data("Inventario")
        if not df_i.empty:
            st.dataframe(df_i, use_container_width=True)
        
        with st.expander("➕ Cargar Nuevo"):
            with st.form("add_s"):
                c1, c2 = st.columns(2)
                fn = c1.text_input("Nombre")
                fc = c1.text_input("Color")
                fq = c2.number_input("Cantidad", min_value=0.0)
                if st.form_submit_button("Sincronizar"):
                    nueva = pd.DataFrame([{"Nombre": fn, "Color": fc, "Cantidad": fq}])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=pd.concat([df_i, nueva], ignore_index=True))
                    st.rerun()

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("Calculadora de Precios")
        c_base = st.number_input("Costo de Insumos $", min_value=0.0)
        margen = st.slider("Ganancia %", 0, 500, 100)
        st.title(f"Precio Venta: ${c_base * (1 + margen/100):,.2f}")

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.subheader("Registrar Nueva Orden")
        with st.form("new_p"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Monto $")
            est = c2.selectbox("Estado", ["Producción", "Listo"])
            des = st.text_area("Descripción (Qué quiere el cliente...)")
            
            if st.form_submit_button("Crear Pedido"):
                df_p = get_data("Pedidos")
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), 
                                      "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": est, "Descripción": des}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("¡Pedido Guardado!"); time.sleep(1); st.rerun()
