import streamlit as st
from agent_backend import ejecutar_agent_loop

# Configuración de la página de Streamlit
st.set_page_config(page_title="Agente DevOps OCI", page_icon="🤖", layout="centered")

st.title("🤖 Agente de Infraestructura & Foro Hub")
st.subheader("Entorno de desarrollo local (Christian Dev)")

# Inicializar el historial de chat en la sesión si no existe
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar los mensajes anteriores del historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar la entrada del usuario
if prompt := st.chat_input("¿Qué querés consultar sobre Nginx, OCI o Foro Hub?"):
    # Mostrar el mensaje del usuario en la UI
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generar la respuesta llamando al backend híbrido
    with st.chat_message("assistant"):
        with st.spinner("Pensando con Llama 3.3 70B..."):
            respuesta = ejecutar_agent_loop(prompt)
            st.markdown(respuesta)
            
    # Guardar la respuesta en el historial
    st.session_state.messages.append({"role": "assistant", "content": respuesta})