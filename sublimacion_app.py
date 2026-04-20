import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="NOVA INK - SISTEMA CLOUD", layout="wide", page_icon="🎨")

# Estilos Neón Nova OS
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        .stApp {
            background: #020005 !important;
            background-image: radial-gradient(circle at 20% 30%, rgba(188, 57, 253, 0.15) 0%, transparent 50%),
                              radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.15) 0%, transparent 50%) !important;
            font-family: 'Rajdhani', sans-serif;
        }
        .main-logo {
            font-size: 60px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            background-size: 200% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 4s linear infinite;
            letter-spacing: 10px; margin-bottom: 20px;
        }
        @keyframes shine { to { background-position: 200% center; } }
        .glass-panel {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-left: 5px solid #bc39fd !important;
            border-radius: 15px; padding: 25px; margin-bottom: 20px;
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Pedidos", ttl=0)
        if data.empty:
            return pd.DataFrame(columns=['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
        return data
    except:
        return pd.DataFrame(columns=['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    # Configuración de emergencia si el archivo no está
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key', 'name': 'nova_cookie'}}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- PANTALLA DE ACCESO / REGISTRO ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_reg = st.tabs(["🔑 LOGIN", "✨ REGISTRO SOCIO"])
        with tab_login:
            authenticator.login(location='main')
        with tab_reg:
            with st.form("reg_socio"):
                u = st.text_input("Usuario")
                p = st.text_input("Password", type="password")
                cp = st.text_input("Confirmar Password", type="password")
                if st.form_submit_button("CREAR CUENTA"):
                    if p == cp and u:
                        hashed = stauth.Hasher.hash(p)
                        config['credentials']['usernames'][u] = {'name': u, 'password': hashed}
                        with open("config_pro.yaml", 'w') as f:
                            yaml.dump(config, f)
                        st.success("Socio creado. Inicia sesión ahora.")
                    else: st.error("Error en los datos.")

# --- APLICACIÓN PRINCIPAL ---
else:
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NOVA OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "💰 COTIZADOR"], label_visibility="collapsed")
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    if menu == "📊 DASHBOARD":
        df = get_data()
        if df.empty:
            st.info("No hay pedidos registrados en Google Sheets.")
        else:
            # Procesamiento de fechas para balances
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Fecha'])
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 ANALÍTICA MENSUAL")
            meses = df['Mes_Año'].unique()
            mes_sel = st.selectbox("Seleccionar Mes", meses, index=len(meses)-1)
            df_mes = df[df['Mes_Año'] == mes_sel]

            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Mes", f"${df_mes['Monto'].sum():,.2f}")
            c2.metric("Cant. Pedidos", len(df_mes))
            c3.metric("Por Cobrar", f"${df_mes[df_mes['Pago'] != 'Total']['Monto'].sum():,.2f}")

            st.divider()
            for index, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Cliente']} ({row['Estado']})"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        n_pago = st.selectbox("Pago", ["Pendiente", "Seña", "Total"], 
                                             index=["Pendiente", "Seña", "Total"].index(row['Pago']), key=f"pg_{row['ID']}")
                    with col_b:
                        n_est = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], 
                                            index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0, key=f"es_{row['ID']}")
                    with col_c:
                        if st.button("Guardar Cambios", key=f"bt_{row['ID']}"):
                            df_full = get_data()
                            df_full.at[index, 'Pago'] = n_pago
                            df_full.at[index, 'Estado'] = n_est
                            conn.update(worksheet="Pedidos", data=df_full)
                            st.success("Sincronizado con la Nube")
                            time.sleep(0.5)
                            st.rerun()

    elif menu == "📝 NUEVO PEDIDO":
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("form_nuevo"):
            st.markdown("### ✍️ REGISTRAR NUEVO TRABAJO")
            c1, c2 = st.columns(2)
            with c1:
                cliente = st.text_input("Cliente")
                producto = st.text_input("Producto")
            with c2:
                monto = st.number_input("Precio Final $", min_value=0.0)
                pago = st.selectbox("Estado Pago", ["Pendiente", "Seña", "Total"])
            
            estado = st.selectbox("Estado Producción", ["Producción", "Vendido", "Entregado"])
            detalle = st.text_area("Detalles (Talle, diseño, etc.)")
            
            if st.form_submit_button("SUBIR A LA NUBE"):
                df_orig = get_data()
                nuevo = pd.DataFrame([{
                    "ID": len(df_orig) + 1,
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": cliente, "Producto": producto, "Detalle": detalle,
                    "Monto": monto, "Pago": pago, "Estado": estado
                }])
                df_up = pd.concat([df_orig, nuevo], ignore_index=True)
                conn.update(worksheet="Pedidos", data=df_up)
                st.success("¡Pedido guardado en Google Sheets!")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif menu == "💰 COTIZADOR":
        st.markdown("### 💰 CALCULADORA NOVA")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        base = st.number_input("Costo Prenda/Insumo $", min_value=0.0)
        margen = st.slider("Margen de Ganancia %", 0, 300, 100)
        st.header(f"Precio de Venta: ${base * (1 + margen/100):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
