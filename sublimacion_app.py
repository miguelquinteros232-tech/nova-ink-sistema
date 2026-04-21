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

# CONFIGURACIÓN DE RUTAS
URL_LOGO_MARCA = "https://i.postimg.cc/85M9m9zV/nova-ink-logo.png" # <--- CAMBIA POR TU URL REAL

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        
        /* FONDO Y MARCA DE AGUA */
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
        .stApp::after {{
            content: "";
            position: fixed; bottom: 50px; right: 50px;
            width: 300px; height: 300px;
            background-image: url("{URL_LOGO_MARCA}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.08; pointer-events: none; z-index: 0;
        }}

        /* LOGO PRINCIPAL NEON */
        .main-logo {{
            font-family: 'Orbitron'; font-size: clamp(40px, 10vw, 80px); text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 15px; filter: drop-shadow(0 0 15px #bc39fd);
            margin-bottom: 30px; font-weight: 900;
        }}

        /* ESTILIZACIÓN DE TARJETAS Y FORMULARIOS */
        .stExpander, .stForm {{
            background: rgba(20, 20, 35, 0.7) !important;
            border: 1px solid #bc39fd !important;
            border-radius: 15px !important;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. GESTIÓN DE CONFIGURACIÓN ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(cfg):
    with open("config_pro.yaml", 'w') as f: yaml.dump(cfg, f, default_flow_style=False)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. SISTEMA DE LOGIN / REGISTRO ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 NUEVO OPERADOR"])
    with t1: 
        authenticator.login(location='main')
    with t2:
        try:
            if authenticator.register_user(location='main'):
                save_config(config)
                st.success('✅ Operador registrado en el sistema.')
        except Exception as e: st.error(f"Error: {e}")
else:
    # --- 4. SISTEMA OPERATIVO (AUTENTICADO) ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['name']}")
        menu = st.radio("MODULOS", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # Lectura de datos
    def get_data(ws): return conn.read(worksheet=ws, ttl=0)

    # --- A. DASHBOARD (BALANCE Y GESTIÓN) ---
    if menu == "📊 DASHBOARD":
        df_p = get_data("Pedidos")
        if not df_p.empty:
            ingresos = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            gastos = df_p['Gasto_Prod'].sum() if 'Gasto_Prod' in df_p.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("INGRESOS TOTALES", f"${ingresos:,.2f}")
            c2.metric("GASTOS PRODUCCIÓN", f"${gastos:,.2f}")
            c3.metric("BALANCE NETO", f"${ingresos - gastos:,.2f}")

            st.write("---")
            st.subheader("📋 Historial y Seguimiento")
            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                icon = "🔒" if bloqueado else "⚙️"
                with st.expander(f"{icon} {r['ID']} | {r['Cliente']} - {r['Estado']}"):
                    if bloqueado:
                        st.info("Venta finalizada. Registro bloqueado para edición.")
                        st.json(r.to_dict())
                    else:
                        with st.form(f"f_edit_{i}"):
                            col1, col2 = st.columns(2)
                            ne = col1.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nm = col2.number_input("Ajustar Monto $", value=float(r['Monto']))
                            nd = st.text_area("Notas / Descripción", value=r.get('Descripcion', ''))
                            if st.form_submit_button("Sincronizar"):
                                df_p.at[i, 'Estado'], df_p.at[i, 'Monto'], df_p.at[i, 'Descripcion'] = ne, nm, nd
                                conn.update(worksheet="Pedidos", data=df_p)
                                st.rerun()

    # --- B. STOCK (ESTRUCTURA SOLICITADA) ---
    elif menu == "📦 STOCK":
        st.subheader("📦 Gestión de Inventario")
        df_inv = get_data("Inventario")
        
        with st.expander("➕ REGISTRAR NUEVO MATERIAL"):
            with st.form("form_inv"):
                c1, c2, c3 = st.columns(3)
                f_cat = c1.text_input("Categoría")
                f_nom = c2.text_input("Nombre")
                f_tip = c3.text_input("Tipo Material")
                f_tal = c1.text_input("Talle/Medida")
                f_col = c2.text_input("Color")
                f_can = c3.number_input("Cantidad", min_value=0)
                f_uni = c1.text_input("Unidad")
                if st.form_submit_button("Guardar en Nube"):
                    nuevo = pd.DataFrame([{"Categoría": f_cat, "Nombre": f_nom, "Tipo Material": f_tip, "Talle/Medida": f_tal, "Color": f_col, "Cantidad": f_can, "Unidad": f_uni}])
                    conn.update(worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                    st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- C. NUEVO PEDIDO (RESTA AUTOMÁTICA) ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = get_data("Inventario")
        with st.form("form_pedido"):
            st.subheader("Nueva Orden de Producción")
            c1, c2 = st.columns(2)
            p_cli = c1.text_input("Cliente")
            p_prd = c2.text_input("Producto Final")
            p_mon = c1.number_input("Precio Cobrado $")
            p_gas = c2.number_input("Gasto Estimado (Materiales) $")
            
            p_mat = st.selectbox("Material a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            p_can = st.number_input("Cantidad de material usada", min_value=1)
            p_det = st.text_area("Detalles del Pedido (ID, Fecha, etc)")
            
            if st.form_submit_button("CREAR PEDIDO"):
                # 1. Descuento Automático
                idx = df_inv[df_inv['Nombre'] == p_mat].index[0]
                df_inv.at[idx, 'Cantidad'] -= p_can
                conn.update(worksheet="Inventario", data=df_inv)
                
                # 2. Registro de Pedido
                df_p = get_data("Pedidos")
                nuevo_p = pd.DataFrame([{
                    "ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"),
                    "Cliente": p_cli, "Producto": p_prd, "Detalle": p_det,
                    "Monto": p_mon, "Estado": "Producción", "Gasto_Prod": p_gas, "Descripcion": ""
                }])
                conn.update(worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                st.success("✅ Pedido cargado y Stock restado."); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora Nova Ink")
        mat_cost = st.number_input("Costo de materiales $")
        ganancia = st.slider("% Ganancia", 0, 500, 100)
        total = mat_cost * (1 + ganancia/100)
        st.title(f"Sugerido: ${total:,.2f}")
