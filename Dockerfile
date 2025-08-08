FROM python:3.10-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем только код и зависимости
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY logo_viewer.py .
COPY Procfile .

# При старте будем использовать Streamlit
CMD ["streamlit", "run", "logo_viewer.py", "--server.port=8501", "--server.address=0.0.0.0"]