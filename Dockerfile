FROM python:3.10-slim

# Установка системных зависимостей, включая git для установки из git+https
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем остальной код приложения
COPY logo_viewer.py .
COPY Procfile .

# Запуск Streamlit приложения
CMD ["streamlit", "run", "logo_viewer.py", "--server.port=8501", "--server.address=0.0.0.0"]