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

# CONFIGURACIÓN DE IMAGEN Y DATOS
ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}"
URL_LOGO_LOGO = "URL_DE_TU_LOGO_AQUI" # <-- PEGA AQUÍ EL LINK DE TU LOGO

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        /* MARCA DE AGUA CON LOGO REAL */
        .stApp::after {{
            content: "";
            position: fixed; bottom: 50px; right: 50px;
            width: 300px; height: 300px;
            background-image: url("{URL_LOGO_LOGO}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.05; pointer-events: none; z-index: 0;
        }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: clamp(30px, 8vw, 60px); text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 10px; filter: drop-shadow(0 0 10px #bc39fd);
            margin-bottom: 20px;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. SISTEMA DE USUARIOS ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(cfg):
    try:
        with open("config_pro.yaml", 'w') as f: yaml.dump(cfg, f, default_flow_style=False)
    except Exception as e: st.error(f"Error al guardar usuario: {e}")

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. ACCESO ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Registrarse"])
    with t1: authenticator.login(location='main')
    with t2:
        try:
            if authenticator.register_user(location='main'):
                save_config(config); st.success('✅ Usuario registrado exitosamente.')
        except Exception as e: st.error(f"Error: {e}")
else:
    # --- 4. SISTEMA OPERATIVO ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['name']}")
        menu = st.radio("NAVEGACIÓN", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    def safe_read(ws):
        try: return conn.read(spreadsheet=URL_HOJA, worksheet=ws, ttl=0)
        except: return pd.DataFrame()

    # --- SECCIÓN: STOCK ---
    if menu == "📦 STOCK":
        st.subheader("📦 Control de Inventario")
        with st.expander("➕ AGREGAR NUEVO ARTÍCULO"):
            with st.form("form_stock"):
                c1, c2, c3 = st.columns(3)
                prod = c1.text_input("Producto")
                cant = c2.number_input("Stock Inicial", min_value=0)
                cost = c3.number_input("Costo Unitario $", min_value=0.0)
                if st.form_submit_button("REGISTRAR ARTÍCULO"):
                    df_s = safe_read("Inventario")
                    nuevo = pd.DataFrame([{"Producto": prod, "Cantidad": cant, "Costo": cost, "Fecha": datetime.now().strftime("%d/%m/%Y")}])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=pd.concat([df_s, nuevo], ignore_index=True))
                    st.success("Guardado"); time.sleep(1); st.rerun()
        
        st.dataframe(safe_read("Inventario"), use_container_width=True)

    # --- SECCIÓN: DASHBOARD ---
    elif menu == "📊 DASHBOARD":
        df = safe_read("Pedidos")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Totales", f"${df['Monto'].sum():,.2f}")
            c2.metric("En Producción", len(df[df['Estado'] == 'Producción']))
            c3.metric("Listos", len(df[df['Estado'] == 'Listo']))
            
            # Gráfico Mensual
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df_g = df.groupby(df['Fecha'].dt.strftime('%m-%Y'))['Monto'].sum().reset_index()
            st.plotly_chart(px.bar(df_g, x='Fecha', y='Monto', title="Ingresos Mensuales", template="plotly_dark", color_discrete_sequence=['#bc39fd']), use_container_width=True)

            st.write("---")
            st.subheader("📋 Gestión de Pedidos")
            for i, r in df.iterrows():
                with st.expander(f"Orden #{r['ID']} - {r['Cliente']}"):
                    with st.form(f"f_{i}"):
                        nc = st.text_input("Cliente", value=r['Cliente'])
                        nm = st.number_input("Monto $", value=float(r['Monto']))
                        ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                        nd = st.text_area("Descripción", value=r.get('Descripción', ''))
                        if st.form_submit_button("Actualizar"):
                            df.at[i, 'Cliente'], df.at[i, 'Monto'], df.at[i, 'Estado'], df.at[i, 'Descripción'] = nc, nm, ne, nd
                            conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                            st.success("Actualizado"); time.sleep(1); st.rerun()

    # --- SECCIÓN: NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        with st.form("new_order"):
            st.subheader("Nueva Venta")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Precio $")
            des = st.text_area("Detalles (Talles, Diseño)")
            if st.form_submit_button("CREAR PEDIDO"):
                df_p = safe_read("Pedidos")
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": "Producción", "Descripción": des}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("✅ ¡Pedido Creado!"); time.sleep(1); st.rerun()

    # --- SECCIÓN: COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Ganancias")
        costo = st.number_input("Costo de materiales $")
        ganancia = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + ganancia/100):,.2f}")
