import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import time
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NOVA INK - PREMIUM OS", layout="wide")
st.markdown('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&display=swap');
        .stApp { background: #05000a; }
        .main-logo { font-family: 'Orbitron'; font-size: 50px; text-align: center; background: linear-gradient(90deg, #bc39fd, #00d4ff, #bc39fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px; font-weight: 900; margin-bottom: 20px; }
        .stMetric { background: rgba(188, 57, 253, 0.05); padding: 15px; border-radius: 10px; border-left: 3px solid #00d4ff; }
        div[data-testid="stExpander"] { border: 1px solid rgba(188, 57, 253, 0.3); background: rgba(20, 0, 40, 0.5); }
    </style>
''', unsafe_allow_html=True)

# --- 2. CARGA DE CONFIGURACIÓN Y AUTENTICADOR ---
def load_config():
    if not os.path.exists("config_pro.yaml"):
        # Estructura inicial obligatoria para evitar que el autenticador falle
        initial_config = {
            'credentials': {'usernames': {}}, 
            'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'},
            'preauthorized': {'emails': []}
        }
        with open("config_pro.yaml", 'w') as f: 
            yaml.dump(initial_config, f)
        return initial_config
    
    with open("config_pro.yaml") as f:
        cfg = yaml.load(f, Loader=SafeLoader)
        # Verificación de seguridad: si el archivo existe pero está mal formado
        if cfg is None or 'credentials' not in cfg:
            return {'credentials': {'usernames': {}}, 'cookie': {'expiry_days': 30, 'key': 'nova_k', 'name': 'nova_auth'}}
        return cfg

# Intentamos crear el objeto authenticator
try:
    config = load_config()
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
except Exception as e:
    st.error(f"Error crítico al inicializar el autenticador: {e}")
    st.stop()

st.markdown('<div class="main-logo">NOVA INK</div>', unsafe_allow_html=True)

# --- 3. ACCESO ---
# Ahora invocamos login con seguridad
try:
    authenticator.login(location='main')
except Exception as e:
    st.error("Error en el módulo de login. Por favor, reinicia la app.")
    st.stop()

if st.session_state.get("authentication_status") is not True:
    st.info("Sistema de gestión Nova Ink. Por favor identifíquese.")
    with st.expander("📝 REGISTRO"):
        try:
            # Nueva firma del método register_user para evitar el TypeError anterior
            result = authenticator.register_user(location='main', pre_authorization=[])
            if result:
                # Si se registró alguien, guardamos los cambios en el archivo
                with open("config_pro.yaml", 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success('Usuario registrado. Ya puede iniciar sesión arriba.')
        except Exception as e:
            st.warning("Complete los campos para registrar un nuevo usuario.")

    # --- DASHBOARD ---
    if menu == "📊 DASHBOARD":
        data = ws_p.get_all_records()
        df_all = pd.DataFrame(data)
        if not df_all.empty:
            df_all['Monto'] = pd.to_numeric(df_all['Monto'], errors='coerce').fillna(0)
            df_active = df_all[df_all['Estado'] != 'Vendido']
            c1, c2 = st.columns(2)
            c1.metric("PEDIDOS ACTIVOS", len(df_active))
            c2.metric("POR COBRAR", f"${df_active['Monto'].sum():,.2f}")
            st.write("### ⚡ Acciones Rápidas")
            for i, r in df_active.iterrows():
                with st.expander(f"🕒 {r['Estado']} | {r['Cliente']} - {r['Producto']}"):
                    st.write(f"**Detalles:** {r['Detalle']}")
                    if st.button(f"MARCAR COMO VENDIDO", key=f"v_{i}"):
                        ws_p.update_cell(i+2, 7, "Vendido")
                        st.success("Vendido!"); time.sleep(1); st.rerun()

    # --- GESTIÓN PEDIDOS ---
    elif menu == "📝 GESTIÓN PEDIDOS":
        tab1, tab2 = st.tabs(["NUEVO PEDIDO", "MODIFICAR"])
        df_inv = pd.DataFrame(ws_i.get_all_records())
        with tab1:
            with st.form("new_o"):
                c1, c2 = st.columns(2)
                cli, prd = c1.text_input("Cliente"), c1.text_input("Producto")
                det = c2.text_area("Descripción (Insumos/Talles)")
                pago = c2.selectbox("Estado Pago", ["No Pago", "Seña", "Pagado Total"])
                mon = st.number_input("Precio Final $")
                mat = st.selectbox("Insumo a descontar", df_inv['Nombre'].tolist() if not df_inv.empty else [])
                can = st.number_input("Cantidad a restar del Stock", min_value=0.0)
                if st.form_submit_button("REGISTRAR PEDIDO"):
                    idx = df_inv[df_inv['Nombre'] == mat].index[0]
                    ws_i.update_cell(idx+2, 6, float(df_inv.at[idx, 'Cantidad']) - can)
                    ws_p.append_row([len(ws_p.get_all_values()), datetime.now().strftime("%d/%m/%Y"), cli, prd, det, mon, "Producción", 0, pago])
                    st.success("Pedido y Stock actualizados."); st.rerun()
        with tab2:
            df_edit = pd.DataFrame(ws_p.get_all_records())
            if not df_edit.empty:
                sel = st.selectbox("Elegir pedido", df_edit['Cliente'] + " - " + df_edit['Producto'])
                idx_e = df_edit[df_edit['Cliente'] + " - " + df_edit['Producto'] == sel].index[0]
                with st.form("e_f"):
                    u_det = st.text_area("Descripción", value=df_edit.iloc[idx_e]['Detalle'])
                    u_mon = st.number_input("Precio $", value=float(df_edit.iloc[idx_e]['Monto']))
                    if st.form_submit_button("ACTUALIZAR"):
                        ws_p.update_cell(idx_e+2, 5, u_det); ws_p.update_cell(idx_e+2, 6, u_mon); st.rerun()

    # --- STOCK (CON TODOS LOS CAMPOS) ---
    elif menu == "📦 STOCK":
        data_i = ws_i.get_all_records()
        df_st = pd.DataFrame(data_i)
        st.write("### Inventario Detallado")
        st.dataframe(df_st, use_container_width=True)
        
        with st.expander("➕ CARGAR NUEVO MATERIAL / INSUMO"):
            with st.form("add_stock_full"):
                c1, c2 = st.columns(2)
                # Campos solicitados
                cat = c1.text_input("Categoría (Ej: Remeras, Vinilos)")
                nom = c1.text_input("Nombre del Producto")
                tipo = c1.text_input("Tipo (Ej: Algodón, Glitter)")
                
                talle = c2.text_input("Talle (S, M, L, etc.)")
                color = c2.text_input("Color")
                cant = c2.number_input("Cantidad Inicial", min_value=0.0)
                unid = c2.text_input("Unidad (Unidades, Metros, etc.)")
                
                if st.form_submit_button("GUARDAR EN INVENTARIO"):
                    # El orden debe ser el mismo que en tu Excel: 
                    # Categoría, Nombre, Tipo, Talle, Color, Cantidad, Unidad
                    ws_i.append_row([cat, nom, tipo, talle, color, cant, unid])
                    st.success(f"Registrado: {nom}")
                    time.sleep(1)
                    st.rerun()

    # --- HISTORIAL ---
    elif menu == "📜 HISTORIAL":
        df_h = pd.DataFrame(ws_p.get_all_records())
        if not df_h.empty:
            df_h['Fecha'] = pd.to_datetime(df_h['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_h['Mes'] = df_h['Fecha'].dt.strftime('%Y-%m')
            df_v = df_h[df_h['Estado'] == 'Vendido']
            mes_sel = st.selectbox("Mes", df_v['Mes'].unique() if not df_v.empty else ["Sin ventas"])
            if mes_sel != "Sin ventas":
                df_mes = df_v[df_v['Mes'] == mes_sel]
                st.metric(f"Ventas {mes_sel}", f"${df_mes['Monto'].sum():,.2f}")
                st.table(df_mes[['Fecha', 'Cliente', 'Producto', 'Monto']])

    # --- COTIZADOR ---
    elif menu == "💰 COTIZADOR":
        c1, c2 = st.columns(2)
        ins = c1.number_input("Costo Insumos $")
        hrs = c1.number_input("Horas Trabajo")
        v_h = c1.number_input("Valor Hora $", value=1500.0)
        mrg = c2.slider("% Ganancia", 0, 400, 100)
        base = ins + (hrs * v_h)
        final = base * (1 + mrg/100)
        st.divider()
        st.title(f"Sugerido: ${final:,.2f}")
        st.info(f"Costo: ${base:,.2f} | Ganancia: ${final-base:,.2f}")
