import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/edit?usp=sharing"
SLOGAN = "CALIDAD QUE DEJA HUELLA"

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Orbitron:wght@900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        /* MARCA DE AGUA SLOGAN */
        .stApp::after {{
            content: "{SLOGAN}";
            position: fixed; bottom: 40px; right: 40px;
            font-size: clamp(30px, 5vw, 60px); font-family: 'Orbitron';
            color: rgba(255, 255, 255, 0.02); transform: rotate(-12deg);
            pointer-events: none; z-index: 0;
        }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: 55px; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 10px; filter: drop-shadow(0 0 10px #bc39fd);
            margin-bottom: 25px;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet):
    try:
        df = conn.read(spreadsheet=URL_HOJA, worksheet=sheet, ttl=0)
        return df if df is not None else pd.DataFrame()
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
        st.write(f"### 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df = get_data("Pedidos")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos Totales", f"${df['Monto'].sum():,.2f}")
            c2.metric("En Producción", len(df[df['Estado'] == 'Producción']))
            c3.metric("Entregas Listas", len(df[df['Estado'] == 'Listo']))

            # Gráfico de Ventas
            try:
                df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
                df_v = df.groupby(df['Fecha'].dt.strftime('%m-%Y'))['Monto'].sum().reset_index()
                fig = px.bar(df_v, x='Fecha', y='Monto', title="Ventas por Mes", template="plotly_dark", color_discrete_sequence=['#bc39fd'])
                st.plotly_chart(fig, use_container_width=True)
            except: st.info("Cargando gráfico...")

            st.write("---")
            st.subheader("📋 Gestión de Pedidos")
            for i, r in df.iterrows():
                with st.expander(f"ORDEN #{r['ID']} - {r['Cliente']} ({r['Estado']})"):
                    if r['Estado'] == "Vendido":
                        st.warning("🔒 Esta venta está cerrada.")
                        st.write(f"**Descripción:** {r.get('Descripción', 'N/A')}")
                    else:
                        with st.form(f"f_ed_{i}"):
                            nc = st.text_input("Cliente", value=r['Cliente'])
                            nm = st.number_input("Monto $", value=float(r['Monto']))
                            ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], 
                                             index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nd = st.text_area("Detalles", value=r.get('Descripción', ''))
                            if st.form_submit_button("Guardar"):
                                df.at[i, 'Cliente'], df.at[i, 'Monto'], df.at[i, 'Estado'], df.at[i, 'Descripción'] = nc, nm, ne, nd
                                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                                st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        with st.form("new_order"):
            st.subheader("Registrar Venta")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Precio $", min_value=0.0)
            est = c2.selectbox("Estado", ["Producción", "Listo"])
            des = st.text_area("Descripción (Medidas, Diseño, etc.)")
            
            if st.form_submit_button("CREAR PEDIDO"):
                df_p = get_data("Pedidos")
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), 
                                      "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": est, "Descripción": des}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("✅ Guardado"); time.sleep(1); st.rerun()

    # --- 📦 STOCK & 💰 COTIZADOR ---
    elif menu == "📦 STOCK":
        st.dataframe(get_data("Inventario"), use_container_width=True)
    elif menu == "💰 COTIZADOR":
        ci = st.number_input("Costo $", min_value=0.0)
        mg = st.slider("Ganancia %", 0, 500, 100)
        st.title(f"Sugerido: ${ci * (1 + mg/100):,.2f}")
