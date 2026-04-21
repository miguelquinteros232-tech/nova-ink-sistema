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

URL_HOJA = "https://docs.google.com/spreadsheets/d/11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
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
            letter-spacing: 10px; filter: drop-shadow(0 0 10px #bc39fd); margin-bottom: 20px;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. GESTIÓN DE CONFIGURACIÓN ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(cfg):
    try:
        with open("config_pro.yaml", 'w') as f: yaml.dump(cfg, f, default_flow_style=False)
    except: pass

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t_log, t_reg = st.tabs(["🔐 Entrar", "📝 Registro"])
    with t_log: authenticator.login(location='main')
    with t_reg:
        if authenticator.register_user(location='main'):
            save_config(config); st.success('✅ Registrado.')
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.write(f"### 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    def safe_read(ws):
        try: return conn.read(spreadsheet=URL_HOJA, worksheet=ws, ttl=0)
        except: return pd.DataFrame()

    # --- SECCIÓN STOCK (TU PEDIDO ESPECIAL) ---
    if menu == "📦 STOCK":
        st.subheader("📦 Control de Inventario")
        
        # 1. Formulario para registrar cosas nuevas
        with st.expander("➕ REGISTRAR NUEVO ARTÍCULO O SUMAR STOCK"):
            with st.form("form_stock"):
                c1, c2, c3 = st.columns(3)
                item = c1.text_input("Producto (Ej: Gorra Trucker)")
                cant = c2.number_input("Cantidad", min_value=0, step=1)
                costo = c3.number_input("Costo Unitario $", min_value=0.0)
                cat = st.selectbox("Categoría", ["Gorras", "Tazas", "Remeras", "Insumos", "Otros"])
                
                if st.form_submit_button("GUARDAR EN INVENTARIO"):
                    df_inv = safe_read("Inventario")
                    nuevo_item = pd.DataFrame([{"Producto": item, "Cantidad": cant, "Costo": costo, "Categoría": cat, "Última Actualización": datetime.now().strftime("%d/%m/%Y")}])
                    df_final = pd.concat([df_inv, nuevo_item], ignore_index=True)
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=df_final)
                    st.success(f"✅ {item} registrado correctamente."); time.sleep(1); st.rerun()

        # 2. Visualización de la tabla
        df_stock = safe_read("Inventario")
        if not df_stock.empty:
            st.dataframe(df_stock, use_container_width=True)
        else:
            st.warning("No hay datos en la hoja 'Inventario'. Asegúrate de que la pestaña exista en Google Sheets.")

    # --- SECCIÓN DASHBOARD ---
    elif menu == "📊 DASHBOARD":
        df = safe_read("Pedidos")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos", f"${df['Monto'].sum():,.2f}")
            c2.metric("Producción", len(df[df['Estado'] == 'Producción']))
            c3.metric("Listos", len(df[df['Estado'] == 'Listo']))
            
            st.subheader("📋 Pedidos Activos")
            for i, r in df.iterrows():
                with st.expander(f"Orden #{r['ID']} - {r['Cliente']}"):
                    with st.form(f"ed_{i}"):
                        nc = st.text_input("Cliente", value=r['Cliente'])
                        ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                        nd = st.text_area("Descripción", value=r.get('Descripción', ''))
                        if st.form_submit_button("Actualizar"):
                            df.at[i, 'Cliente'], df.at[i, 'Estado'], df.at[i, 'Descripción'] = nc, ne, nd
                            conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                            st.rerun()

    # --- SECCIÓN NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        with st.form("new_p"):
            st.subheader("Nueva Venta")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            mon = c2.number_input("Precio $")
            des = st.text_area("Detalles del diseño")
            if st.form_submit_button("REGISTRAR"):
                df_p = safe_read("Pedidos")
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Monto": mon, "Estado": "Producción", "Descripción": des}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("✅ Guardado"); time.sleep(1); st.rerun()

    elif menu == "💰 COTIZADOR":
        ci = st.number_input("Costo $", min_value=0.0)
        mg = st.slider("Ganancia %", 0, 500, 100)
        st.title(f"Sugerido: ${ci * (1 + mg/100):,.2f}")
