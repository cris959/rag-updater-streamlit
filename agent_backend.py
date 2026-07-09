import os
import platform
import oracledb
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# Inicialización segura del cliente Groq
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("❌ Error: La variable de entorno GROQ_API_KEY no está configurada.")

client = Groq(api_key=api_key)

# DETECCIÓN DE ENTORNO
SISTEMA_OPERATIVO = platform.system()
print(f"🖥️ [Sistema] Entorno detectado: {SISTEMA_OPERATIVO}")

# 🧠 Inicializamos el modelo de Embeddings idéntico al del script de carga
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# ========================================================
# 1. RECUPERACIÓN VECTORIAL EN OCI (ANTES FAISS LOCAL)
# ========================================================

def buscar_en_oracle_vector(pregunta_usuario: str, top_k: int = 3) -> str:
    """
    Vectoriza la consulta del usuario y realiza una búsqueda semántica nativa
    K-NN sobre Oracle Autonomous Database utilizando la métrica de Coseno.
    """
    pregunta_lower = pregunta_usuario.lower()
    
    # 1. Recuperar variables de OCI desde el .env
    USER = os.getenv("OCI_DB_USER")
    PASSWORD = os.getenv("OCI_DB_PASSWORD")
    ruta_wallet = os.path.abspath(os.getenv("OCI_WALLET_LOCATION"))
    table_name = "RAG_KNOWLEDGE_BASE"
    
    contexto_recuperado = []
    
    try:
        # 2. Generar el embedding de la pregunta
        vector_pregunta = embeddings.embed_query(pregunta_usuario)
        
        # 3. Conexión segura mTLS Thin Mode a OCI
        wallet_password = os.getenv("OCI_WALLET_PASSWORD") # Levantamos la clave del .env de forma segura
        
        connection = oracledb.connect(
            user=USER,
            password=PASSWORD,
            dsn=os.getenv("OCI_DB_DSN"),
            port=1522,
            config_dir=ruta_wallet,
            wallet_location=ruta_wallet,
            wallet_password=wallet_password  # Ahora es 100% dinámica y segura
            # Quitamos 'thin=True' para evitar el error de argumento inesperado en tu versión
        )
        
        with connection.cursor() as cursor:
            # Consulta SQL nativa 23ai para recuperar los trozos más cercanos
            sql = f"""
                SELECT text, VECTOR_DISTANCE(vector, :1, COSINE) as distancia
                FROM {table_name}
                ORDER BY distancia
                FETCH FIRST :2 ROWS ONLY
            """
            cursor.execute(sql, [str(vector_pregunta), top_k])
            resultados = cursor.fetchall()
            
            for texto, distancia in resultados:
                contexto_recuperado.append(texto)
                
        connection.close()
        contexto_base = "\n---\n".join(contexto_recuperado)
        
    except Exception as e:
        # Backup amigable en la interfaz si la red o OCI llegaran a fallar
        contexto_base = f"⚠️ Sistema: La base de datos vectorial nativa en OCI no está disponible temporalmente. Detalle: {str(e)}"

    # INYECTOR PRIORITARIO: Reglas duras de lógica para el dominio del negocio (Foro Hub)
    reglas_estrictas = ""
    if any(k in pregunta_lower for k in ["solucion", "marcar", "status", "estado", "topico", "tópico"]):
        reglas_estrictas = (
            "\n[¡ALERTA REGLA DE NEGOCIO REAL DEL PROYECTO FORO HUB!]\n"
            "- Los únicos estados válidos de StatusTopico son: NO_RESPONDIDO, NO_SOLUCIONADO, SOLUCIONADO, CERRADO.\n"
            "- NO existen los estados 'Abierto' ni 'Resuelto'.\n"
            "- El flujo de solución lo maneja RespuestaService desmarcando anteriores (solucion=false), "
            "marcando la nueva (solucion=true) y mutando el StatusTopico del padre a SOLUCIONADO.\n"
            "- Prohibido inventar flujos de envío de emails o indicadores de rendimiento si no están explícitos."
        )
        
    return f"[Contexto Semántico Recuperado de OCI]:\n{contexto_base}\n{reglas_estrictas}".strip()

