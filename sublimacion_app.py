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

# Reemplaza con la URL de tu logo real para la marca de agua
URL_LOGO_MARCA = "https://tu-enlace-de-imagen.com/logo.png" 

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap');
        .stApp {{ background: #05000a; }}
        .stApp::after {{
            content: ""; position: fixed; bottom: 50px; right: 50px;
            width: 250px; height: 250px; background-image: url("{URL_LOGO_MARCA}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.05; pointer-events: none; z-index: 0;
        }}
        .main-logo {{
            font-family: 'Orbitron'; font-size: clamp(30px, 8vw, 60px); text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 10px; filter: drop-shadow(0 0 10px #bc39fd); margin-bottom: 20px;
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

# --- 3. INTERFAZ DE ACCESO ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Registro"])
    with t1: authenticator.login(location='main')
    with t2:
        try:
            if authenticator.register_user(location='main'):
                save_config(config); st.success('✅ Registrado.')
        except Exception as e: st.error(f"Error: {e}")
else:
    # --- 4. CONEXIÓN A GOOGLE SHEETS (USANDO SECRETS) ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['name']}")
        menu = st.radio("NAVEGACIÓN", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- FUNCIONES DE NEGOCIO ---
    def get_data(ws):
        return conn.read(worksheet=ws, ttl=0)

    # A. SECCIÓN DASHBOARD (BALANCE Y BLOQUEO)
    if menu == "📊 DASHBOARD":
        df_p = get_data("Pedidos")
        if not df_p.empty:
            ingresos = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            gastos = df_p['Gasto_Prod'].sum() if 'Gasto_Prod' in df_p.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos (Ventas)", f"${ingresos:,.2f}")
            c2.metric("Gastos Producción", f"${gastos:,.2f}")
            c3.metric("Balance Neto", f"${ingresos - gastos:,.2f}")

            st.subheader("📋 Gestión de Pedidos")
            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '✏️'} {r['ID']} - {r['Cliente']} ({r['Estado']})"):
                    if bloqueado:
                        st.info("Venta finalizada. Este registro es histórico y no puede modificarse.")
                        st.write(f"**Detalle:** {r['Detalle']} | **Monto:** ${r['Monto']}")
                    else:
                        with st.form(f"form_ed_{i}"):
                            new_est = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            new_desc = st.text_area("Descripción", value=r.get('Descripcion', ''))
                            if st.form_submit_button("Sincronizar"):
                                df_p.at[i, 'Estado'], df_p.at[i, 'Descripcion'] = new_est, new_desc
                                conn.update(worksheet="Pedidos", data=df_p)
                                st.rerun()

    # B. SECCIÓN STOCK (GESTIÓN COMPLETA)
    elif menu == "📦 STOCK":
        st.subheader("📦 Inventario de Materiales")
        df_inv = get_data("Inventario")
        
        with st.expander("➕ REGISTRAR / ACTUALIZAR MATERIAL"):
            with st.form("f_stock"):
                c1, c2 = st.columns(2)
                cat = c1.text_input("Categoría")
                nom = c1.text_input("Nombre")
                tip = c2.text_input("Tipo Material")
                tal = c2.text_input("Talle/Medida")
                col = c1.text_input("Color")
                can = c2.number_input("Cantidad", min_value=0)
                uni = c1.text_input("Unidad (Hojas, Unids, etc.)")
                if st.form_submit_button("Guardar"):
                    nuevo = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": tip, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": uni}])
                    conn.update(worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                    st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # C. SECCIÓN NUEVO PEDIDO (RESTA AUTOMÁTICA)
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = get_data("Inventario")
        with st.form("n_pedido"):
            st.subheader("Crear Orden y Descontar Stock")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prod = c2.text_input("Producto Final")
            monto = c1.number_input("Monto a cobrar $")
            gasto = c2.number_input("Gasto en materiales $")
            
            mat_select = st.selectbox("Material a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            cant_restar = st.number_input("Cantidad usada", min_value=1)
            
            det = st.text_area("Detalle/Medidas")
            
            if st.form_submit_button("Registrar Pedido"):
                # 1. Restar Stock
                idx = df_inv[df_inv['Nombre'] == mat_select].index[0]
                df_inv.at[idx, 'Cantidad'] -= cant_restar
                conn.update(worksheet="Inventario", data=df_inv)
                
                # 2. Guardar Pedido
                df_ped = get_data("Pedidos")
                nuevo_p = pd.DataFrame([{
                    "ID": len(df_ped)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": cli, "Producto": prod, "Detalle": det, "Monto": monto,
                    "Estado": "Producción", "Gasto_Prod": gasto, "Descripcion": ""
                }])
                conn.update(worksheet="Pedidos", data=pd.concat([df_ped, nuevo_p], ignore_index=True))
                st.success("✅ Pedido creado y Stock actualizado."); time.sleep(1); st.rerun()

    # D. SECCIÓN COTIZADOR
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Producción")
        mat = st.number_input("Inversión en materiales $")
        margen = st.slider("% Ganancia", 0, 500, 100)
        total = mat * (1 + margen/100)
        st.title(f"Sugerido: ${total:,.2f}")
        st.info("Este monto de 'Inversión' es el que debes colocar en 'Gasto_Prod' al crear el pedido.")
