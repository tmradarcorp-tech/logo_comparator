import streamlit as st
import os
import sqlite3
from PIL import Image
import pandas as pd
import re

# Пути к папкам и базе
etalon_folder = "батчинг-тест/Сравнение/Эталон"
compared_folder = "батчинг-тест/Сравнение/Противопоставленное"
DB_PATH = "documents.db"

def extract_number(filename):
    match = re.match(r"(\d+)", filename)
    return int(match.group(1)) if match else float('inf')

st.title("🔍 Визуальное сравнение логотипов")

# Получаем и сортируем список эталонов по числовому префиксу
etalon_files = [
    f for f in os.listdir(etalon_folder)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]
etalon_files.sort(key=extract_number)

# Выбор эталона
selected_etalon = st.selectbox("Выберите эталон", etalon_files)

# Подключаемся к базе и получаем похожие логотипы
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
    SELECT compared, similarity
    FROM clip_similarity
    WHERE etalon = ?
    ORDER BY similarity DESC
    LIMIT 30
""", (selected_etalon,))
top_matches = cursor.fetchall()
conn.close()

# Формируем DataFrame с топом
df = pd.DataFrame(top_matches, columns=["Файл", "Сходство"])
df.insert(0, "Top", [f"Top {i+1}" for i in range(len(df))])

# Формируем список для выбора (Top N — имя файла)
select_options = [f"{row.Top} — {row.Файл}" for _, row in df.iterrows()]

# Выбор похожего логотипа из списка
selected_option = st.selectbox("Выберите логотип из списка", select_options)

# Извлекаем имя файла
selected_file = selected_option.split(" — ", 1)[1]

# Горизонтальное отображение эталона и выбранного логотипа
col1, col2 = st.columns(2)

with col1:
    etalon_path = os.path.join(etalon_folder, selected_etalon)
    st.subheader("🎯 Эталон")
    st.image(etalon_path, caption=selected_etalon, width=300)

with col2:
    if selected_file:
        image_path = os.path.join(compared_folder, selected_file)
        try:
            image = Image.open(image_path)
            st.subheader("🤝 Похожий логотип")
            st.image(image, caption=selected_file, width=300)
        except Exception:
            st.error("⚠️ Не удалось загрузить изображение.")

# Таблица с первыми 5 строками
st.subheader("📋 Таблица похожих логотипов (топ 5)")
st.dataframe(df.head(5), use_container_width=True)
