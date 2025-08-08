import streamlit as st
import os
import sqlite3
from PIL import Image, ImageEnhance
import re
from datetime import datetime, date
import torch
import clip

# Пути
etalon_folder = "батчинг-тест/Сравнение/Эталон"
compared_folder = "батчинг-тест/Сравнение/Противопоставленное"
images_folder = "images"  # Папка с картинками заявок
DB_PATH = "documents.db"

def extract_number(filename):
    match = re.match(r"(\d+)", filename)
    return int(match.group(1)) if match else float('inf')

def show_application_card(app_data):
    st.markdown("---")
    st.header(f"Карточка заявки {app_data['application_number']}")
    st.write(f"**Номер заявки:** {app_data['application_number']}")
    st.write(f"**Дата подачи:** {app_data['application_date']}")
    st.write(f"**Публикация:** {app_data['publication']}")
    st.write(f"**Номер бюллетеня:** {app_data['bulletin_number']}")
    st.write(f"**Заявитель:** {app_data['applicant']}")
    st.write(f"**Адрес:** {app_data['correspondence_address']}")
    st.write(f"**Классы МКТУ:** {app_data['classes']}")
    if st.button("Закрыть карточку"):
        st.session_state.selected_app = None
        st.experimental_rerun()

# === Инициализация CLIP ===
device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "ViT-B/16"
model, preprocess = clip.load(model_name, device=device)
BATCH_SIZE = 16

def enhance_image(image):
    image = image.resize((512, 512), Image.BICUBIC)
    image = ImageEnhance.Contrast(image).enhance(1.5)
    image = ImageEnhance.Sharpness(image).enhance(1.3)
    return image

st.title("🔍 Логотипы и заявки")

tabs = st.tabs(["Визуальное сравнение", "Поиск по заявкам", "Поиск по тексту (ИИ)"])

