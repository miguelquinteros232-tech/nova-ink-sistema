import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NOVA INK - AUTOMATION", layout="wide", page_icon="🎨")

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
            border-radius: 15px; padding: 20px; margin-bottom: 15px;
        }
    </style>
''', unsafe_allow_html=True)

# --- 2. CONEXIÓN A DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_pedidos():
    return conn.read(worksheet="Pedidos", ttl=0)

def get_inventario():
    try:
        return conn.read(worksheet="Inventario", ttl=0)
    except:
        return pd.DataFrame(columns=['Insumo', 'Cantidad', 'Unidad', 'Minimo'])

# --- 3. SEGURIDAD ---
with open("config_pro.yaml") as f:
    config = yaml.load(f, Loader=SafeLoader)

authenticator = stauth.Authenticate(config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'])

if not st.session_state.get("authentication_status"):
    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)
    authenticator.login(location='main')
else:
    with st.sidebar:
        st.markdown("<h3 style='color:#00d4ff;'>NOVA OS</h3>", unsafe_allow_html=True)
        menu = st.radio("", ["📊 DASHBOARD", "📝 REGISTRO VENTAS", "📦 STOCK & INSUMOS", "💰 COTIZADOR"], label_visibility="collapsed")
        st.divider()
        authenticator.logout('Cerrar Sesión', 'sidebar')

    st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

    # --- 📊 DASHBOARD ---
    if menu == "📊 DASHBOARD":
        df = get_pedidos()
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            df['Mes_Año'] = df['Fecha'].dt.strftime('%B %Y')
            mes_sel = st.selectbox("Mes", df['Mes_Año'].unique(), index=len(df['Mes_Año'].unique())-1)
            df_mes = df[df['Mes_Año'] == mes_sel]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas", f"${df_mes['Monto'].sum():,.2f}")
            c2.metric("Pedidos", len(df_mes))
            c3.metric("Por Cobrar", f"${df_mes[df_mes['Pago'] != 'Total']['Monto'].sum():,.2f}")
            
            st.divider()
            for idx, row in df_mes.sort_values(by='ID', ascending=False).iterrows():
                with st.expander(f"#{row['ID']} - {row['Cliente']} ({row['Estado']})"):
                    st.write(f"**Detalle:** {row['Detalle']}")
                    if st.button("Marcar como Entregado", key=f"ent{idx}"):
                        full_df = get_pedidos()
                        full_df.at[idx, 'Estado'] = "Entregado"
                        conn.update(worksheet="Pedidos", data=full_df)
                        st.rerun()

    # --- 📝 REGISTRO VENTAS CON DESCUENTO DE STOCK ---
    elif menu == "📝 REGISTRO VENTAS":
        inv = get_inventario()
        st.subheader("Nueva Orden con Descuento de Stock")
        
        with st.form("form_venta_automatica"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Cliente")
            prd = c1.text_input("Producto")
            mon = c2.number_input("Monto $", min_value=0.0)
            pag = c2.selectbox("Pago", ["Pendiente", "Seña", "Total"])
            
            st.divider()
            st.markdown("🛠️ **Consumo de Insumos**")
            insumo_usado = st.selectbox("¿Qué insumo usaste?", ["Ninguno"] + inv['Insumo'].tolist())
            cantidad_usada = st.number_input("¿Cuánta cantidad consumiste?", min_value=0.0, step=1.0)
            
            est = st.selectbox("Estado", ["Producción", "Vendido", "Entregado"])
            det = st.text_area("Detalles adicionales")
            
            if st.form_submit_button("REGISTRAR Y DESCONTAR STOCK"):
                # 1. Guardar el Pedido
                df_o = get_pedidos()
                n_row = pd.DataFrame([{"ID": len(df_o)+1, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Cliente": cli, "Producto": prd, "Detalle": f"{det} (Usó: {cantidad_usada} de {insumo_usado})", "Monto": mon, "Pago": pag, "Estado": est}])
                conn.update(worksheet="Pedidos", data=pd.concat([df_o, n_row], ignore_index=True))
                
                # 2. Descontar del Inventario (Si seleccionó uno)
                if insumo_usado != "Ninguno":
                    inv.loc[inv['Insumo'] == insumo_usado, 'Cantidad'] -= cantidad_usada
                    conn.update(worksheet="Inventario", data=inv)
                    st.success(f"¡Pedido guardado e inventario de {insumo_usado} actualizado!")
                else:
                    st.success("¡Pedido guardado!")
                
                time.sleep(1)
                st.rerun()

    # --- 📦 STOCK & INSUMOS ---
    elif menu == "📦 STOCK & INSUMOS":
        st.subheader("📦 Gestión de Inventario")
        inv = get_inventario()
        st.dataframe(inv, use_container_width=True)
        
        with st.expander("➕ Cargar / Editar Insumo"):
            with st.form("edit_inv"):
                i_nom = st.text_input("Insumo")
                i_cant = st.number_input("Cantidad", min_value=0.0)
                i_uni = st.selectbox("Unidad", ["Unidades", "Metros", "Hojas"])
                i_min = st.number_input("Mínimo para alerta", min_value=0.0)
                if st.form_submit_button("Sincronizar Insumo"):
                    if i_nom in inv['Insumo'].values:
                        inv.loc[inv['Insumo'] == i_nom, ['Cantidad', 'Unidad', 'Minimo']] = [i_cant, i_uni, i_min]
                    else:
                        inv = pd.concat([inv, pd.DataFrame([{"Insumo": i_nom, "Cantidad": i_cant, "Unidad": i_uni, "Minimo": i_min}])], ignore_index=True)
                    conn.update(worksheet="Inventario", data=inv)
                    st.rerun()

    # --- 💰 COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        st.subheader("💰 Calculadora")
        cst = st.number_input("Costo $", min_value=0.0)
        mrg = st.slider("Ganancia %", 0, 300, 100)
        st.header(f"Precio: ${cst * (1 + mrg/100):,.2f}")
