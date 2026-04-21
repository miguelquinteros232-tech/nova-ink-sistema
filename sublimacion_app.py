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
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp { background: #05000a; background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%); }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; }
        .stMetric { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }
    </style>
''', unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

config = load_config()
auth = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    auth.login(location='main')
else:
    # --- 3. CONEXIÓN DIRECTA (GSPREAD) ---
    @st.cache_resource
    def get_gspread_client():
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Extraemos las credenciales de los secrets de Streamlit
        creds_dict = st.secrets["connections"]["gsheets"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(credentials)

    client = get_gspread_client()
    SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
    sh = client.open_by_key(SHEET_ID)

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD ---
    if menu == "📊 DASHBOARD":
        ws = sh.worksheet("Pedidos")
        df_p = pd.DataFrame(ws.get_all_records())
        
        if not df_p.empty:
            df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
            df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
            
            v_ok = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            g_ok = df_p['Gasto_Prod'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS", f"${v_ok:,.2f}")
            c2.metric("GASTOS", f"${g_ok:,.2f}")
            c3.metric("UTILIDAD", f"${v_ok - g_ok:,.2f}")

            st.divider()
            for i, r in df_p.iterrows():
                is_sold = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if is_sold else '⚙️'} {r['ID']} - {r['Cliente']}"):
                    if is_sold:
                        st.info("Venta finalizada. Bloqueado.")
                    else:
                        with st.form(f"f_{i}"):
                            new_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            new_mon = st.number_input("Precio $", value=float(r['Monto']))
                            if st.form_submit_button("Guardar Cambios"):
                                ws.update_cell(i+2, 7, new_est) # Columna G (Estado)
                                ws.update_cell(i+2, 6, new_mon) # Columna F (Monto)
                                st.rerun()

    # --- B. STOCK ---
    elif menu == "📦 STOCK":
        ws_inv = sh.worksheet("Inventario")
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        
        with st.expander("➕ CARGAR MATERIAL"):
            with st.form("add_s"):
                c1, c2 = st.columns(2)
                cat, nom = c1.text_input("Categoría"), c1.text_input("Nombre")
                tip, tal = c2.text_input("Tipo"), c2.text_input("Talle")
                col, can = c1.text_input("Color"), c2.number_input("Cantidad", min_value=0.0)
                uni = c2.text_input("Unidad")
                if st.form_submit_button("Guardar"):
                    ws_inv.append_row([cat, nom, tip, tal, col, can, uni])
                    st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- C. NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        ws_p = sh.worksheet("Pedidos")
        ws_i = sh.worksheet("Inventario")
        df_inv = pd.DataFrame(ws_i.get_all_records())
        
        with st.form("new_p"):
            st.subheader("Registro de Orden")
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio $"), st.number_input("Costo $")
            mat = st.selectbox("Material usado", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad usada", min_value=0.1)
            det = st.text_area("Detalles")
            
            if st.form_submit_button("REGISTRAR"):
                # Restar Stock
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                nueva_cant = float(df_inv.at[idx, 'Cantidad']) - can_u
                ws_i.update_cell(idx+2, 6, nueva_cant) # Columna F (Cantidad)
                
                # Crear Pedido
                ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", gas, ""])
                st.success("Registrado."); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        costo = st.number_input("Costo materiales $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