# ========================================================
# 2. BÚSQUEDA EN INTERNET REAL (PRODUCCIÓN / NOVEDADES)
# ========================================================

def buscar_en_internet_real(query: str) -> str:
    """Busca en internet en tiempo real usando DuckDuckGo."""
    print(f"    🌐 Conectando con la Web para buscar: '{query}'...")
    try:
        with DDGS() as ddgs:
            resultados = [r for r in ddgs.text(query, max_results=3)]
            if resultados:
                contexto_web = "[Fuentes de Internet Real]:\n"
                for i, res in enumerate(resultados, 1):
                    contexto_web += f"{i}. {res['title']}: {res['body']}\n"
                return contexto_web
            return "No se encontraron resultados recientes en internet."
    except Exception as e:
        return f"Error al consultar internet: {str(e)}"
    
# ========================================================
# 3. MOTOR PRINCIPAL: EJECUTAR AGENT LOOP (LLAMA 3.3 70B)
# ========================================================

def ejecutar_agent_loop(pregunta_usuario: str) -> str:
    """
    Orquesta el flujo agéntico híbrido conectando dinámicamente con OCI Vector DB.
    """
    print(f"\n🤖 [Agente] Iniciando análisis para: '{pregunta_usuario}'")
    
    contexto_local = ""
    contexto_web = ""
    pregunta_lower = pregunta_usuario.lower()
    
    # Palabras clave para consultar infraestructura, vectores o dominio
    palabras_clave_local = [
        "nginx", "puerto", "ubuntu", "local", "servidor", "foro", 
        "inventario", "faiss", "ruta", "endpoint", "swagger", "api", "extension",
        "solucion", "status", "estado", "topico", "tópico", "vector", "base", "rag"
    ]
    
    # 1. Recuperación condicional de herramientas
    if any(k in pregunta_lower for k in palabras_clave_local):
        contexto_local = buscar_en_oracle_vector(pregunta_usuario, top_k=3)
        
    if any(k in pregunta_lower for k in ["seguridad", "internet", "ia", "web", "últimas", "actualidad"]):
        contexto_web = buscar_en_internet_real(pregunta_usuario)
        
    # 2. Respaldo de seguridad: si no disparó flags específicos, consultamos OCI por defecto
    if not contexto_local and not contexto_web:
        contexto_local = buscar_en_oracle_vector(pregunta_usuario, top_k=3)
        
    contexto_total = f"{contexto_local}\n\n{contexto_web}".strip()
    if not contexto_total:
        contexto_total = "No se requirieron herramientas externas adicionales para esta consulta."

    # 3. System Prompt adaptativo anti-alucinaciones teóricas
    system_prompt = (
        "Sos un Ingeniero DevOps y Desarrollador Backend Senior experto en Java, Spring Boot, Nginx y Oracle Cloud (OCI).\n"
        "El usuario es Christian Dev (Cris959), creador del proyecto Foro Hub.\n\n"
        "REGLAS DE RESPUESTA CRÍTICAS (PROHIBIDO ALUCINAR TEORÍA BÁSICA):\n"
        "1. Hablá como un colega técnico senior: sé pragmático, directo y enfocado en infraestructura o código real.\n"
        "2. NUNCA respondas con definiciones de diccionario web (no expliques qué es un protocolo, qué es un subdominio o qué es un archivo .html). El usuario ya sabe eso.\n"
        "3. Si el usuario pregunta por extensiones, rutas o paths después del dominio (ej. '/api/swagger-ui/index.html'), comprendé inmediatamente que se refiere a los ENDPOINTS de Spring Boot, la documentación de Swagger o el ruteo en el bloque 'location' de Nginx.\n"
        "4. Vinculá tus respuestas al contexto real de Foro Hub: ruteo hacia el backend, configuración de Spring Security (público vs protegido) o cómo el proxy inverso de Nginx maneja esas rutas."
    )
    
    # 4. Invocación al modelo en Groq
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Contexto disponible:\n{contexto_total}\n\nConsulta: {pregunta_usuario}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,  # Alta precisión técnica
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error al procesar la respuesta con el LLM: {str(e)}"