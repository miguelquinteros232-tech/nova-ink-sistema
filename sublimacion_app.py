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

# --- 1. CONFIGURACIÓN VISUAL (ESTILO NOVA INK) ---
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

# --- 2. AUTENTICACIÓN ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        initial_config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'}}
        with open("config_pro.yaml", 'w') as f: yaml.dump(initial_config, f)
        return initial_config
    with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
authenticator.login(location='main')

if st.session_state.get("authentication_status") is not True:
    st.info("Sistema de gestión Nova Ink. Por favor identifíquese.")
    with st.expander("📝 REGISTRO"):
        if authenticator.register_user(location='main', pre_authorization=[]):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f, default_flow_style=False)
            st.success('Registrado correctamente.')

# --- 3. CONEXIÓN Y LÓGICA ---
else:
    @st.cache_resource
    def get_db():
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = dict(st.secrets["connections"]["gsheets"])
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
            client = gspread.authorize(Credentials.from_service_account_info(creds, scopes=scope))
            sh = client.open_by_key("11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8")
            return sh
        except Exception as e: return None

    sh = get_db()
    if not sh:
        st.error("Error de conexión. Verifique permisos en Google Sheets."); st.stop()

    ws_p = sh.worksheet("Pedidos")
    ws_i = sh.worksheet("Inventario")

    with st.sidebar:
        st.title("NOVA OS")
        menu = st.radio("NAVEGACIÓN", ["📊 DASHBOARD", "📝 GESTIÓN PEDIDOS", "📦 STOCK", "📜 HISTORIAL", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    # --- DASHBOARD (SOLO PENDIENTES) ---
    if menu == "📊 DASHBOARD":
        data = ws_p.get_all_records()
        df_all = pd.DataFrame(data)
        if not df_all.empty:
            df_all['Monto'] = pd.to_numeric(df_all['Monto'], errors='coerce').fillna(0)
            df_all['Gasto_Prod'] = pd.to_numeric(df_all['Gasto_Prod'], errors='coerce').fillna(0)
            
            # Filtrar solo Pendientes/Listo (No Vendidos) para el Dashboard activo
            df_active = df_all[df_all['Estado'] != 'Vendido']
            
            c1, c2 = st.columns(2)
            c1.metric("PEDIDOS EN CURSO", len(df_active))
            c2.metric("CAPITAL PENDIENTE", f"${df_active['Monto'].sum():,.2f}")

            st.write("### ⚡ Acciones Rápidas")
            for i, r in df_active.iterrows():
                with st.expander(f"🕒 {r['Estado']} | {r['Cliente']} - {r['Producto']}"):
                    st.write(f"**Descripción:** {r['Detalle']}")
                    if st.button(f"Marcar como VENDIDO", key=f"v_{i}"):
                        ws_p.update_cell(i+2, 7, "Vendido")
                        st.success("¡Vendido! Movido al historial."); time.sleep(1); st.rerun()

    # --- GESTIÓN DE PEDIDOS (NUEVO Y EDICIÓN) ---
    elif menu == "📝 GESTIÓN PEDIDOS":
        tab1, tab2 = st.tabs(["NUEVO PEDIDO", "EDITAR REGISTRADOS"])
        df_inv = pd.DataFrame(ws_i.get_all_records())
        
        with tab1:
            with st.form("new_o"):
                c1, c2 = st.columns(2)
                cli = c1.text_input("Cliente")
                prd = c1.text_input("Producto (Tipo)")
                det = c2.text_area("Descripción detallada (Requerimientos)")
                pago = c2.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"])
                
                mon = st.number_input("Precio Final $")
                mat = st.selectbox("Insumo principal", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                can = st.number_input("Cantidad a descontar del stock", min_value=0.0)
                
                if st.form_submit_button("REGISTRAR Y DESCONTAR"):
                    # Descuento Stock
                    idx = df_inv[df_inv['Nombre'] == mat].index[0]
                    ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                    # Registro Pedido
                    ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                    st.success("Pedido registrado."); st.rerun()

        with tab2:
            data_edit = ws_p.get_all_records()
            df_edit = pd.DataFrame(data_edit)
            if not df_edit.empty:
                sel_p = st.selectbox("Seleccionar pedido para modificar", df_edit['Cliente'] + " - " + df_edit['Producto'])
                idx_e = df_edit[df_edit['Cliente'] + " - " + df_edit['Producto'] == sel_p].index[0]
                row = df_edit.iloc[idx_e]
                
                with st.form("edit_form"):
                    u_det = st.text_area("Modificar descripción", value=row['Detalle'])
                    u_mon = st.number_input("Ajustar Precio $", value=float(row['Monto']))
                    u_pag = st.selectbox("Actualizar Pago", ["No Pago", "Seña", "Pagado Total"], index=["No Pago", "Seña", "Pagado Total"].index(row['Notas'] if row['Notas'] in ["No Pago", "Seña", "Pagado Total"] else "No Pago"))
                    if st.form_submit_button("GUARDAR CAMBIOS"):
                        ws_p.update_cell(idx_e+2, 5, u_det)
                        ws_p.update_cell(idx_e+2, 6, u_mon)
                        ws_p.update_cell(idx_e+2, 9, u_pag)
                        st.success("Cambios guardados."); st.rerun()

    # --- HISTORIAL MENSUAL ---
    elif menu == "📜 HISTORIAL":
        df_h = pd.DataFrame(ws_p.get_all_records())
        if not df_h.empty:
            df_h['Fecha'] = pd.to_datetime(df_h['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_h['Mes'] = df_h['Fecha'].dt.strftime('%Y-%m')
            
            # Solo los vendidos para el historial de ventas
            df_v = df_h[df_h['Estado'] == 'Vendido'].copy()
            
            meses = df_v['Mes'].unique()
            mes_sel = st.selectbox("Seleccionar Mes de Registro", meses if len(meses)>0 else ["Sin registros"])
            
            if mes_sel != "Sin registros":
                df_mes = df_v[df_v['Mes'] == mes_sel]
                st.write(f"### 📈 Balance {mes_sel}")
                st.metric("TOTAL MES", f"${df_mes['Monto'].sum():,.2f}")
                st.table(df_mes[['Fecha', 'Cliente', 'Producto', 'Monto']])
        else:
            st.info("No hay historial aún.")

    # --- STOCK ---
    elif menu == "📦 STOCK":
        df_st = pd.DataFrame(ws_i.get_all_records())
        st.write("### Inventario Actual")
        st.dataframe(df_st, use_container_width=True)
        with st.expander("➕ Cargar nuevo material/insumo"):
            with st.form("st_add"):
                c1, c2, c3 = st.columns(3)
                cat = c1.text_input("Categoría")
                nom = c1.text_input("Nombre Material")
                can = c2.number_input("Cantidad Inicial")
                uni = c2.text_input("Unidad (Mts/Un)")
                if st.form_submit_button("Cargar Stock"):
                    ws_i.append_row([cat, nom, "", "", "", can, uni])
                    st.rerun()

    # --- COTIZADOR VARIABLE ---
    elif menu == "💰 COTIZADOR":
        st.write("### 🧮 Cotizador Pro")
        with st.container():
            c1, c2 = st.columns(2)
            costo_m = c1.number_input("Costo de Materiales $", min_value=0.0)
            horas = c1.number_input("Horas de Trabajo", min_value=0.0)
            val_h = c1.number_input("Valor Hora $", value=1000.0)
            
            envio = c2.number_input("Gasto de Envío/Logística $", min_value=0.0)
            margen = c2.slider("% De Ganancia Deseada", 0, 300, 100)
            
            total_costo = costo_m + (horas * val_h) + envio
            sugerido = total_costo * (1 + margen/100)
            
            st.divider()
            st.title(f"Precio Sugerido: ${sugerido:,.2f}")
            st.info(f"Costo base: ${total_costo:,.2f} | Ganancia neta: ${sugerido - total_costo:,.2f}")
