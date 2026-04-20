import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ "ULTRA NEON" ---
st.set_page_config(page_title="NOVA INK - PREMIUM MANAGEMENT", layout="wide", page_icon="🎨")

ID_SHEET = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8"
URL_HOJA = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/edit?usp=sharing"

st.markdown(f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Orbitron:wght@400;900&display=swap');
        
        .stApp {{
            background: #05000a;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(188, 57, 253, 0.2) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 212, 255, 0.2) 0%, transparent 40%);
            color: #f0f0f0; font-family: 'Rajdhani', sans-serif;
        }}

        .main-logo {{
            font-family: 'Orbitron', sans-serif; font-size: 65px; font-weight: 900; 
            text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 12px; margin-bottom: 20px; filter: drop-shadow(0 0 10px #bc39fd);
        }}

        .glass-panel {{
            background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #00d4ff; border-radius: 15px; padding: 25px; 
            backdrop-filter: blur(10px); margin-bottom: 20px;
        }}

        .metric-card {{
            background: rgba(0, 212, 255, 0.1); border: 1px solid #00d4ff;
            border-radius: 10px; padding: 15px; text-align: center;
        }}
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        df = conn.read(spreadsheet=URL_HOJA, worksheet=sheet_name, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f: config = yaml.load(f, Loader=SafeLoader)
except: config = {'credentials': {'usernames': {}}}

auth = stauth.Authenticate(config['credentials'], "nova_p", "nova_k", 30)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    auth.login(location='main')
else:
    with st.sidebar:
        st.markdown(f"## 👤 {st.session_state['name']}")
        menu = st.radio("SISTEMA", ["📊 DASHBOARD", "📦 STOCK & MATERIALES", "💰 COTIZADOR PRO", "📝 NUEVO PEDIDO"])
        st.divider()
        auth.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD: BALANCES MENSUALES Y ANUALES ---
    if menu == "📊 DASHBOARD":
        df_p = get_data("Pedidos")
        if not df_p.empty:
            df_p['Fecha'] = pd.to_datetime(df_p['Fecha'], dayfirst=True, errors='coerce')
            df_p['Mes'] = df_p['Fecha'].dt.strftime('%m-%Y')
            df_p['Año'] = df_p['Fecha'].dt.year
            
            st.subheader("📈 Resumen Financiero")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Total Histórico", f"${df_p['Monto'].sum():,.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Filtros de Historial
            st.divider()
            f_col1, f_col2 = st.columns(2)
            sel_año = f_col1.selectbox("Ver Año", sorted(df_p['Año'].dropna().unique(), reverse=True))
            df_año = df_p[df_p['Año'] == sel_año]
            
            sel_mes = f_col2.selectbox("Ver Mes", sorted(df_año['Mes'].dropna().unique(), reverse=True))
            df_mes = df_año[df_año['Mes'] == sel_mes]
            
            st.write(f"### Detalle de {sel_mes}")
            st.dataframe(df_mes[['ID', 'Fecha', 'Cliente', 'Producto', 'Monto', 'Estado']], use_container_width=True)
            st.success(f"Recaudación del mes: ${df_mes['Monto'].sum():,.2f}")
        else:
            st.info("No hay datos de ventas registrados aún.")

    # --- 📦 STOCK & MATERIALES (TIPO Y COLOR) ---
    elif menu == "📦 STOCK & MATERIALES":
        st.subheader("📦 Almacén de Insumos")
        
        # Tabla de visualización constante
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
        else:
            st.warning("El inventario está vacío.")

        st.divider()
        with st.expander("➕ Cargar Nuevo Material o Insumo", expanded=False):
            with st.form("form_stock"):
                c1, c2, c3 = st.columns(3)
                f_cat = c1.selectbox("Categoría", ["Material Base", "Insumo"])
                f_nom = c1.text_input("Nombre (ej. Gorra Trucker)")
                f_tip = c2.text_input("Tipo de Material (ej. Poliéster)")
                f_col = c2.text_input("Color / Diseño")
                f_tal = c3.text_input("Talle / Medida")
                f_can = c3.number_input("Cantidad", min_value=0.0)
                
                if st.form_submit_button("GUARDAR EN DRIVE"):
                    try:
                        nueva_fila = pd.DataFrame([{
                            "Categoría": f_cat, "Nombre": f_nom, "Tipo Material": f_tip, 
                            "Talle/Medida": f_tal, "Color": f_col, "Cantidad": f_can, "Unidad": "u"
                        }])
                        df_final = pd.concat([df_inv, nueva_fila], ignore_index=True)
                        conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=df_final)
                        st.success("✅ Stock actualizado."); time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

    # --- 💰 COTIZADOR PRO (CON DESCUENTO DE STOCK SIMULADO) ---
    elif menu == "💰 COTIZADOR PRO":
        st.subheader("💰 Calculadora de Costos Reales")
        inv = get_data("Inventario")
        
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        if not inv.empty:
            # Opción de elegir materiales existentes
            lista_mat = inv['Nombre'] + " [" + inv['Color'] + "]"
            seleccionados = st.multiselect("Materiales a utilizar:", lista_mat.tolist())
            
            costo_acumulado = 0.0
            for item in seleccionados:
                col1, col2 = st.columns([2, 1])
                pu = col1.number_input(f"Costo unitario de {item} $", min_value=0.0, key=f"p_{item}")
                cant = col2.number_input(f"Cantidad a usar", min_value=0.0, key=f"q_{item}")
                costo_acumulado += (pu * cant)
            
            st.divider()
            margen = st.slider("Margen de Ganancia %", 0, 500, 100)
            p_final = costo_acumulado * (1 + margen/100)
            
            st.markdown(f"""
                <div style='text-align:center;'>
                    <h2 style='color:#00d4ff;'>Costo Total: ${costo_acumulado:,.2f}</h2>
                    <h1 style='color:#bc39fd; font-size:55px;'>PRECIO SUGERIDO: ${p_final:,.2f}</h1>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Carga materiales en el inventario para usar el cotizador dinámico.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 📝 NUEVO PEDIDO (REGISTRO Y DESCUENTO) ---
    elif menu == "📝 NUEVO PEDIDO":
        st.subheader("📝 Registrar Nueva Venta")
        inv = get_data("Inventario")
        
        with st.form("form_pedidos"):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Nombre del Cliente")
            f_prd = c1.text_input("Producto Final")
            f_mon = c2.number_input("Precio Final Cobrado $", min_value=0.0)
            f_est = c2.selectbox("Estado del Pedido", ["Producción", "Listo", "Entregado"])
            
            st.write("---")
            st.write("🔻 Descontar del Inventario (Opcional)")
            lista_inv = ["Ninguno"] + (inv['Nombre'] + " (" + inv['Color'] + ")").tolist() if not inv.empty else ["Ninguno"]
            mat_desc = st.selectbox("Material usado", lista_inv)
            cant_desc = st.number_input("Cantidad utilizada", min_value=0.0)
            
            if st.form_submit_button("REGISTRAR PEDIDO Y ACTUALIZAR STOCK"):
                try:
                    # 1. Guardar Pedido
                    df_p = get_data("Pedidos")
                    nuevo_p = pd.DataFrame([{
                        "ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), 
                        "Cliente": f_cli, "Producto": f_prd, "Monto": f_mon, "Estado": f_est
                    }])
                    conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                    
                    # 2. Descontar Stock si aplica
                    if mat_desc != "Ninguno" and not inv.empty:
                        idx = (inv['Nombre'] + " (" + inv['Color'] + ")").tolist().index(mat_desc)
                        inv.at[idx, 'Cantidad'] -= cant_desc
                        conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=inv)
                    
                    st.success("✅ Pedido registrado y stock actualizado.")
                    time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
