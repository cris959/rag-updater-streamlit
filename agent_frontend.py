from dotenv import load_dotenv
load_dotenv()
import time
import streamlit as st
st.set_page_config(page_title="Agente DevOps OCI", page_icon="🤖", layout="centered")
# 1. Importamos los prompts puros
from prompts import PROMPT_FOROHUB, PROMPT_LANGCHAIN_MIGRATOR, PROMPT_RAG_OPTIMIZER, ROUTER_PROMPT_TEMPLATE
# 2. Importamos la función de carga de datos cacheada
#from config import cargar_conectores_de_datos, inicializar_modelos, obtener_router_chain
from config import cargar_conectores_de_datos, inicializar_modelos, buscador_web
# 3. Inicializamos las variables de datos de forma global y segura
retriever_rag, CONTEXTO_FOROHUB_TXT = cargar_conectores_de_datos()
llm_router, llm_gemini, llm_mistral_code, llm_deepseek_rag = inicializar_modelos()
from streamlit_cookies_controller import CookieController

# Inicializamos el controlador de cookies
controller = CookieController()

LIMITE_CONSULTAS = 5
# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA DE STREAMLIT (Debe ir primero)
# ==============================================================================

with st.sidebar:
   # st.title("🤖 Centro de Operaciones Multi-Agente")
    st.subheader("Desarrollado por Christian Dev")
    
    st.markdown("### ⚙️ Configuración Global")
    # ESTE ES EL PUNTO 1 MODIFICADO:
    idioma_seleccionado = st.radio(
        "Idioma de respuesta de los Agentes:",
        options=["Español", "English"],
        index=0  # Hace que arranque seleccionado en Español por defecto
    )
    st.divider()
    
st.title("🤖 Panel de Control Multi-Agente")
# 🛡️ COMIENZO DEL ENVOLTORIO OCULTO PARA EL HONEYPOT
  # 🛡️ Crear el Honeypot de forma nativa e invisible
ocultador = st.empty()
with ocultador:
    st.text_input("Confirm Your Email Address", key="email_confirm", label_visibility="collapsed")

