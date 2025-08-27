import streamlit as st
import pandas as pd
from io import BytesIO

# === Масса деталей ===
DETAIL_MASS_KG = {
    "Рама": 8500,
    "Балка": 3500,
    "Тягове ярмо": 1200,
    "Автозчеп 1008": 1350,
    "Автозчеп 1028": 1400,
    "Пластина-упор": 180,
    "Передній упор": 140,
    "Задній упор": 140
}

# === Загрузка спецификаций ===
@st.cache_data
def load_materials():
    return pd.read_excel("material.xlsx")

materials_df = load_materials()

st.title("Калькулятор розрахунку матеріалів")

# === Шаг 1: Выбор детали ===
selected_detail = st.selectbox("Оберіть деталь:", list(DETAIL_MASS_KG.keys()))
detail_mass = DETAIL_MASS_KG[selected_detail]

# === Шаг 2: Ввод количества деталей ===
count = st.number_input("Введіть кількість деталей:", min_value=1, value=1)

# === Шаг 3: Ввод массы стали ===
mass_kg = st.number_input("Введіть масу рідкої сталі (кг)", min_value=1.0, step=0.1)

total_mass = mass_kg * count
st.markdown(f"**Загальна маса рідкої сталі:** {total_mass} кг")

# === Шаг 3: Выбор стадий процесса ===
available_stages = materials_df["process_stage"].dropna().unique().tolist()
selected_stages = st.multiselect("Оберіть стадії процесу:", available_stages)

# === Шаг 4: Выбор спецификаций для стадий ===
spec_selection = {}
for stage in selected_stages:
    specs = materials_df[materials_df["process_stage"] == stage]["spec_version"].dropna().unique().tolist()
    if specs:
        selected_spec = st.selectbox(f"Оберіть варіант для стадії '{stage}':", specs, key=stage)
        spec_selection[stage] = selected_spec

# === Кнопка запуска расчета ===
if st.button("Розрахувати"):
    result_rows = []
    for stage, spec in spec_selection.items():
        stage_df = materials_df[
            (materials_df["process_stage"] == stage) &
            (materials_df["spec_version"] == spec)
        ]
        result_rows.append(stage_df)

    if result_rows:
        final_df = pd.concat(result_rows)
        final_df["quantity"] = final_df["rate_per_kg"] * total_mass
        final_df["price"] = final_df["price"].fillna(0)
        final_df["total_cost"] = (final_df["quantity"] * final_df["price"]).round(2)

        # === Финальная таблица ===
        result = final_df[["operation_name", "unit", "price", "quantity", "total_cost", "process_stage"]].copy()
        result.columns = ["Найменування", "Одиниця", "Ціна за одиницю, грн.", "Кількість", "Вартість, грн.", "Стадія процесу"]
        result = result.reset_index(drop=True)
        result.index += 1
        result.index.name = "№"

        st.markdown("**Результат розрахунку:**")
        st.dataframe(result, use_container_width=True)

        # === Суммарная стоимость ===
        total_sum = result["Вартість, грн."].sum().round(2)
        st.subheader(f"**Сумарна вартість всіх матеріалів: {total_sum:.2f} грн.**")

        # === Скачать Excel ===
        def to_excel(dataframe,total_sum):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                dataframe.to_excel(writer, index=True, startrow=2, sheet_name="Матеріали")
                workbook = writer.book
                worksheet = writer.sheets["Матеріали"]
                bold = workbook.add_format({'bold': True})
                title = f"Розрахунок матеріалів на {total_mass:.1f} кг сталі"
                worksheet.write("A1", title, bold)

                # Добавляем суммарную стоимость внизу таблицы
                last_row = len(dataframe) + 4  # 2 строки смещение + 1 заголовок + 1 для индекса
                worksheet.write(f"B{last_row}", "Сумарна вартість, грн.:", bold)
                worksheet.write(f"F{last_row}", total_sum, bold)

            output.seek(0)
            return output

        excel_file = to_excel(result, total_sum)
        st.download_button(
            label="📥 Скачати Excel",
            data=excel_file,
            file_name=f"розрахунок_{selected_detail}_{int(total_mass)}кг.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Не знайдено жодної специфікації для обраних стадій.")