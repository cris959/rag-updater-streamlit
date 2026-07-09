import os
import oracledb
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

# 🔐 Cargamos las variables
load_dotenv()


# ==============================================================================
# 🔥 ACTIVAR MODO THICK DE ORACLE (Agregá esta línea acá)
# ==============================================================================
try:
    # Inicializa el modo grueso. Si tenés Oracle Instant Client instalado, 
    # podés pasarle la ruta en lib_dir, ej: oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient")
    # Si usas las herramientas nativas de tu entorno, dejarlo vacío suele bastar:
    oracledb.init_oracle_client(thin=True)
    print("💎 Modo Oracle Thick activado correctamente.")
except Exception as e:
    print(f"⚠️ Nota al activar Thick Mode: {e}")
    print("Asegúrate de tener Oracle Instant Client instalado si el error persiste.")

print("⏳ Iniciando sincronización RAG nativa sobre OCI...")

USER = os.getenv("OCI_DB_USER")
#------------------------------
print("⏳ Iniciando sincronización RAG nativa sobre OCI...")

USER = os.getenv("OCI_DB_USER")
PASSWORD = os.getenv("OCI_DB_PASSWORD")
DB_STRING = os.getenv("OCI_DB_CONNECTION_STRING")

archivo_texto = "contexto_infraestructura.txt"
table_name = "RAG_KNOWLEDGE_BASE"

if os.path.exists(archivo_texto):
    with open(archivo_texto, "r", encoding="utf-8") as f:
        texto = f.read()
    
    try:
        # 1. Procesamiento semántico local
        print("🧠 Generando chunks semánticos y calculando vectores...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        text_splitter = SemanticChunker(embeddings)
        chunks = text_splitter.create_documents([texto])
        
        # 2. Conexión mTLS Inteligente en Modo Thin
        print("🔌 Conectando de forma segura a Oracle Autonomous Database...")
        
        ruta_wallet = os.path.abspath(os.getenv("OCI_WALLET_LOCATION"))
        wallet_password = os.getenv("OCI_WALLET_PASSWORD") # Levantamos la clave del .env de forma segura
        
        connection = oracledb.connect(
            user=USER,
            password=PASSWORD,
            dsn=os.getenv("OCI_DB_DSN"),
            port=1522,
            config_dir=ruta_wallet,
            wallet_location=ruta_wallet,
            wallet_password=wallet_password  # Ahora es 100% dinámica y segura
            # Quitamos 'thin=True' para mantener la compatibilidad con el contenedor
        )
        
        print("📡 Conexión establecida con éxito. Preparando base de datos...")
        
        # Maniobramos el cursor de forma segura dentro del bloque de conexión
        cursor = connection.cursor()
        try:
            # 3. Crear la tabla con soporte nativo para vectores si no existe (384 dimensiones)
            print(f"🛠️ Verificando existencia de la tabla '{table_name}'...")
            cursor.execute(f"""
                BEGIN
                    EXECUTE IMMEDIATE 'CREATE TABLE {table_name} (
                        id VARCHAR2(64) PRIMARY KEY,
                        text CLOB,
                        vector VECTOR(384, FLOAT32)
                    )';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE != -955 THEN RAISE; END IF;
                END;
            """)
            
            # 4. Limpiar datos viejos
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            
            # 5. Insertar los vectores en OCI
            print(f"🚀 Subiendo {len(chunks)} vectores a la nube de Oracle...")
            for i, chunk in enumerate(chunks):
                vector_calculado = embeddings.embed_query(chunk.page_content)
                cursor.execute(
                    f"INSERT INTO {table_name} (id, text, vector) VALUES (:1, :2, :3)",
                    [f"chunk_{i}", chunk.page_content, str(vector_calculado)]
                )
            
            connection.commit()
            
            # 📊 Validación real en OCI
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_filas = cursor.fetchone()[0]
            print(f"✅ ¡Éxito absoluto! Vectores inyectados. Filas totales en OCI: {total_filas}")
            
        except Exception as e_sql:
            print(f"❌ Error ejecutando sentencias SQL en OCI: {e_sql}")
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e_conexion:
        print(f"❌ Error al intentar conectar con OCI: {e_conexion}")
else:
    print(f"❌ Error: Archivo '{archivo_texto}' no encontrado.")