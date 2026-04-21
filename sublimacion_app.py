import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import PermissionDenied, WorksheetNotFound
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

# --- 2. FUNCIONES DE CONFIGURACIÓN ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_a'}}
        with open("config_pro.yaml", 'w') as f:
            yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f:
        return yaml.load(f, Loader=SafeLoader)

# --- 3. AUTENTICACIÓN ---
config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t1:
        authenticator.login(location='main')
    with t2:
        try:
            if authenticator.register_user(location='main', pre_authorization=False):
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('Usuario registrado. Inicia sesión.')
        except Exception as e:
            st.error(f"Error al registrar: {e}")

# --- 4. APP PRINCIPAL ---
elif st.session_state["authentication_status"]:
    
    @st.cache_resource
    def get_gspread_client():
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(credentials)

    try:
        client = get_gspread_client()
        SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
        sh = client.open_by_key(SHEET_ID)
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")
    except PermissionDenied:
        st.error("❌ ERROR DE PERMISOS: Comparte tu Google Sheet con el correo del bot como EDITOR.")
        st.info(f"Email del bot: `{st.secrets['connections']['gsheets']['client_email']}`")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

    with st.sidebar:
        st.write(f"👤 Operador: {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df_p = pd.DataFrame(ws_p.get_all_records())
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            
            v_reales = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            g_totales = df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("VENTAS TOTALES", f"${v_reales:,.2f}")
            c2.metric("COSTOS PRODUCCIÓN", f"${g_totales:,.2f}")
            c3.metric("UTILIDAD NETA", f"${v_reales - g_totales:,.2f}")

            st.divider()
            for i, r in df_p.iterrows():
                es_vendido = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if es_vendido else '⚙️'} {r['ID']} - {r['Cliente']} ({r['Producto']})"):
                    if es_vendido:
                        st.warning("Venta cerrada. Edición deshabilitada.")
                        st.write(f"Monto: ${r['Monto']} | Gasto: ${r['Gasto_Prod']} | Detalle: {r['Detalle']}")
                    else:
                        with st.form(f"f_edit_{i}"):
                            col_a, col_b = st.columns(2)
                            n_est = col_a.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            n_mon = col_b.number_input("Precio Cobrado $", value=float(r['Monto']))
                            n_gas = col_b.number_input("Gasto Material $", value=float(r['Gasto_Prod']))
                            n_det = st.text_area("Detalles/Notas", value=r['Detalle'])
                            if st.form_submit_button("Actualizar Registro"):
                                ws_p.update_cell(i+2, 6, n_mon) # Monto
                                ws_p.update_cell(i+2, 7, n_est) # Estado
                                ws_p.update_cell(i+2, 8, n_gas) # Gasto
                                ws_p.update_cell(i+2, 5, n_det) # Detalle
                                st.rerun()

    # --- STOCK ---
    elif menu == "📦 STOCK":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.expander("➕ AGREGAR NUEVO MATERIAL"):
            with st.form("f_add_stock"):
                c1, c2 = st.columns(2)
                v_cat = c1.selectbox("Categoría", ["Remeras", "Tazas", "Gorras", "Telas", "Tintas", "Papel", "Otros"])
                v_nom = c1.text_input("Nombre del Producto")
                v_tip, v_tal = c2.text_input("Tipo Material"), c2.text_input("Talle/Medida")
                v_col, v_can = c1.text_input("Color"), c2.number_input("Cantidad Inicial", min_value=0.0)
                v_uni = c2.text_input("Unidad (Un, Mts, etc)")
                if st.form_submit_button("Guardar en Stock"):
                    ws_i.append_row([v_cat, v_nom, v_tip, v_tal, v_col, v_can, v_uni])
                    st.rerun()
        st.subheader("📦 Inventario Actual")
        st.dataframe(df_inv, use_container_width=True)

    # --- NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with st.form("f_new_order"):
            st.subheader("Alta de Producción")
            c1, c2 = st.columns(2)
            p_cli, p_prd = c1.text_input("Cliente"), c2.text_input("Producto")
            p_mon, p_gas = c1.number_input("Monto $"), c2.number_input("Gasto $")
            
            st.divider()
            mats = df_inv['Nombre'].tolist() if not df_inv.empty else []
            p_mat = st.selectbox("Insumo a descontar", mats if mats else ["Sin stock"])
            p_can = st.number_input("Cantidad usada", min_value=0.1)
            p_det = st.text_area("Notas de diseño")
            
            if st.form_submit_button("REGISTRAR Y DESCONTAR STOCK"):
                if p_mat != "Sin stock":
                    # Restar stock
                    idx = df_inv[df_inv['Nombre'] == p_mat].index[0]
                    nueva_c = float(df_inv.at[idx, 'Cantidad']) - p_can
                    ws_i.update_cell(idx+2, 6, nueva_c)
                    # Guardar pedido
                    ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), p_cli, p_prd, p_det, p_mon, "Producción", p_gas, ""])
                    st.success("✅ Pedido y Stock actualizados."); time.sleep(1); st.rerun()
                else:
                    st.error("No hay materiales cargados.")

    # --- COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Margen")
        c_costo = st.number_input("Inversión en materiales $")
        c_margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${c_costo * (1 + c_margen/100):,.2f}")

elif st.session_state["authentication_status"] is False:
    st.error('Usuario/Contraseña incorrectos')
