import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO VISUAL "PAINT EXPLOSION" ---
st.set_page_config(page_title="NOVA INK - FULL SYSTEM", layout="wide", page_icon="🎨")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        
        .stApp {
            background: #05000a;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(188, 57, 253, 0.18) 0%, transparent 45%),
                radial-gradient(circle at 90% 80%, rgba(0, 212, 255, 0.18) 0%, transparent 45%),
                url("https://www.transparenttextures.com/patterns/carbon-fibre.png");
            color: #e0e0e0;
            font-family: 'Rajdhani', sans-serif;
        }

        /* Animación de objetos flotantes */
        .stApp::before {
            content: "🧢 👕 ☕ 🎨";
            position: fixed; top: -50px; left: 50%; font-size: 28px; opacity: 0.15;
            animation: drift 25s linear infinite; z-index: -1;
        }
        @keyframes drift {
            from { transform: translateY(0) rotate(0deg) translateX(-40vw); }
            to { transform: translateY(110vh) rotate(360deg) translateX(40vw); }
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
            border-left: 5px solid #bc39fd; border-radius: 15px; padding: 25px; margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN A DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet, cols):
    try:
        data = conn.read(worksheet=sheet, ttl=0)
        return data if not data.empty else pd.DataFrame(columns=cols)
    except: return pd.DataFrame(columns=cols)

# --- 3. GESTIÓN DE USUARIOS (REGISTRO Y LOGIN) ---
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    # Configuración inicial si el archivo no existe
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key', 'name': 'nova_cookie'}}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Pantalla de Login
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    
    tab_login, tab_reg = st.tabs(["🔐 Iniciar Sesión", "👤 Registrarse"])
    
    with tab_login:
        authenticator.login(location='main')
        if st.session_state["authentication_status"] is False:
            st.error("Usuario/Contraseña incorrectos")
        elif st.session_state["authentication_status"] is None:
            st.warning("Por favor, introduce tus credenciales")

    with tab_reg:
        try:
            if authenticator.register_user(location='main'):
                with open('config_pro.yaml', 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('¡Usuario registrado con éxito! Ya puedes iniciar sesión.')
        except Exception as e:
            st.error(f"Error al registrar: {e}")

else:
    # --- SISTEMA INTERNO (DASHBOARD, VENTAS, ETC) ---
    with st.sidebar:
        st.markdown(f"<h3 style='color:#00d4ff;'>Hola, {st.session_state['name']}</h3>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 INVENTARIO", "💰 COTIZADOR PRO"], label_visibility="collapsed")
        st.divider()
        # Opción para cambiar contraseña dentro de la sesión
        with st.expander("Seguridad"):
            try:
                if authenticator.reset_password(st.session_state['username'], 'Cambiar contraseña'):
                    with open('config_pro.yaml', 'w') as f:
                        yaml.dump(config, f, default_flow_style=False)
                    st.success('Contraseña actualizada')
            except Exception as e:
                st.error(e)
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD & EDICIÓN ---
    if menu == "📊 DASHBOARD":
        df = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 ANALÍTICA MENSUAL")
            m_sel = st.selectbox("Período Actual", df['Mes_Año'].unique(), index=len(df['Mes_Año'].unique())-1)
            df_m = df[df['Mes_Año'] == m_sel]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Mes", f"${df_m['Monto'].sum():,.2f}")
            c2.metric("Total Pedidos", len(df_m))
            c3.metric("Deuda Pendiente", f"${df_m[df_m['Pago'] != 'Total']['Monto'].sum():,.2f}")

            st.divider()
            st.subheader("🛠️ Gestión de Pedidos")
            for idx, row in df_m.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Cliente']} ({row['Estado']})"):
                    with st.form(f"edit_form_{idx}"):
                        cc1, cc2 = st.columns(2)
                        up_cli = cc1.text_input("Cliente", row['Cliente'])
                        up_mon = cc2.number_input("Monto", value=float(row['Monto']))
                        up_est = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0)
                        if st.form_submit_button("ACTUALIZAR DATOS"):
                            df.at[idx, 'Cliente'] = up_cli
                            df.at[idx, 'Monto'] = up_mon
                            df.at[idx, 'Estado'] = up_est
                            conn.update(worksheet="Pedidos", data=df)
                            st.success("Guardado"); time.sleep(0.5); st.rerun()

    # --- 💰 COTIZADOR INTELIGENTE (CALCULO POR INSUMOS) ---
    elif menu == "💰 COTIZADOR PRO":
        st.subheader("💰 Calculadora de Costos e Insumos")
        inv = get_data("Inventario", ['Nombre', 'Talle/Medida', 'Color'])
        
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        col_list, col_calc = st.columns([1, 1])
        
        # Selección de materiales
        lista_opciones = inv['Nombre'] + " | " + inv['Talle/Medida']
        seleccionados = col_list.multiselect("Insumos/Materiales usados:", lista_opciones.tolist())
        
        costo_total_insumos = 0.0
        for item in seleccionados:
            with col_calc:
                c_u = st.number_input(f"Costo de {item} $", min_value=0.0, key=f"cost_{item}")
                cant = st.number_input(f"Cantidad de {item}", min_value=0.0, step=1.0, key=f"cant_{item}")
                costo_total_insumos += (c_u * cant)
        
        st.divider()
        extra = st.number_input("Costos adicionales (Luz, Diseño, Envío) $", min_value=0.0)
        margen = st.slider("Margen de Ganancia %", 0, 500, 100)
        
        costo_final = costo_total_insumos + extra
        precio_venta = costo_final * (1 + margen/100)
        
        st.markdown(f"""
            <div style='text-align:center;'>
                <p style='font-size:20px; color:#00d4ff;'>Costo de Producción: ${costo_final:,.2f}</p>
                <h1 style='font-size:50px; color:#bc39fd;'>PRECIO FINAL: ${precio_venta:,.2f}</h1>
                <p style='color:#00ff88;'>Ganancia Limpia: ${(precio_venta - costo_final):,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 📦 INVENTARIO ---
    elif menu == "📦 INVENTARIO":
        inv = get_data("Inventario", ['Categoría', 'Nombre', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad', 'Minimo'])
        st.subheader("📦 Control de Stock")
        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Cargar Material"):
            with st.form("add_stock"):
                c1, c2 = st.columns(2)
                t_cat = c1.selectbox("Categoría", ["Insumo", "Material"])
                t_nom = c1.text_input("Nombre")
                t_tal = c2.text_input("Talle/Medida")
                t_can = c2.number_input("Cantidad Inicial", min_value=0.0)
                if st.form_submit_button("REGISTRAR EN STOCK"):
                    n_row = pd.DataFrame([{"Categoría": t_cat, "Nombre": t_nom, "Talle/Medida": t_tal, "Color": "-", "Cantidad": t_can, "Unidad": "u", "Minimo": 1.0}])
                    conn.update(worksheet="Inventario", data=pd.concat([inv, n_row], ignore_index=True))
                    st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = get_data("Inventario", ['Nombre', 'Talle/Medida', 'Cantidad'])
        with st.form("new_order"):
            st.subheader("📝 Registro de Orden")
            c1, c2 = st.columns(2)
            c_cli, c_prd = c1.text_input("Cliente"), c1.text_input("Producto")
            c_mon, c_pag = c2.number_input("Precio $", min_value=0.0), c2.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            
            lista_inv = inv['Nombre'] + " | " + inv['Talle/Medida']
            c_ins = st.selectbox("Descontar Stock", ["Ninguno"] + lista_inv.tolist())
            c_can = st.number_input("Cantidad", min_value=0.0)
            
            if st.form_submit_button("CREAR ORDEN"):
                df_p = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
                nueva = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": c_cli, "Producto": c_prd, "Detalle": f"Stock: {c_can} de {c_ins}", "Monto": c_mon, "Pago": c_pag, "Estado": "Producción"}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_p, nueva], ignore_index=True))
                
                if c_ins != "Ninguno":
                    idx = lista_inv[lista_inv == c_ins].index[0]
                    inv.at[idx, 'Cantidad'] -= c_can
                    conn.update(worksheet="Inventario", data=inv)
                st.success("Pedido Creado"); time.sleep(1); st.rerun()
