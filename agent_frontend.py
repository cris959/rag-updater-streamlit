import os
import time
import streamlit as st

# Integraciones de Modelos de Lenguaje (LLMs)
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Componentes Core de LangChain (LCEL)
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool

# Almacenamiento Vectorial (FAISS) e Inyección de Entorno
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from duckduckgo_search import DDGS

load_dotenv()

# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA DE STREAMLIT (Debe ir primero)
# ==============================================================================
# st.set_page_config(page_title="Agente DevOps OCI", page_icon="🤖", layout="centered")

# st.title("🤖 Centro de Operaciones Multi-Agente")
# st.subheader("Entorno de desarrollo local (Christian Dev)")

# # Subtítulo corregido con formato limpio y banderas descriptivas
# st.caption("🌐 **Soporte Bilingüe Activo:** Puedes realizar tus consultas y pasar código tanto en **Español** 🇦🇷🇪🇸 como en **Inglés** 🇺🇸🇬🇧.")

with st.sidebar:
    st.title("🤖 Centro de Operaciones Multi-Agente")
    st.subheader("Desarrollado por Christian Dev")
    
    st.markdown("### ⚙️ Configuración Global")
    # ESTE ES EL PUNTO 1 MODIFICADO:
    idioma_seleccionado = st.radio(
        "Idioma de respuesta de los Agentes:",
        options=["Español", "English"],
        index=0  # Hace que arranque seleccionado en Español por defecto
    )
    st.divider()

# ==============================================================================
# 2. INICIALIZACIÓN DE MODELOS E INFRAESTRUCTURA DE IA
# ==============================================================================
# Router Orquestador (Groq - Llama 3 - Ultra Veloz y Determinista)
llm_router = ChatGroq(
    model="llama-3.1-8b-instant", 
    groq_api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.0
)

# Agente 1: Foro Hub & OCI (Google Gemini - Contexto Técnico RAG)
llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0.0
)

# Agente 2: Especialista en Código y Sintaxis (Mistral Large - Alta Capacidad de Lógica)
llm_mistral_code = ChatMistralAI(
    model="mistral-large-latest", 
    api_key=os.environ.get("MISTRAL_API_KEY"),
    temperature=0.1
)

# Agente 3: Arquitecto RAG Avanzado (Groq - DeepSeek con Razonamiento Crítico)
llm_deepseek_rag = ChatGroq(
    model="qwen/qwen3-32b", #meta-llama/llama-4-scout-17b-16e-instruct
    groq_api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.0
)

# ==============================================================================
# 3. CONFIGURACIÓN DE CONECTORES DE DATOS Y HERRAMIENTAS VIVAS
# ==============================================================================
# Herramienta de Internet para el Agente 2 (Sintaxis nativa y estable)
@tool
def buscador_web(query: str) -> str:
    """Busca información en tiempo real en internet usando DuckDuckGo. 
    Útil para responder preguntas sobre actualidad, errores de código recientes o soporte técnico."""
    try:
        with DDGS() as ddgs:
            # Realiza la búsqueda utilizando la nueva API de la librería
            resultados = list(ddgs.text(query, max_results=5))
            if not resultados:
                return "No se encontraron resultados en internet para esa consulta."
            
            # Formateamos una respuesta estructurada y limpia para el contexto del agente
            lineas = []
            for r in resultados:
                lineas.append(f"Título: {r.get('title')}\nEnlace: {r.get('href')}\nResumen: {r.get('body')}\n---")
            return "\n".join(lineas)
    except Exception as e:
        return f"Error al conectar con el motor de búsqueda: {str(e)}"

# Conector a la Base Vectorial indexada mes a mes para el Agente 3
embeddings_service = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=os.environ.get("GEMINI_API_KEY")
)

# Nombre técnico y limpio para el almacén de vectores
RUTA_VECTOR_DB = "./data/rag_knowledge_base"

if os.path.exists(os.path.join(RUTA_VECTOR_DB, "index.faiss")):
    vector_store = FAISS.load_local(
        RUTA_VECTOR_DB, 
        embeddings_service, 
        allow_dangerous_deserialization=True # Requerido por seguridad en FAISS local
    )
    retriever_rag = vector_store.as_retriever(search_kwargs={"k": 4})
else:
    retriever_rag = None

# Carga de la base de conocimientos estática de Foro Hub (Agente 1)
try:
    with open("contexto_infraestructura.txt", "r", encoding="utf-8") as f:
        CONTEXTO_FOROHUB_TXT = f.read()
except FileNotFoundError:
    CONTEXTO_FOROHUB_TXT = "Error de Sistema: No se encontró 'contexto_infraestructura.txt'."

