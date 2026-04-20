import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ CON FONDO ANIMADO ---
st.set_page_config(page_title="NOVA INK - ULTRA SYSTEM", layout="wide", page_icon="🎨")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        
        /* Fondo Animado Nova */
        .stApp {
            background: linear-gradient(125deg, #05000a, #1a0033, #001a33, #05000a);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
            color: #e0e0e0;
            font-family: 'Rajdhani', sans-serif;
        }
        
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .main-logo {
            font-size: 65px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            background-size: 200% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 4s linear infinite;
            letter-spacing: 12px; margin-bottom: 30px;
            text-shadow: 0px 0px 20px rgba(188, 57, 253, 0.4);
        }
        @keyframes shine { to { background-position: 200% center; } }

        .glass-panel {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #bc39fd;
            border-radius: 15px; padding: 25px; margin-bottom: 20px;
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

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f: config = yaml.load(f, Loader=SafeLoader)
except: config = {'credentials': {'usernames': {}}}

auth = stauth.Authenticate(config['credentials'], "nova_cookie", "nova_key", 30)

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    auth.login(location='main')
else:
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NOVA OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 INVENTARIO", "💰 COTIZADOR"], label_visibility="collapsed")
        st.divider()
        auth.logout('Salir', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD: BALANCES Y EDICIÓN ---
    if menu == "📊 DASHBOARD":
        df = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
        
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            df['Año'] = df['Fecha'].dt.year

            # --- SECCIÓN BALANCES ---
            st.markdown("### 📈 BALANCE HISTÓRICO")
            tab1, tab2 = st.tabs(["📅 Balance Mensual", "🗓️ Historial Anual"])
            
            with tab1:
                m_sel = st.selectbox("Seleccionar Período", df['Mes_Año'].unique(), index=len(df['Mes_Año'].unique())-1)
                df_m = df[df['Mes_Año'] == m_sel]
                c1, c2, c3 = st.columns(3)
                c1.metric("Ventas", f"${df_m['Monto'].sum():,.2f}")
                c2.metric("Pedidos", len(df_m))
                c3.metric("Por Cobrar", f"${df_m[df_m['Pago'] != 'Total']['Monto'].sum():,.2f}")
            
            with tab2:
                balance_h = df.groupby(['Año', 'Mes_Año'])['Monto'].sum().reset_index()
                st.table(balance_h.sort_values(by='Año', ascending=False))

            st.divider()
            st.subheader(f"🛠️ Gestión de Pedidos - {m_sel}")

            for idx, row in df_m.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Cliente']}"):
                    with st.form(f"edit_{idx}"):
                        st.write("**Modificar datos del pedido:**")
                        col1, col2 = st.columns(2)
                        u_cli = col1.text_input("Cliente", value=row['Cliente'])
                        u_prd = col1.text_input("Producto", value=row['Producto'])
                        u_mon = col2.number_input("Monto $", value=float(row['Monto']))
                        u_pag = col2.selectbox("Pago", ["Pendiente", "Seña", "Total"], index=["Pendiente", "Seña", "Total"].index(row['Pago']))
                        u_est = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0)
                        u_det = st.text_area("Detalles", value=row['Detalle'])
                        
                        if st.form_submit_button("GUARDAR CAMBIOS EN NUBE"):
                            full_df = get_data("Pedidos", [])
                            full_df.at[idx, 'Cliente'] = u_cli
                            full_df.at[idx, 'Producto'] = u_prd
                            full_df.at[idx, 'Monto'] = u_mon
                            full_df.at[idx, 'Pago'] = u_pag
                            full_df.at[idx, 'Estado'] = u_est
                            full_df.at[idx, 'Detalle'] = u_det
                            conn.update(worksheet="Pedidos", data=full_df)
                            st.success("¡Pedido actualizado!"); time.sleep(0.5); st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = get_data("Inventario", ['Categoría', 'Nombre', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad', 'Minimo'])
        with st.form("nv_form"):
            st.subheader("📝 Registro de Venta")
            c1, c2 = st.columns(2)
            cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
            mon, pag = c2.number_input("Precio $", min_value=0.0), c2.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            
            st.markdown("---")
            st.write("📦 **Insumo/Material utilizado**")
            lista_inv = inv['Nombre'] + " (" + inv['Talle/Medida'] + " - " + inv['Color'] + ")"
            mat_usado = st.selectbox("Seleccionar Item", ["Ninguno"] + lista_inv.tolist())
            cant_usada = st.number_input("Cantidad", min_value=0.0, step=1.0)
            
            est, det = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"]), st.text_area("Notas")
            
            if st.form_submit_button("REGISTRAR PEDIDO"):
                df_p = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
                nueva = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": f"{det} (Insumo: {cant_usada} {mat_usado})", "Monto": mon, "Pago": pag, "Estado": est}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_p, nueva], ignore_index=True))
                
                if mat_usado != "Ninguno":
                    idx_i = lista_inv[lista_inv == mat_usado].index[0]
                    inv.at[idx_i, 'Cantidad'] -= cant_usada
                    conn.update(worksheet="Inventario", data=inv)
                st.success("Registrado."); time.sleep(1); st.rerun()

    # --- 📦 INVENTARIO ---
    elif menu == "📦 INVENTARIO":
        inv = get_data("Inventario", ['Categoría', 'Nombre', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad', 'Minimo'])
        st.subheader("📦 Control de Stock")
        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Cargar Nuevo Item"):
            with st.form("inv_add"):
                cc1, cc2 = st.columns(2)
                cat = cc1.selectbox("Categoría", ["Insumos", "Materiales (Gorras/Remeras)", "Otros"])
                nom, tal = cc1.text_input("Nombre"), cc2.text_input("Talle/Medida")
                col, can = cc2.text_input("Color"), st.number_input("Cantidad", min_value=0.0)
                if st.form_submit_button("GUARDAR EN INVENTARIO"):
                    nuevo_item = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": "Unid.", "Minimo": 1.0}])
                    conn.update(worksheet="Inventario", data=pd.concat([inv, nuevo_item], ignore_index=True))
                    st.rerun()

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("💰 Calculadora de Precios")
        costo = st.number_input("Costo base $", min_value=0.0)
        margen = st.slider("Margen %", 0, 400, 100)
        st.header(f"Sugerido: ${costo * (1 + margen/100):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
