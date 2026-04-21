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

# URL de la hoja (Asegúrate de que esté como "Cualquier persona con el enlace" y "Editor")
URL_HOJA = "https://docs.google.com/spreadsheets/d/11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
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
        # Estructura inicial si el archivo no existe
        return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(config):
    try:
        with open("config_pro.yaml", 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        st.error(f"Error al guardar configuración: {e}")

config = load_config()

# --- 3. AUTENTICACIÓN ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Renderizado de Interfaz de Acceso
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["🔐 Entrar", "📝 Registrar Nuevo Operador"])
    
    with tab_login:
        authenticator.login(location='main')
        if st.session_state["authentication_status"] is False:
            st.error('Usuario o contraseña incorrectos')
    
    with tab_register:
        try:
            if authenticator.register_user(location='main'):
                save_config(config)
                st.success('✅ Usuario registrado. Ahora puedes iniciar sesión en la otra pestaña.')
        except Exception as e:
            st.error(f'Error en registro: {e}')
else:
    # --- 4. SISTEMA PRINCIPAL (LOGUEADO) ---
    conn = st.connection("gsheets", type=GSheetsConnection)

    with st.sidebar:
        st.markdown(f"## 👤 {st.session_state['name']}")
        menu = st.radio("MENÚ DE CONTROL", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # Función para lectura segura de Sheets
    def safe_read(worksheet_name):
        try:
            return conn.read(spreadsheet=URL_HOJA, worksheet=worksheet_name, ttl=0)
        except Exception:
            st.error(f"⚠️ No se pudo conectar con la hoja '{worksheet_name}'. Revisa los permisos de Google Sheets.")
            return pd.DataFrame()

    # --- LÓGICA DE MENÚS ---
    if menu == "📊 DASHBOARD":
        df = safe_read("Pedidos")
        if not df.empty:
            # Métricas rápidas
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos Totales", f"${df['Monto'].sum():,.2f}")
            c2.metric("En Producción", len(df[df['Estado'] == 'Producción']))
            c3.metric("Listos para Entrega", len(df[df['Estado'] == 'Listo']))

            # Gráfico de Ventas Mensuales
            try:
                df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
                df_ventas = df.groupby(df['Fecha'].dt.strftime('%m-%Y'))['Monto'].sum().reset_index()
                fig = px.bar(df_ventas, x='Fecha', y='Monto', title="Rendimiento de Ventas", template="plotly_dark")
                fig.update_traces(marker_color='#bc39fd')
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.info("Gráfico en proceso de datos...")

            st.write("---")
            st.subheader("📋 Gestión de Pedidos Actuales")
            
            # Listado de pedidos con edición
            for i, r in df.iterrows():
                with st.expander(f"ORDEN #{r['ID']} - {r['Cliente']} ({r['Estado']})"):
                    if r['Estado'] == "Vendido":
                        st.info("🔒 Pedido finalizado. Solo lectura.")
                        st.write(f"**Descripción Original:** {r.get('Descripción', 'Sin detalle')}")
                    else:
                        with st.form(f"edit_form_{i}"):
                            col1, col2 = st.columns(2)
                            new_cli = col1.text_input("Cliente", value=r['Cliente'])
                            new_mon = col2.number_input("Monto $", value=float(r['Monto']))
                            new_est = st.selectbox("Cambiar Estado", ["Producción", "Listo", "Vendido"], 
                                                 index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            new_des = st.text_area("Descripción (Talles, Colores, Notas de diseño)", value=r.get('Descripción', ''))
                            
                            if st.form_submit_button("Sincronizar Cambios"):
                                df.at[i, 'Cliente'] = new_cli
                                df.at[i, 'Monto'] = new_mon
                                df.at[i, 'Estado'] = new_est
                                df.at[i, 'Descripción'] = new_des
                                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                                st.success("¡Datos actualizados en Google Sheets!"); time.sleep(1); st.rerun()

    elif menu == "📝 NUEVO PEDIDO":
        with st.form("form_nuevo_pedido"):
            st.subheader("Registrar Nueva Venta")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Nombre del Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Precio de Venta $", min_value=0.0)
            est = c2.selectbox("Estado Inicial", ["Producción", "Listo"])
            des = st.text_area("Detalles del pedido (Ej: Remera Negra XL, Diseño Logo Frente)")
            
            if st.form_submit_button("REGISTRAR EN SISTEMA"):
                df_existente = safe_read("Pedidos")
                nuevo_id = len(df_existente) + 1
                fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                
                nuevo_registro = pd.DataFrame([{
                    "ID": nuevo_id, "Fecha": fecha_hoy, "Cliente": cli, 
                    "Producto": prd, "Monto": mon, "Estado": est, "Descripción": des
                }])
                
                df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df_final)
                st.success("✅ Pedido guardado exitosamente"); time.sleep(1); st.rerun()

    elif menu == "📦 STOCK":
        st.subheader("📦 Control de Inventario")
        df_inv = safe_read("Inventario")
        st.dataframe(df_inv, use_container_width=True)
    
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Costos")
        costo_insumo = st.number_input("Costo de insumos (Materia prima) $", min_value=0.0)
        margen = st.slider("Margen de Ganancia deseado %", 0, 500, 100)
        precio_sugerido = costo_insumo * (1 + margen/100)
        st.title(f"Sugerido: ${precio_sugerido:,.2f}")
        st.caption("Recuerda sumar costos de envío o diseño si aplica.")
