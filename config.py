# config.py
# ==============================================================================
# CONFIGURACIÓN E INICIALIZACIÓN DE MODELOS E INFRAESTRUCTURA DE IA
# Desarrollado por Christian Dev
# ==============================================================================

import os
import streamlit as st
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI

# ==============================================================================
# 1. HERRAMIENTAS VIVAS (Buscador Web)
# ==============================================================================
@tool
def buscador_web(query: str) -> str:
    """Busca información en tiempo real en internet usando DuckDuckGo. 
    Útil para responder preguntas sobre actualidad, errores de código recientes o soporte técnico."""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=5))
            if not resultados:
                return "No se encontraron resultados en internet para esa consulta."
            
            lineas = []
            for r in resultados:
                lineas.append(f"Título: {r.get('title')}\nEnlace: {r.get('href')}\nResumen: {r.get('body')}\n---")
            return "\n".join(lineas)
    except Exception as e:
        return f"Error al conectar con el motor de búsqueda: {str(e)}"


# ==============================================================================
# 2. CONECTORES DE DATOS (FAISS RAG y Contexto Estático)
# ==============================================================================
@st.cache_resource
def cargar_conectores_de_datos():
    """Inicializa los servicios de embeddings, carga la base vectorial FAISS 
    y lee el contexto local de Foro Hub de manera eficiente."""
    
    embeddings_service = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.environ.get("GEMINI_API_KEY")
    )

    RUTA_VECTOR_DB = "./data/rag_knowledge_base"

    if os.path.exists(os.path.join(RUTA_VECTOR_DB, "index.faiss")):
        vector_store = FAISS.load_local(
            RUTA_VECTOR_DB, 
            embeddings_service, 
            allow_dangerous_deserialization=True
        )
        retriever_rag = vector_store.as_retriever(search_kwargs={"k": 4})
    else:
        retriever_rag = None

    try:
        with open("contexto_infraestructura.txt", "r", encoding="utf-8") as f:
            CONTEXTO_FOROHUB_TXT = f.read()
    except FileNotFoundError:
        CONTEXTO_FOROHUB_TXT = "Error de Sistema: No se encontró 'contexto_infraestructura.txt'."
        
    return retriever_rag, CONTEXTO_FOROHUB_TXT


# ==============================================================================
# 3. INICIALIZACIÓN CENTRALIZADA DE LLMs
# ==============================================================================
@st.cache_resource
def inicializar_modelos():
    """Inicializa todos los modelos de lenguaje de la arquitectura multi-agente
    reutilizando las conexiones en cada re-render de Streamlit."""
    
    # Router Orquestador (Groq - Llama 3)
    llm_router = ChatGroq(
        model="llama-3.1-8b-instant", 
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.0
    )

    # Agente 1: Foro Hub & OCI (Google Gemini)
    llm_gemini = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.0
    )

    # Agente 2: Código y Sintaxis (Mistral Large)
    llm_mistral_code = ChatMistralAI(
        model="mistral-large-latest", 
        api_key=os.environ.get("MISTRAL_API_KEY"),
        temperature=0.1
    )

    # Agente 3: Arquitecto RAG (Groq - Qwen / DeepSeek)
    llm_deepseek_rag = ChatGroq(
        model="qwen/qwen3-32b", 
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.0
    )
    
    return llm_router, llm_gemini, llm_mistral_code, llm_deepseek_rag