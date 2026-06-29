import os
import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

def indexar_fuentes_agente():
    url_langchain = "https://docs.langchain.com/oss/python/langchain/overview"
    url_jina = f"https://r.jina.ai/{url_langchain}"
    archivo_local = "contexto_infraestructura.txt"
    
    bloques_totales = []
    
    # 1. PARTICIONADO DE LA DOCUMENTACIÓN WEB (LangChain)
    print(f"📥 Extrayendo documentación oficial desde: {url_langchain}...")
    try:
        respuesta = requests.get(url_jina, timeout=15)
        if respuesta.status_code == 200:
            text_splitter_web = RecursiveCharacterTextSplitter(
                chunk_size=700, chunk_overlap=120, separators=["\n\n", "\n", " ", ""]
            )
            fragmentos_web = text_splitter_web.split_text(respuesta.text)
            bloques_totales.extend(fragmentos_web)
            print(f"✅ ¡Éxito! {len(fragmentos_web)} bloques de LangChain procesados.")
        else:
            print(f"⚠️ No se pudo acceder a la URL web (Código {respuesta.status_code}).")
    except Exception as e:
        print(f"⚠️ Error al scrapear la documentación web: {str(e)}")

    # 2. PARTICIONADO DEL ARCHIVO LOCAL (Infraestructura y Proyectos)
    if os.path.exists(archivo_local):
        print(f"📄 Leyendo archivo de contexto local: {archivo_local}...")
        with open(archivo_local, "r", encoding="utf-8") as f:
            contenido_local = f.read()
            
        # Al ser datos muy específicos de configuración, usamos fragmentos más pequeños
        text_splitter_local = RecursiveCharacterTextSplitter(
            chunk_size=400, chunk_overlap=50, separators=["\n\n", "\n"]
        )
        fragmentos_local = text_splitter_local.split_text(contenido_local)
        bloques_totales.extend(fragmentos_local)
        print(f"✅ ¡Éxito! {len(fragmentos_local)} bloques de infraestructura local procesados.")
    else:
        print(f"⚠️ No se encontró el archivo '{archivo_local}'. Pasando de largo.")

    # 3. GENERACIÓN DEL ÍNDICE VECTORIAL FAISS
    if bloques_totales:
        print(f"\n🧠 Inicializando embeddings con HuggingFace para {len(bloques_totales)} bloques en total...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        print("💾 Compilando y guardando base de datos vectorial FAISS...")
        db = FAISS.from_texts(bloques_totales, embeddings)
        
        RUTA_FAISS = "faiss_index_oci"
        db.save_local(RUTA_FAISS)
        print(f"🚀 [COMPLETO] Base vectorial guardada con éxito en la carpeta '{RUTA_FAISS}'!")
    else:
        print("❌ Error: No se recolectaron datos para indexar.")

if __name__ == "__main__":
    indexar_fuentes_agente()