# ==============================================================================
# 4. DEFINICIÓN REESTRUCTURADA DE PROMPTS DEL SISTEMA
# ==============================================================================
PROMPT_FOROHUB = f"""Eres el Agente Experto en la Infraestructura y Sistema de Foro Hub.
Asistes de manera directa al desarrollador Christian (Christian Dev) en la gestión de su backend.

REGLA ABSOLUTA DE GENERACIÓN:
1. Identifica el idioma de la consulta en la sección [REQUERIMIENTO DEL DESARROLLADOR]. Si Christian escribe en Español, responde el 100% en Español. Si escribe en Inglés, responde el 100% en Inglés.
2. Queda terminantemente PROHIBIDO usar respuestas híbridas o spanglish. Si la base de conocimientos provista abajo contiene directivas o logs en Inglés, tradúcelas o adáptalas al idioma de la respuesta actual (la sintaxis nativa de Java/Spring Boot o comandos Bash lógicamente se mantiene).
3. Sé conciso, técnico y directo al código o comandos de consola.

[BASE DE CONOCIMIENTOS DE INFRAESTRUCTURA]:
{CONTEXTO_FOROHUB_TXT}"""

PROMPT_LANGCHAIN_MIGRATOR = """Eres el Agente Especialista en Actualizaciones de LangChain y Python. Tu tarea es tomar la consulta y el código del usuario, combinarlos con la información externa y estructurar una solución moderna (LangChain v0.2/v0.3+).

REGLA ABSOLUTA DE GENERACIÓN:
1. Responde de manera estrictamente MONOLINGÜE basándote en el idioma detectado en [REQUERIMIENTO DEL DESARROLLADOR].
2. Si el usuario consulta en Español, toda la explicación teórica, la justificación de los cambios y los comentarios del código DEBEN escribirse exclusivamente en Español. No dejes párrafos explicativos en Inglés bajo ninguna circunstancia.
3. Si consulta en Inglés, genera absolutamente todo en Inglés.
4. Reemplaza arquitecturas obsoletas (como LLMChain) por cadenas LCEL (usando el operador pipe |) y corrige módulos movidos a langchain-core o langchain-community."""

PROMPT_RAG_OPTIMIZER = """Eres el Agente de Optimización de Arquitecturas RAG y Bases Vectoriales. Tu rol es analizar la consulta de Christian Dev contrastándola con la documentación técnica oficial almacenada en tu base de datos indexada.

REGLA ABSOLUTA DE GENERACIÓN:
1. Identifica el idioma de la pregunta del usuario dentro del bloque [REQUERIMIENTO DEL DESARROLLADOR].
2. Si la pregunta está en Español, escribe el 100% de tu respuesta en Español. Si el contexto técnico de los documentos inyectados contiene fragmentos o términos en Inglés, TRADÚCELOS o explícalos en Español dentro de tu desarrollo. Está estrictamente PROHIBIDO alternar párrafos en idiomas distintos.
3. Si la pregunta está en Inglés, escribe el 100% de tu respuesta en Inglés, traduciendo cualquier concepto que provenga de documentos en Español.
4. Usa tu capacidad de razonamiento crítico para desglosar paso a paso (Chain of Thought) estrategias de fragmentación, embeddings y rendimiento de FAISS."""

# ==============================================================================
# 5. CONFIGURACIÓN DEL ENRUTADOR DINÁMICO (ROUTER)
# ==============================================================================
ROUTER_PROMPT_TEMPLATE = """Analiza detalladamente la consulta del usuario y clasifícala en una de las tres categorías técnicas disponibles.

Regla de oro: Responde ÚNICAMENTE con la palabra clave de la categoría en mayúsculas (FOROHUB, MIGRATOR o OPTIMIZER). No agregues puntos, saludos, explicaciones ni formato markdown. Solo la palabra.

Consulta del usuario: "{query}"

Guía de Clasificación:

Responde 'FOROHUB' si la consulta se refiere a: Foro Hub, Spring Boot, Java 21, JPA, Hibernate, API REST, endpoints de la app, base de datos Oracle (23ai/26ai), carpetas wallet, servidores OCI, Ubuntu, Nginx, scripts de Bash (.sh) o logs del foro.
Responde 'MIGRATOR' si la consulta incluye fragmentos de código de Python, errores de ejecución, advertencias de obsolescencia (DeprecationWarnings) o preguntas sobre cómo actualizar la sintaxis vieja de LangChain a versiones modernas de la librería.
Responde 'OPTIMIZER' si la consulta es conceptual o práctica sobre el diseño de sistemas RAG, estrategias de fragmentación (chunking semántico o de tamaño fijo), embeddings, bases de datos vectoriales (Chroma, PGVector), recuperación avanzada o métricas de búsqueda vectoriales.
Categoría asignada:"""

router_prompt = PromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE) 
router_chain = router_prompt | llm_router | StrOutputParser()

# ==============================================================================
# 6. CAPA DE SEGURIDAD, POLÍTICAS DE SESIÓN Y LÍMITES
# ==============================================================================
LIMITE_CONSULTAS = 5

if "contador_consultas" not in st.session_state: st.session_state.contador_consultas = 0

if "messages" not in st.session_state: st.session_state.messages = []

# Detener ejecución temprana SI Y SÓLO SI superó las cuotas
if st.session_state.contador_consultas >= LIMITE_CONSULTAS: 
    st.error(f"⚠️ Has alcanzado el límite de {LIMITE_CONSULTAS} consultas por sesión.")
    st.info("Por favor, regresa más tarde o reinicia la aplicación.") 
    st.stop()

