# 🤖 Agente de Infraestructura & Foro Hub (Frontend Chat)

Este repositorio contiene la interfaz de usuario interactiva desarrollada en **Streamlit** para interactuar con el Agente de Inteligencia Artificial enfocado en la infraestructura de **Foro Hub**. La aplicación implementa una arquitectura RAG (Retrieval-Augmented Generation) local para responder consultas técnicas precisas basándose en el entorno real de despliegue.

---

## 🛠️ Características Principales

*   **Interfaz de Chat Fluida:** Basada en los componentes nativos de chat de Streamlit para una experiencia limpia y responsiva.
*   **Contexto RAG de Infraestructura:** El agente consume el archivo `contexto_infraestructura.txt` para responder con datos reales del entorno sin recurrir a alucinaciones genéricas.
*   **Seguridad Anti-Bots (Honeypot Nativo):** Implementación de una trampa de seguridad oculta mediante un sistema de pestañas (`st.tabs`) asimétricas. El input de confirmación es invisible para usuarios humanos pero completamente expuesto para scrapers y bots automatizados, mitigando spam y ataques dirigidos.
*   **Despliegue Aislado:** Configurado para convivir de forma segura con entornos modernos de Python 3.13.

---

## 🏗️ Arquitectura del Entorno de Destino (Christian Dev)
El agente está entrenado para dar soporte sobre la siguiente arquitectura de infraestructura documentada en el contexto local:

* Servidor Web: Nginx actuando como proxy inverso en el puerto **8000**.

* SO del Servidor: Ubuntu Server alojado en la nube de Oracle Cloud Infrastructure (OCI) (Instancia Always Free).

* Cifrado: Certificados SSL administrados y renovados mediante Let's Encrypt y Certbot.

* Dominio Público: [https://foro-hub-christian.duckdns.org/api/swagger-ui/html](https://foro-hub-christian.duckdns.org/api/swagger-ui/html).

* Backend Relacionado: API REST desarrollada con Spring Boot 3.x y Java 21.

* Persistencia y Conexión de Datos: Base de datos Oracle Cloud (23ai/26ai) de alta disponibilidad (**@forohubdb_high**). Utiliza credenciales cifradas con Oracle Wallet dinámico mediante la siguiente configuración externalizada:
````
Properties
# CONFIGURACION DE CONEXION (ORACLE 26ai)
# ==========================================
# La ruta usa ${user.dir} para que funcione en cualquier PC donde descargues el proyecto
spring.datasource.url=jdbc:oracle:thin:@forohubdb_high?TNS_ADMIN=${TNS_ADMIN_PATH}
spring.datasource.username=ADMIN
spring.datasource.password=${DB_PASSWORD}
spring.datasource.driver-class-name=oracle.jdbc.OracleDriver

````

---

## 📁 Estructura de Archivos Clave

```text
├── agent_frontend.py          # Script principal de la aplicación Streamlit.
├── contexto_infraestructura.txt # Base de conocimiento RAG con la topología de la app.
├── README.md                  # Documentación del proyecto (este archivo).
└── requirements.txt           # Dependencias del entorno Python.
```

## 🚀 Cómo Ejecutar en Local
1. Requisitos Previos
* Python 3.11 o superior (**Testeado con éxito en Python 3.13**).

2. Instalación de Dependencias
* Cloná el repositorio, parate en la carpeta raíz e instalá Streamlit y los conectores necesarios:
``` 
Bash
pip install -r requirements.txt
```
3. Configurar la Base de Conocimiento
Asegurate de que el archivo **contexto_infraestructura.txt** contenga los datos actualizados del pipeline de despliegue, entidades JPA, reglas de negocio del foro y configuraciones del proxy inverso.

4. Lanzar la Aplicación
Ejecutá el servidor local de Streamlit:

``` 
Bash
streamlit run agent_frontend.py
```

Abre tu navegador en http://localhost:8501 para interactuar con el frontend.

## 🛡️ Seguridad: Implementación del Honeypot
Para evitar peleaduras con las restricciones de inyección de CSS/JS en iFrames aislados de las últimas versiones de Streamlit, la trampa anti-bots se despliega utilizando contenedores de layouts nativos:
````
Python
tab_principal, tab_sistema = st.tabs(["💬 Chat", " "])

with tab_principal:
    # Renderizado normal del historial de chat y chat_input
    pass

with tab_sistema:
    # Input trampa expuesto en el DOM pero fuera de la vista humana
    honeypot_field = st.text_input("Confirm email (dejar en blanco)", value="", key="email_confirm")
````
Si un script automatizado intenta rellenar masivamente los campos detectados en el DOM, el backend detectará que el valor de **key="email_confirm"** no está vacío y procederá a rechazar o bloquear la sesión del atacante.


## 📝 Licencia
Este proyecto está bajo la Licencia MIT. Para más detalles, consulta el archivo [LICENSE](https://github.com/cris959/rag-updater-streamlit/blob/main/LICENSE.txt) adjunto en este repositorio.

Copyright © 2026 [Christian Garay](https://github.com/cris959/rag-updater-streamlit/blob/main/LICENSE.txt) - Backend Developer.
