from dotenv import load_dotenv
load_dotenv()
import time
import streamlit as st
st.set_page_config(page_title="Agente DevOps OCI", page_icon="🤖", layout="centered")
# 1. Importamos los prompts puros
from prompts import PROMPT_FOROHUB, PROMPT_LANGCHAIN_MIGRATOR, PROMPT_RAG_OPTIMIZER, ROUTER_PROMPT_TEMPLATE
# 2. Importamos la función de carga de datos cacheada
from config import cargar_conectores_de_datos, inicializar_modelos, buscador_web
# 3. Inicializamos las variables de datos de forma global y segura
retriever_rag, CONTEXTO_FOROHUB_TXT = cargar_conectores_de_datos()
llm_router, llm_gemini, llm_mistral_code, llm_deepseek_rag = inicializar_modelos()
from streamlit_cookies_controller import CookieController
import os
import oracledb

# Inicializamos el controlador de cookies
controller = CookieController()

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (OCI) - AUDITORÍA DEL RAG
# ==============================================================================
@st.cache_resource
def obtener_conexion_db():
    """
    Centraliza la conexión a Oracle Cloud en modo Thin de forma persistente.
    """
    try:
        user = os.getenv("OCI_DB_USER")
        password = os.getenv("OCI_DB_PASSWORD")
        dsn = os.getenv("OCI_DB_DSN")
        ruta_wallet = os.getenv("TNS_ADMIN", "/app/Wallet_forohubdb2")        
        wallet_password = os.getenv("OCI_WALLET_PASSWORD")
        
        return oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
            port=1522,
            config_dir=ruta_wallet,
            wallet_location=ruta_wallet,
            wallet_password=wallet_password  # Ahora es 100% dinámica
        )
    except Exception as e:
        print(f"❌ Error crítico al obtener conexión DB: {e}")
        return None

# 2. SEGUNDO: CORREMOS EL BLOQUE DE TELEMETRÍA (Ahora sí encuentra la función)
try:
    conexion_telemetria = obtener_conexion_db()
    
    if conexion_telemetria:
        # IMPORTANTE: NO pongas conexion_telemetria.close() acá.
        # Si la cerrás, los componentes de Streamlimt que corren milisegundos después
        # se van a quedar sin conexión y lanzarán el DPY-1001.
        print("🖥️ [Sistema] Telemetría validada en OCI con éxito en modo Thin.")
    else:
        print("⚠️ [Sistema] No se pudo establecer la conexión inicial de telemetría.")

except Exception as e:
    print(f"Error de configuración en el arranque de telemetría: {e}")


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
st.text_input(
    "Confirm Your Email Address", 
    placeholder="Confirm Your Email Address", 
    key="email_confirm", 
    label_visibility="collapsed"
)

