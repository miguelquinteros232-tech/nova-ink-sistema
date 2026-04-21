import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp { background: #05000a; background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%); }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; margin-bottom: 20px; }
        .stMetric { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }
    </style>
''', unsafe_allow_html=True)

# --- 2. FUNCIONES DE BASE (Carga y Configuración) ---
def load_config():
    """Carga la configuración de usuarios. Si no existe, la crea."""
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'}}
        with open("config_pro.yaml", 'w') as f:
            yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f:
        return yaml.load(f, Loader=SafeLoader)

# --- 3. SISTEMA DE AUTENTICACIÓN ---
config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Renderizado de Interfaz de Acceso
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(["🔐 INICIAR SESIÓN", "📝 REGISTRARSE"])
    
    with tab_login:
        authenticator.login(location='main')
    
    with tab_reg:
        try:
            # Registro de usuario (versión compatible)
            if authenticator.register_user(location='main'):
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('¡Usuario registrado! Ya puedes iniciar sesión.')
        except Exception as e:
            st.error(f"Error al registrar: {e}")

# --- 4. APLICACIÓN PRINCIPAL (ACCESO CONCEDIDO) ---
elif st.session_state["authentication_status"]:
    
   @st.cache_resource
    def get_gspread_client():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            
            # 1. Cargamos las credenciales desde Secrets
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            
            # 2. LIMPIEZA CRÍTICA: Reparamos los saltos de línea de la clave privada
            if "private_key" in creds_dict:
                # Esto soluciona el 90% de los errores de conexión en Streamlit Cloud
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"❌ Error al procesar credenciales: {e}")
            st.stop()

    # Conexión con manejo de errores de permisos
    try:
        client = get_gspread_client()
        SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
        sh = client.open_by_key(SHEET_ID)
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")
    except Exception as e:
        if "Permission" in str(e) or "403" in str(e):
            st.error("❌ ERROR DE PERMISOS DE GOOGLE")
            bot_mail = st.secrets["connections"]["gsheets"]["client_email"]
            st.info(f"Copia este correo y dale acceso de EDITOR en tu Google Sheet:\n\n`{bot_mail}`")
        else:
            st.error(f"❌ Error de conexión: {e}")
        st.stop()

    # Sidebar de navegación
    with st.sidebar:
        st.write(f"👤 Operador: {st.session_state['name']}")
        menu = st.radio("MENÚ PRINCIPAL", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- MÓDULO A: DASHBOARD & BALANCE ---
    if menu == "📊 DASHBOARD":
        df_p = pd.DataFrame(ws_p.get_all_records())
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            
            v_ok = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            g_ok = df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS (VENTAS)", f"${v_ok:,.2f}")
            c2.metric("GASTOS (COSTOS)", f"${g_ok:,.2f}")
            c3.metric("UTILIDAD NETA", f"${v_ok - g_ok:,.2f}")

            st.divider()
            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '⚙️'} {r['ID']} - {r['Cliente']} ({r['Producto']})"):
                    if bloqueado:
                        st.warning("Este registro está cerrado y protegido.")
                        st.write(f"Monto final: ${r['Monto']} | Gasto: ${r['Gasto_Prod']}")
                    else:
                        with st.form(f"edit_{i}"):
                            col_a, col_b = st.columns(2)
                            n_est = col_a.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            n_mon = col_b.number_input("Precio Cobrado $", value=float(r['Monto']))
                            n_gas = col_b.number_input("Gasto Material $", value=float(r['Gasto_Prod']))
                            n_det = st.text_area("Notas", value=r['Detalle'])
                            if st.form_submit_button("Guardar Cambios"):
                                ws_p.update_cell(i+2, 6, n_mon) # Monto
                                ws_p.update_cell(i+2, 7, n_est) # Estado
                                ws_p.update_cell(i+2, 8, n_gas) # Gasto
                                ws_p.update_cell(i+2, 5, n_det) # Detalle
                                st.rerun()

    # --- MÓDULO B: STOCK (INVENTARIO 7 CAMPOS) ---
    elif menu == "📦 STOCK":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.expander("➕ REGISTRAR NUEVO MATERIAL"):
            with st.form("add_stock_form"):
                c1, c2 = st.columns(2)
                cat = c1.selectbox("Categoría", ["Remeras", "Tazas", "Gorras", "Telas", "Insumos", "Otros"])
                nom = c1.text_input("Nombre del Insumo")
                tip = c2.text_input("Tipo de Material")
                tal = c2.text_input("Talle/Medida")
                col = c1.text_input("Color")
                can = c2.number_input("Cantidad Inicial", min_value=0.0)
                uni = c2.text_input("Unidad (Un, Mts, Grs)")
                if st.form_submit_button("Cargar a Inventario"):
                    ws_i.append_row([cat, nom, tip, tal, col, can, uni])
                    st.success("Cargado correctamente"); time.sleep(1); st.rerun()
        
        st.subheader("📦 Stock Disponible")
        st.dataframe(df_inv, use_container_width=True)

    # --- MÓDULO C: NUEVO PEDIDO (CON DESCUENTO AUTOMÁTICO) ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.form("new_order_form"):
            st.subheader("Alta de Trabajo")
            c1, c2 = st.columns(2)
            p_cli, p_prd = c1.text_input("Nombre del Cliente"), c2.text_input("Producto a fabricar")
            p_mon, p_gas = c1.number_input("Monto a Cobrar $"), c2.number_input("Costo Estimado $")
            
            st.divider()
            materiales = df_inv['Nombre'].tolist() if not df_inv.empty else []
            p_mat = st.selectbox("Material a descontar del stock", materiales if materiales else ["Sin stock"])
            p_can = st.number_input("Cantidad de material usada", min_value=0.1)
            p_det = st.text_area("Detalles del pedido / Diseño")
            
            if st.form_submit_button("REGISTRAR Y ACTUALIZAR STOCK"):
                if p_mat != "Sin stock":
                    # 1. Restar del Stock en Google Sheets
                    idx = df_inv[df_inv['Nombre'] == p_mat].index[0]
                    nueva_cant = float(df_inv.at[idx, 'Cantidad']) - p_can
                    ws_i.update_cell(idx+2, 6, nueva_cant) # Columna F es Cantidad
                    
                    # 2. Registrar el Pedido
                    ws_p.append_row([
                        len(ws_p.get_all_values()), 
                        datetime.now().strftime("%d/%m/%Y"),
                        p_cli, p_prd, p_det, p_mon, "Producción", p_gas, ""
                    ])
                    st.success("✅ Pedido creado y Stock descontado."); time.sleep(1); st.rerun()
                else:
                    st.error("No hay materiales en el inventario para descontar.")

    # --- MÓDULO D: COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Precios Sugeridos")
        inv = st.number_input("Inversión en materiales $", min_value=0.0)
        gan = st.slider("% de Ganancia deseada", 0, 500, 100)
        st.title(f"Precio Final Sugerido: ${inv * (1 + gan/100):,.2f}")

elif st.session_state["authentication_status"] is False:
    st.error('Usuario o contraseña incorrectos')
