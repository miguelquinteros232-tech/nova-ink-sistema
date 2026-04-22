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

import streamlit as st
import pandas as pd

# --- 2. CONFIGURACIÓN DE AUTH (LÓGICA ORIGINAL) ---
def load_config():
    file_path = "config_pro.yaml"
    initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key_pro', 'name': 'nova_auth'}, 'preauthorized': {'emails': []}}
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
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

# --- INYECCIÓN DE ESTILO "IMAGEN 3" ---
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Inter:wght@400;700&display=swap');
        .stApp { background-color: #000000 !important; }
        [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1a1a1a !important; }
        h1, h2, h3, p, span, label, div { color: white !important; }
        div[role="radiogroup"] label {
            background: #0d0d0d !important; border: 1px solid #1a1a1a !important;
            padding: 15px 20px !important; border-radius: 12px !important; margin-bottom: 10px !important;
            transition: 0.3s all ease;
        }
        div[role="radiogroup"] label:hover { border-color: #00d4ff !important; transform: translateX(5px); }
        div[role="radiogroup"] [aria-checked="true"] label { border-left: 5px solid #00d4ff !important; border-color: #1a1a1a !important; }
    </style>
''', unsafe_allow_html=True)

# --- 3. LOGIN Y REGISTRO ---
name, authentication_status, username = authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Inicia sesión o regístrate para gestionar Nova Ink.")
    with st.expander("📝 CREAR CUENTA NUEVA (REGISTRO)"):
        with st.form("registro_manual"):
            new_email = st.text_input("Correo electrónico")
            new_username = st.text_input("Nombre de Usuario (ID)")
            new_name = st.text_input("Tu Nombre Completo")
            new_password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("REGISTRAR USUARIO"):
                if new_email and new_username and new_password:
                    hashed_password = stauth.Hasher([new_password]).generate()[0]
                    config['credentials']['usernames'][new_username] = {
                        'email': new_email, 'name': new_name, 'password': hashed_password
                    }
                    with open("config_pro.yaml", 'w') as f: yaml.dump(config, f, default_flow_style=False)
                    st.success("✅ Usuario creado."); time.sleep(1); st.rerun()

# --- 4. APLICACIÓN PRINCIPAL (REEMPLAZAR TODO DESDE AQUÍ) ---
elif st.session_state["authentication_status"]:
    @st.cache_resource
    def get_sh_conn():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds_dict = dict(st.secrets["connections"]["gsheets"])
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            return gspread.authorize(credentials).open_by_key("1Y0pJANMQxuW_HTS6__Td69fJYvyfyeOyX0thC1CpzlA")
        except: return None

    sh = get_sh_conn()
    if sh:
        ws_p = sh.worksheet("Pedidos"); ws_i = sh.worksheet("Inventario")

        with st.sidebar:
            st.write(f'''
                <div style="text-align: center; padding: 20px 0; margin-bottom: 10px;">
                    <h1 style="font-family: 'Orbitron', sans-serif; font-size: 35px; font-weight: 700; color: #FFFFFF !important; text-shadow: 0 0 15px #00d4ff; margin: 0;">
                        NOVA INK<span style="color: #00d4ff !important;">.</span>
                    </h1>
                </div>
            ''', unsafe_allow_html=True)
            menu = st.radio("", ["📊 DASHBOARD", "🛍️ PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"], key="nav_nova_ink")

        # --- SECCIÓN DASHBOARD (CON ACCIONES RÁPIDAS) ---
        if "📊 DASHBOARD" in menu:
            try:
                df_p = pd.DataFrame(ws_p.get_all_records())
                df_act = df_p[df_p['Estado'] != 'Vendido'] if not df_p.empty else pd.DataFrame()
                df_vendidos = df_p[df_p['Estado'] == 'Vendido'] if not df_p.empty else pd.DataFrame()
                v_monto = pd.to_numeric(df_vendidos['Monto'], errors='coerce').sum()
                v_pedidos = len(df_act)
            except:
                v_pedidos, v_monto, df_act = 0, 0, pd.DataFrame()

            col1, col2 = st.columns(2)
            with col1:
                st.write(f'<div style="background: linear-gradient(145deg, #0d0d0d, #050505); border: 1px solid #222; padding: 35px; border-radius: 15px; text-align: center;"><p style="color: #666 !important; font-size: 12px; font-weight: bold;">PEDIDOS ACTIVOS</p><h2 style="font-family: Orbitron; font-size: 45px;">{v_pedidos}</h2></div>', unsafe_allow_html=True)
            with col2:
                st.write(f'<div style="background: linear-gradient(145deg, #0d0d0d, #050505); border: 1px solid #222; padding: 35px; border-radius: 15px; text-align: center;"><p style="color: #666 !important; font-size: 12px; font-weight: bold;">VENTAS REALIZADAS</p><h2 style="color: #00d4ff !important; font-family: Orbitron; font-size: 45px;">${v_monto:,.0f}</h2></div>', unsafe_allow_html=True)
            
            st.write("### 🔍 GESTIÓN RÁPIDA DE PEDIDOS")
            if not df_act.empty:
                for i, row in df_act.iterrows():
                    with st.expander(f"🔹 {row['Cliente']} | {row['Producto']} (${row['Monto']})"):
                        st.write(f"**Descripción:** {row['Descripción']}")
                        c1, c2, c3 = st.columns(3)
                        # El índice real en Sheets es i + 2
                        if c1.button("✅ MARCAR VENDIDO", key=f"v_{i}"):
                            ws_p.update_cell(i+2, 7, "Vendido")
                            st.rerun()
                        if c2.button("❌ ELIMINAR / CANCELAR", key=f"d_{i}"):
                            ws_p.delete_rows(i+2)
                            st.rerun()
                        st.info(f"Estado: {row['Estado']} | Pago: {row['Estado Pago']}")
            else:
                st.info("No hay pedidos activos.")

        # --- SECCIÓN PEDIDOS (MODIFICACIÓN COMPLETA) ---
        elif "🛍️ PEDIDOS" in menu:
            tab1, tab2 = st.tabs(["NUEVO PEDIDO", "MODIFICAR / EDITAR"])
            df_inv = pd.DataFrame(ws_i.get_all_records())
            
            with tab1:
                with st.form("n_p"):
                    c1, c2 = st.columns(2)
                    cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
                    det, pago = c2.text_area("Descripción"), c2.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"])
                    mon = st.number_input("Precio Final $")
                    mat = st.selectbox("Insumo a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                    can = st.number_input("Cantidad a restar", min_value=0.0)
                    if st.form_submit_button("REGISTRAR"):
                        idx = df_inv[df_inv['Nombre'] == mat].index[0]
                        ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                        ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                        st.success("Registrado."); st.rerun()
            
            with tab2:
                df_p = pd.DataFrame(ws_p.get_all_records())
                if not df_p.empty:
                    opciones = [f"{i+2} | {row['Cliente']} - {row['Producto']}" for i, row in df_p.iterrows()]
                    sel = st.selectbox("Seleccionar Pedido para editar cualquier dato", opciones)
                    if sel:
                        fila = int(sel.split(" | ")[0])
                        datos = df_p.iloc[fila-2]
                        with st.form("edit_p"):
                            c1, c2 = st.columns(2)
                            e_cli = c1.text_input("Cliente", value=datos['Cliente'])
                            e_prd = c1.text_input("Producto", value=datos['Producto'])
                            e_mon = c1.number_input("Monto $", value=float(datos['Monto']))
                            e_det = c2.text_area("Descripción", value=datos['Descripción'])
                            e_est = c2.selectbox("Estado", ["Producción", "Pendiente", "Vendido"], index=["Producción", "Pendiente", "Vendido"].index(datos['Estado']))
                            e_pag = c2.selectbox("Pago", ["No Pago", "Seña", "Pagado Total"], index=["No Pago", "Seña", "Pagado Total"].index(datos['Estado Pago']))
                            if st.form_submit_button("GUARDAR CAMBIOS TOTALES"):
                                # Actualizamos celda por celda según tus columnas
                                ws_p.update_cell(fila, 3, e_cli)
                                ws_p.update_cell(fila, 4, e_prd)
                                ws_p.update_cell(fila, 5, e_det)
                                ws_p.update_cell(fila, 6, e_mon)
                                ws_p.update_cell(fila, 7, e_est)
                                ws_p.update_cell(fila, 9, e_pag)
                                st.success("¡Datos actualizados!"); time.sleep(1); st.rerun()

        # --- SECCIÓN STOCK ---
        elif "📦 STOCK" in menu:
            df_st = pd.DataFrame(ws_i.get_all_records())
            st.dataframe(df_st, use_container_width=True)
            with st.expander("➕ AGREGAR MATERIAL"):
                with st.form("add_s"):
                    c1, c2 = st.columns(2)
                    cat, nom, tip = c1.text_input("Categoría"), c1.text_input("Nombre"), c1.text_input("Tipo")
                    tal, col, can, uni = c2.text_input("Talle"), c2.text_input("Color"), c2.number_input("Cantidad"), c2.text_input("Unidad")
                    if st.form_submit_button("CARGAR"):
                        ws_i.append_row([cat, nom, tip, tal, col, can, uni]); st.rerun()

        # --- SECCIÓN HISTORIAL ---
        elif "📜 HISTORIAL" in menu:
            df_h = pd.DataFrame(ws_p.get_all_records())
            if not df_h.empty:
                st.write("### ✅ Ventas Finalizadas")
                st.table(df_h[df_h['Estado'] == 'Vendido'])

        # --- SECCIÓN COTIZADOR ---
        elif "💰 COTIZADOR" in menu:
            c1, c2 = st.columns(2)
            ins, hrs, v_h = c1.number_input("Insumos $"), c1.number_input("Horas"), c1.number_input("Valor Hora $", 2000.0)
            mrg = c2.slider("% Ganancia", 0, 400, 100)
            total = (ins + (hrs * v_h)) * (1 + mrg/100)
            st.title(f"Sugerido: ${total:,.2f}")
