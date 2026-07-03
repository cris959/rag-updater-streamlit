import os
from google import genai

# Inicializa el cliente oficial con la variable que acabamos de setear
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("🔍 Listando modelos disponibles en tu cuenta de Google GenAI...")
print("-" * 70)

# Recorre y muestra los modelos activos
for model in client.models.list():
    # Filtramos para ver el nombre limpio y sus capacidades
    print(f"🤖 Modelo: {model.name}")
    print(f"   💡 Métodos soportados: {model.supported_actions}")
    print("-" * 70)