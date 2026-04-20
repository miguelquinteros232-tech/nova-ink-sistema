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

# Estilos Neón Nova OS
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        .stApp { background: #020005; color: white; font-family: 'Rajdhani', sans-serif; }
        .main-logo {
            font-size: 50px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 5px; margin-bottom: 10px;
        }
        .glass-panel {
            background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #bc39fd; border-radius: 15px; padding: 20px; margin-bottom: 15px;
        }
        .metric-card { background: rgba(0, 212, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(0,212,255,0.2); text-align: center; }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN A DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_get_data(sheet_name, columns):
    try:
        data = conn.read(worksheet=sheet_name, ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=columns)
        return data.dropna(how='all')
    except:
        return pd.DataFrame(columns=columns)

# --- 3. SEGURIDAD ---
try:
    with open("config_pro.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except:
    config = {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_c'}}

authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    authenticator.login(location='main')
else:
    # --- NAVEGACIÓN ---
    with st.sidebar:
        st.markdown("<h3 style='color:#00d4ff;'>NAV OS</h3>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 STOCK", "💰 COTIZADOR"], label_visibility="collapsed")
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD & BALANCES (MES Y AÑO) ---
    if menu == "📊 DASHBOARD":
        df = safe_get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
        
        if df.empty:
            st.info("Sin datos registrados.")
        else:
            # Procesamiento de Fechas
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Fecha'])
            df['Mes'] = df['Fecha'].dt.strftime('%B')
            df['Año'] = df['Fecha'].dt.year.astype(str)
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')

            st.markdown("### 📈 ANALÍTICA FINANCIERA")
            
            # Filtros de Balances
            c1, c2 = st.columns(2)
            año_sel = c1.selectbox("Filtrar por Año", sorted(df['Año'].unique(), reverse=True))
            meses_disp = df[df['Año'] == año_sel]['Mes_Año'].unique()
            mes_sel = c2.selectbox("Filtrar por Mes", meses_disp, index=len(meses_disp)-1)

            # --- Balance Mensual ---
            df_mes = df[df['Mes_Año'] == mes_sel]
            st.markdown(f"#### Resumen de {mes_sel}")
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Ventas Mes", f"${df_mes['Monto'].sum():,.2f}")
            with m2: st.metric("Pedidos", len(df_mes))
            with m3: 
                por_cobrar = df_mes[df_mes['Pago'] != 'Total']['Monto'].sum()
                st.metric("Por Cobrar", f"${por_cobrar:,.2f}", delta=f"-${por_cobrar:,.2f}", delta_color="inverse")

            # --- Balance Anual ---
            st.markdown(f"#### Balance Anual {año_sel}")
            df_año = df[df['Año'] == año_sel]
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            resumen_anual = df_año.groupby('Mes')['Monto'].sum().reindex([
                'January', 'February', 'March', 'April', 'May', 'June', 
                'July', 'August', 'September', 'October', 'November', 'December'
            ], fill_value=0)
            st.bar_chart(resumen_anual)
            st.write(f"**Total recaudado en {año_sel}:** ${df_año['Monto'].sum():,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

            # Gestión de Pedidos Actuales
            st.divider()
            st.subheader("📋 Gestión de Pedidos")
            for idx, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Cliente']}"):
                    st.write(f"**Producto:** {row['Producto']} | **Detalle:** {row['Detalle']}")
                    col_p, col_e, col_b = st.columns(3)
                    new_p = col_p.selectbox("Pago", ["Pendiente", "Seña", "Total"], index=["Pendiente", "Seña", "Total"].index(row['Pago']), key=f"p{idx}")
                    new_e = col_e.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0, key=f"e{idx}")
                    if col_b.button("Actualizar", key=f"btn{idx}"):
                        full_df = safe_get_data("Pedidos", [])
                        full_df.at[idx, 'Pago'] = new_p
                        full_df.at[idx, 'Estado'] = new_e
                        conn.update(worksheet="Pedidos", data=full_df)
                        st.rerun()

    # --- 📝 NUEVO PEDIDO CON DESCUENTO DE STOCK ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = safe_get_data("Inventario", ['Insumo', 'Cantidad', 'Unidad', 'Minimo'])
        st.subheader("📝 Registrar Nueva Venta")
        
        with st.form("venta_form"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Monto Total $", min_value=0.0)
            pag = c2.selectbox("Estado de Pago", ["Pendiente", "Seña", "Total"])
            
            st.divider()
            st.markdown("🛠️ **Consumo de Almacén**")
            ins_sel = st.selectbox("Insumo utilizado", ["Ninguno"] + inv['Insumo'].tolist())
            cant_sel = st.number_input("Cantidad consumida", min_value=0.0)
            
            est = st.selectbox("Estado Inicial", ["Producción", "Vendido", "Entregado"])
            det = st.text_area("Detalles / Notas")
            
            if st.form_submit_button("GUARDAR Y DESCONTAR STOCK"):
                # Guardar Pedido
                df_p = safe_get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
                nueva_fila = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": f"{det} (Insumo: {cant_sel} {ins_sel})", "Monto": mon, "Pago": pag, "Estado": est}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_p, nueva_fila], ignore_index=True))
                
                # Descontar Inventario
                if ins_sel != "Ninguno" and cant_sel > 0:
                    inv.loc[inv['Insumo'] == ins_sel, 'Cantidad'] -= cant_sel
                    conn.update(worksheet="Inventario", data=inv)
                
                st.success("Operación Exitosa")
                time.sleep(1)
                st.rerun()

    # --- 📦 MÓDULO DE STOCK ---
    elif menu == "📦 STOCK":
        st.subheader("📦 Control de Insumos")
        inv = safe_get_data("Inventario", ['Insumo', 'Cantidad', 'Unidad', 'Minimo'])
        
        # Alertas de Stock Bajo
        for _, r in inv.iterrows():
            if r['Cantidad'] <= r['Minimo']:
                st.warning(f"⚠️ STOCK CRÍTICO: {r['Insumo']} ({r['Cantidad']} {r['Unidad']})")

        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Cargar / Editar Insumo"):
            with st.form("inv_form"):
                n = st.text_input("Nombre del Insumo")
                c = st.number_input("Cantidad", min_value=0.0)
                u = st.selectbox("Unidad", ["Unidades", "Metros", "Hojas", "Litros"])
                m = st.number_input("Mínimo para Alerta", min_value=0.0)
                if st.form_submit_button("Sincronizar Almacén"):
                    if n in inv['Insumo'].values:
                        inv.loc[inv['Insumo'] == n, ['Cantidad', 'Unidad', 'Minimo']] = [c, u, m]
                    else:
                        inv = pd.concat([inv, pd.DataFrame([{"Insumo": n, "Cantidad": c, "Unidad": u, "Minimo": m}])], ignore_index=True)
                    conn.update(worksheet="Inventario", data=inv)
                    st.rerun()

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora Rápida")
        costo = st.number_input("Costo de Insumo $", min_value=0.0)
        margen = st.slider("Margen %", 0, 400, 100)
        st.header(f"Precio Sugerido: ${costo * (1 + margen/100):,.2f}")