# ==============================================================================
# 7. INTERFAZ GRÁFICA DE USUARIO (CON TRAMPA HONEYPOT INTEGRADA)
# ==============================================================================
tab_principal, tab_sistema = st.tabs(["💬 Chat Multi-Agente", " "])

with tab_principal: # Renderizado del historial persistente en la sesión for message in st.session_state.messages: with st.chat_message(message["role"]): st.markdown(message["content"])

# Captura de prompts del usuario
 if prompt := st.chat_input("¿Qué querés resolver hoy? 🇦🇷 / What do you want to solve today? 🇺🇸"):
    
    # VALIDACIÓN 1: Verificación del Honeypot (Seguridad perimetral anti-bots)
    if st.session_state.get("email_confirm", "") != "":
        st.warning("Acceso denegado de forma preventiva.")
        time.sleep(2)
        st.stop()

    # VALIDACIÓN 2: Check redundante de cuotas
    if st.session_state.contador_consultas >= LIMITE_CONSULTAS:
        st.stop()

    # Pintar el input en la UI
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

 # --- PIPELINE DE LOGICA DE MULTI-AGENTE ---
    with st.chat_message("assistant"):
        
        # Paso 1: El Router clasifica la consulta en milisegundos
        with st.spinner("Enrutando consulta de forma inteligente..."):
            decision = router_chain.invoke({"query": prompt}).strip()

        # Configuración INFALIBLE basada en el botón seleccionado por Christian
        if idioma_seleccionado == "English":
            recordatorio_idioma = "ORDER: You must write 100% of your response in ENGLISH. Translate any internal data if needed."
        else:
            recordatorio_idioma = "ORDEN ESTRICTA: Debes escribir el 100% de tu respuesta en ESPAÑOL. Traduce cualquier dato interno al español."

        # Paso 2: Ejecución según el agente especialista asignado
        if "FOROHUB" in decision:
            nombre_agente = "Agente Foro Hub e Infraestructura Cloud (Gemini 2.5 Flash)"
            with st.spinner(f"Consultando contexto local con {nombre_agente}..."):
                prompt_combinado = (
                    f"[REQUERIMIENTO DEL DESARROLLADOR]\n{prompt}\n\n"
                    f"[INSTRUCCIÓN DE SALIDA OBLIGATORIA]\n{recordatorio_idioma}"
                )
                mensajes = [("system", PROMPT_FOROHUB), ("human", prompt_combinado)]
                respuesta_final = llm_gemini.invoke(mensajes).content
        
        elif "MIGRATOR" in decision:
            nombre_agente = "Agente LangChain Migrator (Buscador Web + Mistral Large)"
            with st.spinner("Buscando actualizaciones en la documentación viva de LangChain..."):
                contexto_internet = buscador_web.run(f"site:python.langchain.com {prompt}")
            
            with st.spinner(f"Refactorizando sintaxis con {nombre_agente}..."):
                prompt_combinado = (
                    f"[INFORMACIÓN EN VIVO DESDE INTERNET]\n{contexto_internet}\n\n"
                    f"[REQUERIMIENTO DEL DESARROLLADOR]\n{prompt}\n\n"
                    f"[INSTRUCCIÓN DE SALIDA OBLIGATORIA]\n{recordatorio_idioma}"
                )
                mensajes = [("system", PROMPT_LANGCHAIN_MIGRATOR), ("human", prompt_combinado)]
                respuesta_final = llm_mistral_code.invoke(mensajes).content
        
        else:
            nombre_agente = "Agente Arquitecto RAG (FAISS + Qwen)"
            if retriever_rag:
                with st.spinner("Buscando en la base de datos vectorial actualizada de RAG..."):
                    docs_vectoriales = retriever_rag.invoke(prompt)
                    contexto_vectorial = "\n\n".join([doc.page_content for doc in docs_vectoriales])
                
                with st.spinner(f"Analizando arquitectura con {nombre_agente}..."):
                    prompt_combinado = (
                        f"[DOCUMENTACIÓN DE SOPORTE INDEXADA]\n{contexto_vectorial}\n\n"
                        f"[REQUERIMIENTO DEL DESARROLLADOR]\n{prompt}\n\n"
                        f"[INSTRUCCIÓN DE SALIDA OBLIGATORIA]\n{recordatorio_idioma}"
                    )
                    mensajes = [("system", PROMPT_RAG_OPTIMIZER), ("human", prompt_combinado)]
                    respuesta_final = llm_deepseek_rag.invoke(mensajes).content
            else:
                respuesta_final = "⚠️ Sistema: La base de datos vectorial local para el Agente RAG está vacía en `./data/rag_knowledge_base`. Por favor, inicialízala o ejecuta el script de actualización mensual."

        # Desplegar resultado final en pantalla
        st.markdown(respuesta_final)
        st.caption(f"*Procesado por: {nombre_agente}*")
        
        # Guardar estados y aumentar métricas
        st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
        st.session_state.contador_consultas += 1
        st.caption(f"Consultas usadas en la sesión: {st.session_state.contador_consultas}/{LIMITE_CONSULTAS}")