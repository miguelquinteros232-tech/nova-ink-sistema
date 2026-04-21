import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. IDENTIDAD VISUAL ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")

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
            width: 250px; height: 250px; background-image: url("{URL_LOGO_REAL}");
            background-size: contain; background-repeat: no-repeat;
            opacity: 0.08; pointer-events: none; z-index: 0;
        }}
        .stMetric {{ background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #bc39fd; }}
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
    # --- 3. CONEXIÓN REFORZADA ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"

    with st.sidebar:
        st.write(f"👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD (GESTIÓN Y BALANCE) ---
    if menu == "📊 DASHBOARD":
        try:
            df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
            if df_p is not None and not df_p.empty:
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
                
                ventas = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
                gastos = df_p['Gasto_Prod'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("INGRESOS REALES", f"${ventas:,.2f}")
                c2.metric("GASTOS TOTALES", f"${gastos:,.2f}")
                c3.metric("UTILIDAD NETA", f"${ventas - gastos:,.2f}")

                st.divider()
                for i, r in df_p.iterrows():
                    bloqueado = r['Estado'] == "Vendido"
                    with st.expander(f"{'🔒' if bloqueado else '⚙️'} {r['ID']} - {r['Cliente']}"):
                        if bloqueado:
                            st.warning("PEDIDO FINALIZADO. Edición bloqueada.")
                            st.json(r.to_dict())
                        else:
                            with st.form(f"edit_{i}"):
                                c_a, c_b = st.columns(2)
                                n_est = c_a.selectbox("Estado", ["Producción", "Listo", "Vendido"], 
                                                     index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                                n_mon = c_b.number_input("Precio $", value=float(r['Monto']))
                                n_gas = c_b.number_input("Gasto $", value=float(r['Gasto_Prod']))
                                n_det = st.text_area("Detalles", value=r['Detalle'])
                                if st.form_submit_button("Actualizar Registro"):
                                    df_p.at[i, 'Estado'], df_p.at[i, 'Monto'] = n_est, n_mon
                                    df_p.at[i, 'Gasto_Prod'], df_p.at[i, 'Detalle'] = n_gas, n_det
                                    conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=df_p)
                                    st.rerun()
            else:
                st.info("No hay pedidos registrados.")
        except Exception as e:
            st.error(f"Error en Dashboard: {e}")

    # --- B. STOCK (INVENTARIO DETALLADO) ---
    elif menu == "📦 STOCK":
        try:
            df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
            if df_inv is None: df_inv = pd.DataFrame(columns=['Categoría', 'Nombre', 'Tipo Material', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad'])
            
            with st.expander("➕ CARGAR NUEVO MATERIAL"):
                with st.form("add_stock"):
                    c1, c2 = st.columns(2)
                    cat, nom = c1.text_input("Categoría"), c1.text_input("Nombre")
                    tip, tal = c2.text_input("Tipo Material"), c2.text_input("Talle/Medida")
                    col, can = c1.text_input("Color"), c2.number_input("Cantidad", min_value=0.0)
                    uni = c2.text_input("Unidad")
                    if st.form_submit_button("Guardar en Inventario"):
                        nuevo = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Tipo Material": tip, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": uni}])
                        conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=pd.concat([df_inv, nuevo], ignore_index=True))
                        st.rerun()
            st.subheader("📦 Stock Disponible")
            st.dataframe(df_inv, use_container_width=True)
        except Exception as e:
            st.error(f"Error en Stock: {e}")

    # --- C. NUEVO PEDIDO (CON DESCUENTO DE STOCK) ---
    elif menu == "📝 NUEVO PEDIDO":
        try:
            df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
            df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
            
            with st.form("new_order_form"):
                st.subheader("Registro de Producción")
                c1, c2 = st.columns(2)
                cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
                mon, gas = c2.number_input("Precio Cobrado $"), c2.number_input("Costo Materiales $")
                
                st.divider()
                mat_list = df_inv['Nombre'].tolist() if (df_inv is not None and not df_inv.empty) else []
                mat_sel = st.selectbox("Material a descontar", mat_list if mat_list else ["Sin materiales"])
                can_u = st.number_input("Cantidad usada", min_value=0.1)
                det_p = st.text_area("Detalles del Diseño")
                
                if st.form_submit_button("REGISTRAR Y DESCONTAR"):
                    if mat_sel != "Sin materiales":
                        # Descuento de stock
                        idx = df_inv[df_inv['Nombre'] == mat_sel].index[0]
                        df_inv.at[idx, 'Cantidad'] -= can_u
                        conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=df_inv)
                        # Registro de pedido
                        nuevo_p = pd.DataFrame([{
                            "ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"),
                            "Cliente": cli, "Producto": prd, "Detalle": det_p,
                            "Monto": mon, "Estado": "Producción", "Gasto_Prod": gas, "Descripcion": ""
                        }])
                        conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                        st.success("✅ Pedido registrado y stock actualizado."); time.sleep(1); st.rerun()
                    else:
                        st.error("No hay materiales en stock para descontar.")
        except Exception as e:
            st.error(f"Error al crear pedido: {e}")

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Precios")
        costo = st.number_input("Inversión en insumos $")
        margen = st.slider("% Ganancia deseada", 0, 500, 100)
        st.title(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
