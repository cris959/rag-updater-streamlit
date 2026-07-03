import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
# Importamos el cliente oficial directo de Google para saltearnos el bug de LangChain
from google import genai

load_dotenv()

# --- Clase intermedia para empaquetar los embeddings nativos en FAISS ---
class DirectGoogleEmbeddings:
    def __init__(self, api_key: str):
        # Inicializa el cliente oficial de Google GenAI
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-embedding-001"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Llama directamente al método oficial sin wrappers intermedios
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts
        )
        # Retorna la lista de vectores numéricos
        return [embedding.values for embedding in response.embeddings]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text
        )
        return response.embeddings[0].values

def inicializar_db_ficticia():
    print("🚀 Iniciando la carga de la Base de Datos Vectorial (FAISS) de prueba...")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: La variable de entorno GEMINI_API_KEY no está configurada.")
        return

    ruta_vector_db = "./data/rag_knowledge_base"

    documentacion_rag = """
    DOCUMENTACIÓN DE OPTIMIZACIÓN RAG (ACTUALIZACIÓN JUNIO 2026)
    
    1. Estrategias de Chunking (Fragmentación):
    Para documentos técnicos o código fuente, el tamaño de chunk recomendado es de 500 a 1000 tokens con un solapamiento (overlap) del 10% al 20%. 
    El chunking semántico (Semantic Chunking) analiza las variaciones en las distancias de los embeddings entre oraciones consecutivas para romper el texto solo cuando cambia el significado del contexto.
    
    2. Modelos de Embeddings Recomendados:
    Para arquitecturas en la nube OCI, el modelo 'text-embedding-004' ofrece una excelente relación entre dimensiones vectoriales y velocidad de recuperación.
    
    3. Retrieval Avanzado (Reranking):
    Para evitar el "ruido" en contextos largos, se implementa una capa de Re-ranking después de la búsqueda semántica inicial. Esto reordena los 4 chunks más relevantes utilizando un modelo cross-encoder para asegurar que la información crítica esté al principio del prompt.

    4. RAG Rule for Hybrid Search:
    Combining dense vector retrieval with sparse keyword search (BM25) yields the highest accuracy for programming and DevOps queries. This is known as Hybrid Search.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        length_function=len
    )
    
    chunks = text_splitter.create_documents([documentacion_rag])
    print(f"📦 Texto procesado y fragmentado en {len(chunks)} chunks vectoriales.")

    print("🧠 Conectando directo con la API oficial de Google GenAI...")
    embeddings_service = DirectGoogleEmbeddings(api_key=api_key)

    print("🧠 Generando vectores e indexando en FAISS...")
    vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings_service)
    
    vector_store.save_local(ruta_vector_db)
    print(f"✅ ¡Base de datos de prueba creada con éxito en: {ruta_vector_db}!")

if __name__ == "__main__":
    inicializar_db_ficticia()