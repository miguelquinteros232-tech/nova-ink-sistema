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

# URL LIMPIA (Sin el /edit al final)
URL_HOJA = "https://docs.google.com/spreadsheets/d/11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8/edit?gid=0#gid=0"
SLOGAN = "CALIDAD QUE DEJA HUELLA"

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap');
        .stApp {{ background: #05000a; background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%); }}
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

# --- 2. GESTIÓN DE CONFIGURACIÓN ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(cfg):
    with open("config_pro.yaml", 'w') as f: yaml.dump(cfg, f, default_flow_style=False)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

# Login y Registro
t_log, t_reg = st.tabs(["🔐 Entrar", "📝 Registro"])
with t_log: authenticator.login(location='main')
with t_reg:
    try:
        if authenticator.register_user(location='main'):
            save_config(config)
            st.success('✅ Registrado. Ya puedes entrar.')
    except Exception as e: st.error(f'Error: {e}')

# --- 4. SISTEMA PRINCIPAL ---
if st.session_state["authentication_status"]:
    conn = st.connection("gsheets", type=GSheetsConnection)

    with st.sidebar:
        st.write(f"### 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    # Función segura para leer datos
    def safe_read(worksheet):
        try:
            return conn.read(spreadsheet=URL_HOJA, worksheet=worksheet, ttl=0)
        except Exception as e:
            st.error(f"⚠️ Error de conexión con Google Sheets en la hoja '{worksheet}'. Verifica que la hoja sea pública.")
            return pd.DataFrame()

    if menu == "📊 DASHBOARD":
        df = safe_read("Pedidos")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos", f"${df['Monto'].sum():,.2f}")
            c2.metric("En Producción", len(df[df['Estado'] == 'Producción']))
            c3.metric("Listos", len(df[df['Estado'] == 'Listo']))

            try:
                df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
                df_v = df.groupby(df['Fecha'].dt.strftime('%m-%Y'))['Monto'].sum().reset_index()
                st.plotly_chart(px.bar(df_v, x='Fecha', y='Monto', template="plotly_dark", color_discrete_sequence=['#bc39fd']), use_container_width=True)
            except: pass

            st.subheader("📋 Gestión de Pedidos")
            for i, r in df.iterrows():
                with st.expander(f"Orden #{r['ID']} - {r['Cliente']}"):
                    with st.form(f"ed_{i}"):
                        nc = st.text_input("Cliente", value=r['Cliente'])
                        nm = st.number_input("Monto $", value=float(r['Monto']))
                        ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                        nd = st.text_area("Descripción", value=r.get('Descripción', ''))
                        if st.form_submit_button("Actualizar"):
                            df.at[i, 'Cliente'], df.at[i, 'Monto'], df.at[i, 'Estado'], df.at[i, 'Descripción'] = nc, nm, ne, nd
                            conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                            st.rerun()

    elif menu == "📝 NUEVO PEDIDO":
        with st.form("new"):
            st.subheader("Registrar Venta")
            c1, c2 = st.columns(2)
            cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
            mon, est = c2.number_input("Precio $"), c2.selectbox("Estado", ["Producción", "Listo"])
            des = st.text_area("Descripción (Talles, Diseño...)")
            if st.form_submit_button("CREAR"):
                df_p = safe_read("Pedidos")
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": est, "Descripción": des}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("✅ Guardado"); time.sleep(1); st.rerun()

    elif menu == "📦 STOCK":
        st.dataframe(safe_read("Inventario"), use_container_width=True)
    
    elif menu == "💰 COTIZADOR":
        ci = st.number_input("Costo $", min_value=0.0)
        mg = st.slider("Ganancia %", 0, 500, 100)
        st.title(f"Sugerido: ${ci * (1 + mg/100):,.2f}")

elif st.session_state["authentication_status"] is False:
    st.error('Credenciales incorrectas')
