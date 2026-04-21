import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")

# Estilos CSS
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap');
        .stApp { background: #05000a; }
        .main-logo {
            font-family: 'Orbitron'; font-size: 50px; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 10px #bc39fd); margin-bottom: 20px;
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. FUNCIONES DE DATOS ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    auth_tab1, auth_tab2 = st.tabs(["🔐 Entrar", "📝 Registro"])
    with auth_tab1: authenticator.login(location='main')
    with auth_tab2:
        if authenticator.register_user(location='main'):
            with open("config_pro.yaml", 'w') as f: yaml.dump(config, f); st.success('Registrado')
else:
    # CONEXIÓN USANDO SECRETS (SERVICE ACCOUNT)
    conn = st.connection("gsheets", type=GSheetsConnection)

    with st.sidebar:
        st.write(f"### Operador: {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- LÓGICA DE DASHBOARD (BALANCE) ---
    if menu == "📊 DASHBOARD":
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        if not df_p.empty:
            # Ventas reales (solo estado Vendido)
            ventas_reales = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            # Gastos de producción (de todos los pedidos cargados)
            gastos_totales = df_p['Gasto_Prod'].sum() if 'Gasto_Prod' in df_p.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos Reales", f"${ventas_reales:,.2f}")
            c2.metric("Gastos Producción", f"${gastos_totales:,.2f}")
            c3.metric("Utilidad Neta", f"${ventas_reales - gastos_totales:,.2f}")

            st.subheader("📋 Control de Órdenes")
            for i, r in df_p.iterrows():
                bloqueado = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if bloqueado else '✏️'} {r['ID']} - {r['Cliente']}"):
                    if bloqueado:
                        st.info("Este pedido ya fue vendido. Registro histórico bloqueado.")
                        st.table(pd.DataFrame([r]))
                    else:
                        with st.form(f"edit_{i}"):
                            nuevo_estado = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nueva_desc = st.text_area("Descripción", value=r['Descripcion'])
                            if st.form_submit_button("Guardar Cambios"):
                                df_p.at[i, 'Estado'] = nuevo_estado
                                df_p.at[i, 'Descripcion'] = nueva_desc
                                conn.update(worksheet="Pedidos", data=df_p)
                                st.rerun()

    # --- LÓGICA DE STOCK (ESTRUCTURA SOLICITADA) ---
    elif menu == "📦 STOCK":
        df_inv = conn.read(worksheet="Inventario", ttl=0)
        with st.form("nuevo_item"):
            st.subheader("Registrar en Inventario")
            c1, c2, c3 = st.columns(3)
            cat = c1.text_input("Categoría")
            nom = c2.text_input("Nombre")
            tip = c3.text_input("Tipo Material")
            tal = c1.text_input("Talle/Medida")
            col = c2.text_input("Color")
            can = c3.number_input("Cantidad", min_value=0)
            if st.form_submit_button("Agregar"):
                nuevo = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": tip, "Talle/Medida": tal, "Color": col, "Cantidad": can}])
                df_final = pd.concat([df_inv, nuevo], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_final)
                st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- LÓGICA DE PEDIDO Y DESCUENTO AUTOMÁTICO ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = conn.read(worksheet="Inventario", ttl=0)
        with st.form("pedido_form"):
            st.subheader("Crear Pedido y Descontar Stock")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prod = c2.text_input("Producto")
            monto = c1.number_input("Monto $")
            gasto = c2.number_input("Gasto de producción $")
            
            material = st.selectbox("Material a usar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            cantidad_usada = st.number_input("Cantidad a descontar", min_value=1)
            
            if st.form_submit_button("Crear Orden"):
                # 1. Restar del inventario
                idx = df_inv[df_inv['Nombre'] == material].index[0]
                df_inv.at[idx, 'Cantidad'] -= cantidad_usada
                conn.update(worksheet="Inventario", data=df_inv)
                
                # 2. Agregar pedido
                df_p = conn.read(worksheet="Pedidos", ttl=0)
                nuevo_p = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prod, "Monto": monto, "Estado": "Producción", "Gasto_Prod": gasto, "Descripcion": ""}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                st.success("Stock actualizado y pedido registrado")
                time.sleep(1); st.rerun()

    # --- LÓGICA DE COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("Calculadora de Producción")
        mat_cost = st.number_input("Gasto en materiales $")
        margen = st.slider("% Ganancia", 0, 300, 100)
        total = mat_cost * (1 + margen/100)
        st.metric("Precio Sugerido", f"${total:,.2f}")
        st.info("Este gasto se puede cargar luego en la sección de Nuevo Pedido.")
