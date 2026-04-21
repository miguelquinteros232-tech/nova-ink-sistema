import streamlit as st
from streamlit_gsheets import GSheetsConnection
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
        .stApp {{ background: #05000a; background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%); }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: clamp(35px, 9vw, 75px); text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 12px; filter: drop-shadow(0 0 15px #bc39fd);
            margin-bottom: 25px; font-weight: 900;
        }}
        .stApp::after {{
            content: ""; position: fixed; bottom: 40px; right: 40px;
            width: 280px; height: 280px; background-image: url("{URL_LOGO_REAL}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.07; pointer-events: none; z-index: 0;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. LOGIN ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

config = load_config()
auth = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t1: auth.login(location='main')
    with t2:
        if auth.register_user(location='main'):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f)
            st.success('Operador registrado.')
else:
    # --- 3. CONEXIÓN CORREGIDA ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Limpiamos la URL por si tiene basura al final
    URL_LIMPIA = st.secrets["connections"]["gsheets"]["spreadsheet"].split("/edit")[0]

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df_p = conn.read(spreadsheet=URL_LIMPIA, worksheet="Pedidos", ttl=0)
        if not df_p.empty:
            v_ok = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            g_ok = df_p['Gasto_Prod'].sum() if 'Gasto_Prod' in df_p.columns else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS", f"${v_ok:,.2f}")
            c2.metric("GASTOS", f"${g_ok:,.2f}")
            c3.metric("UTILIDAD", f"${v_ok - g_ok:,.2f}")

            st.divider()
            for i, r in df_p.iterrows():
                is_lock = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if is_lock else '⚙️'} {r['ID']} - {r['Cliente']}"):
                    if is_lock:
                        st.info("Venta Finalizada. Solo lectura.")
                        st.table(pd.DataFrame([r[['Fecha', 'Producto', 'Monto']]]))
                    else:
                        with st.form(f"f_{i}"):
                            ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nm = st.number_input("Precio $", value=float(r['Monto']))
                            if st.form_submit_button("Sincronizar"):
                                df_p.at[i, 'Estado'], df_p.at[i, 'Monto'] = ne, nm
                                conn.update(spreadsheet=URL_LIMPIA, worksheet="Pedidos", data=df_p)
                                st.rerun()

    # --- B. STOCK ---
    elif menu == "📦 STOCK":
        df_inv = conn.read(spreadsheet=URL_LIMPIA, worksheet="Inventario", ttl=0)
        with st.form("add_s"):
            st.subheader("Cargar Inventario")
            c1, c2 = st.columns(2)
            cat = c1.text_input("Categoría")
            nom = c1.text_input("Nombre")
            can = c2.number_input("Cantidad", min_value=0)
            uni = c2.text_input("Unidad")
            if st.form_submit_button("Guardar"):
                # Agregamos columnas faltantes para que no rompa la estructura
                nue = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": "", "Talle/Medida": "", "Color": "", "Cantidad": can, "Unidad": uni}])
                conn.update(spreadsheet=URL_LIMPIA, worksheet="Inventario", data=pd.concat([df_inv, nue], ignore_index=True))
                st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- C. NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = conn.read(spreadsheet=URL_LIMPIA, worksheet="Inventario", ttl=0)
        with st.form("new_p"):
            st.subheader("Cargar Producción")
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio $"), st.number_input("Gasto Prod $")
            mat = st.selectbox("Material usado", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad usada", min_value=1)
            if st.form_submit_button("REGISTRAR"):
                # Restar stock
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                df_inv.at[idx, 'Cantidad'] -= can_u
                conn.update(spreadsheet=URL_LIMPIA, worksheet="Inventario", data=df_inv)
                # Guardar pedido
                df_p = conn.read(spreadsheet=URL_LIMPIA, worksheet="Pedidos", ttl=0)
                nuevo = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": "", "Monto": mon, "Estado": "Producción", "Gasto_Prod": gas, "Descripcion": ""}])
                conn.update(spreadsheet=URL_LIMPIA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("Registrado correctamente"); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora")
        costo = st.number_input("Inversión en insumos $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
