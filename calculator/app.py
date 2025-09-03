
import streamlit as st
import pandas as pd
from io import BytesIO

# === Масса деталей ===
DETAIL_MASS_KG = {
    "Рама": 7500,
    "Балка": 3500,
    "Тягове ярмо": 1200,
    "Автозчеп 1008": 1350,
    "Автозчеп 1028": 1400,
    "Пластина-упор": 180,
    "Передній упор": 140,
    "Задній упор": 140
}

ALL_DETAILS = list(DETAIL_MASS_KG.keys())

# === Список стадий процесса в правильном порядке ===
PROCESS_STAGES_ORDERED = [
    "Підготовка сталевого брухту", "Підготовка печі (футеровка)", "Підготовка стопора",
    "Підготовка ковша (футеровка)", "Виплавляння сталі", "Розливання сталі",
    "Приготування сумішей", "Транспортування суміші та стрижнів на АФЛ",
    "Підготовка. Встановлення модельного комплекту, трубки сифонної",
    "Виготовлення напівформ", "Відділка і складання напівформи", "Збирання форм",
    "Заливання форм", "Підготовка форм до розпаровки", "Переміщення форм/розпаровка",
    "Вибивка виливок (первинна обрубка)", "Обрубка", "Очищення дробометне",
    "Обробка на ВДР", "Обнаждачування", "Виправлення дефектів",
    "Неруйнівний контроль", "Термічна обробка", "Здача виливка"
]

# === Стадии, на которых может остановиться производство ===
STOP_STAGES = [
    "Обрубка", "Неруйнівний контроль", "Здача виливка", "Очищення дробометне",
    "Обнаждачування", "Виправлення дефектів", "Обробка на ВДР", "Вибивка виливок (первинна обрубка)"
]

# === Загрузка спецификаций ===
@st.cache_data
def load_materials():
    return pd.read_excel("material.xlsx")

materials_df = load_materials()

st.subheader("Калькулятор розрахунку собiвартостi матеріалів")

# === Инициализация доступных деталей ===
if "available_details" not in st.session_state:
    st.session_state.available_details = ["Рама"]  # пока доступна только Рама

# === Выбор детали ===
# Формируем список для selectbox с пометкой недоступных деталей 

select_options = []
for d in ALL_DETAILS:
    if d in st.session_state.available_details:
        select_options.append(d)
    else:
        select_options.append(f"{d} (не доступно)")

selected_raw = st.selectbox("Оберіть деталь:", options=select_options)

# Проверяем выбор
if selected_raw.endswith("(не доступно)"):
    st.warning("Ця деталь поки недоступна для розрахунку.")
    selected_detail = st.session_state.available_details[0]
else:
    selected_detail = selected_raw

detail_mass = DETAIL_MASS_KG[selected_detail]
st.info(f"Маса рідкої сталі для однієї деталі: {detail_mass} кг")

# === Инициализация session_state для итераций ===
if "iterations" not in st.session_state:
    st.session_state.iterations = []


# === Функции для добавления/удаления итерации ===
def add_iteration():
    st.session_state.iterations.append({"stage": STOP_STAGES[0], "qty": 0})

def remove_iteration(idx):
    if idx < len(st.session_state.iterations):
        st.session_state.iterations.pop(idx)

# === Кнопка добавления новой итерации ===
st.button("Додати порцію деталей", on_click=add_iteration)

# === Вывод всех итераций  ===
for idx, _ in enumerate(st.session_state.iterations):
    st.markdown(f"**Ітерація {idx+1}**")
    col1, col2, col3 = st.columns([4, 3, 1])

    stage_key = f"stage_{idx}"
    qty_key   = f"qty_{idx}"

    # Инициализация значений для первого рендера
    if stage_key not in st.session_state:
        st.session_state[stage_key] = st.session_state.iterations[idx]["stage"]
    if qty_key not in st.session_state:
        st.session_state[qty_key] = st.session_state.iterations[idx]["qty"]

    with col1:
        st.selectbox(
            f"Стадія зупинки (ітерація {idx+1}):",
            STOP_STAGES,
            key=stage_key  # без index/value на дальнейших перерендерах
        )
    with col2:
        st.number_input(
            f"Кількість деталей на цій стадії:",
            min_value=0,
            step=1,
            key=qty_key    # без value=...
        )
    with col3:
        if st.button("❌ Видалити", key=f"remove_{idx}"):
            remove_iteration(idx)
            st.rerun()

    # Синхронизация обратно в список итераций
    st.session_state.iterations[idx]["stage"] = st.session_state[stage_key]
    st.session_state.iterations[idx]["qty"]   = st.session_state[qty_key]

