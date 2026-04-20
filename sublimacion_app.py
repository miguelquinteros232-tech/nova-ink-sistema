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
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        .stApp::after {{
            content: "{SLOGAN}";
            position: fixed; bottom: 40px; right: 40px;
            font-size: clamp(30px, 5vw, 60px); font-family: 'Orbitron';
            color: rgba(255, 255, 255, 0.02); transform: rotate(-12deg);
            pointer-events: none; z-index: 0;
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

# --- 2. GESTIÓN DE CONFIGURACIÓN (USUARIOS) ---
def load_config():
    try:
        with open("config_pro.yaml") as f:
            return yaml.load(f, Loader=SafeLoader)
    except:
        return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(config):
    with open("config_pro.yaml", 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

config = load_config()

# --- 3. AUTENTICACIÓN Y REGISTRO ---
auth = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

# Pestañas de Acceso
tab_login, tab_register = st.tabs(["🔐 Entrar", "📝 Registrar Nuevo Usuario"])

with tab_login:
    name, authentication_status, username = auth.login(location='main')

with tab_register:
    try:
        if auth.register_user(location='main'):
            save_config(config)
            st.success('✅ Usuario registrado exitosamente. Ahora puedes iniciar sesión.')
    except Exception as e:
        st.error(f'Error: {e}')

# --- 4. SISTEMA PRINCIPAL ---
if st.session_state["authentication_status"]:
    # Conexión a Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)

    with st.sidebar:
        st.write(f"### 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    # --- 📊 DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df = conn.read(spreadsheet=URL_HOJA, worksheet="Pedidos", ttl=0)
        if df is not None and not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Totales", f"${df['Monto'].sum():,.2f}")
            c2.metric("En Producción", len(df[df['Estado'] == 'Producción']))
            c3.metric("Listos", len(df[df['Estado'] == 'Listo']))

            # Gráfico Plotly
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df_v = df.groupby(df['Fecha'].dt.strftime('%m-%Y'))['Monto'].sum().reset_index()
            fig = px.bar(df_v, x='Fecha', y='Monto', title="Ventas Mensuales", template="plotly_dark", color_discrete_sequence=['#bc39fd'])
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Gestión de Pedidos")
            for i, r in df.iterrows():
                with st.expander(f"Orden #{r['ID']} - {r['Cliente']} ({r['Estado']})"):
                    if r['Estado'] == "Vendido":
                        st.warning("🔒 Venta cerrada. No se permiten cambios.")
                        st.write(f"**Descripción:** {r.get('Descripción', 'N/A')}")
                    else:
                        with st.form(f"edit_{i}"):
                            nc = st.text_input("Cliente", value=r['Cliente'])
                            nm = st.number_input("Monto $", value=float(r['Monto']))
                            ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], 
                                             index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nd = st.text_area("Descripción detallada", value=r.get('Descripción', ''))
                            if st.form_submit_button("Sincronizar"):
                                df.at[i, 'Cliente'], df.at[i, 'Monto'], df.at[i, 'Estado'], df.at[i, 'Descripción'] = nc, nm, ne, nd
                                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                                st.success("¡Hecho!"); time.sleep(1); st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        with st.form("new_order"):
            st.subheader("Registrar Venta")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Precio $", min_value=0.0)
            est = c2.selectbox("Estado", ["Producción", "Listo"])
            des = st.text_area("Descripción (Talles, Diseño, Notas Especiales)")
            
            if st.form_submit_button("CREAR"):
                df_p = conn.read(spreadsheet=URL_HOJA, worksheet="Pedidos", ttl=0)
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), 
                                      "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": est, "Descripción": des}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("✅ Pedido guardado en la nube"); time.sleep(1); st.rerun()

    # --- 📦 STOCK & 💰 COTIZADOR ---
    elif menu == "📦 STOCK":
        st.subheader("📦 Inventario Nova Ink")
        st.dataframe(conn.read(spreadsheet=URL_HOJA, worksheet="Inventario", ttl=0), use_container_width=True)
    
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Precios")
        ci = st.number_input("Costo de insumos $", min_value=0.0)
        mg = st.slider("Porcentaje de Ganancia %", 0, 500, 100)
        st.title(f"Sugerido: ${ci * (1 + mg/100):,.2f}")

elif st.session_state["authentication_status"] is False:
    st.error('Usuario/Contraseña incorrectos')
