import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ MAESTRA ---
st.set_page_config(page_title="NOVA INK - SISTEMA CLOUD", layout="wide", page_icon="🎨")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        .stApp {
            background: #020005 !important;
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(188, 57, 253, 0.15) 0%, transparent 50%),
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
    return conn.read(worksheet="Pedidos", ttl=0)

# --- 3. SEGURIDAD ---
with open("config_pro.yaml") as f:
    config = yaml.load(f, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    authenticator.login(location='main')
else:
    # --- NAVEGACIÓN ---
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NAV OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "💰 COTIZADOR MULTI"], label_visibility="collapsed")
        st.divider()
        authenticator.logout('Finalizar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD & HISTORIAL ---
    if menu == "📊 DASHBOARD":
        df = get_data()
        if df.empty:
            st.info("No hay pedidos registrados en la nube.")
        else:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 ANALÍTICA MENSUAL")
            meses = df['Mes_Año'].unique()
            mes_sel = st.selectbox("Seleccionar Mes", meses, index=len(meses)-1)
            df_mes = df[df['Mes_Año'] == mes_sel]

            c1, c2, c3 = st.columns(3)
            c1.metric(f"Ventas {mes_sel}", f"${df_mes['Monto'].sum():,.2f}")
            c2.metric("Pedidos", len(df_mes))
            c3.metric("Por Cobrar", f"${df_mes[df_mes['Pago'] != 'Total']['Monto'].sum():,.2f}")

            st.divider()
            st.subheader("📝 Gestión de Pedidos Actuales")
            for index, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"#{row['ID']} - {row['Cliente']} - {row['Estado']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        nuevo_pago = st.selectbox("Pago", ["Pendiente", "Seña", "Total"], index=["Pendiente", "Seña", "Total"].index(row['Pago']), key=f"p_{row['ID']}")
                    with col2:
                        nuevo_estado = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0, key=f"e_{row['ID']}")
                    with col3:
                        if st.button("Actualizar", key=f"b_{row['ID']}"):
                            df.at[index, 'Pago'] = nuevo_pago
                            df.at[index, 'Estado'] = nuevo_estado
                            df['Fecha'] = df['Fecha'].dt.strftime('%d/%m/%Y')
                            df_save = df.drop(columns=['Mes_Año'])
                            conn.update(worksheet="Pedidos", data=df_save)
                            st.success("Sincronizado con la Nube")
                            time.sleep(1)
                            st.rerun()

    # --- 📝 REGISTRO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.markdown("### ✍️ REGISTRO DE TRABAJO")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("nuevo_p"):
            cliente = st.text_input("Nombre del Cliente")
            producto = st.text_input("Producto")
            monto = st.number_input("Monto Total $", min_value=0.0)
            pago = st.selectbox("Estado de Pago", ["Pendiente", "Seña", "Total"])
            estado = st.selectbox("Estado de Producción", ["Producción", "Vendido", "Entregado"])
            detalle = st.text_area("Notas del diseño / medidas")
            
            if st.form_submit_button("GUARDAR EN LA NUBE"):
                df_orig = get_data()
                nuevo_p = pd.DataFrame([{
                    "ID": len(df_orig) + 1,
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": cliente,
                    "Producto": producto,
                    "Detalle": detalle,
                    "Monto": monto,
                    "Pago": pago,
                    "Estado": estado
                }])
                df_final = pd.concat([df_orig, nuevo_p], ignore_index=True)
                conn.update(worksheet="Pedidos", data=df_final)
                st.success("¡Pedido inyectado exitosamente!")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR MULTI":
        st.markdown("### 💰 CALCULADORA RÁPIDA")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            costo_base = st.number_input("Costo de prenda/insumo $", min_value=0.0)
        with c2:
            margen = st.slider("Margen de Ganancia %", 0, 300, 100)
        
        precio_final = costo_base * (1 + margen/100)
        st.markdown(f"<h2 style='text-align:center; color:#00ff00;'>PRECIO: ${precio_final:,.2f}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
