import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN VISUAL (ESTILO CYBERPUNK INTEGRAL) ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

# Link de tu logo real
URL_LOGO_REAL = "https://i.postimg.cc/85M9m9zV/nova-ink-logo.png" 

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp {{
            background: #05000a;
            background-image: radial-gradient(circle at 15% 15%, rgba(188, 57, 253, 0.15) 0%, transparent 50%);
        }}
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
        .stMetric {{ background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }}
    </style>
''', unsafe_allow_html=True)

# --- 2. GESTIÓN DE SEGURIDAD ---
def load_config():
    try:
        with open("config_pro.yaml") as f: return yaml.load(f, Loader=SafeLoader)
    except: return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_p'}}

def save_config(cfg):
    with open("config_pro.yaml", 'w') as f: yaml.dump(cfg, f, default_flow_style=False)

config = load_config()
authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

# --- 3. LOGIN ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])
    with t1: authenticator.login(location='main')
    with t2:
        if authenticator.register_user(location='main'):
            save_config(config); st.success('Operador registrado.')
else:
    # --- 4. CONEXIÓN (MÉTODO ROBUSTO) ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['name']}")
        menu = st.radio("MÓDULOS", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD (BALANCE + HISTORIAL BLOQUEADO) ---
    if menu == "📊 DASHBOARD":
        df_p = conn.read(worksheet="Pedidos", ttl=0)
        if not df_p.empty:
            ingresos = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
            gastos = df_p['Gasto_Prod'].sum() if 'Gasto_Prod' in df_p.columns else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("VENTAS REALIZADAS", f"${ingresos:,.2f}")
            c2.metric("COSTOS PROD.", f"${gastos:,.2f}")
            c3.metric("UTILIDAD NETTA", f"${ingresos - gastos:,.2f}")

            st.write("---")
            for i, r in df_p.iterrows():
                es_v = r['Estado'] == "Vendido"
                with st.expander(f"{'🔒' if es_v else '⚙️'} {r['ID']} - {r['Cliente']}"):
                    if es_v:
                        st.warning("Venta cerrada. Solo lectura.")
                        st.table(pd.DataFrame([r[['Fecha', 'Producto', 'Monto', 'Gasto_Prod', 'Detalle']]]))
                    else:
                        with st.form(f"edit_{i}"):
                            c_a, c_b = st.columns(2)
                            st_est = c_a.selectbox("Estado", ["Producción", "Listo", "Vendido"], index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                            st_mon = c_b.number_input("Precio $", value=float(r['Monto']))
                            st_des = st.text_area("Notas", value=r.get('Descripcion', ''))
                            if st.form_submit_button("Actualizar"):
                                df_p.at[i, 'Estado'], df_p.at[i, 'Monto'], df_p.at[i, 'Descripcion'] = st_est, st_mon, st_des
                                conn.update(worksheet="Pedidos", data=df_p)
                                st.rerun()

    # --- B. STOCK (CAMPOS DETALLADOS) ---
    elif menu == "📦 STOCK":
        df_inv = conn.read(worksheet="Inventario", ttl=0)
        with st.expander("➕ REGISTRAR MATERIAL"):
            with st.form("add_st"):
                c1, c2 = st.columns(2)
                i_cat = c1.text_input("Categoría")
                i_nom = c1.text_input("Nombre")
                i_tip = c2.text_input("Tipo Material")
                i_tal = c2.text_input("Talle/Medida")
                i_col = c1.text_input("Color")
                i_can = c2.number_input("Cantidad", min_value=0)
                i_uni = c2.text_input("Unidad")
                if st.form_submit_button("Guardar"):
                    nue = pd.DataFrame([{"Categoría": i_cat, "Nombre": i_nom, "Tipo Material": i_tip, "Talle/Medida": i_tal, "Color": i_col, "Cantidad": i_can, "Unidad": i_uni}])
                    conn.update(worksheet="Inventario", data=pd.concat([df_inv, nue], ignore_index=True))
                    st.rerun()
        st.dataframe(df_inv, use_container_width=True)

    # --- C. NUEVO PEDIDO (RESTA AUTOMÁTICA) ---
    elif menu == "📝 NUEVO PEDIDO":
        df_inv = conn.read(worksheet="Inventario", ttl=0)
        with st.form("f_new"):
            st.subheader("Cargar Producción")
            c1, c2 = st.columns(2)
            p_cli = c1.text_input("Cliente")
            p_prd = c2.text_input("Producto Final")
            p_mon = c1.number_input("Precio $")
            p_gas = c2.number_input("Gasto Materiales $")
            
            p_mat = st.selectbox("Material usado del Stock", df_inv['Nombre'].tolist() if not df_inv.empty else [])
            p_can = st.number_input("Cantidad usada", min_value=1)
            p_det = st.text_area("Detalles (Fecha, ID, Diseño)")
            
            if st.form_submit_button("REGISTRAR"):
                # 1. Resta del Inventario
                idx = df_inv[df_inv['Nombre'] == p_mat].index[0]
                df_inv.at[idx, 'Cantidad'] -= p_can
                conn.update(worksheet="Inventario", data=df_inv)
                # 2. Guardar Pedido
                df_pe = conn.read(worksheet="Pedidos", ttl=0)
                nuevo = pd.DataFrame([{"ID": len(df_pe)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": p_cli, "Producto": p_prd, "Detalle": p_det, "Monto": p_mon, "Estado": "Producción", "Gasto_Prod": p_gas, "Descripcion": ""}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_pe, nuevo], ignore_index=True))
                st.success("Operación Exitosa"); time.sleep(1); st.rerun()

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Precios")
        c_mat = st.number_input("Inversión en insumos $")
        c_gan = st.slider("% Ganancia deseada", 0, 500, 100)
        st.title(f"Sugerido: ${c_mat * (1 + c_gan/100):,.2f}")
