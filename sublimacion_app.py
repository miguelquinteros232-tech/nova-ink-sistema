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

# --- 1. ESTILO VISUAL NOVA INK ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp { background: #05000a; }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; margin-bottom: 20px; }
        .stMetric { background: rgba(188, 57, 253, 0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #00d4ff; }
        div[data-testid="stExpander"] { border: 1px solid rgba(188, 57, 253, 0.3); background: rgba(20, 0, 40, 0.5); }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONFIGURACIÓN DE USUARIOS ---
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {
        'credentials': {'usernames': {}},
        'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'},
        'preauthorized': {'emails': []}
    }
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f: yaml.dump(initial_config, f)
        return initial_config
    with open(file_path) as f:
        cfg = yaml.load(f, Loader=SafeLoader)
        return cfg if cfg else initial_config

config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

# --- 3. PROCESO DE LOGIN ---
name, authentication_status, username = authenticator.login(location='main')

if st.session_state["authentication_status"] is False:
    st.error('Usuario o contraseña incorrectos')
elif st.session_state["authentication_status"] is None:
    st.info("Bienvenido. Inicia sesión o regístrate para gestionar Nova Ink.")
    with st.expander("📝 REGISTRO DE NUEVO USUARIO"):
        try:
            # Parche para la versión más reciente de la librería
            if authenticator.register_user(location='main', pre_authorization=False):
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('¡Registro exitoso! Ya puedes ingresar.')
        except Exception:
            st.caption("Completa los campos para crear tu cuenta de acceso.")

# --- 4. APLICACIÓN PRINCIPAL ---
elif st.session_state["authentication_status"]:
    
    @st.cache_resource
    def get_sh_conn():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(credentials)
            return client.open_by_key("1Y0pJANMQxuW_HTS6__Td69fJYvyfyeOyX0thC1CpzlA")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return None

    sh = get_sh_conn()
    
    if sh:
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")

        with st.sidebar:
            st.title(f"Hola, {st.session_state['name']} 👋")
            menu = st.radio("NAVEGACIÓN", ["📊 DASHBOARD", "📝 GESTIÓN PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"])
            authenticator.logout('Cerrar Sesión', 'sidebar')

        # --- A. DASHBOARD (SOLO PENDIENTES) ---
        if menu == "📊 DASHBOARD":
            df_p = pd.DataFrame(ws_p.get_all_records())
            if not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_act = df_p[df_p['Estado'] != 'Vendido']
                
                c1, c2 = st.columns(2)
                c1.metric("PEDIDOS ACTIVOS", len(df_act))
                c2.metric("CAPITAL PENDIENTE", f"${df_act['Monto'].sum():,.2f}")
                
                st.write("### ⚡ Acciones Rápidas")
                for i, r in df_act.iterrows():
                    with st.expander(f"🕒 {r['Estado']} | {r['Cliente']} - {r['Producto']}"):
                        st.write(f"**Requerimientos:** {r['Detalle']}")
                        st.write(f"**Pago:** {r['Notas']}")
                        if st.button("FINALIZAR Y MOVER A HISTORIAL", key=f"f_{i}"):
                            ws_p.update_cell(i+2, 7, "Vendido")
                            st.success("¡Venta registrada!"); time.sleep(1); st.rerun()

        # --- B. GESTIÓN PEDIDOS (CARGA + EDICIÓN) ---
        elif menu == "📝 GESTIÓN PEDIDOS":
            tab1, tab2 = st.tabs(["NUEVO PEDIDO", "MODIFICAR EXISTENTE"])
            df_inv = pd.DataFrame(ws_i.get_all_records())
            
            with tab1:
                with st.form("form_new"):
                    c1, c2 = st.columns(2)
                    cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
                    det = c2.text_area("Descripción detallada")
                    pago = c2.selectbox("Estado de Pago", ["No Pago", "Seña", "Pagado Total"])
                    
                    mon = st.number_input("Precio Final $")
                    mat = st.selectbox("Insumo a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                    can = st.number_input("Cantidad a restar", min_value=0.0)
                    
                    if st.form_submit_button("REGISTRAR"):
                        # Descuento de Stock
                        idx = df_inv[df_inv['Nombre'] == mat].index[0]
                        ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                        # Registro en Pedidos
                        ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                        st.success("Pedido y Stock actualizados correctamente."); st.rerun()

            with tab2:
                df_e = pd.DataFrame(ws_p.get_all_records())
                if not df_e.empty:
                    sel_p = st.selectbox("Elegir pedido para editar", df_e['Cliente'] + " | " + df_e['Producto'])
                    idx_e = df_e[df_e['Cliente'] + " | " + df_e['Producto'] == sel_p].index[0]
                    with st.form("edit_o"):
                        u_det = st.text_area("Editar Descripción", value=df_e.iloc[idx_e]['Detalle'])
                        u_mon = st.number_input("Editar Precio $", value=float(df_e.iloc[idx_e]['Monto']))
                        u_pag = st.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"], index=0)
                        if st.form_submit_button("GUARDAR CAMBIOS"):
                            ws_p.update_cell(idx_e+2, 5, u_det)
                            ws_p.update_cell(idx_e+2, 6, u_mon)
                            ws_p.update_cell(idx_e+2, 9, u_pag)
                            st.success("Cambios aplicados."); st.rerun()

        # --- C. STOCK COMPLETO ---
        elif menu == "📦 STOCK":
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.write("### Inventario General")
            st.dataframe(df_st, use_container_width=True)
            with st.expander("➕ AGREGAR NUEVO MATERIAL"):
                with st.form("add_s"):
                    c1, c2 = st.columns(2)
                    cat, nom, tip = c1.text_input("Categoría"), c1.text_input("Nombre"), c1.text_input("Tipo")
                    tal, col, can, uni = c2.text_input("Talle"), c2.text_input("Color"), c2.number_input("Cantidad"), c2.text_input("Unidad")
                    if st.form_submit_button("CARGAR"):
                        ws_i.append_row([cat, nom, tip, tal, col, can, uni])
                        st.rerun()

        # --- D. HISTORIAL MENSUAL ---
        elif menu == "📜 HISTORIAL":
            df_h = pd.DataFrame(ws_p.get_all_records())
            if not df_h.empty:
                df_h['Fecha'] = pd.to_datetime(df_h['Fecha'], format='%d/%m/%Y', errors='coerce')
                df_h['Mes'] = df_h['Fecha'].dt.strftime('%Y-%m')
                df_v = df_h[df_h['Estado'] == 'Vendido']
                
                meses = df_v['Mes'].unique() if not df_v.empty else ["Sin ventas"]
                mes_sel = st.selectbox("Seleccionar Mes", meses)
                
                if mes_sel != "Sin ventas":
                    df_mes = df_v[df_v['Mes'] == mes_sel]
                    st.metric(f"TOTAL VENTAS {mes_sel}", f"${df_mes['Monto'].sum():,.2f}")
                    st.table(df_mes[['Fecha', 'Cliente', 'Producto', 'Monto', 'Notas']])

        # --- E. COTIZADOR ---
        elif menu == "💰 COTIZADOR":
            c1, c2 = st.columns(2)
            ins, hrs = c1.number_input("Costo Insumos $"), c1.number_input("Horas de Trabajo")
            v_h = c1.number_input("Valor Hora $", value=2000.0)
            mrg = c2.slider("% Ganancia", 0, 400, 100)
            
            costo_base = ins + (hrs * v_h)
            total = costo_base * (1 + mrg/100)
            
            st.divider()
            st.title(f"Sugerido: ${total:,.2f}")
            st.info(f"Costo: ${costo_base:,.2f} | Ganancia: ${total - costo_base:,.2f}")
