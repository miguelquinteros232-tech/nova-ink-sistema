import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN VISUAL NOVA INK ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")

URL_LOGO_REAL = "https://i.postimg.cc/85M9m9zV/nova-ink-logo.png" 

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: 50px; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 10px; font-weight: 900; margin-bottom: 20px;
        }}
        .stMetric {{ background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }}
    </style>
''', unsafe_allow_html=True)

# --- 2. SISTEMA DE REGISTRO Y AUTENTICACIÓN ---
def load_config():
    try:
        with open("config_pro.yaml") as f:
            return yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        # Configuración inicial si el archivo no existe
        return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_ink_key', 'name': 'nova_ink_auth'}}

config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Interfaz de Login/Registro
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])
    
    with tab_login:
        authenticator.login(location='main')
    
    with tab_reg:
        try:
            if authenticator.register_user(location='main', pre_authorization=False):
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('Usuario registrado con éxito. Ya puedes iniciar sesión.')
        except Exception as e:
            st.error(f"Error al registrar: {e}")

# --- 3. APLICACIÓN PRINCIPAL (Si está autenticado) ---
elif st.session_state["authentication_status"]:
    
    # Conexión Directa a Google Sheets (Gspread)
   # --- 3. CONEXIÓN DIRECTA A GOOGLE SHEETS (GSPREAD) ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Intentar obtener credenciales de los Secrets
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            st.error("❌ No se encontraron las credenciales en los Secrets de Streamlit.")
            st.stop()
            
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        
        # Corregir posibles problemas de saltos de línea en la clave privada
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Error al autenticar con Google: {str(e)}")
        st.stop()

try:
    client = get_gspread_client()
    SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
    sh = client.open_by_key(SHEET_ID)
    
    # Intentar acceder a las pestañas y avisar si no existen
    try:
        ws_pedidos = sh.worksheet("Pedidos")
        ws_inventario = sh.worksheet("Inventario")
    except gspread.exceptions.WorksheetNotFound:
        st.error("❌ No se encontró la pestaña 'Pedidos' o 'Inventario' en el Excel.")
        st.info("Asegúrate de que los nombres de las pestañas sean exactos.")
        st.stop()
        
except gspread.exceptions.PermissionDenied:
    st.error("❌ Error de Permisos: El bot no tiene acceso a la hoja.")
    st.info("Copia el 'client_email' de tus Secrets y dale permisos de EDITOR en tu Google Sheet.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error inesperado: {e}")
    st.stop()

    # --- A. DASHBOARD (BALANCE Y GESTIÓN) ---
    if menu == "📊 DASHBOARD":
        data_p = ws_pedidos.get_all_records()
        df_p = pd.DataFrame(data_p)
        
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            
            ingresos = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            gastos = df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("VENTAS REALES", f"${ingresos:,.2f}")
            c2.metric("GASTOS PROD.", f"${gastos:,.2f}")
            c3.metric("UTILIDAD NETA", f"${ingresos - gastos:,.2f}")

            st.divider()
            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '⚙️'} {r['ID']} - {r['Cliente']}"):
                    if bloqueado:
                        st.info("Venta cerrada. Los datos están protegidos.")
                        st.table(pd.DataFrame([r]))
                    else:
                        with st.form(f"edit_{i}"):
                            col1, col2 = st.columns(2)
                            nuevo_est = col1.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nuevo_mon = col2.number_input("Precio $", value=float(r['Monto']))
                            nuevo_gas = col2.number_input("Gasto $", value=float(r['Gasto_Prod']))
                            nuevo_det = st.text_area("Detalles", value=r['Detalle'])
                            if st.form_submit_button("Actualizar"):
                                # Actualizar celdas específicas (Fila i+2 porque gspread empieza en 1 y la fila 1 es encabezado)
                                ws_pedidos.update_cell(i+2, 6, nuevo_mon) # Monto
                                ws_pedidos.update_cell(i+2, 7, nuevo_est) # Estado
                                ws_pedidos.update_cell(i+2, 8, nuevo_gas) # Gasto
                                ws_pedidos.update_cell(i+2, 5, nuevo_det) # Detalle
                                st.success("Guardado"); time.sleep(1); st.rerun()

    # --- B. STOCK (INVENTARIO DETALLADO) ---
    elif menu == "📦 STOCK":
        data_i = ws_inventario.get_all_records()
        df_inv = pd.DataFrame(data_i)
        
        with st.expander("➕ CARGAR NUEVO MATERIAL"):
            with st.form("add_stock"):
                c1, c2 = st.columns(2)
                cat = c1.selectbox("Categoría", ["Remeras", "Tazas", "Gorras", "Telas", "Tintas", "Papel", "Otros"])
                nom = c1.text_input("Nombre del Insumo")
                tip = c2.text_input("Tipo de Material")
                tal = c2.text_input("Talle/Medida")
                col = c1.text_input("Color")
                can = c2.number_input("Cantidad Actual", min_value=0.0)
                uni = c2.text_input("Unidad (Un, Mts, etc)")
                if st.form_submit_button("Registrar Insumo"):
                    ws_inventario.append_row([cat, nom, tip, tal, col, can, uni])
                    st.success("Inventario actualizado"); time.sleep(1); st.rerun()
        
        st.subheader("📦 Inventario en Tiempo Real")
        st.dataframe(df_inv, use_container_width=True)

    # --- C. NUEVO PEDIDO (CON DESCUENTO DE STOCK) ---
    elif menu == "📝 NUEVO PEDIDO":
        data_i = ws_inventario.get_all_records()
        df_inv = pd.DataFrame(data_i)
        
        with st.form("form_order"):
            st.subheader("Registrar Venta/Producción")
            c1, c2 = st.columns(2)
            p_cli = c1.text_input("Nombre Cliente")
            p_prd = c2.text_input("Producto Final")
            p_mon = c1.number_input("Monto Cobrado $", min_value=0.0)
            p_gas = c2.number_input("Gasto de Insumos $", min_value=0.0)
            
            st.divider()
            st.write("🔧 Selección de Material")
            materiales = df_inv['Nombre'].tolist() if not df_inv.empty else []
            p_mat = st.selectbox("Insumo a utilizar", materiales if materiales else ["Sin stock"])
            p_can = st.number_input("Cantidad a descontar", min_value=0.1)
            p_det = st.text_area("Detalles del Pedido")
            
            if st.form_submit_button("REGISTRAR Y RESTAR STOCK"):
                if p_mat != "Sin stock":
                    # 1. Restar Stock
                    idx = df_inv[df_inv['Nombre'] == p_mat].index[0]
                    nueva_cant = float(df_inv.at[idx, 'Cantidad']) - p_can
                    ws_inventario.update_cell(idx+2, 6, nueva_cant) # Columna F (Cantidad)
                    
                    # 2. Registrar Pedido
                    ws_pedidos.append_row([
                        len(ws_pedidos.get_all_values()), 
                        datetime.now().strftime("%d/%m/%Y"),
                        p_cli, p_prd, p_det, p_mon, "Producción", p_gas, ""
                    ])
                    st.success("✅ ¡Hecho! Stock y Pedidos actualizados."); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Margen")
        costo = st.number_input("Costo de producción $")
        margen = st.slider("% Ganancia deseada", 0, 500, 100)
        st.title(f"Precio Sugerido: ${costo * (1 + margen/100):,.2f}")

# Mensaje si la autenticación falla
elif st.session_state["authentication_status"] is False:
    st.error('Usuario o contraseña incorrectos')
