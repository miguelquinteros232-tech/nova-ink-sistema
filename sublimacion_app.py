import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN VISUAL (ESTILO CYBERPUNK) ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

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

# --- 2. SEGURIDAD Y ACCESO ---
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
            st.success('Usuario registrado.')
else:
    # --- 3. CONEXIÓN A DATOS ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_ID = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"

    with st.sidebar:
        st.write(f"👤 Operador: {st.session_state['name']}")
        menu = st.radio("MENÚ PRINCIPAL", ["📊 DASHBOARD", "📦 STOCK", "📝 NUEVO PEDIDO", "💰 COTIZADOR"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- A. DASHBOARD (BALANCE Y GESTIÓN) ---
    if menu == "📊 DASHBOARD":
        try:
            df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
            if not df_p.empty:
                # Limpieza de datos numéricos
                df_p['Monto'] = pd.to_numeric(df_p['Monto'], errors='coerce').fillna(0)
                df_p['Gasto_Prod'] = pd.to_numeric(df_p['Gasto_Prod'], errors='coerce').fillna(0)
                
                ventas_totales = df_p[df_p['Estado'] == 'Vendido']['Monto'].sum()
                gastos_totales = df_p['Gasto_Prod'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("INGRESOS (Ventas)", f"${ventas_totales:,.2f}")
                c2.metric("GASTOS (Producción)", f"${gastos_totales:,.2f}")
                c3.metric("UTILIDAD NETA", f"${ventas_totales - gastos_totales:,.2f}")

                st.divider()
                st.subheader("📋 Gestión de Pedidos Activos")
                
                for i, r in df_p.iterrows():
                    is_sold = r['Estado'] == "Vendido"
                    label = f"{'🔒' if is_sold else '⚙️'} {r['ID']} | {r['Cliente']} - {r['Producto']}"
                    
                    with st.expander(label):
                        if is_sold:
                            st.warning("Este pedido ha sido finalizado y la edición está bloqueada.")
                            st.json(r.to_dict())
                        else:
                            with st.form(f"form_edit_{i}"):
                                col_a, col_b = st.columns(2)
                                nuevo_estado = col_a.selectbox("Estado", ["Producción", "Listo", "Vendido"], 
                                                              index=["Producción", "Listo", "Vendido"].index(r['Estado']))
                                nuevo_monto = col_b.number_input("Precio Final $", value=float(r['Monto']))
                                nuevas_notas = st.text_area("Notas/Descripción", value=r.get('Descripcion', ''))
                                
                                if st.form_submit_button("Actualizar Pedido"):
                                    df_p.at[i, 'Estado'] = nuevo_estado
                                    df_p.at[i, 'Monto'] = nuevo_monto
                                    df_p.at[i, 'Descripcion'] = nuevas_notas
                                    conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=df_p)
                                    st.success("Sincronizado con la nube"); time.sleep(1); st.rerun()
            else:
                st.info("No hay pedidos registrados en la base de datos.")
        except Exception as e:
            st.error(f"Error al cargar pedidos: {e}")

    # --- B. STOCK (CONTROL DETALLADO) ---
    elif menu == "📦 STOCK":
        try:
            df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
            
            with st.expander("➕ AGREGAR NUEVO MATERIAL AL INVENTARIO"):
                with st.form("nuevo_material"):
                    c1, c2 = st.columns(2)
                    v_cat = c1.selectbox("Categoría", ["Telas", "Tazas", "Gorras", "Remeras", "Tintas", "Papel", "Otros"])
                    v_nom = c1.text_input("Nombre del Producto")
                    v_tip = c2.text_input("Tipo de Material")
                    v_tal = c2.text_input("Talle o Medida")
                    v_col = c1.text_input("Color")
                    v_can = c2.number_input("Cantidad Inicial", min_value=0.0)
                    v_uni = c2.text_input("Unidad (Un, Metros, Hojas)")
                    
                    if st.form_submit_button("Registrar en Stock"):
                        nuevo_item = pd.DataFrame([{
                            "Categoría": v_cat, "Nombre": v_nom, "Tipo Material": v_tip,
                            "Talle/Medida": v_tal, "Color": v_col, "Cantidad": v_can, "Unidad": v_uni
                        }])
                        df_updated = pd.concat([df_inv, nuevo_item], ignore_index=True)
                        conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=df_updated)
                        st.success("Inventario actualizado"); time.sleep(1); st.rerun()
            
            st.subheader("📦 Inventario Actual")
            st.dataframe(df_inv, use_container_width=True)
        except Exception as e:
            st.error(f"Error en inventario: {e}")

    # --- C. NUEVO PEDIDO (CON DESCUENTO AUTOMÁTICO) ---
    elif menu == "📝 NUEVO PEDIDO":
        try:
            df_inv = conn.read(spreadsheet=SHEET_ID, worksheet="Inventario", ttl=0)
            df_p = conn.read(spreadsheet=SHEET_ID, worksheet="Pedidos", ttl=0)
            
            with st.form("form_nuevo_pedido"):
                st.subheader("Nueva Orden de Producción")
                c1, c2 = st.columns(2)
                p_cli = c1.text_input("Cliente")
                p_prd = c2.text_input("Producto a realizar")
                p_mon = c1.number_input("Monto a Cobrar $", min_value=0.0)
                p_gas = c2.number_input("Costo de Materiales $ (Gasto)", min_value=0.0)
                
                st.divider()
                st.write("🔧 Descontar Insumo")
                p_mat = st.selectbox("Seleccionar Material del Stock", df_inv['Nombre'].tolist() if not df_inv.empty else ["Sin Stock"])
                p_can = st.number_input("Cantidad a usar", min_value=0.1)
                p_det = st.text_area("Detalles del Diseño (Talle, Color, Fecha entrega)")

                if st.form_submit_button("REGISTRAR PEDIDO Y DESCONTAR STOCK"):
                    if not df_inv.empty and p_mat != "Sin Stock":
                        # 1. Restar del Stock
                        idx = df_inv[df_inv['Nombre'] == p_mat].index[0]
                        df_inv.at[idx, 'Cantidad'] -= p_can
                        conn.update(spreadsheet=SHEET_ID, worksheet="Inventario", data=df_inv)
                        
                        # 2. Crear el Pedido
                        nuevo_p = pd.DataFrame([{
                            "ID": len(df_p) + 1,
                            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Cliente": p_cli,
                            "Producto": p_prd,
                            "Detalle": p_det,
                            "Monto": p_mon,
                            "Estado": "Producción",
                            "Gasto_Prod": p_gas,
                            "Descripcion": ""
                        }])
                        conn.update(spreadsheet=SHEET_ID, worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                        st.success("✅ Pedido creado y Stock actualizado."); time.sleep(1); st.rerun()
                    else:
                        st.error("No se puede descontar stock. Revisa el inventario.")
        except Exception as e:
            st.error(f"Fallo al crear pedido: {e}")

    # --- D. COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Precios Sugeridos")
        with st.container():
            c_costo = st.number_input("Inversión total en materiales $", min_value=0.0)
            c_margen = st.slider("% de Ganancia deseada", 0, 500, 100)
            
            sugerido = c_costo * (1 + c_margen/100)
            
            st.markdown(f"""
            <div style="background: rgba(188, 57, 253, 0.2); padding: 20px; border-radius: 15px; border: 1px solid #bc39fd; text-align: center;">
                <h2 style="color: white; margin: 0;">PRECIO SUGERIDO</h2>
                <h1 style="color: #00d4ff; font-size: 60px; margin: 10px 0;">${sugerido:,.2f}</h1>
                <p style="color: #ccc;">Usa el valor de 'Inversión' como 'Gasto Prod' al cargar el pedido.</p>
            </div>
            """, unsafe_allow_html=True)