# Forzamos la desaparición total del contenedor por CSS
st.markdown(
    """
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"]:has(input[key="email_confirm"]),
    div[data-testid="element-container"]:has(input[type="text"]) {
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 🛡️ FIN DEL HONEYPOT
# ==============================================================================
# INDICADOR VISUAL DE INTENTOS DISPONIBLES
# ==============================================================================
# Calculamos los intentos que le quedan al usuario
consultas_actuales = st.session_state.get("contador_consultas", 0)
intentos_restantes = max(0, LIMITE_CONSULTAS - consultas_actuales)

# Diseñamos un contenedor visual limpio con columnas
col_titulo, col_metric = st.columns([3, 1])

with col_metric:
    if intentos_restantes > 2:
        st.metric(label="Intentos disponibles", value=f"{intentos_restantes}/{LIMITE_CONSULTAS}")
    elif intentos_restantes > 0:
        st.metric(label="⚠️ ¡Últimos intentos!", value=f"{intentos_restantes}/{LIMITE_CONSULTAS}")
    else:
        st.metric(label="🚫 Límite agotado", value="0")
# ==============================================================================
# 4. INICIALIZACIÓN DEL HISTORIAL Y CUOTAS (POR COOKIE PARA OCI)
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Leemos la cookie del navegador del usuario
cookie_contador = controller.get("contador_usuario")

if "contador_consultas" not in st.session_state:
    if cookie_contador is not None:
        st.session_state.contador_consultas = int(cookie_contador)
    else:
        st.session_state.contador_consultas = 0

# 📋 DIBUJAR HISTORIAL (Asegurate de tener este bloque justo acá abajo)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("agent"):
            st.caption(f"🤖 Realizado por: {msg['agent']}")

# ==============================================================================
# 5. PIPELINE DE PROCESAMIENTO MULTI-AGENTE
# ==============================================================================

prompt = st.chat_input("Escribe tu consulta técnica aquí...")

if prompt:
    # 🛑 VALIDACIÓN 1: Verificación del Honeypot (Seguridad perimetral anti-bots)
    if st.session_state.get("email_confirm", "") != "":
        st.warning("Acceso denegado de forma preventiva.")
        time.sleep(2)
        st.stop()

    # ⏱️ VALIDACIÓN 2: Check redundante de cuotas
    if st.session_state.get("contador_consultas", 0) >= LIMITE_CONSULTAS:
        st.error("Has alcanzado el límite de consultas permitidas.")
        st.stop()
   
   # 📈 INCREMENTO INMEDIATO Y PERSISTENCIA EN EL NAVEGADOR
    st.session_state.contador_consultas = st.session_state.get("contador_consultas", 0) + 1
    
    # Guardamos la cookie en el cliente (dura viva la sesión actual)
    controller.set("contador_usuario", st.session_state.contador_consultas)
        

    # Pintar el input en la UI si pasa los filtros
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
   
    # Procesamiento del Asistente
    with st.chat_message("assistant"):
        respuesta_final = ""
        nombre_agente = ""

        # Paso A: Enrutamiento inteligente
        with st.spinner("Enrutando consulta de forma inteligente..."):
            try:
                # Armamos el mensaje para el router usando el prompt de prompts.py
                mensajes_router = [
                    ("system", ROUTER_PROMPT_TEMPLATE),
                    ("human", f"Idioma: {idioma_seleccionado}\nConsulta: {prompt}")
                ]
                decision = llm_router.invoke(mensajes_router).content.strip().upper()
            except Exception as e:
                # FALLBACK: Si Gemini 503 saturado, asumimos RAG o un agente por defecto
                st.caption("⚠️ El enrutador principal está saturado. Rebalanceando carga automáticamente...")
                decision = "RAG"  # Contingencia por si falla el router

        # Paso B: Configurar recordatorio de idioma nativo
        if idioma_seleccionado == "English":
            recordatorio_idioma = "\n[CRITICAL ORDER]: You must write 100% of your response in ENGLISH."
        else:
            recordatorio_idioma = "\n[ORDEN CRÍTICA]: Debes escribir el 100% de tu respuesta en ESPAÑOL. Está prohibido el Inglés."

        # ==============================================================================
        # Paso C: Ejecución del agente especialista seleccionado (Con AI de Refuerzo)
        # ==============================================================================
        # 🤖 AGENTE 1: FOROHUB (Principal: Gemini -> Refuerzo: Mistral)
        if "FOROHUB" in decision:
            nombre_agente = "Agente Foro Hub e Infraestructura Cloud (Gemini 2.5 Flash)"
            with st.spinner("Consultando contexto local..."):
                prompt_sistema_inyectado = PROMPT_FOROHUB.format(contexto_local=CONTEXTO_FOROHUB_TXT)
                mensajes = [
                    ("system", f"{prompt_sistema_inyectado}\n{recordatorio_idioma}"),
                    ("human", f"{prompt}\n{recordatorio_idioma}")
                ]
                try:
                    respuesta_final = llm_gemini.invoke(mensajes).content
                except Exception:
                    # FALLBACK DE EMERGENCIA: Si Gemini cae, responde Mistral
                    nombre_agente = "Agente Foro Hub (Contingencia - Mistral)"
                    st.caption("🔄 Reenrutando consulta al agente de contingencia por alta demanda...")
                respuesta_final = llm_gemini.invoke(mensajes).content
        
        # 🤖 AGENTE 2: MIGRATOR (Principal: Mistral -> Refuerzo: Gemini)
        elif "MIGRATOR" in decision:
            nombre_agente = "Agente LangChain Migrator (Buscador Web + Mistral Large)"
            with st.spinner("Buscando en documentación viva de LangChain..."):
                try:
                  contexto_internet = buscador_web.invoke(prompt)
                except Exception as e:
                    contexto_internet = f"No se pudo obtener datos recientes: {str(e)}"    
            with st.spinner("Refactorizando sintaxis..."):
                mensajes = [
                    ("system", f"{PROMPT_LANGCHAIN_MIGRATOR}\n{recordatorio_idioma}"),
                    ("human", f"Web data: {contexto_internet}\nUser: {prompt}\n{recordatorio_idioma}")
                ]
                try:
                 respuesta_final = llm_mistral_code.invoke(mensajes).content
                except Exception as e:
                    # Activación AI de Refuerzo
                    nombre_agente = "Agente LangChain Migrator (Refuerzo - Gemini 2.5)"
                    st.caption("⚠️ Mistral experimenta alta demanda. Activando AI de refuerzo (Gemini)...")
                    respuesta_final = llm_gemini.invoke(mensajes).content
        
        # 🤖 AGENTE 3: RAG OPTIMIZER (Principal: DeepSeek/Qwen -> Refuerzo: Mistral)
        else:
            nombre_agente = "Agente Arquitecto RAG (FAISS + Qwen)"
            if retriever_rag:
                with st.spinner("Buscando en la base vectorial RAG..."):
                    docs = retriever_rag.invoke(prompt)
                    contexto_vectorial = "\n\n".join([d.page_content for d in docs])
                with st.spinner("Analizando arquitectura..."):
                    mensajes = [
                        ("system", f"{PROMPT_RAG_OPTIMIZER}\n{recordatorio_idioma}"),
                        ("human", f"Context: {contexto_vectorial}\nUser: {prompt}\n{recordatorio_idioma}")
                    ]
                    try:
                      respuesta_final = llm_deepseek_rag.invoke(mensajes).content
                    except Exception as e:
                        # 🔄 Activación AI de Refuerzo
                        nombre_agente = "Agente Arquitecto RAG (Refuerzo - Mistral Large)"
                        st.caption("⚠️ El modelo RAG principal no responde. Activando AI de refuerzo (Mistral)...")
                        respuesta_final = llm_mistral_code.invoke(mensajes).content
            else:
                respuesta_final = "⚠️ Sistema: La base de datos vectorial local para el Agente RAG no está disponible."
      
        # ==============================================================================
        # Paso C.2: Guarda de Idioma Post-Procesamiento (Garantía de salida unificada)
        # ==============================================================================
        # 📋 Definimos la lista ACÁ AFUERA. Así existe SIEMPRE, elijas inglés o español.
        indicadores_ingles = ["the ", "this ", "we can ", "instead of ", "here is ", "however"]

        if respuesta_final and ("ESPAÑOL" in recordatorio_idioma.upper() or "SPANISH" in recordatorio_idioma.upper()):
            
            if any(indicador in respuesta_final.lower() for indicador in indicadores_ingles):
                with st.spinner("Refinando traducción de la narrativa técnica..."):
                    prompt_corrector = [
                        ("system", (
                            "Actúas como un traductor y refinador técnico de software profesional. "
                            "Tu única tarea es tomar la respuesta proporcionada y asegurarte de que TODA la explicación, "
                            "narrativa, comentarios y texto estén estrictamente en ESPAÑOL. "
                            "CRÍTICO: No traduzcas código fuente, palabras clave de lenguajes (if, public, class, etc.), "
                            "nombres de librerías ni rutas. Solo traduce la explicación que los rodea para que sea 100% en español.\n\n"
                            "⚠️ REGLA DE SALIDA ABSOLUTA: Devuelve ÚNICAMENTE el texto técnico corregido final. "
                            "No agregues introducciones, no expliques qué cambiaste, no digas 'aquí está la respuesta', "
                            "ni des notas de aprobación. Si no hay nada que corregir, devuelve el texto original idéntico, "
                            "sin una sola palabra extra."
                        )),
                        ("human", f"Respuesta a corregir:\n\n{respuesta_final}")
                    ]
                    try:
                        respuesta_final = llm_gemini.invoke(prompt_corrector).content
                    except Exception:
                        respuesta_final = llm_mistral_code.invoke(prompt_corrector).content

        # ==============================================================================
        # Paso D: Renderizar respuesta y guardar en el historial con su metadata
        # ==============================================================================
        if respuesta_final:
            # 1. Mostramos la burbuja en pantalla inmediatamente para que el usuario la vea
            st.markdown(respuesta_final)
            st.caption(f"🤖 Realizado por: {nombre_agente}")
            
            # 2. Guardamos de forma persistente en la lista de mensajes
            st.session_state.messages.append({
                "role": "assistant", 
                "content": respuesta_final, 
                "agent": nombre_agente
            })
            
            # 3. Forzamos la recarga de la interfaz para refrescar el contador visual
            #    después de haber modificado todo el estado de la sesión de forma segura.
            st.rerun()