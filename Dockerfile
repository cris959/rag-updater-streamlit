# Usamos Python 3.12 como base
FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ACTUALIZACIÓN CLAVE: Llevamos pip a la última versión para que detecte los binarios de Rust nativos
RUN pip install --no-cache-dir --upgrade pip

COPY requirements-prod.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "agent_frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]