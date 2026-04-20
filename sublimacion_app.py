import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO VISUAL "PAINT EXPLOSION" ---
st.set_page_config(page_title="NOVA INK - ULTRA MASTER", layout="wide", page_icon="🎨")

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

        /* Animación de Objetos Nova */
        .stApp::before {
            content: "🧢 👕 ☕ 🎨";
            position: fixed; top: -50px; left: 50%; font-size: 32px; opacity: 0.1;
            animation: drift 20s linear infinite; z-index: -1;
        }
        @keyframes drift {
            from { transform: translateY(0) rotate(0deg) translateX(-45vw); }
            to { transform: translateY(110vh) rotate(360deg) translateX(45vw); }
        }

        .main-logo {
            font-size: 60px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #ff007b, #bc39fd);
            background-size: 300% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 5s linear infinite;
            letter-spacing: 10px; margin-bottom: 20px;
        }
        @keyframes shine { to { background-position: 300% center; } }

        .glass-panel {
            background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #00d4ff; border-radius: 15px; padding: 25px; margin-bottom: 20px;
            backdrop-filter: blur(12px);
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN (IMPORTANTE: USA SERVICE ACCOUNT) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet, cols):
    try:
        # Al usar Service Account, no pasamos URL, el sistema la toma de los Secrets
        data = conn.read(worksheet=sheet, ttl=0)
        return data if data is not None and not data.empty else pd.DataFrame(columns=cols)
    except:
        return pd.DataFrame(columns=cols)

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except:
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova', 'name': 'nova_c'}}

auth = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Login", "👤 Registro"])
    with t1: auth.login(location='main')
    with t2:
        if auth.register_user(location='main'):
            with open('config_pro.yaml', 'w') as f: yaml.dump(config, f)
            st.success("Registrado correctamente.")
else:
    with st.sidebar:
        st.markdown(f"### Bienvenido, {st.session_state['name']}")
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 STOCK DETALLADO", "💰 COTIZADOR PRO"], label_visibility="collapsed")
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 💰 COTIZADOR PRO (CON CÁLCULO DE MATERIALES) ---
    if menu == "💰 COTIZADOR PRO":
        st.subheader("💰 Calculadora de Costos Reales")
        inv = get_data("Inventario", ['Nombre', 'Tipo Material', 'Color', 'Talle/Medida'])
        
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        opciones = inv['Nombre'] + " [" + inv['Tipo Material'] + "] - " + inv['Color']
        seleccionados = st.multiselect("Materiales Usados", opciones.tolist())
        
        costo_acumulado = 0.0
        for item in seleccionados:
            c1, c2 = st.columns([2, 1])
            val = c1.number_input(f"Costo de {item} $", min_value=0.0, key=f"v_{item}")
            cant = c2.number_input(f"Cantidad", min_value=0.0, step=1.0, key=f"q_{item}")
            costo_acumulado += (val * cant)
        
        st.divider()
        margen = st.slider("Ganancia %", 0, 500, 100)
        final = costo_acumulado * (1 + margen/100)
        
        st.markdown(f"<h1 style='color:#bc39fd; text-align:center;'>PRECIO: ${final:,.2f}</h1>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 📦 STOCK DETALLADO ---
    elif menu == "📦 STOCK DETALLADO":
        cols = ['Categoría', 'Nombre', 'Tipo Material', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad']
        inv = get_data("Inventario", cols)
        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Registrar Nuevo"):
            with st.form("add_mat"):
                c1, c2, c3 = st.columns(3)
                f_cat = c1.selectbox("Categoría", ["Insumo", "Material Base"])
                f_nom = c1.text_input("Nombre")
                f_tip = c2.text_input("Tipo (Algodón, Vinilo, etc)")
                f_col = c2.text_input("Color")
                f_tal = c3.text_input("Talle/Medida")
                f_can = c3.number_input("Cantidad", min_value=0.0)
                
                if st.form_submit_button("REGISTRAR"):
                    nueva = pd.DataFrame([{"Categoría": f_cat, "Nombre": f_nom, "Tipo Material": f_tip, "Talle/Medida": f_tal, "Color": f_col, "Cantidad": f_can, "Unidad": "u"}])
                    # Fix: Actualizamos la tabla completa
                    conn.update(worksheet="Inventario", data=pd.concat([inv, nueva], ignore_index=True))
                    st.success("Guardado!"); time.sleep(1); st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = get_data("Inventario", ['Nombre', 'Color', 'Cantidad'])
        with st.form("p_f"):
            st.subheader("📝 Nueva Venta")
            c1, c2 = st.columns(2)
            cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
            mon, pag = c2.number_input("Monto $", min_value=0.0), c2.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            
            lista = inv['Nombre'] + " (" + inv['Color'] + ")"
            mat = st.selectbox("Descontar Stock", ["Ninguno"] + lista.tolist())
            can = st.number_input("Cantidad", min_value=0.0)
            
            if st.form_submit_button("CREAR ORDEN"):
                pedidos = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Monto', 'Pago', 'Estado'])
                n_p = pd.DataFrame([{"ID": len(pedidos)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Monto": mon, "Pago": pag, "Estado": "Producción"}])
                conn.update(worksheet="Pedidos", data=pd.concat([pedidos, n_p], ignore_index=True))
                
                if mat != "Ninguno":
                    idx = lista[lista == mat].index[0]
                    inv.at[idx, 'Cantidad'] -= can
                    conn.update(worksheet="Inventario", data=inv)
                st.rerun()

    # --- 📊 DASHBOARD ---
    elif menu == "📊 DASHBOARD":
        df = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Monto', 'Pago', 'Estado'])
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            # Aquí iría el historial por mes/año que ya teníamos
