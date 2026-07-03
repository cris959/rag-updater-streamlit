import os
from dotenv import load_dotenv
from groq import Groq

# 1. Cargamos las variables de entorno (.env)
load_dotenv()

def consultar_catalogo_groq():
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Error: No se encontró la variable GROQ_API_KEY en tu archivo .env")
        return

    print("🔌 Conectando con los servidores de Groq...")
    try:
        # Inicializamos el cliente nativo
        client = Groq(api_key=api_key)
        
        # Consultamos el listado de modelos disponibles en su infraestructura
        lista_modelos = client.models.list()
        
        print("\n========================================================")
        print("🤖 CATÁLOGO DE MODELOS DISPONIBLES EN TU CUENTA DE GROQ")
        print("========================================================\n")
        
        # Filtramos y ordenamos para mostrar los IDs limpios
        modelos_activos = sorted([model.id for model in lista_modelos.data])
        
        # Separamos los de DeepSeek para que los veas al toque
        modelos_deepseek = [m for m in modelos_activos if "deepseek" in m.lower()]
        otros_modelos = [m for m in modelos_activos if "deepseek" not in m.lower()]
        
        print("🎯 Modelos de DeepSeek activos:")
        if modelos_deepseek:
            for m in modelos_deepseek:
                print(f"  • {m}")
        else:
            print("  (No hay modelos de DeepSeek activos en este momento en Groq)")
            
        print("\n🚀 Otros modelos disponibles (Llama, Gemma, Mistral, etc.):")
        for m in otros_modelos:
            print(f"  • {m}")
            
        print("\n========================================================")
        
    except Exception as e:
        print(f"❌ Ocurrió un error al consultar la API: {str(e)}")

if __name__ == "__main__":
    consultar_catalogo_groq()