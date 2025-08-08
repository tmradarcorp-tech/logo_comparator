FROM python:3.10-slim

# 1. Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Копируем файл с зависимостями заранее, чтобы кешировать установку pip
COPY requirements.txt .

# 3. Обновляем pip и ставим зависимости
#    PyTorch и Torchvision тянем с официального CPU-репозитория
RUN pip install --upgrade pip && \
    pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# 4. Копируем код приложения
COPY logo_viewer.py .
COPY Procfile .

# 5. Запускаем Streamlit
CMD ["streamlit", "run", "logo_viewer.py", "--server.port=8501", "--server.address=0.0.0.0"]

