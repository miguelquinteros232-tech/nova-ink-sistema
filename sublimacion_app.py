import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
import yaml
import os
import time
from yaml.loader import SafeLoader
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ MAESTRA ---
st.set_page_config(page_title="NOVA INK - PROFESIONAL", layout="wide", page_icon="🎨")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');

        /* FONDO DINÁMICO DE TINTA */
        .stApp {
            background: #020005 !important;
            background-image: 
                radial-gradient(circle at 20% 30%, rgba(188, 57, 253, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.15) 0%, transparent 50%) !important;
            font-family: 'Rajdhani', sans-serif;
        }

        /* LOGO ANIMADO */
        .main-logo {
            font-size: 60px;
            font-weight: 700;
            text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shine 4s linear infinite;
            letter-spacing: 10px;
            margin-bottom: 20px;
        }
        @keyframes shine { to { background-position: 200% center; } }

        /* CONTENEDORES GLASSMORPHISM */
        .glass-panel {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-left: 5px solid #bc39fd !important;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            transition: 0.3s ease;
        }
        .glass-panel:hover {
            border-left: 5px solid #00d4ff !important;
            transform: translateX(5px);
            background: rgba(255, 255, 255, 0.05) !important;
        }

        /* NAVEGACIÓN LATERAL */
        [data-testid="stSidebar"] {
            background-color: #05000a !important;
            border-right: 1px solid #bc39fd !important;
        }

        /* ANIMACIÓN DE SALPICADURA AL GUARDAR */
        .splash {
            position: fixed;
            top: 50%; left: 50%;
            width: 10px; height: 10px;
            background: #00d4ff;
            border-radius: 50%;
            z-index: 9999;
            animation: splash-anim 1s forwards;
        }
        @keyframes splash-anim {
            0% { transform: scale(0); opacity: 1; }
            100% { transform: scale(300); opacity: 0; filter: blur(30px); }
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. GESTIÓN DE BASES DE DATOS (TODAS LAS FUNCIONES) ---
def init_all_db():
    files = {
        'pedidos_pro.csv': ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'],
        'stock_pro.csv': ['Nombre', 'Material', 'Talle', 'Color', 'Precio_Costo', 'Cantidad'],
        'insumos_pro.csv': ['Insumo', 'Precio_Costo', 'Unidad']
    }
    for f, cols in files.items():
        if not os.path.exists(f): 
            df = pd.DataFrame(columns=cols)
            # Datos iniciales para que no esté vacío
            if f == 'stock_pro.csv':
                df = pd.DataFrame([['Remera Blanca', 'Algodón', 'L', 'Blanco', 2500, 10]], columns=cols)
            elif f == 'insumos_pro.csv':
                df = pd.DataFrame([['Papel A3', 50, 'Hoja']], columns=cols)
            df.to_csv(f, index=False)

init_all_db()

def play_splash():
    p = st.empty()
    p.markdown('<div class="splash"></div>', unsafe_allow_html=True)
    time.sleep(0.6)
    p.empty()

# --- 3. SEGURIDAD ---
CONFIG = "config_pro.yaml"
if not os.path.exists(CONFIG):
    c = {'credentials':{'usernames':{}}, 'cookie':{'expiry_days':30,'key':'npro','name':'npro'}}
    with open(CONFIG,'w') as f: yaml.dump(c, f)
else:
    with open(CONFIG) as f: c = yaml.load(f, Loader=SafeLoader)

auth = stauth.Authenticate(c['credentials'], c['cookie']['name'], c['cookie']['key'], c['cookie']['expiry_days'])

# --- 4. INTERFAZ ---
if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    _, col, _ = st.columns([0.2, 0.6, 0.2])
    with col:
        auth.login(location='main')
        with st.expander("✨ Registro de Nuevo Socio"):
            with st.form("reg"):
                u, p = st.text_input("Usuario"), st.text_input("Clave", type="password")
                if st.form_submit_button("REGISTRAR"):
                    c['credentials']['usernames'][u] = {'name':u, 'password':stauth.Hasher.hash(p)}
                    with open(CONFIG,'w') as f: yaml.dump(c,f)
                    st.success("Socio añadido.")
else:
    # NAVEGACIÓN TOTAL
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NAV OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "💰 COTIZADOR MULTI", "📦 STOCK / INSUMOS"], label_visibility="collapsed")
        st.divider()
        auth.logout('Finalizar', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

 # --- DASHBOARD DE INTELIGENCIA MENSUAL V56 ---
    if menu == "📊 DASHBOARD":
        df = pd.read_csv('pedidos_pro.csv')
        
        if df.empty:
            st.info("No hay pedidos registrados para generar balances.")
        else:
            # --- PROCESAMIENTO DE FECHAS ---
            df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y')
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y') # Ejemplo: "April 2026"
            
            st.markdown("### 📈 ANALÍTICA Y BALANCES")
            
            # Selector de Mes para ver el balance específico
            meses_disponibles = df['Mes_Año'].unique()
            mes_seleccionado = st.selectbox("Seleccionar Mes para Balance", meses_disponibles, index=len(meses_disponibles)-1)
            
            # Filtramos los datos del mes elegido
            df_mes = df[df['Mes_Año'] == mes_seleccionado]
            
            # --- MÉTRICAS DEL MES SELECCIONADO ---
            c1, c2, c3 = st.columns(3)
            with c1:
                total_mes = df_mes['Monto'].sum()
                st.metric(f"Ventas {mes_seleccionado}", f"${total_mes:,.2f}")
            with c2:
                prod_mes = len(df_mes)
                st.metric("Productos Vendidos", prod_mes)
            with c3:
                # Calculamos saldo pendiente (lo que no está marcado como "Total")
                pendiente = df_mes[df_mes['Pago'] != 'Total']['Monto'].sum()
                st.metric("Saldo por Cobrar", f"${pendiente:,.2f}", delta=f"-${pendiente:,.2f}", delta_color="inverse")

            # --- GRÁFICO DE RENDIMIENTO ---
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            st.write(f"Ventas diarias en {mes_seleccionado}")
            ventas_diarias = df_mes.groupby(df_mes['Fecha'].dt.day)['Monto'].sum()
            st.line_chart(ventas_diarias)
            st.markdown('</div>', unsafe_allow_html=True)

            # --- HISTORIAL DE BALANCES (RESUMEN POR MES) ---
            st.divider()
            st.subheader("📁 Historial de Balances Mensuales")
            
            # Agrupamos por mes para mostrar la tabla de historia
            historial = df.groupby('Mes_Año').agg({
                'Monto': 'sum',
                'ID': 'count',
                'Producto': lambda x: ', '.join(x.unique()[:2]) + "..." # Muestra algunos productos
            }).rename(columns={'Monto': 'Total Facturado', 'ID': 'Cant. Ventas'})
            
            st.table(historial)

            # --- GESTIÓN DE PEDIDOS DEL MES (Interactivo) ---
            st.divider()
            st.subheader(f"📝 Pedidos de {mes_seleccionado}")
            
            for index, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"#{row['ID']} - {row['Cliente']} (${row['Monto']}) - {row['Estado']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        nuevo_pago = st.selectbox("Pago", ["Pendiente", "Seña", "Total"], 
                                                 index=["Pendiente", "Seña", "Total"].index(row['Pago']), 
                                                 key=f"pago_{row['ID']}")
                    with col2:
                        nuevo_estado = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"], 
                                                   index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0,
                                                   key=f"est_{row['ID']}")
                    with col3:
                        if st.button("Guardar Cambios", key=f"btn_{row['ID']}"):
                            # Actualizamos el DataFrame original usando el índice
                            df.at[index, 'Pago'] = nuevo_pago
                            df.at[index, 'Estado'] = nuevo_estado
                            # Guardamos respetando el formato original de fecha para no romper el sistema
                            df['Fecha'] = df['Fecha'].dt.strftime('%d/%m/%Y')
                            df.drop(columns=['Mes_Año'], inplace=True)
                            df.to_csv('pedidos_pro.csv', index=False)
                            st.success("Actualizado")
                            st.rerun()

    # --- NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        st.markdown("### ✍️ REGISTRO DE TRABAJO")
        ds = pd.read_csv('stock_pro.csv')
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("pedido_f", clear_on_submit=True):
            cliente = st.text_input("Cliente")
            ca, cb = st.columns(2)
            with ca:
                prod = st.selectbox("Base", ds['Nombre'].tolist())
                monto = st.number_input("Precio $", min_value=0.0)
            with cb:
                pago = st.selectbox("Pago", ["Pendiente", "Seña", "Total"])
                estado = st.selectbox("Estado", ["Producción", "Vendido"])
            detalle = st.text_area("Notas del diseño")
            
            if st.form_submit_button("INYECTAR PEDIDO"):
                play_splash()
                df_p = pd.read_csv('pedidos_pro.csv')
                nuevo = pd.DataFrame([[len(df_p)+1, datetime.now().strftime("%d/%m/%Y"), cliente, prod, detalle, monto, pago, estado]], columns=df_p.columns)
                pd.concat([df_p, nuevo]).to_csv('pedidos_pro.csv', index=False)
                st.success("Dato inyectado.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- COTIZADOR MULTI-PRODUCTO (LA FUNCIÓN QUE PEDISTE) ---
    elif menu == "💰 COTIZADOR MULTI":
        st.markdown("### 💰 CALCULADORA DE COSTOS COMPLETA")
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        ds = pd.read_csv('stock_pro.csv')
        di = pd.read_csv('insumos_pro.csv')
        
        col1, col2 = st.columns(2)
        with col1:
            p_sel = st.multiselect("Seleccionar Productos Base", ds['Nombre'].tolist())
            costo_p = ds[ds['Nombre'].isin(p_sel)]['Precio_Costo'].sum()
        with col2:
            i_sel = st.multiselect("Seleccionar Insumos", di['Insumo'].tolist())
            costo_i = di[di['Insumo'].isin(i_sel)]['Precio_Costo'].sum()
        
        margen = st.slider("Ganancia %", 0, 500, 100)
        total_costo = costo_p + costo_i
        precio_final = total_costo * (1 + margen/100)
        
        st.divider()
        st.markdown(f"<h2 style='text-align:center; color:#00ff00;'>PRECIO SUGERIDO: ${precio_final:,.2f}</h2>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- STOCK E INSUMOS (DURANTE EL MISMO PROCESO) ---
    elif menu == "📦 STOCK / INSUMOS":
        tab1, tab2 = st.tabs(["📦 PRODUCTOS BASE", "🧪 INSUMOS / TINTAS"])
        
        with tab1:
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            res1 = st.data_editor(pd.read_csv('stock_pro.csv'), num_rows="dynamic", use_container_width=True)
            if st.button("GUARDAR STOCK"):
                play_splash()
                res1.to_csv('stock_pro.csv', index=False)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab2:
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            res2 = st.data_editor(pd.read_csv('insumos_pro.csv'), num_rows="dynamic", use_container_width=True)
            if st.button("GUARDAR INSUMOS"):
                play_splash()
                res2.to_csv('insumos_pro.csv', index=False)
            st.markdown('</div>', unsafe_allow_html=True)