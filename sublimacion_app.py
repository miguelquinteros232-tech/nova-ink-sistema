import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN E INTERFAZ CON MARCA DE AGUA ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/edit?usp=sharing"
SLOGAN = "CALIDAD QUE DEJA HUELLA" # Tu slogan aquí

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Orbitron:wght@400;900&display=swap');
        
        .stApp {{
            background: #05000a;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(188, 57, 253, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 212, 255, 0.15) 0%, transparent 40%);
            color: #f0f0f0; font-family: 'Rajdhani', sans-serif;
        }}

        /* MARCA DE AGUA (SLOGAN) */
        .stApp::after {{
            content: "{SLOGAN}";
            position: fixed; bottom: 10%; right: 5%;
            font-size: 80px; font-family: 'Orbitron', sans-serif;
            font-weight: 900; color: rgba(255, 255, 255, 0.03);
            transform: rotate(-15deg); pointer-events: none; z-index: 0;
        }}

        .main-logo {{
            font-family: 'Orbitron', sans-serif; font-size: 60px; font-weight: 900; 
            text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 10px; margin-bottom: 20px; filter: drop-shadow(0 0 8px #bc39fd);
        }}

        .glass-panel {{
            background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #00d4ff; border-radius: 15px; padding: 25px; 
            backdrop-filter: blur(10px); margin-bottom: 20px;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(spreadsheet=URL_HOJA, worksheet=sheet_name, ttl=0)
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
        st.markdown(f"## 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 INVENTARIO", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD: MÉTRICAS Y EDICIÓN ---
    if menu == "📊 DASHBOARD":
        df_p = get_data("Pedidos")
        if not df_p.empty:
            df_p['Fecha'] = pd.to_datetime(df_p['Fecha'], dayfirst=True, errors='coerce')
            
            # Métricas Superiores
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Totales", f"${df_p['Monto'].sum():,.2f}")
            c2.metric("Pendientes", len(df_p[df_p['Estado'] != 'Vendido']))
            c3.metric("Completados", len(df_p[df_p['Estado'] == 'Vendido']))

            # Gráfico Simple
            st.write("### 📈 Rendimiento Reciente")
            ventas_dia = df_p.groupby('Fecha')['Monto'].sum().reset_index()
            fig = px.bar(ventas_dia, x='Fecha', y='Monto', color_discrete_sequence=['#00d4ff'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("📋 Gestión de Pedidos")
            
            # --- SISTEMA DE EDICIÓN ---
            for index, row in df_p.iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Cliente']} ({row['Estado']})"):
                    if row['Estado'] == 'Vendido':
                        st.warning("🔒 Este pedido está marcado como VENDIDO y no puede modificarse.")
                        st.write(f"**Descripción:** {row.get('Descripción', 'Sin descripción')}")
                        st.write(f"**Monto:** ${row['Monto']}")
                    else:
                        with st.form(f"edit_{row['ID']}"):
                            ec1, ec2 = st.columns(2)
                            new_cli = ec1.text_input("Cliente", value=row['Cliente'])
                            new_prd = ec1.text_input("Producto", value=row['Producto'])
                            new_mon = ec2.number_input("Monto $", value=float(row['Monto']))
                            new_est = ec2.selectbox("Estado", ["Producción", "Listo", "Vendido"], 
                                                  index=["Producción", "Listo", "Vendido"].index(row['Estado']))
                            new_desc = st.text_area("Descripción del trabajo", value=row.get('Descripción', ''))
                            
                            if st.form_submit_button("Actualizar Registro"):
                                df_p.at[index, 'Cliente'] = new_cli
                                df_p.at[index, 'Producto'] = new_prd
                                df_p.at[index, 'Monto'] = new_mon
                                df_p.at[index, 'Estado'] = new_est
                                df_p.at[index, 'Descripción'] = new_desc
                                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df_p)
                                st.success("Cambios guardados"); time.sleep(1); st.rerun()

    # --- 📦 INVENTARIO ---
    elif menu == "📦 INVENTARIO":
        st.subheader("📦 Control de Stock")
        df_inv = get_data("Inventario")
        if not df_inv.empty: st.dataframe(df_inv, use_container_width=True)
        
        with st.expander("➕ Cargar Material"):
            with st.form("f_stock"):
                c1, c2 = st.columns(2)
                f_nom = c1.text_input("Nombre")
                f_col = c1.text_input("Color")
                f_can = c2.number_input("Cantidad", min_value=0.0)
                if st.form_submit_button("Guardar"):
                    nueva = pd.DataFrame([{"Nombre": f_nom, "Color": f_col, "Cantidad": f_can}])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=pd.concat([df_inv, nueva], ignore_index=True))
                    st.rerun()

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora Rápida")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        costo = st.number_input("Costo base $", min_value=0.0)
        margen = st.slider("Ganancia %", 0, 500, 100)
        st.write(f"## Total: ${costo * (1 + margen/100):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.subheader("📝 Registrar Nueva Orden")
        with st.form("form_new_p"):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Cliente")
            f_prd = c1.text_input("Producto")
            f_mon = c2.number_input("Monto $", min_value=0.0)
            f_est = c2.selectbox("Estado", ["Producción", "Listo"])
            f_desc = st.text_area("Descripción de lo que el cliente quiere (detalles, talle, diseño, etc.)")
            
            if st.form_submit_button("Crear Pedido"):
                df_p = get_data("Pedidos")
                nuevo = pd.DataFrame([{
                    "ID": len(df_p)+1, 
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": f_cli, 
                    "Producto": f_prd, 
                    "Monto": f_mon, 
                    "Estado": f_est,
                    "Descripción": f_desc
                }])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("Pedido registrado con éxito"); time.sleep(1); st.rerun()
