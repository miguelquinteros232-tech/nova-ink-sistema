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
            width: 250px; height: 250px; background-image: url("{URL_LOGO_REAL}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.08; pointer-events: none; z-index: 0;
        }}
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
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t1: auth.login(location='main')
    with t2:
        if auth.register_user(location='main'):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f)
            st.success('Registrado.')
else:
    # --- 3. CONEXIÓN ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD ---
    if menu == "📊 DASHBOARD":
        try:
            df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
            if not df_p.empty:
                # Asegurar que los números sean números
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
                
                ventas = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
                gastos = df_p['Gasto_Prod'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("INGRESOS", f"${ventas:,.2f}")
                c2.metric("GASTOS", f"${gastos:,.2f}")
                c3.metric("UTILIDAD", f"${ventas - gastos:,.2f}")

                st.divider()
                for i, r in df_p.iterrows():
                    bloqueado = r['Estado'] == "Vendido"
                    with st.expander(f"{'🔒' if bloqueado else '⚙️'} {r['ID']} - {r['Cliente']}"):
                        if bloqueado:
                            st.info("Venta Finalizada.")
                            st.json(r.to_dict())
                        else:
                            with st.form(f"f_{i}"):
                                n_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                                n_mon = st.number_input("Precio $", value=float(r['Monto']))
                                if st.form_submit_button("Actualizar"):
                                    df_p.at[i, 'Estado'], df_p.at[i, 'Monto'] = n_est, n_mon
                                    conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=df_p)
                                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}. Verifica que la pestaña se llame 'Pedidos' y tenga encabezados.")

    # --- B. STOCK ---
    elif menu == "📦 STOCK":
        try:
            df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
            with st.form("add_inv"):
                st.subheader("Cargar Material")
                c1, c2 = st.columns(2)
                cat, nom = c1.text_input("Categoría"), c1.text_input("Nombre")
                tip, tal = c2.text_input("Tipo"), c2.text_input("Talle")
                col, can = c1.text_input("Color"), c2.number_input("Cantidad", min_value=0.0)
                uni = c2.text_input("Unidad")
                if st.form_submit_button("Guardar"):
                    nuevo = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": tip, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": uni}])
                    conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                    st.rerun()
            st.dataframe(df_inv, use_container_width=True)
        except:
            st.error("Error al cargar Inventario. Verifica la pestaña.")

    # --- C. NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
        with st.form("new_order"):
            st.subheader("Registrar Orden")
            cli, prd = st.text_input("Cliente"), st.text_input("Producto")
            mon, gas = st.number_input("Precio $"), st.number_input("Gasto Materiales $")
            mat = st.selectbox("Material usado", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad usada", min_value=1.0)
            det = st.text_area("Detalles")
            if st.form_submit_button("REGISTRAR"):
                # Restar stock
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                df_inv.at[idx, 'Cantidad'] -= can_u
                conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=df_inv)
                # Guardar pedido
                df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
                nuevo_p = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": det, "Monto": mon, "Estado": "Producción", "Gasto_Prod": gas, "Descripcion": ""}])
                conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                st.success("Hecho."); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora")
        costo = st.number_input("Inversión $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
