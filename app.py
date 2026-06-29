import streamlit as st
# Corregido: Importamos la función con su nuevo nombre agéntico
from agent_backend import ejecutar_agent_loop
#from agent_backend import ejecutar_agente_hibrido

# Configuración de la página web
st.set_page_config(page_title="RAG Agéntico Híbrido", page_icon="🤖", layout="centered")

st.title("🤖 Asistente RAG Experto")
# Corregido: Usamos subheader en lugar de subtitle
st.subheader("Búsqueda Inteligente: FAISS Local + Internet")
st.markdown("---")

# 1. Inicializar la memoria de la conversación en Local (Session State)
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# 2. Renderizar los mensajes del historial en la pantalla
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# 3. Caja de entrada de texto para el usuario
if pregunta_usuario := st.chat_input("Escribí tu consulta técnica aquí..."):
    
    # Mostrar el mensaje del usuario de inmediato
    with st.chat_message("user"):
        st.markdown(pregunta_usuario)
    
    # Guardarlo en la memoria local de la sesión
    st.session_state.mensajes.append({"role": "user", "content": pregunta_usuario})
    
    # Llamar al backend para procesar la respuesta con Llama 3.3
    with st.chat_message("assistant"):
        with st.spinner("Pensando y consultando fuentes..."):
            respuesta_agente = ejecutar_agent_loop(pregunta_usuario)
            st.markdown(respuesta_agente)
            
    # Guardar la respuesta del asistente en la memoria local
    st.session_state.mensajes.append({"role": "assistant", "content": respuesta_agente})