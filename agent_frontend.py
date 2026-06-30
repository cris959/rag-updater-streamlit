import streamlit as st
import time
from agent_backend import ejecutar_agent_loop

# 1. Configuración de la página de Streamlit (SIEMPRE debe ir primero)
st.set_page_config(page_title="Agente DevOps OCI", page_icon="🤖", layout="centered")

st.title("🤖 Agente de Infraestructura & Foro Hub")
st.subheader("Entorno de desarrollo local (Christian Dev)")

# 2. Configuración de Seguridad y Límites
LIMITE_CONSULTAS = 5

if "contador_consultas" not in st.session_state:
    st.session_state.contador_consultas = 0

if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. Mostrar los mensajes anteriores del historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- TRAMPA HONEYPOT (Nativa y fuera de la vista) ---
# Creamos dos pestañas, pero la segunda (donde está la trampa) la dejamos sin texto visible
tab_principal, tab_sistema = st.tabs(["💬 Chat", " "])

with tab_principal:
    # ACÁ ADENTRO VA TODO TU CÓDIGO ACTUAL DEL CHAT
    # (El st.chat_input, el historial de mensajes, etc.)
    pass

with tab_sistema:
    # Colocamos el honeypot en la pestaña vacía que los humanos no van a clickear
    honeypot_field = st.text_input("Confirm email (dejar en blanco)", value="", key="email_confirm")
# -----------------------------------------------------------------

# Control visual previo: si ya superó el límite, frena la ejecución aquí
if st.session_state.contador_consultas >= LIMITE_CONSULTAS:
    st.error(f"⚠️ Has alcanzado el límite de {LIMITE_CONSULTAS} consultas por sesión.")
    st.info("Por favor, regresa más tarde o reinicia la aplicación.")
    st.stop()

# 4. Capturar la entrada del usuario mediante Chat Input
if prompt := st.chat_input("¿Qué querés consultar sobre Nginx, OCI o Foro Hub?"):
    
    # VALIDACIÓN 1: ¿Es un bot interactuando con el backend?
    if honeypot_field != "":
        st.warning("Acceso denegado de forma preventiva.")
        time.sleep(2)
        st.stop()

    # VALIDACIÓN 2: ¿Pasó el límite de consultas? (Doble check de seguridad)
    if st.session_state.contador_consultas >= LIMITE_CONSULTAS:
        st.stop()

    # Mostrar el mensaje del usuario en la UI
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generar la respuesta llamando al backend real
    with st.chat_message("assistant"):
        with st.spinner("Pensando con Llama 3.3 70B..."):
            # Consumimos la lógica real de tu agente local
            respuesta = ejecutar_agent_loop(prompt)
            st.markdown(respuesta)
            
    # Incrementar el contador de consultas únicamente tras una ejecución exitosa
    st.session_state.contador_consultas += 1
            
    # Guardar la respuesta obtenida en el historial
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    
    # Mostrar el estado de consultas consumidas de forma elegante
    st.caption(f"Consultas usadas: {st.session_state.contador_consultas}/{LIMITE_CONSULTAS}")