# === Кнопка расчета ===
if st.button("Розрахувати"):
    all_results = []

    for it in st.session_state.iterations:
        stage_name = it["stage"]
        qty = it["qty"]
        if qty == 0:
            continue

        # Определяем все стадии до выбранной включительно
        idx_stage = PROCESS_STAGES_ORDERED.index(stage_name)
        stages_to_calc = PROCESS_STAGES_ORDERED[:idx_stage+1]

        # Выбираем спецификации для этих стадий
        stage_df = materials_df[materials_df["process_stage"].isin(stages_to_calc)].copy()
        stage_df["quantity"] = stage_df["rate_per_kg"] * detail_mass * qty
        stage_df["price"] = stage_df["price"].fillna(0)
        stage_df["total_cost"] = (stage_df["quantity"] * stage_df["price"]).round(2)
        stage_df["порція деталей"] = f"{qty} шт. до {stage_name}"
        stage_df["маса рідкої сталі на порцію, кг"] = detail_mass * qty

        all_results.append(stage_df)

    if all_results:
        final_df = pd.concat(all_results)
        result = final_df[["operation_name", "unit", "price", "quantity", "total_cost",
                           "process_stage", "порція деталей", "маса рідкої сталі на порцію, кг"]].copy()
        result.columns = ["Найменування", "Одиниця", "Ціна за одиницю, грн.", "Кількість",
                          "Вартість, грн.", "Стадія процесу", "Порція деталей", "Маса рідкої сталі, кг"]
        result = result.reset_index(drop=True)
        result.index += 1
        result.index.name = "№"

        st.markdown("**Результат розрахунку:**")
        st.dataframe(result, use_container_width=True)

        total_sum = result["Вартість, грн."].sum().round(2)
        st.subheader(f"**Сумарна вартість всіх матеріалів: {total_sum:.2f} грн.**")

        # === Скачать Excel ===
        def to_excel(dataframe, total_sum, selected_detail):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # пишем датафрейм начиная со 2-й строки (после заголовка)
                dataframe.to_excel(writer, index=True, startrow=2, sheet_name="Матеріали")
                workbook  = writer.book
                worksheet = writer.sheets["Матеріали"]

                bold = workbook.add_format({'bold': True})
                money_fmt = workbook.add_format({'num_format': '#,##0.00', 'bold': False})

                # Заголовок
                title = f"Розрахунок матеріалів для {selected_detail}"
                worksheet.write("A1", title, bold)

                # Форматирование числовых колонок
                qty_col   = dataframe.columns.get_loc("Кількість") + 2  # +2, т.к. в xlsxwriter первая колонка = A, и index=True
                cost_col  = dataframe.columns.get_loc("Вартість, грн.") + 2
                price_col = dataframe.columns.get_loc("Ціна за одиницю, грн.") + 2

                # применяем формат
                worksheet.set_column(qty_col-1, qty_col-1, 15, money_fmt)
                worksheet.set_column(cost_col-1, cost_col-1, 18, money_fmt)
                worksheet.set_column(price_col-1, price_col-1, 18, money_fmt)

                # Итог внизу
                last_row = len(dataframe) + 4
                worksheet.write(last_row, 1, "Сумарна вартість, грн.:", bold)
                worksheet.write(last_row, cost_col-1, total_sum, bold)

                # Автоширина по колонкам
                for i, col in enumerate(dataframe.reset_index().columns):
                    max_len = max(
                        [len(str(s)) for s in dataframe.reset_index()[col]] + [len(col)]
                    )
                    worksheet.set_column(i, i, max_len + 2)

            output.seek(0)
            return output

        excel_file = to_excel(result, total_sum, selected_detail)
        st.download_button(
            label="📥 Скачати Excel",
            data=excel_file,
            file_name=f"розрахунок_{selected_detail}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )




        # Если нужно чтобы в эксель писался каждый блок расчетов по каждой итерации отдельно

        # def to_excel(dataframe, total_sum, selected_detail):
        #     output = BytesIO()
        #     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        #         workbook  = writer.book
        #         worksheet = workbook.add_worksheet("Матеріали")
        #         writer.sheets["Матеріали"] = worksheet

        #         bold = workbook.add_format({'bold': True})
        #         money_fmt = workbook.add_format({'num_format': '#,##0.00'})

        #         # Заголовок
        #         title = f"Розрахунок матеріалів для {selected_detail}"
        #         worksheet.write("A1", title, bold)

        #         row_offset = 2  # начинаем с 3-й строки

        #         for portion in dataframe["Порція деталей"].unique():
        #             portion_df = dataframe[dataframe["Порція деталей"] == portion]
        #             # подпись блока
        #             worksheet.write(row_offset, 0, f"Розрахунок для: {portion}", bold)
        #             row_offset += 1

        #             # пишем заголовки колонок
        #             for col_num, col_name in enumerate(portion_df.columns):
        #                 worksheet.write(row_offset, col_num, col_name, bold)
        #             row_offset += 1

        #             # пишем данные
        #             for i in range(len(portion_df)):
        #                 for col_num, val in enumerate(portion_df.iloc[i]):
        #                     # если числовое поле, применяем формат
        #                     if isinstance(val, (int, float)):
        #                         worksheet.write(row_offset, col_num, val, money_fmt)
        #                     else:
        #                         worksheet.write(row_offset, col_num, val)
        #                 row_offset += 1

        #             # пустая строка после блока
        #             row_offset += 1

        #         # итоговая сумма
        #         worksheet.write(row_offset, 1, "Сумарна вартість, грн.:", bold)
        #         # находим индекс колонки "Вартість, грн."
        #         cost_col = dataframe.columns.get_loc("Вартість, грн.")
        #         worksheet.write(row_offset, cost_col, total_sum, bold)

        #         # автоширина колонок
        #         for i, col in enumerate(dataframe.columns):
        #             max_len = max(
        #                 [len(str(s)) for s in dataframe[col]] + [len(col)]
        #             )
        #             worksheet.set_column(i, i, max_len + 2)

        #     output.seek(0)
        #     return output