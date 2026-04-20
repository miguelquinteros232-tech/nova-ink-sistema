import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="NOVA INK - SISTEMA INTEGRAL", layout="wide", page_icon="🎨")

# Estilos Neón Nova OS (Mantenemos tu estética premium)
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        .stApp {
            background: #020005 !important;
            background-image: radial-gradient(circle at 20% 30%, rgba(188, 57, 253, 0.15) 0%, transparent 50%),
                              radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.15) 0%, transparent 50%) !important;
            font-family: 'Rajdhani', sans-serif;
        }
        .main-logo {
            font-size: 60px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            background-size: 200% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 4s linear infinite;
            letter-spacing: 10px; margin-bottom: 20px;
        }
        @keyframes shine { to { background-position: 200% center; } }
        .glass-panel {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-left: 5px solid #bc39fd !important;
            border-radius: 15px; padding: 25px; margin-bottom: 20px;
        }
        .stMetric { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(0,212,255,0.2); }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Pedidos", ttl=0)
        return data if not data.empty else pd.DataFrame(columns=['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
    except:
        return pd.DataFrame(columns=['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_key', 'name': 'nova_cookie'}}

authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_l, tab_r = st.tabs(["🔑 LOGIN", "✨ NUEVO SOCIO"])
        with tab_l: authenticator.login(location='main')
        with tab_r:
            with st.form("reg"):
                u, p, cp = st.text_input("Usuario"), st.text_input("Password", type="password"), st.text_input("Confirmar", type="password")
                if st.form_submit_button("REGISTRAR"):
                    if p == cp and u:
                        config['credentials']['usernames'][u] = {'name': u, 'password': stauth.Hasher.hash(p)}
                        with open("config_pro.yaml", 'w') as f: yaml.dump(config, f)
                        st.success("Socio creado.")
else:
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NAV OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "💰 COTIZADOR PRO"], label_visibility="collapsed")
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD INTERACTIVO & HISTORIAL ---
    if menu == "📊 DASHBOARD":
        df = get_data()
        if df.empty:
            st.info("Sin datos. Registra un pedido para comenzar.")
        else:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Fecha'])
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 ANALÍTICA Y BALANCES")
            meses = df['Mes_Año'].unique()
            mes_sel = st.selectbox("Seleccionar Período", meses, index=len(meses)-1)
            df_mes = df[df['Mes_Año'] == mes_sel]

            # Métricas Pro
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Ventas {mes_sel}", f"${df_mes['Monto'].sum():,.2f}")
            m2.metric("Productos/Pedidos", len(df_mes))
            pend = df_mes[df_mes['Pago'] != 'Total']['Monto'].sum()
            m3.metric("Saldo por Cobrar", f"${pend:,.2f}", delta=f"-${pend:,.2f}", delta_color="inverse")

            # Gráfico de Rendimiento
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            st.write(f"Rendimiento Diario: {mes_sel}")
            v_diarias = df_mes.groupby(df_mes['Fecha'].dt.day)['Monto'].sum()
            st.line_chart(v_diarias)
            st.markdown('</div>', unsafe_allow_html=True)

            # Historial de Balances
            st.subheader("📁 Historial de Cierres Mensuales")
            hist = df.groupby('Mes_Año').agg({'Monto': 'sum', 'ID': 'count'}).rename(columns={'Monto': 'Total $', 'ID': 'Ventas'})
            st.table(hist)

            # Gestión Interactiva de Pedidos
            st.divider()
            st.subheader(f"📝 Gestión de Pedidos - {mes_sel}")
            for index, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                # Color dinámico
                b_col = "#00d4ff" if row['Pago'] == "Total" else "#bc39fd"
                st.markdown(f'<div style="border-left: 5px solid {b_col}; padding:10px; margin-bottom:5px; background:rgba(255,255,255,0.02);"><b>#{row["ID"]} {row["Cliente"]}</b> - {row["Producto"]} (${row["Monto"]})</div>', unsafe_allow_html=True)
                
                c_a, c_b, c_c = st.columns([2,2,1])
                with c_a: 
                    nP = st.selectbox("Pago", ["Pendiente", "Seña", "Total"], index=["Pendiente", "Seña", "Total"].index(row['Pago']), key=f"p{row['ID']}")
                with c_b: 
                    nE = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0, key=f"e{row['ID']}")
                with c_c:
                    if st.button("ACTUALIZAR", key=f"b{row['ID']}"):
                        full_df = get_data()
                        full_df.at[index, 'Pago'] = nP
                        full_df.at[index, 'Estado'] = nE
                        conn.update(worksheet="Pedidos", data=full_df)
                        st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("f_new"):
            st.subheader("✍️ Registro de Trabajo")
            col_1, col_2 = st.columns(2)
            with col_1:
                cli = st.text_input("Cliente")
                prd = st.text_input("Producto/Servicio")
            with col_2:
                mon = st.number_input("Precio $", min_value=0.0)
                pag = st.selectbox("Estado Pago", ["Pendiente", "Seña", "Total"])
            est = st.selectbox("Estado Inicial", ["Producción", "Vendido", "Entregado"])
            det = st.text_area("Detalles del Pedido")
            if st.form_submit_button("INYECTAR A GOOGLE SHEETS"):
                df_o = get_data()
                n_row = pd.DataFrame([{"ID": len(df_o)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": det, "Monto": mon, "Pago": pag, "Estado": est}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_o, n_row], ignore_index=True))
                st.success("Guardado en la nube!")
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR PRO":
        st.markdown("### 💰 CALCULADORA DE COSTOS & MARGEN")
        with st.container():
            c1, c2 = st.columns(2)
            costo = c1.number_input("Costo de Insumo/Prenda $", min_value=0.0)
            margen = c2.slider("Margen Ganancia %", 0, 400, 100)
            precio = costo * (1 + margen/100)
            st.markdown(f'<div class="glass-panel"><h1 style="text-align:center; color:#00ff00;">PRECIO SUGERIDO: ${precio:,.2f}</h1></div>', unsafe_allow_html=True)
