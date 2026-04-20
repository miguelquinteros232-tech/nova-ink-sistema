import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN E INTERFAZ VISUAL ---
st.set_page_config(page_title="NOVA INK - ELITE SYSTEM", layout="wide", page_icon="🎨")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        
        .stApp {
            background: #05000a !important;
            color: #e0e0e0;
            font-family: 'Rajdhani', sans-serif;
        }
        
        /* Estilo del Logo Nova */
        .main-logo {
            font-size: 65px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd);
            background-size: 200% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 4s linear infinite;
            letter-spacing: 12px; margin-bottom: 30px;
            text-shadow: 0px 0px 20px rgba(188, 57, 253, 0.3);
        }
        @keyframes shine { to { background-position: 200% center; } }

        /* Paneles Glassmorphism */
        .glass-panel {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #00d4ff;
            border-radius: 15px; padding: 25px; margin-bottom: 20px;
            box-shadow: 10px 10px 20px rgba(0,0,0,0.5);
        }

        /* Botones y Inputs Custom */
        .stButton>button {
            background: linear-gradient(45deg, #bc39fd, #00d4ff) !important;
            color: white !important; font-weight: bold !important; border: none !important;
            border-radius: 8px !important; transition: 0.3s !important;
        }
        .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 15px #bc39fd; }
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
    # --- NAVEGACIÓN SIDEBAR ---
    with st.sidebar:
        st.markdown("<h2 style='color:#00d4ff; text-align:center;'>NOVA OS</h2>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 INVENTARIO TOTAL", "💰 COTIZADOR"], label_visibility="collapsed")
        st.divider()
        auth.logout('Salir del Sistema', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD & BALANCES ---
    if menu == "📊 DASHBOARD":
        pedidos = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
        if not pedidos.empty:
            pedidos['Fecha'] = pd.to_datetime(pedidos['Fecha'], dayfirst=True)
            pedidos['Mes_Año'] = pedidos['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 MÉTRICAS DE RENDIMIENTO")
            m_sel = st.selectbox("Seleccionar Mes", pedidos['Mes_Año'].unique(), index=len(pedidos['Mes_Año'].unique())-1)
            df_m = pedidos[pedidos['Mes_Año'] == m_sel]
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Ventas", f"${df_m['Monto'].sum():,.2f}")
            with c2: st.metric("Órdenes", len(df_m))
            with c3: 
                cobrar = df_m[df_m['Pago'] != 'Total']['Monto'].sum()
                st.metric("Deuda Clientes", f"${cobrar:,.2f}", delta_color="inverse")

            st.divider()
            st.subheader(f"Lista de Trabajos - {m_sel}")
            for idx, row in df_m.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"Pedido #{row['ID']} | {row['Cliente']} | {row['Estado']}"):
                    st.info(f"Detalle: {row['Detalle']}")
                    if st.button("Marcar Entregado", key=f"btn{idx}"):
                        full_p = get_data("Pedidos", [])
                        full_p.at[idx, 'Estado'] = "Entregado"
                        conn.update(worksheet="Pedidos", data=full_p)
                        st.rerun()

    # --- 📝 NUEVO PEDIDO CON DESCUENTO INTELIGENTE ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = get_data("Inventario", ['Categoría', 'Nombre', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad', 'Minimo'])
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        with st.form("form_v"):
            st.subheader("📝 Registrar Nueva Venta")
            c1, c2 = st.columns(2)
            cliente = c1.text_input("Cliente")
            producto_v = c1.text_input("Producto Final (ej. Gorra Sublimada)")
            precio = c2.number_input("Monto Total $", min_value=0.0)
            pago = c2.selectbox("Estado de Pago", ["Pendiente", "Seña", "Total"])
            
            st.markdown("---")
            st.write("📦 **Descontar del Inventario**")
            # Filtramos para que solo aparezcan productos con stock
            lista_inv = inv['Nombre'] + " | " + inv['Talle/Medida'] + " | " + inv['Color']
            mat_usado = st.selectbox("Seleccionar Material/Insumo", ["Ninguno"] + lista_inv.tolist())
            cant_usada = st.number_input("Cantidad a descontar", min_value=0.0, step=1.0)
            
            estado = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"])
            notas = st.text_area("Notas del pedido")
            
            if st.form_submit_button("REGISTRAR Y ACTUALIZAR"):
                # Guardar Pedido
                df_ped = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
                n_fila = pd.DataFrame([{"ID": len(df_ped)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cliente, "Producto": producto_v, "Detalle": f"{notas} (Usó: {cant_usada} de {mat_usado})", "Monto": precio, "Pago": pago, "Estado": estado}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_ped, n_fila], ignore_index=True))
                
                # Descontar Stock
                if mat_usado != "Ninguno":
                    idx_inv = lista_inv[lista_inv == mat_usado].index[0]
                    inv.at[idx_inv, 'Cantidad'] -= cant_usada
                    conn.update(worksheet="Inventario", data=inv)
                
                st.success("Pedido y Stock actualizados correctamente.")
                time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 📦 INVENTARIO CATEGORIZADO (LA MEJORA) ---
    elif menu == "📦 INVENTARIO TOTAL":
        inv = get_data("Inventario", ['Categoría', 'Nombre', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad', 'Minimo'])
        
        t1, t2 = st.tabs(["📋 LISTADO", "➕ CARGA / EDICIÓN"])
        
        with t1:
            st.subheader("Gestión de Almacén")
            cat_filter = st.multiselect("Filtrar por Categoría", ["Insumos", "Materiales (Gorras/Remeras)", "Otros"], default=["Insumos", "Materiales (Gorras/Remeras)"])
            df_filtro = inv[inv['Categoría'].isin(cat_filter)]
            st.dataframe(df_filtro, use_container_width=True)
            
            # Alertas
            for _, r in inv.iterrows():
                if r['Cantidad'] <= r['Minimo']:
                    st.error(f"🚨 STOCK BAJO: {r['Nombre']} ({r['Talle/Medida']}) - Quedan {r['Cantidad']}")

        with t2:
            with st.form("form_inv"):
                st.write("**Agregar o Modificar Item**")
                cc1, cc2, cc3 = st.columns(3)
                cat = cc1.selectbox("Categoría", ["Insumos", "Materiales (Gorras/Remeras)", "Otros"])
                nom = cc1.text_input("Nombre (ej. Gorra Trucker, Vinilo Textil)")
                tal = cc2.text_input("Talle / Medida (ej. XL, 50cm, A4)")
                col = cc2.text_input("Color")
                can = cc3.number_input("Cantidad Actual", min_value=0.0)
                min_s = cc3.number_input("Mínimo Crítico", min_value=0.0)
                uni = cc3.selectbox("Unidad", ["Unidades", "Metros", "Hojas", "Litros"])
                
                if st.form_submit_button("SINCRONIZAR CON NUBE"):
                    # Buscamos si ya existe la combinación exacta para actualizarla
                    match = inv[(inv['Nombre'] == nom) & (inv['Talle/Medida'] == tal) & (inv['Color'] == col)]
                    if not match.empty:
                        inv.loc[match.index, ['Categoría', 'Cantidad', 'Unidad', 'Minimo']] = [cat, can, uni, min_s]
                    else:
                        n_it = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": uni, "Minimo": min_s}])
                        inv = pd.concat([inv, n_it], ignore_index=True)
                    
                    conn.update(worksheet="Inventario", data=inv)
                    st.success("Inventario actualizado."); time.sleep(1); st.rerun()

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("💰 Calculadora Nova")
        c_i = st.number_input("Costo base del material $", min_value=0.0)
        c_g = st.slider("Porcentaje de ganancia deseada %", 0, 400, 100)
        st.header(f"Precio Sugerido: ${c_i * (1 + c_g/100):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