# El CSS busca el input exacto por su placeholder o su ID de componente y oculta sus contenedores superiores
st.markdown(
    """
    <style>
    /* 1. Apunta al contenedor del componente de texto que contiene nuestro input clave */
    div[data-testid="stTextInput"]:has(input[placeholder="Confirm Your Email Address"]),
    div[data-testid="stTextInput"]:has(#email_confirm) {
        display: none !important;
        visibility: hidden !important;
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

prompt = st.chat_input("Escribe tu consulta aquí / Type your technical query here...")

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
                    # ✅ CORREGIDO: Ahora sí invoca a Mistral si Gemini se cae
                    nombre_agente = "Agente Foro Hub (Contingencia - Mistral)"
                    st.caption("🔄 Reenrutando consulta al agente de contingencia por alta demanda...")
                    respuesta_final = llm_mistral_code.invoke(mensajes).content
        
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
        
       # ========================================================
# 🤖 AGENTE 3: RAG OPTIMIZER (Migrado a Oracle Cloud 23ai Vector DB)
# ========================================================
        else:
            nombre_agente = "Agente Arquitecto RAG (OCI Vector DB + DeepSeek)"
            
            # Importamos la función que creamos en tu backend para consultar OCI
            from agent_backend import buscar_en_oracle_vector
            
            with st.spinner("Buscando de forma semántica en Oracle Cloud (OCI)..."):
                # Recuperamos los chunks semánticos directo de OCI pasándole el prompt
                contexto_vectorial = buscar_en_oracle_vector(prompt, top_k=3)
            
            with st.spinner("Analizando arquitectura..."):
                mensajes = [
                    ("system", f"{PROMPT_RAG_OPTIMIZER}\n{recordatorio_idioma}"),
                    ("human", f"Context:\n{contexto_vectorial}\nUser: {prompt}\n{recordatorio_idioma}")
                ]
                try:
                    respuesta_final = llm_deepseek_rag.invoke(mensajes).content
                except Exception as e:
                    # 🔄 Activación AI de Refuerzo (Se mantiene intacto por seguridad)
                    nombre_agente = "Agente Arquitecto RAG (Refuerzo - Mistral Large)"
                    st.caption("⚠️ El modelo RAG principal no responde. Activando AI de refuerzo (Mistral)...")
                    respuesta_final = llm_mistral_code.invoke(mensajes).content
        # ==============================================================================
        # Paso C.2: Guarda de Idioma Post-Procesamiento (Garantía de salida unificada)
        # ==============================================================================
        # 📋 Definimos la lista ACÁ AFUERA con espacios limpios para evitar falsos positivos
        indicadores_ingles = [" the ", "this ", " we can ", "instead of ", "here is ", "however "]

        if respuesta_final and ("ESPAÑOL" in recordatorio_idioma.upper() or "SPANISH" in recordatorio_idioma.upper()):
            
            # Buscamos minúsculas y agregamos espacios en los extremos del texto para matchear palabras sueltas
            texto_analizar = f" {respuesta_final.lower()} "
            if any(indicador in texto_analizar for indicador in indicadores_ingles):
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
                        # ✅ CORREGIDO: Se agregó .content para extraer la cadena de texto limpia de Mistral
                        respuesta_final = llm_mistral_code.invoke(prompt_corrector).content

        # ==============================================================================
        # Paso D: Renderizar respuesta, persistir en OCI y guardar en el historial
        # ==============================================================================
        if respuesta_final:
            # 1. Mostramos la burbuja en pantalla inmediatamente para que el usuario la vea
            st.markdown(respuesta_final)
            st.caption(f"🤖 Realizado por: {nombre_agente}")
            
            # 2. Guardamos de forma persistente en la lista de mensajes local
            st.session_state.messages.append({
                "role": "assistant", 
                "content": respuesta_final, 
                "agent": nombre_agente
            })
            
            # 🗄️ PERSISTENCIA EN TU TABLA OPERATIVA DE OCI
            try:
                # Abrimos conexión usando la Wallet
                conn_oci = obtener_conexion_db() 
                if conn_oci:
                    cursor_oci = conn_oci.cursor()
                    
                    sql_telemetria = """
                        INSERT INTO TELEMETRIA_AGENTES 
                        (PROMPT_USUARIO, AGENTE_ASIGNADO, DECISION_ROUTER, LONGITUD_RESPUESTA) 
                        VALUES (:1, :2, :3, :4)
                    """
                    
                    # Insertamos la telemetría del RAG sin tocar nada del Foro
                    cursor_oci.execute(sql_telemetria, [
                        prompt, 
                        nombre_agente, 
                        decision, 
                        len(respuesta_final)
                    ])
                    
                    conn_oci.commit()
                    cursor_oci.close()
                    conn_oci.close()
            except Exception as e:
                # Si parpadea la red, el chat sigue andando y te avisa en la terminal
                print(f"Error de persistencia en telemetría OCI: {e}")
            
            # 3. Forzamos la recarga de la interfaz para refrescar el contador visual
            st.rerun()