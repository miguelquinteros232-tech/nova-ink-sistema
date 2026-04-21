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

URL_HOJA = "https://docs.google.com/spreadsheets/d/11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
# URL_LOGO_LOGO = "PEGA_AQUI_TU_URL" # Descomenta y pega tu URL para la marca de agua

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@900&display=swap');
        .stApp {{ background: #05000a; background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%); }}
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

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t_log, t_reg = st.tabs(["🔐 Entrar", "📝 Registro"])
    with t_log: authenticator.login(location='main')
    with t_reg:
        if authenticator.register_user(location='main'):
            save_config(config); st.success('✅ Registrado.')
else:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.write(f"### 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    def safe_read(ws):
        try: return conn.read(spreadsheet=URL_HOJA, worksheet=ws, ttl=0)
        except: return pd.DataFrame()

    # --- SECCIÓN: STOCK ---
    if menu == "📦 STOCK":
        st.subheader("📦 Inventario de Materiales")
        with st.expander("➕ REGISTRAR / ACTUALIZAR MATERIAL"):
            with st.form("form_stock"):
                c1, c2 = st.columns(2)
                cat = c1.selectbox("Categoría", ["Remeras", "Gorras", "Tazas", "Insumos", "Papelería"])
                nom = c1.text_input("Nombre del Producto")
                tipo = c2.text_input("Tipo de Material")
                medida = c2.text_input("Talle / Medida")
                color = c1.text_input("Color")
                cant = c2.number_input("Cantidad a Ingresar", min_value=0)
                uni = st.selectbox("Unidad", ["Unidades", "Metros", "Hojas", "Gramos"])
                
                if st.form_submit_button("GUARDAR EN INVENTARIO"):
                    df_inv = safe_read("Inventario")
                    nuevo = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": tipo, "Talle/Medida": medida, "Color": color, "Cantidad": cant, "Unidad": uni}])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                    st.success("✅ Stock actualizado"); time.sleep(1); st.rerun()

        df_s = safe_read("Inventario")
        st.dataframe(df_s, use_container_width=True)

    # --- SECCIÓN: DASHBOARD (HISTORIAL Y BALANCE) ---
    elif menu == "📊 DASHBOARD":
        df = safe_read("Pedidos")
        if not df.empty:
            # Cálculos de Balance
            ingresos = df[df['Estado'] == 'Vendido']['Monto'].sum()
            gastos = df['Gasto_Prod'].sum() if 'Gasto_Prod' in df.columns else 0
            balance = ingresos - gastos

            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos (Ventas Realizadas)", f"${ingresos:,.2f}")
            c2.metric("Gastos de Producción", f"${gastos:,.2f}")
            c3.metric("Balance Neto (Utilidad)", f"${balance:,.2f}", delta=float(balance))

            st.write("---")
            st.subheader("📋 Gestión de Pedidos y Ventas")
            for i, r in df.iterrows():
                # BLOQUEO SI ESTÁ VENDIDO
                es_vendido = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if es_vendido else '✏️'} {r['ID']} - {r['Cliente']} ({r['Estado']})"):
                    if es_vendido:
                        st.warning("Este pedido ya ha sido vendido y no puede modificarse.")
                        st.json(r.to_dict())
                    else:
                        with st.form(f"edit_{i}"):
                            nc = st.text_input("Cliente", value=r['Cliente'])
                            nm = st.number_input("Monto $", value=float(r['Monto']))
                            ne = st.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            nd = st.text_area("Descripción", value=r.get('Descripcion', ''))
                            if st.form_submit_button("Actualizar"):
                                df.at[i, 'Cliente'], df.at[i, 'Monto'], df.at[i, 'Estado'], df.at[i, 'Descripcion'] = nc, nm, ne, nd
                                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=df)
                                st.rerun()

    # --- SECCIÓN: NUEVO PEDIDO (RESTA AUTOMÁTICA) ---
    elif menu == "📝 NUEVO PEDIDO":
        with st.form("new_p"):
            st.subheader("Cargar Nueva Orden")
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prod_name = c1.text_input("Producto a fabricar")
            monto = c2.number_input("Monto a cobrar $")
            
            # Selección de material para descuento automático
            df_inv = safe_read("Inventario")
            material_usado = st.selectbox("Material a usar del stock", df_inv['Nombre'].unique() if not df_inv.empty else ["No hay stock"])
            cant_usada = st.number_input("Cantidad de material a usar", min_value=0)
            gasto_est = st.number_input("Gasto de producción estimado $", min_value=0.0)
            
            det = st.text_area("Detalle del pedido")
            
            if st.form_submit_button("REGISTRAR Y DESCONTAR STOCK"):
                # 1. Descuento automático en Inventario
                if not df_inv.empty and material_usado != "No hay stock":
                    idx = df_inv[df_inv['Nombre'] == material_usado].index[0]
                    df_inv.at[idx, 'Cantidad'] -= cant_usada
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=df_inv)
                
                # 2. Registro de Pedido
                df_p = safe_read("Pedidos")
                nuevo = pd.DataFrame([{
                    "ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), 
                    "Cliente": cli, "Producto": prod_name, "Monto": monto, 
                    "Estado": "Producción", "Gasto_Prod": gasto_est, "Descripcion": det
                }])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo], ignore_index=True))
                st.success("✅ Pedido registrado y stock descontado."); time.sleep(1); st.rerun()

    # --- SECCIÓN: COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Cotizador Premium")
        c1, c2 = st.columns(2)
        costo_mat = c1.number_input("Costo de Materiales $", min_value=0.0)
        horas = c1.number_input("Horas de trabajo", min_value=0.0)
        margen = c2.slider("% Ganancia Deseada", 0, 500, 100)
        
        precio_sugerido = (costo_mat + (horas * 10)) * (1 + margen/100)
        
        st.metric("Precio Sugerido al Cliente", f"${precio_sugerido:,.2f}")
        st.info(f"Este cálculo estima un gasto de producción de ${costo_mat + (horas * 10):,.2f}")
