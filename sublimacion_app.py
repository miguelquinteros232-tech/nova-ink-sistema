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

# URL de tu logo real para la marca de agua (Pega tu link aquí)
URL_LOGO_MARCA = "https://i.postimg.cc/85M9m9zV/nova-ink-logo.png" 

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        
        /* FONDO Y ESTÉTICA CYBERPUNK */
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        
        /* MARCA DE AGUA DEL LOGO */
        .stApp::after {{
            content: "";
            position: fixed; bottom: 50px; right: 50px;
            width: 300px; height: 300px;
            background-image: url("{URL_LOGO_MARCA}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.08; pointer-events: none; z-index: 0;
        }}

        /* LOGO NOVA INK NEÓN */
        .main-logo {{
            font-family: 'Orbitron'; font-size: clamp(40px, 10vw, 80px); text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 15px; filter: drop-shadow(0 0 15px #bc39fd);
            margin-bottom: 30px; font-weight: 900;
        }}

        /* TARJETAS ESTILIZADAS */
        .stExpander, .stForm {{
            background: rgba(20, 20, 35, 0.7) !important;
            border: 1px solid #bc39fd !important;
            border-radius: 15px !important;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. GESTIÓN DE USUARIOS ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(cfg):
    with open("config_pro.yaml", 'w') as f: yaml.dump(cfg, f, default_flow_style=False)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. LOGIN Y ACCESO ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t_login, t_reg = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t_login: 
        authenticator.login(location='main')
    with t_reg:
        if authenticator.register_user(location='main'):
            save_config(config); st.success('✅ Registrado.')
else:
    # --- 4. CONEXIÓN A DATOS ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['name']}")
        menu = st.radio("MÓDULOS", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- LÓGICA DASHBOARD (BALANCE Y CIERRE) ---
    if menu == "📊 DASHBOARD":
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        if not df_p.empty:
            ventas_ok = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            gastos_ok = df_p['Gasto_Prod'].sum() if 'Gasto_Prod' in df_p.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS TOTALES", f"${ventas_ok:,.2f}")
            c2.metric("GASTOS TOTALES", f"${gastos_ok:,.2f}")
            c3.metric("UTILIDAD NETTA", f"${ventas_ok - gastos_ok:,.2f}")

            st.write("---")
            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '⚙️'} PEDIDO #{r['ID']} - {r['Cliente']}"):
                    if bloqueado:
                        st.info("Venta finalizada. Este registro no se puede modificar.")
                        st.table(pd.DataFrame([r]))
                    else:
                        with st.form(f"edit_{i}"):
                            new_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            new_mon = st.number_input("Ajustar Monto $", value=float(r['Monto']))
                            new_desc = st.text_area("Notas", value=r.get('Descripcion', ''))
                            if st.form_submit_button("Actualizar"):
                                df_p.at[i, 'Estado'], df_p.at[i, 'Monto'], df_p.at[i, 'Descripcion'] = new_est, new_mon, new_desc
                                conn.update(worksheet="Pedidos", data=df_p)
                                st.rerun()

    # --- LÓGICA STOCK (ESTRUCTURA COMPLETA) ---
    elif menu == "📦 STOCK":
        df_inv = conn.read(worksheet="Inventario", ttl=0)
        with st.expander("➕ CARGAR NUEVO MATERIAL"):
            with st.form("f_inv"):
                c1, c2 = st.columns(2)
                f_cat = c1.text_input("Categoría")
                f_nom = c1.text_input("Nombre")
                f_tip = c2.text_input("Tipo Material")
                f_tal = c2.text_input("Talle/Medida")
                f_col = c1.text_input("Color")
                f_can = c2.number_input("Cantidad", min_value=0)
                f_uni = c2.text_input("Unidad")
                if st.form_submit_button("Guardar"):
                    nuevo = pd.DataFrame([{"Categoría": f_cat, "Nombre": f_nom, "Tipo Material": f_tip, "Talle/Medida": f_tal, "Color": f_col, "Cantidad": f_can, "Unidad": f_uni}])
                    conn.update(worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                    st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- NUEVO PEDIDO (DESCUENTO AUTOMÁTICO) ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = conn.read(worksheet="Inventario", ttl=0)
        with st.form("f_pedido"):
            st.subheader("Cargar Orden")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c2.text_input("Producto")
            mon = c1.number_input("Precio $")
            gas = c2.number_input("Gasto de producción $")
            mat = st.selectbox("Material a usar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            can_u = st.number_input("Cantidad usada", min_value=1)
            det = st.text_area("Detalles/Descripción")
            
            if st.form_submit_button("REGISTRAR PEDIDO"):
                # 1. Descontar Inventario
                idx = df_inv[df_inv['Nombre'] == mat].index[0]
                df_inv.at[idx, 'Cantidad'] -= can_u
                conn.update(worksheet="Inventario", data=df_inv)
                # 2. Guardar Pedido
                df_ped = conn.read(worksheet="Pedidos", ttl=0)
                nuevo_p = pd.DataFrame([{"ID": len(df_ped)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": det, "Monto": mon, "Estado": "Producción", "Gasto_Prod": gas, "Descripcion": ""}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_ped, nuevo_p], ignore_index=True))
                st.success("Hecho."); time.sleep(1); st.rerun()

    # --- COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora")
        cost_mat = st.number_input("Costo materiales $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        st.title(f"Sugerido: ${cost_mat * (1 + margen/100):,.2f}")
