import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="NOVA INK - FULL SYSTEM", layout="wide", page_icon="🎨")

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

# --- 2. CONEXIÓN A DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(worksheet="Pedidos", ttl=0)

# --- 3. SEGURIDAD Y REGISTRO ---
# Cargamos el config. Si no existe, creamos una estructura base para evitar errores
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key', 'name': 'nova_cookie'}}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Pantalla de Login / Registro
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_reg = st.tabs(["🔑 Iniciar Sesión", "✨ Nuevo Socio"])
        
        with tab_login:
            authenticator.login(location='main')
            if st.session_state["authentication_status"] is False:
                st.error("Usuario o contraseña incorrectos")
            elif st.session_state["authentication_status"] is None:
                st.warning("Ingresa tus credenciales para acceder al sistema.")
        
        with tab_reg:
            with st.form("registro_nuevo"):
                new_user = st.text_input("Nombre de Usuario")
                new_pw = st.text_input("Nueva Contraseña", type="password")
                confirm_pw = st.text_input("Confirmar Contraseña", type="password")
                
                if st.form_submit_button("REGISTRAR SOCIO"):
                    if new_pw == confirm_pw and new_user:
                        # CORRECCIÓN AQUÍ: Nueva sintaxis para Hasher
                        hashed_pw = stauth.Hasher.hash(new_pw)
                        
                        config['credentials']['usernames'][new_user] = {
                            'name': new_user,
                            'password': hashed_pw
                        }
                        # Guardamos el cambio en el archivo local
                        with open("config_pro.yaml", 'w') as f:
                            yaml.dump(config, f)
                        st.success("Socio registrado. Ahora intenta iniciar sesión.")
                    else:
                        st.error("Las contraseñas no coinciden o faltan datos.")

# --- 4. APLICACIÓN PRINCIPAL (POST-LOGIN) ---
else:
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NAV OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "💰 COTIZADOR"], label_visibility="collapsed")
        st.divider()
        authenticator.logout('Finalizar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df = get_data()
        if df.empty:
            st.info("No hay registros en Google Sheets.")
        else:
            # Asegurar formato de fecha
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Fecha']) # Limpiar filas vacías si existen
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 BALANCES MENSUALES")
            meses = df['Mes_Año'].unique()
            mes_sel = st.selectbox("Seleccionar Mes", meses, index=len(meses)-1)
            df_mes = df[df['Mes_Año'] == mes_sel]

            c1, c2, c3 = st.columns(3)
            c1.metric(f"Ventas", f"${df_mes['Monto'].sum():,.2f}")
            c2.metric("Pedidos", len(df_mes))
            c3.metric("Por Cobrar", f"${df_mes[df_mes['Pago'] != 'Total']['Monto'].sum():,.2f}")

            st.divider()
            for index, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"#{row['ID']} - {row['Cliente']} ({row['Estado']})"):
                    ca, cb, cc = st.columns(3)
                    with ca:
                        nPago = st.selectbox("Pago", ["Pendiente", "Seña", "Total"], index=["Pendiente", "Seña", "Total"].index(row['Pago']), key=f"p_{row['ID']}")
                    with cb:
                        nEst = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0, key=f"e_{row['ID']}")
                    with cc:
                        if st.button("Sincronizar ✅", key=f"b_{row['ID']}"):
                            # Volvemos a leer para no sobreescribir otros cambios
                            df_full = get_data() 
                            # Actualizamos
                            df_full.at[index, 'Pago'] = nPago
                            df_full.at[index, 'Estado'] = nEst
                            conn.update(worksheet="Pedidos", data=df_full)
                            st.rerun()

    # --- REGISTRO DE PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("nuevo_p"):
            st.markdown("### ✍️ NUEVA ENTRADA")
            cliente = st.text_input("Cliente")
            prod = st.text_input("Producto")
            monto = st.number_input("Monto $", min_value=0.0)
            pago = st.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            estado = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"])
            detalle = st.text_area("Detalle")
            
            if st.form_submit_button("GUARDAR EN GOOGLE SHEETS"):
                df_orig = get_data()
                nuevo = pd.DataFrame([{
                    "ID": len(df_orig) + 1,
                    "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": cliente, "Producto": prod, "Detalle": detalle,
                    "Monto": monto, "Pago": pago, "Estado": estado
                }])
                df_final = pd.concat([df_orig, nuevo], ignore_index=True)
                conn.update(worksheet="Pedidos", data=df_final)
                st.success("¡Pedido inyectado correctamente!")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.markdown("### 💰 CALCULADORA RÁPIDA")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        base = st.number_input("Costo Base (Insumo) $", min_value=0.0)
        ganancia = st.slider("Ganancia %", 0, 300, 100)
        st.header(f"Precio Sugerido: ${base * (1 + ganancia/100):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
