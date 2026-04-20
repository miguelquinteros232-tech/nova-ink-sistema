import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="NOVA INK OS", layout="wide", page_icon="🎨")

# 1. PEGA AQUÍ SOLO EL ID DE TU EXCEL (lo que está entre /d/ y /edit/)
ID_DOCUMENTO = "11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8" 
URL_HOJA = f"https://docs.google.com/spreadsheets/d/11n1oFM8CNn9N_HfI0wOyMzZ7G17Og9d8w27FXUyjOF8/edit?usp=sharing"

st.markdown('''
    <style>
        .stApp { background: #05000a; color: #e0e0e0; font-family: sans-serif; }
        .main-logo { font-size: 50px; font-weight: bold; text-align: center; color: #bc39fd; letter-spacing: 5px; }
        .glass-panel { background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 20px; border-left: 5px solid #00d4ff; }
    </style>
''', unsafe_allow_html=True)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    try:
        # Intento de lectura forzado con URL
        df = conn.read(spreadsheet=URL_HOJA, worksheet=sheet_name, ttl=0)
        return df
    except Exception as e:
        st.error(f"⚠️ Error en pestaña '{sheet_name}': {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
try:
    with open("config_pro.yaml") as f: config = yaml.load(f, Loader=SafeLoader)
except: config = {'credentials': {'usernames': {}}}

auth = stauth.Authenticate(config['credentials'], "nova_c", "nova_k", 30)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    auth.login(location='main')
else:
    with st.sidebar:
        st.write(f"Usuario: {st.session_state['name']}")
        menu = st.radio("MENÚ", ["📦 STOCK", "📊 DASHBOARD", "💰 COTIZADOR", "📝 NUEVO PEDIDO"])
        auth.logout('Salir', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- SECCIÓN STOCK (CORREGIDA) ---
    if menu == "📦 STOCK":
        st.header("📦 Control de Inventario")
        
        # Primero mostramos el formulario para que SIEMPRE puedas registrar aunque la tabla falle
        with st.expander("➕ REGISTRAR NUEVO MATERIAL (Click aquí para abrir)", expanded=True):
            with st.form("registro_stock"):
                c1, c2, c3 = st.columns(3)
                f_cat = c1.selectbox("Categoría", ["Insumo", "Material Base"])
                f_nom = c1.text_input("Nombre del Producto")
                f_tip = c2.text_input("Tipo de Material (ej: Algodón)")
                f_col = c2.text_input("Color")
                f_tal = c3.text_input("Talle/Medida")
                f_can = c3.number_input("Cantidad inicial", min_value=0.0)
                
                if st.form_submit_button("💾 GUARDAR EN GOOGLE SHEETS"):
                    # Intentamos obtener los datos actuales para anexar
                    df_actual = get_data("Inventario")
                    nueva_fila = pd.DataFrame([{
                        "Categoría": f_cat, "Nombre": f_nom, "Tipo Material": f_tip, 
                        "Talle/Medida": f_tal, "Color": f_col, "Cantidad": f_can, "Unidad": "u"
                    }])
                    
                    try:
                        final_df = pd.concat([df_actual, nueva_fila], ignore_index=True)
                        conn.update(spreadsheet=URL_HOJA, worksheet="Inventario", data=final_df)
                        st.success("✅ ¡Registrado con éxito! Recargando...")
                        time.sleep(1)
                        st.rerun()
                    except Exception as ex:
                        st.error(f"No se pudo guardar: {ex}")

        st.divider()
        
        # Luego intentamos mostrar la tabla
        st.subheader("📋 Inventario Actual")
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
        else:
            st.info("La tabla está vacía o no se puede leer. Registra tu primer material arriba.")

    # --- SECCIÓN DASHBOARD ---
    elif menu == "📊 DASHBOARD":
        df_ped = get_data("Pedidos")
        if not df_ped.empty:
            st.dataframe(df_ped)
        else:
            st.warning("No hay pedidos registrados.")

    # --- SECCIÓN COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora de Precios")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        costo = st.number_input("Costo de materiales $", min_value=0.0)
        margen = st.slider("Margen de Ganancia %", 0, 400, 100)
        st.write(f"### Precio Sugerido: ${costo * (1 + margen/100):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- SECCIÓN PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.subheader("📝 Registrar Nueva Venta")
        with st.form("p"):
            cli = st.text_input("Cliente")
            prd = st.text_input("Producto")
            mon = st.number_input("Monto $")
            if st.form_submit_button("Registrar Pedido"):
                df_p = get_data("Pedidos")
                n_p = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Monto": mon, "Estado": "Producción"}])
                conn.update(spreadsheet=URL_HOJA, worksheet="Pedidos", data=pd.concat([df_p, n_p], ignore_index=True))
                st.success("Pedido anotado.")