# --- Первая вкладка: Визуальное сравнение ---
with tabs[0]:
    etalon_files = [f for f in os.listdir(etalon_folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    etalon_files.sort(key=extract_number)

    selected_etalon = st.selectbox("Выберите эталон", etalon_files)

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

    import pandas as pd
    df = pd.DataFrame(top_matches, columns=["Файл", "Сходство"])
    df.insert(0, "Top", [f"Top {i+1}" for i in range(len(df))])
    select_options = [f"{row.Top} — {row.Файл}" for _, row in df.iterrows()]
    selected_option = st.selectbox("Выберите логотип из списка", select_options)
    selected_file = selected_option.split(" — ", 1)[1]

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

    st.subheader("📋 Таблица похожих логотипов (топ 5)")
    st.dataframe(df.head(5), use_container_width=True)

# --- Вторая вкладка: Поиск по заявкам ---
with tabs[1]:
    st.title("🔎 Поиск по заявкам на регистрацию товарных знаков")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT classes FROM documents_pdf")
    all_classes_raw = [row[0] for row in cursor.fetchall()]
    unique_classes = set()
    for cl_str in all_classes_raw:
        unique_classes.update([c.strip() for c in cl_str.split(",") if c.strip()])
    unique_classes = sorted(unique_classes)

    cursor.execute("SELECT MIN(application_date), MAX(application_date) FROM documents_pdf")
    min_date_str, max_date_str = cursor.fetchone()

    def str_to_date(s):
        try:
            return datetime.strptime(s, "%d.%m.%Y").date()
        except Exception:
            return None

    min_date = str_to_date(min_date_str) or date.today()
    max_date = str_to_date(max_date_str) or date.today()

    selected_dates = st.date_input(
        "Выберите даты подачи заявки (диапазон)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    selected_classes = st.multiselect("Выберите классы МКТУ", unique_classes)

    query = "SELECT application_number, application_date, publication, bulletin_number, applicant, correspondence_address, classes FROM documents_pdf WHERE 1=1"
    params = []

    if selected_dates and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        start_str = start_date.strftime("%d.%m.%Y")
        end_str = end_date.strftime("%d.%m.%Y")
        query += " AND (application_date BETWEEN ? AND ?)"
        params.extend([start_str, end_str])

    if selected_classes:
        like_clauses = []
        for cl in selected_classes:
            like_clauses.append("classes LIKE ?")
            params.append(f"%{cl}%")
        query += " AND (" + " OR ".join(like_clauses) + ")"

    query += " ORDER BY application_date DESC LIMIT 100"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    all_apps = {row[0]: {
        'application_number': row[0],
        'application_date': row[1],
        'publication': row[2],
        'bulletin_number': row[3],
        'applicant': row[4],
        'correspondence_address': row[5],
        'classes': row[6],
    } for row in rows}

    st.header(f"📁 Результаты поиска заявок ({len(rows)} из максимум 100)")

    if not rows:
        st.info("По выбранным фильтрам заявок не найдено.")
    else:
        cols_per_row = 3
        for i in range(0, len(rows), cols_per_row):
            cols = st.columns(cols_per_row)
            for col, row in zip(cols, rows[i:i+cols_per_row]):
                app_num = row[0]
                img_path = None
                for ext in ['jpg', 'png']:
                    path = os.path.join(images_folder, f"{app_num}.{ext}")
                    if os.path.exists(path):
                        img_path = path
                        break
                with col:
                    if img_path:
                        if st.button(app_num, key=f"btn_{app_num}"):
                            show_application_card(all_apps[app_num])
                        st.image(img_path, use_container_width=True)
                    else:
                        st.write(f"🖼 Нет изображения для {app_num}")
                        if st.button(app_num, key=f"btn_{app_num}"):
                            show_application_card(all_apps[app_num])

# --- Третья вкладка: Поиск по тексту (ИИ) ---
with tabs[2]:
    st.header("Поиск по тексту (ИИ)")
    st.write("ИИ Поиск по тексту по всем товарным знакам в базе")

    text_input = st.text_area("Введите текстовый запрос (можно несколько строк)", height=100)

    if st.button("🔍 Запустить поиск"):
        if not text_input.strip():
            st.warning("Введите хотя бы один запрос.")
        else:
            folder = compared_folder

            text_queries = [line.strip() for line in text_input.split("\n") if line.strip()]
            text_tokens = clip.tokenize(text_queries).to(device)
            with torch.no_grad():
                text_features = model.encode_text(text_tokens)
                text_features = text_features.mean(dim=0, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                text_features = text_features.cpu()

            image_files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            total_images = len(image_files)
            results = []

            progress_bar = st.progress(0, text=f"Обработано 0 из {total_images}")

            for i in range(0, total_images, BATCH_SIZE):
                batch_files = image_files[i:i + BATCH_SIZE]
                batch_images = []
                valid_files = []

                for fname in batch_files:
                    try:
                        image_path = os.path.join(folder, fname)
                        image = Image.open(image_path).convert("RGB")
                        image = enhance_image(image)
                        image_tensor = preprocess(image)
                        batch_images.append(image_tensor)
                        valid_files.append(fname)
                    except Exception as e:
                        st.warning(f"Ошибка с файлом {fname}: {e}")

                if batch_images:
                    batch_tensor = torch.stack(batch_images).to(device)
                    with torch.no_grad():
                        image_features = model.encode_image(batch_tensor)
                        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                        image_features = image_features.cpu()

                    similarities = (image_features @ text_features.T).squeeze(1)

                    for fname, sim in zip(valid_files, similarities):
                        results.append((fname, sim.item()))

                done = min(i + BATCH_SIZE, total_images)
                progress_bar.progress(done / total_images, text=f"Обработано {done} из {total_images}")

            results.sort(key=lambda x: x[1], reverse=True)
            st.subheader("Результаты поиска (топ-5):")

            for fname, score in results[:5]:
                img_path = os.path.join(folder, fname)
                st.image(img_path, caption=f"{fname} — Сходство: {score:.4f}", use_container_width=True)
