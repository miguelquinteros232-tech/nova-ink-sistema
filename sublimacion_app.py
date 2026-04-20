import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN Y FONDO ANIMADO "PAINT EXPLOSION" ---
st.set_page_config(page_title="NOVA INK - ART SYSTEM", layout="wide", page_icon="🎨")

st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');
        
        /* Fondo con Animación de Explosión de Color */
        .stApp {
            background: #05000a;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(188, 57, 253, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 212, 255, 0.15) 0%, transparent 40%),
                url("https://www.transparenttextures.com/patterns/carbon-fibre.png");
            color: #e0e0e0;
            font-family: 'Rajdhani', sans-serif;
            overflow-x: hidden;
        }

        /* Simulación de Partículas/Explosiones (CSS puro) */
        .stApp::before {
            content: "🧢 👕 ☕";
            position: fixed;
            top: -50px;
            left: 50%;
            font-size: 30px;
            opacity: 0.1;
            animation: drift 20s linear infinite;
            z-index: -1;
        }

        @keyframes drift {
            from { transform: translateY(0) rotate(0deg) translateX(-50vw); }
            to { transform: translateY(110vh) rotate(360deg) translateX(50vw); }
        }

        .main-logo {
            font-size: 65px; font-weight: 700; text-align: center;
            background: linear-gradient(90deg, #bc39fd, #00d4ff, #ff007b, #bc39fd);
            background-size: 300% auto; -webkit-background-clip: text;
            -webkit-text-fill-color: transparent; animation: shine 5s linear infinite;
            letter-spacing: 12px; margin-bottom: 30px;
            filter: drop-shadow(0px 0px 15px rgba(188, 57, 253, 0.5));
        }
        @keyframes shine { to { background-position: 300% center; } }

        .glass-panel {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 5px solid #00d4ff;
            border-radius: 15px; padding: 25px; margin-bottom: 20px;
            backdrop-filter: blur(8px);
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
        menu = st.radio("", ["📊 DASHBOARD", "📝 NUEVO PEDIDO", "📦 INVENTARIO", "💰 COTIZADOR INTELIGENTE"], label_visibility="collapsed")
        st.divider()
        auth.logout('Salir', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD (EDICIÓN Y BALANCES) ---
    if menu == "📊 DASHBOARD":
        df = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            
            st.markdown("### 📈 MÉTRICAS")
            m_sel = st.selectbox("Período", df['Mes_Año'].unique(), index=len(df['Mes_Año'].unique())-1)
            df_m = df[df['Mes_Año'] == m_sel]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas", f"${df_m['Monto'].sum():,.2f}")
            c2.metric("Órdenes", len(df_m))
            c3.metric("Deuda", f"${df_m[df_m['Pago'] != 'Total']['Monto'].sum():,.2f}")

            st.divider()
            for idx, row in df_m.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"⚙️ Editar: {row['Cliente']} - {row['Producto']}"):
                    with st.form(f"ed_{idx}"):
                        cc1, cc2 = st.columns(2)
                        n_cli = cc1.text_input("Cliente", row['Cliente'])
                        n_mon = cc2.number_input("Monto $", value=float(row['Monto']))
                        n_pag = cc1.selectbox("Pago", ["Pendiente", "Seña", "Total"], index=["Pendiente", "Seña", "Total"].index(row['Pago']))
                        n_est = cc2.selectbox("Estado", ["Producción", "Vendido", "Entregado"], index=["Producción", "Vendido", "Entregado"].index(row['Estado']) if row['Estado'] in ["Producción", "Vendido", "Entregado"] else 0)
                        if st.form_submit_button("GUARDAR CAMBIOS"):
                            df.at[idx, 'Cliente'], df.at[idx, 'Monto'], df.at[idx, 'Pago'], df.at[idx, 'Estado'] = n_cli, n_mon, n_pag, n_est
                            conn.update(worksheet="Pedidos", data=df)
                            st.rerun()

    # --- 💰 COTIZADOR INTELIGENTE (LA MEJORA) ---
    elif menu == "💰 COTIZADOR INTELIGENTE":
        st.subheader("💰 Calculadora de Costo Real")
        inv = get_data("Inventario", ['Nombre', 'Talle/Medida', 'Color', 'Cantidad'])
        
        with st.container():
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            
            # Selección de materiales del inventario
            lista_items = inv['Nombre'] + " - " + inv['Talle/Medida']
            items_c = col_a.multiselect("Selecciona los materiales usados:", lista_items.tolist())
            
            costo_materiales = 0.0
            for item in items_c:
                c_unit = col_b.number_input(f"Costo unitario de {item} $", min_value=0.0, key=f"c_{item}")
                cant_u = col_b.number_input(f"Cantidad usada de {item}", min_value=0.0, step=1.0, key=f"q_{item}")
                costo_materiales += (c_unit * cant_u)
            
            st.divider()
            costo_extra = st.number_input("Costos extra (Luz, envase, diseño) $", min_value=0.0)
            margen = st.slider("Margen de Ganancia %", 0, 500, 100)
            
            costo_total = costo_materiales + costo_extra
            precio_final = costo_total * (1 + margen/100)
            
            st.markdown(f"""
                <h2 style='color:#00d4ff; text-align:center;'>COSTO TOTAL: ${costo_total:,.2f}</h2>
                <h1 style='color:#bc39fd; text-align:center;'>PRECIO VENTA: ${precio_final:,.2f}</h1>
                <p style='text-align:center;'>Ganancia Neta: ${(precio_final - costo_total):,.2f}</p>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 📦 INVENTARIO ---
    elif menu == "📦 INVENTARIO":
        inv = get_data("Inventario", ['Categoría', 'Nombre', 'Talle/Medida', 'Color', 'Cantidad', 'Unidad', 'Minimo'])
        st.subheader("📦 Almacén Nova")
        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Cargar Nuevo Material"):
            with st.form("add_i"):
                c1, c2, c3 = st.columns(3)
                cat = c1.selectbox("Tipo", ["Insumo", "Material (Gorra/Remera)"])
                nom = c1.text_input("Nombre")
                tal = c2.text_input("Talle/Medida")
                col = c2.text_input("Color")
                can = c3.number_input("Stock Inicial", min_value=0.0)
                if st.form_submit_button("REGISTRAR"):
                    n_i = pd.DataFrame([{"Categoría": cat, "Nombre": nom, "Talle/Medida": tal, "Color": col, "Cantidad": can, "Unidad": "u", "Minimo": 1.0}])
                    conn.update(worksheet="Inventario", data=pd.concat([inv, n_i], ignore_index=True))
                    st.rerun()

    # --- 📝 NUEVO PEDIDO ---
    elif menu == "📝 NUEVO PEDIDO":
        inv = get_data("Inventario", ['Nombre', 'Talle/Medida', 'Color', 'Cantidad'])
        with st.form("n_p"):
            st.subheader("📝 Nueva Orden de Producción")
            c1, c2 = st.columns(2)
            cli, prd = c1.text_input("Cliente"), c1.text_input("Producto Final")
            mon, pag = c2.number_input("Precio $", min_value=0.0), c2.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            
            lista_stock = inv['Nombre'] + " - " + inv['Talle/Medida']
            ins_usado = st.selectbox("Material a descontar", ["Ninguno"] + lista_stock.tolist())
            cant_d = st.number_input("Cantidad", min_value=0.0, step=1.0)
            
            if st.form_submit_button("CREAR PEDIDO"):
                df_p = get_data("Pedidos", ['ID', 'Fecha', 'Cliente', 'Producto', 'Detalle', 'Monto', 'Pago', 'Estado'])
                nueva = pd.DataFrame([{"ID": len(df_p)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": f"Consumo: {cant_d} de {ins_usado}", "Monto": mon, "Pago": pag, "Estado": "Producción"}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_p, nueva], ignore_index=True))
                
                if ins_usado != "Ninguno":
                    idx = lista_stock[lista_stock == ins_usado].index[0]
                    inv.at[idx, 'Cantidad'] -= cant_d
                    conn.update(worksheet="Inventario", data=inv)
                st.success("¡Pedido en marcha!"); time.sleep(1); st.rerun()
