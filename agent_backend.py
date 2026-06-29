import os
import platform
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# DETECCIÓN DE ENTORNO
SISTEMA_OPERATIVO = platform.system()
print(f"🖥️ [Sistema] Entorno detectado: {SISTEMA_OPERATIVO}")

# ========================================================
# 1. CONFIGURACIÓN HÍBRIDA DE BASE DE DATOS VECTORIAL
# ========================================================

if SISTEMA_OPERATIVO == "Windows":
    # --- MODO DESARROLLO (Windows - Python 3.13) ---
    print("📂 Cargando Simulador de Base Vectorial (In-Memory)...")
    
    documentos_locales = [
        {"contenido": "Para desplegar aplicaciones en OCI Always Free de Christian Dev, se usa Ubuntu con Nginx como proxy inverso."},
        {"contenido": "El proyecto Foro Hub está alojado en foro-hub-christian.duckdns.org usando certificados SSL."}
    ]

def buscar_en_faiss_local(pregunta_usuario: str) -> str:
   """
   Simula la recuperación de contexto local (RAG) en desarrollo.
   Si detecta términos críticos del negocio, inyecta las reglas de oro
   del proyecto para evitar que el LLM delire flujos estándar.
   """
   pregunta_lower = pregunta_usuario.lower()
   contexto_base = ""
    
    # Intentar leer el archivo de contexto real si existe
   try:
        with open("contexto_infraestructura.txt", "r", encoding="utf-8") as f:
            contexto_base = f.read()
   except FileNotFoundError:
        contexto_base = "Contexto local no disponible."

    # INYECTOR PRIORITARIO: Reglas duras para la IA
   reglas_estrictas = ""
    
   if any(k in pregunta_lower for k in ["solucion", "marcar", "status", "estado", "topico"]):
        reglas_estrictas = (
            "\n[¡ALERTA REGLA DE NEGOCIO REAL DEL PROYECTO FORO HUB!]\n"
            "- Los únicos estados válidos de StatusTopico son: NO_RESPONDIDO, NO_SOLUCIONADO, SOLUCIONADO, CERRADO.\n"
            "- NO existen los estados 'Abierto' ni 'Resuelto'.\n"
            "- El flujo de solución lo maneja RespuestaService desmarcando anteriores (solucion=false), "
            "marcando la nueva (solucion=true) y mutando el StatusTopico del padre a SOLUCIONADO.\n"
            "- Prohibido inventar flujos de envío de emails o indicadores de rendimiento si no están explícitos."
        )
   return f"{contexto_base}\n{reglas_estrictas}"

# ========================================================
# 2. BÚSQUEDA EN INTERNET REAL
# ========================================================
def buscar_en_internet_real(query: str) -> str:
    """Busca en internet en tiempo real usando DuckDuckGo (Adaptable a v5 y v6)."""
    print(f"   🌐 Conectando con la Web para buscar: '{query}'...")
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
# 3. FUNCIÓN PRINCIPAL CORREGIDA: EVITAR ALUCINACIONES TEÓRICAS
# ========================================================
def ejecutar_agent_loop(pregunta_usuario: str) -> str:
    """
    Orquesta el flujo agéntico llamando a las herramientas dinámicas.
    Tiene reglas estrictas para evitar alucinaciones teóricas y responder
    como un DevOps/Backend Senior pragmático.
    """
    print(f"\n🤖 [Agente] Iniciando análisis para: '{pregunta_usuario}'")
    
    contexto_local = ""
    contexto_web = ""
    pregunta_lower = pregunta_usuario.lower()
    
    # Ampliamos palabras clave para capturar rutas, swagger, api y endpoints en el contexto local
    palabras_clave_local = [
        "nginx", "puerto", "ubuntu", "local", "servidor", "foro", 
        "inventario", "faiss", "ruta", "endpoint", "swagger", "api", "extension"
    ]
    
    if any(k in pregunta_lower for k in palabras_clave_local):
        contexto_local = buscar_en_faiss_local(pregunta_usuario)
        
    if any(k in pregunta_lower for k in ["seguridad", "internet", "ia", "web", "últimas", "recomendaciones", "actualidad"]):
        contexto_web = buscar_en_internet_real(pregunta_usuario)
        
    contexto_total = f"{contexto_local}\n\n{contexto_web}".strip()
    if not contexto_total:
        contexto_total = "No se requirieron herramientas externas para esta consulta."

    # SYSTEM PROMPT AJUSTADO PARA CORREGIR ALUCINACIONES
    system_prompt = (
        "Sos un Ingeniero DevOps y Desarrollador Backend Senior experto en Java, Spring Boot, Nginx y Oracle Cloud (OCI).\n"
        "El usuario es Christian Dev (Cris959), creador del proyecto Foro Hub.\n\n"
        "REGLAS DE RESPUESTA CRÍTICAS (PROHIBIDO ALUCINAR TEORÍA BÁSICA):\n"
        "1. Hablá como un colega técnico senior: sé pragmático, directo y enfocado en infraestructura o código real.\n"
        "2. NUNCA respondas con definiciones de diccionario web (no expliques qué es un protocolo, qué es un subdominio o qué es un archivo .html). El usuario ya sabe eso.\n"
        "3. Si el usuario pregunta por extensiones, rutas o paths después del dominio (ej. '/api/swagger-ui/index.html'), comprendé inmediatamente que se refiere a los ENDPOINTS de Spring Boot, la documentación de Swagger o el ruteo en el bloque 'location' de Nginx.\n"
        "4. Vinculá tus respuestas al contexto real de Foro Hub: ruteo hacia el backend, configuración de Spring Security (público vs protegido) o cómo el proxy inverso de Nginx maneja esas rutas."
    )
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Contexto disponible:\n{contexto_total}\n\nConsulta: {pregunta_usuario}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3, # Bajamos un toque la temperatura (estaba en 0.5) para que sea más preciso y menos creativo
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error al procesar la respuesta con el LLM: {str(e)}"