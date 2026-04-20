import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ "PAINT EXPLOSION" ---
st.set_page_config(page_title="NOVA INK - MASTER SYSTEM", layout="wide", page_icon="🎨")

# Reemplaza esta URL con la tuya
URL_HOJA = "https://docs.google.com/spreadsheets/d/11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8/edit?usp=sharing"

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        
        .stApp {
            background: #05000a;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(188, 57, 253, 0.2) 0%, transparent 45%),
                radial-gradient(circle at 90% 80%, rgba(0, 212, 255, 0.2) 0%, transparent 45%),
                url("https://www.transparenttextures.com/patterns/carbon-fibre.png");
            color: #e0e0e0; font-family: 'Rajdhani', sans-serif;
        }

        /* Explosiones de pintura y objetos flotantes */
        .stApp::before {
            content: "🧢 👕 ☕ 🎨";
            position: fixed; top: -50px; left: 50%; font-size: 32px; opacity: 0.12;
            animation: drift 20s linear infinite; z-index: -1;
        }
        @keyframes drift {
            from { transform: translateY(0) rotate(0deg) translateX(-45vw); }
            to { transform: translateY(110vh) rotate(360deg) translateX(45vw); }
        }

        .main-logo {
            font-size: 65px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #ff007b, #bc39fd);
            background-size: 300% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 5s linear infinite;
            letter-spacing: 12px; margin-bottom: 20px;
            filter: drop-shadow(0px 0px 15px rgba(188, 57, 253, 0.6));
        }
        @keyframes shine { to { background-position: 300% center; } }

        .glass-panel {
            background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #00d4ff; border-radius: 15px; padding: 25px; margin-bottom: 20px;
            backdrop-filter: blur(12px);
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN A DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name, cols):
    try:
        # Intenta leer la hoja
        data = conn.read(spreadsheet=URL_HOJA, worksheet=sheet_name, ttl=0)
        
        if data is None or data.empty:
            st.warning(f"La hoja '{sheet_name}' está vacía o no existe.")
            return pd.DataFrame(columns=cols)
            
        # Forzamos a que solo use las columnas que necesitamos para evitar errores
        return data
    except Exception as e:
        st.error(f"⚠️ Error de conexión en '{sheet_name}': {e}")
        return pd.DataFrame(columns=cols)

# --- 3. SEGURIDAD Y USUARIOS ---
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except:
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_ink', 'name': 'nova_c'}}

auth = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    tab_l, tab_r = st.tabs(["🔐 Login", "👤 Registro"])
    with tab_l: auth.login(location='main')
    with tab_r:
        if auth.register_user(location='main'):
            with open('config_pro.yaml', 'w') as f: yaml.dump(config, f)
            st.success("Usuario creado con éxito.")
else:
    with st.sidebar:
        st.markdown(f"### Operador: {st.session_state['name']}")
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 STOCK MAESTRO", "💰 COTIZADOR PRO"], label_visibility="collapsed")
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD & BALANCES ---
    if menu == "📊 DASHBOARD":
        df = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Monto', 'Pago', 'Estado'])
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df['Mes'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 ANALÍTICA")
            mes_sel = st.selectbox("Filtrar Mes", df['Mes'].unique(), index=len(df['Mes'].unique())-1)
            df_m = df[df['Mes'] == mes_sel]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas", f"${df_m['Monto'].sum():,.2f}")
            c2.metric("Pedidos", len(df_m))
            c3.metric("Por Cobrar", f"${df_m[df_m['Pago'] != 'Total']['Monto'].sum():,.2f}")
            
            st.divider()
            st.subheader("📋 Lista de Pedidos")
            st.dataframe(df_m.sort_values(by='ID', ascending=False), use_container_width=True)

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = get_data("Inventario", ['Nombre', 'Color', 'Cantidad', 'Talle/Medida'])
        with st.form("form_pedido"):
            st.subheader("📝 Registro de Venta")
            c1, c2 = st.columns(2)
            cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
            mon, pag = c2.number_input("Precio $", min_value=0.0), c2.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            
            # Selector de Stock
            lista_s = inv['Nombre'] + " | " + inv['Color'] + " (" + inv['Talle/Medida'] + ")"
            mat_d = st.selectbox("Descontar del Inventario", ["Ninguno"] + lista_s.tolist())
            can_d = st.number_input("Cantidad utilizada", min_value=0.0)
            
            if st.form_submit_button("GUARDAR PEDIDO"):
                peds = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Monto', 'Pago', 'Estado'])
                n_p = pd.DataFrame([{"ID": len(peds)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Monto": mon, "Pago": pag, "Estado": "Producción"}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([peds, n_p], ignore_index=True))
                
                if mat_d != "Ninguno":
                    idx = lista_s[lista_s == mat_d].index[0]
                    inv.at[idx, 'Cantidad'] -= can_d
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=inv)
                st.success("¡Pedido creado!"); time.sleep(1); st.rerun()

    # --- 📦 STOCK MAESTRO (COLOR Y MATERIAL) ---
    elif menu == "📦 STOCK":
        cols_i = ['Categoría', 'Nombre', 'Tipo Material', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad']
        inv = get_data("Inventario", cols_i)
        st.subheader("📦 Control de Almacén")
        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Cargar Nuevo Material"):
            with st.form("form_inv"):
                cc1, cc2, cc3 = st.columns(3)
                f_cat = cc1.selectbox("Categoría", ["Insumo", "Material Base"])
                f_nom = cc1.text_input("Nombre (ej. Gorra, Taza)")
                f_tip = cc2.text_input("Tipo de Material (ej. Poliéster, Cerámica)")
                f_col = cc2.text_input("Color")
                f_tal = cc3.text_input("Talle/Medida")
                f_can = cc3.number_input("Cantidad Inicial", min_value=0.0)
                
                if st.form_submit_button("SINCRONIZAR"):
                    nueva_f = pd.DataFrame([{"Categoría": f_cat, "Nombre": f_nom, "Tipo Material": f_tip, "Talle/Medida": f_tal, "Color": f_col, "Cantidad": f_can, "Unidad": "u"}])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=pd.concat([inv, nueva_f], ignore_index=True))
                    st.success("Guardado!"); time.sleep(1); st.rerun()

    # --- 💰 COTIZADOR PRO ---
    elif menu == "💰 COTIZADOR PRO":
        st.subheader("💰 Calculadora de Costos Detallada")
        inv = get_data("Inventario", ['Nombre', 'Tipo Material', 'Color', 'Talle/Medida'])
        
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        opciones = inv['Nombre'] + " [" + inv['Tipo Material'] + "] - " + inv['Color']
        seleccion = st.multiselect("Selecciona materiales para el cálculo:", opciones.tolist())
        
        costo_total = 0.0
        for item in seleccion:
            col1, col2 = st.columns([2, 1])
            c_u = col1.number_input(f"Costo de {item} $", min_value=0.0, key=f"c_{item}")
            cant = col2.number_input(f"Cantidad usada", min_value=0.0, step=1.0, key=f"q_{item}")
            costo_total += (c_u * cant)
        
        st.divider()
        margen = st.slider("Margen de Ganancia %", 0, 500, 100)
        precio_v = costo_total * (1 + margen/100)
        
        st.markdown(f"""
            <div style='text-align:center;'>
                <p style='color:#00d4ff; font-size:20px;'>Costo Base: ${costo_total:,.2f}</p>
                <h1 style='color:#bc39fd; font-size:50px;'>PRECIO FINAL: ${precio_v:,.2f}</h1>
                <p style='color:#00ff88;'>Ganancia: ${(precio_v - costo_total):,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
