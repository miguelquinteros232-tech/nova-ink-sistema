import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ VISUAL AVANZADA ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide", page_icon="🎨")

# ID de Google Sheets integrado
ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/edit?usp=sharing"

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Orbitron:wght@400;900&display=swap');
        
        /* Fondo con explosión de pintura */
        .stApp {{
            background: #05000a;
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(188, 57, 253, 0.25) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.25) 0%, transparent 50%),
                url("https://www.transparenttextures.com/patterns/carbon-fibre.png");
            color: #f0f0f0;
            font-family: 'Rajdhani', sans-serif;
        }}

        /* Partículas flotantes (Gorra, Taza, Remera) */
        .stApp::before {{
            content: "🧢 👕 ☕ 🎨";
            position: fixed; top: -50px; left: 50%; font-size: 35px; opacity: 0.15;
            animation: drift 22s linear infinite; z-index: -1;
        }}
        @keyframes drift {{
            from {{ transform: translateY(0) rotate(0deg) translateX(-45vw); }}
            to {{ transform: translateY(110vh) rotate(360deg) translateX(45vw); }}
        }}

        .main-logo {{
            font-family: 'Orbitron', sans-serif;
            font-size: 70px; font-weight: 900; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #ff007b, #bc39fd);
            background-size: 300% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 6s linear infinite;
            letter-spacing: 15px; margin-bottom: 30px;
            filter: drop-shadow(0px 0px 20px rgba(188, 57, 253, 0.7));
        }}
        @keyframes shine {{ to {{ background-position: 300% center; }} }}

        .glass-panel {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 6px solid #00d4ff;
            border-radius: 20px; padding: 30px; margin-bottom: 25px;
            backdrop-filter: blur(15px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN BLINDADA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        return conn.read(spreadsheet=URL_HOJA, worksheet=sheet_name, ttl=0)
    except Exception as e:
        st.error(f"⚠️ Error al conectar con '{sheet_name}': {e}")
        return pd.DataFrame()

# --- 3. GESTIÓN DE SEGURIDAD ---
try:
    with open("config_pro.yaml") as f: config = yaml.load(f, Loader=SafeLoader)
except: config = {'credentials': {'usernames': {}}}

auth = stauth.Authenticate(config['credentials'], "nova_p", "nova_k", 30)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Entrar", "👤 Nuevo Usuario"])
    with t1: auth.login(location='main')
    with t2:
        if auth.register_user(location='main'):
            with open('config_pro.yaml', 'w') as f: yaml.dump(config, f)
            st.success("Usuario registrado. Inicia sesión.")
else:
    with st.sidebar:
        st.markdown(f"<h2 style='color:#00d4ff; text-align:center;'>{st.session_state['name']}</h2>", unsafe_allow_html=True)
        menu = st.radio("SISTEMA", ["📦 INVENTARIO", "💰 COTIZADOR PRO", "📝 PEDIDOS", "📊 DASHBOARD"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- SECCIÓN: INVENTARIO (CON COLOR Y TIPO) ---
  if st.form_submit_button("💾 GUARDAR MATERIAL"):
                    try:
                        # Obtenemos datos (si la hoja está vacía, creamos un DF base)
                        df_actual = get_data("Inventario")
                        
                        nueva_f = pd.DataFrame([{
                            "Categoría": cat, "Nombre": nom, "Tipo Material": tip, 
                            "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": "u"
                        }])
                        
                        # Intentamos la actualización
                        if df_actual is None or df_actual.empty:
                            df_final = nueva_f
                        else:
                            df_final = pd.concat([df_actual, nueva_f], ignore_index=True)
                            
                        conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=df_final)
                        st.success("✅ ¡Guardado con éxito!"); time.sleep(1); st.rerun()
                    
                    except Exception as e:
                        # ESTO ES LO MÁS IMPORTANTE:
                        st.error("❌ ERROR TÉCNICO DETECTADO:")
                        st.code(str(e)) # Esto nos dirá si es un problema de permisos (403)
                        st.info("Si el error menciona '403', el correo del JSON no tiene permiso de Editor en el Excel.")

    # --- SECCIÓN: COTIZADOR (CÁLCULO POR GASTO) ---
    elif menu == "💰 COTIZADOR PRO":
        st.subheader("💰 Calculadora de Costos e Insumos")
        inv = get_data("Inventario")
        
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        if not inv.empty:
            opciones = inv['Nombre'] + " (" + inv['Color'] + ")"
            seleccion = st.multiselect("Selecciona los materiales usados:", opciones.tolist())
            
            costo_materiales = 0.0
            for item in seleccion:
                col1, col2 = st.columns([2, 1])
                p_u = col1.number_input(f"Costo unitario de {item} $", min_value=0.0, key=f"p_{item}")
                cant = col2.number_input(f"Cantidad usada", min_value=0.0, step=1.0, key=f"q_{item}")
                costo_materiales += (p_u * cant)
            
            st.divider()
            margen = st.slider("Margen de Ganancia %", 0, 400, 100)
            precio_final = costo_materiales * (1 + margen/100)
            
            st.markdown(f"""
                <div style='text-align:center;'>
                    <h3 style='color:#00d4ff;'>Costo de Producción: ${costo_materiales:,.2f}</h3>
                    <h1 style='color:#bc39fd; font-size:60px;'>VENTA: ${precio_final:,.2f}</h1>
                    <p style='color:#00ff88;'>Ganancia Limpia: ${(precio_final - costo_materiales):,.2f}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Primero carga materiales en el Inventario para cotizar.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- SECCIÓN: PEDIDOS ---
    elif menu == "📝 PEDIDOS":
        st.subheader("📝 Registro de Nuevos Pedidos")
        with st.form("order_form"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Precio Venta $", min_value=0.0)
            est = c2.selectbox("Estado inicial", ["Producción", "Vendido"])
            
            if st.form_submit_button("REGISTRAR PEDIDO"):
                df_p = get_data("Pedidos")
                n_p = pd.DataFrame([{
                    "ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), 
                    "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": est
                }])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, n_p], ignore_index=True))
                st.success("✅ Pedido anotado."); time.sleep(1); st.rerun()

    # --- SECCIÓN: DASHBOARD ---
    elif menu == "📊 DASHBOARD":
        df_p = get_data("Pedidos")
        if not df_p.empty:
            st.subheader("📈 Resumen de Ventas")
            st.metric("Total Facturado", f"${df_p['Monto'].sum():,.2f}")
            st.dataframe(df_p.sort_values(by="ID", ascending=False), use_container_width=True)
        else:
            st.info("No hay pedidos para mostrar.")
