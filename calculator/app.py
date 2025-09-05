import streamlit as st
import pandas as pd
from io import BytesIO
import base64

# === Масса деталей ===
DETAIL_MASS_KG = {
    "Рама": 750,
    "Балка": 350,
    "Тягове ярмо": 120,
    "Автозчеп 1008": 135,
    "Автозчеп 1028": 140,
    "Пластина-упор": 18,
    "Передній упор": 14,
    "Задній упор": 14
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
    return pd.read_excel("materials.xlsx")

materials_df = load_materials()

st.subheader("Калькулятор розрахунку собiвартостi матеріалів")

# === CSS для кастомных кнопок ===
st.markdown(
    """
    <style>
    /* зелёная кнопка Excel */
    div[data-testid="stDownloadButton"] > button {
        background-color: #79ab7c !important;
        color: white !important;
        padding: 12px 24px;
        font-size: 16px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #45a049 !important;
        color: white !important;
    }

    /* синяя кнопка Розрахувати */
    div[data-testid="stButton"] > button:has(span:contains("Розрахувати")) {
        background-color: #008CBA !important;
        color: white !important;
        padding: 12px 24px;
        font-size: 16px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    div[data-testid="stButton"] > button:has(span:contains("Розрахувати")):hover {
        background-color: #007bb5 !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# === Инициализация доступных деталей ===
if "available_details" not in st.session_state:
    st.session_state.available_details = ["Рама"]  # пока доступна только Рама

# === Выбор детали ===
select_options = []
for d in ALL_DETAILS:
    if d in st.session_state.available_details:
        select_options.append(d)
    else:
        select_options.append(f"{d} (не доступно)")

selected_raw = st.selectbox("Оберіть деталь:", options=select_options)

if selected_raw.endswith("(не доступно)"):
    st.warning("Ця деталь поки недоступна для розрахунку.")
    selected_detail = st.session_state.available_details[0]
else:
    selected_detail = selected_raw

detail_mass = DETAIL_MASS_KG[selected_detail]
st.info(f"Маса рідкої сталі для однієї деталі: {detail_mass} кг")

# === Инициализация списка итераций ===
if "iterations" not in st.session_state:
    st.session_state.iterations = [{
        "stage": STOP_STAGES[0],
        "qty": 0,
        "result": None,
        "sum": 0.0
    }]

# === Функции ===
def compute_iteration(detail_mass, stage_name, qty):
    idx_stage = PROCESS_STAGES_ORDERED.index(stage_name)
    stages_to_calc = PROCESS_STAGES_ORDERED[:idx_stage+1]

    stage_df = materials_df[materials_df["process_stage"].isin(stages_to_calc)].copy()
    stage_df["price"] = stage_df["price"].fillna(0)
    stage_df["quantity"] = stage_df["rate_per_kg"] * detail_mass * qty
    stage_df["total_cost"] = (stage_df["quantity"] * stage_df["price"]).round(2)
    stage_df["порція деталей"] = f"{qty} шт. до {stage_name}"
    stage_df["маса рідкої сталі на порцію, кг"] = detail_mass * qty

    nice = stage_df[[
        "operation_name", "unit", "price", "quantity", "total_cost",
        "process_stage", "порція деталей", "маса рідкої сталі на порцію, кг"
    ]].copy()
    nice.columns = [
        "Найменування", "Одиниця", "Ціна за одиницю, грн.", "Кількість",
        "Вартість, грн.", "Стадія процесу", "Порція деталей", "Маса рідкої сталі, кг"
    ]
    nice = nice.reset_index(drop=True)
    nice.index += 1
    nice.index.name = "№"

    s = float(nice["Вартість, грн."].sum().round(2))
    return nice, s

def to_excel_single(portion_df, total_sum, selected_detail, portion_name):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook  = writer.book
        worksheet = workbook.add_worksheet("Матеріали")
        writer.sheets["Матеріали"] = worksheet

        bold = workbook.add_format({"bold": True})
        money_fmt = workbook.add_format({"num_format": "#,##0.00"})

        title = f"Розрахунок матеріалів для {selected_detail} ({portion_name})"
        worksheet.write("A1", title, bold)

        for col_num, col_name in enumerate(portion_df.columns):
            worksheet.write(2, col_num, col_name, bold)

        for i in range(len(portion_df)):
            for col_num, val in enumerate(portion_df.iloc[i]):
                if isinstance(val, (int, float)):
                    worksheet.write(i+3, col_num, val, money_fmt)
                else:
                    worksheet.write(i+3, col_num, val)

        worksheet.write(len(portion_df)+4, 1, "Сумарна вартість, грн.:", bold)
        cost_col = portion_df.columns.get_loc("Вартість, грн.")
        worksheet.write(len(portion_df)+4, cost_col, total_sum, bold)

        for i, col in enumerate(portion_df.columns):
            max_len = max([len(str(s)) for s in portion_df[col]] + [len(col)])
            worksheet.set_column(i, i, max_len + 2)

    output.seek(0)
    return output

def insert_iteration_after(idx):
    st.session_state.iterations.insert(
        idx + 1,
        {"stage": STOP_STAGES[0], "qty": 0, "result": None, "sum": 0.0}
    )


# === Рендер итераций ===
for idx, it in enumerate(st.session_state.iterations):
    st.markdown(f"##### Група {idx + 1}")

    stage_key = f"stage_{idx}"
    qty_key   = f"qty_{idx}"

    if stage_key not in st.session_state:
        st.session_state[stage_key] = it["stage"]
    if qty_key not in st.session_state:
        st.session_state[qty_key] = it["qty"]

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        st.selectbox("Стадія зупинки:", STOP_STAGES, key=stage_key)
    with c2:
        st.number_input("Кількість деталей:", min_value=0, step=1, key=qty_key)
    with c3:
        if idx > 0:  # первую итерацию не удаляем
            if st.button("❌", key=f"remove_{idx}"):
                st.session_state.iterations.pop(idx)
                st.rerun()

    it["stage"] = st.session_state[stage_key]
    it["qty"]   = st.session_state[qty_key]

    if st.button("Розрахувати", key=f"calc_{idx}"):
        if it["qty"] <= 0:
            st.warning("Вкажіть кількість більше нуля, щоб виконати розрахунок.")
        else:
            nice_df, ssum = compute_iteration(detail_mass, it["stage"], it["qty"])
            it["result"] = nice_df
            it["sum"] = ssum
            st.rerun()

    if it["result"] is not None:
        st.dataframe(it["result"], use_container_width=True)
        formatted_sum = f"{it['sum']:,.2f}".replace(",", " ").replace(".", ",")
        st.write(f"**Сумарна вартість матерiалiв: {formatted_sum} грн.**")

        portion_name = it["result"]["Порція деталей"].iloc[0]

        c1, c2 = st.columns([1, 1])
        with c1:
            st.download_button(
                label="💾 Зберегти в Excel",
                data=to_excel_single(it["result"], it["sum"], selected_detail, portion_name),
                file_name=f"Матеріали_{selected_detail}_ітерація_{idx+1}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"save_{idx}"
            )
        with c2:
            if st.button("➕ Додати ітерацію", key=f"add_{idx}"):
                insert_iteration_after(idx)
                st.rerun()


    st.divider()
