"""Практична робота №06: інтерактивна панель кіно."""
# Варіанти: PY-D6P / PR06-C6P

import sqlite3
import threading
from pathlib import Path

import pandas as pd
import streamlit as st

DB = Path(__file__).parent / "kino.db"

st.set_page_config(
    page_title="Кіно — PR06-C6P",
    page_icon="🎬",
    layout="wide"
)

# Одне з'єднання SQLite для застосунку
@st.cache_resource
def zyednannya():
    conn = sqlite3.connect(
        DB,
        check_same_thread=False
    )
    conn.execute("PRAGMA foreign_keys = ON")
    return conn, threading.RLock()


# Отримуємо реальні кінотеатри з БД
@st.cache_data
def kino_teatry():
    conn, lock = zyednannya()

    with lock:
        rows = conn.execute("""
            SELECT DISTINCT cinema
            FROM views
            ORDER BY cinema
        """).fetchall()

    return [row[0] for row in rows]


# Вибірка для таблиці, метрик і майбутніх графіків
@st.cache_data(ttl=300)
def zavantazhyty(
    rik_vid: int,
    rik_do: int,
    cinema: str,
    only_awarded: bool
) -> pd.DataFrame:

    sql = """
        WITH award_counts AS (
            SELECT
                film_id,
                COUNT(*) AS awards_count
            FROM awards
            GROUP BY film_id
        )
        SELECT
            f.id AS film_id,
            f.title,
            f.year,
            f.director,
            f.duration_min,
            COALESCE(a.awards_count, 0) AS awards_count,
            v.id AS view_id,
            v.viewed_on,
            v.cinema,
            v.viewers
        FROM films AS f
        LEFT JOIN award_counts AS a
            ON a.film_id = f.id
        LEFT JOIN views AS v
            ON v.film_id = f.id
            AND (
                ? = 'Усі кінотеатри'
                OR v.cinema = ?
            )
        WHERE f.year BETWEEN ? AND ?
          AND (
                ? = 0
                OR a.film_id IS NOT NULL
          )
        ORDER BY
            f.director ASC,
            f.title ASC,
            v.viewed_on ASC
    """

    params = (
        cinema,
        cinema,
        rik_vid,
        rik_do,
        int(only_awarded)
    )

    conn, lock = zyednannya()

    with lock:
        return pd.read_sql_query(
            sql,
            conn,
            params=params
        )


# Заголовок
st.title("🎬 Кіно: аналітична панель")
st.caption(
    "Практична робота №06 | "
    "PY-D6P / PR06-C6P"
)

# Три обов'язкові віджети
with st.sidebar:
    st.header("Фільтри")

    rik_vid, rik_do = st.slider(
        "Діапазон років випуску",
        min_value=1960,
        max_value=1989,
        value=(1960, 1989)
    )

    cinema = st.selectbox(
        "Кінотеатр",
        options=[
            "Усі кінотеатри",
            *kino_teatry()
        ]
    )

    only_awarded = st.checkbox(
        "Тільки фільми із записами awards",
        value=False
    )

    st.divider()
    st.caption("Основний зріз: 1960–1989 роки")

# Один SQL-запит для всіх даних панелі
events = zavantazhyty(
    rik_vid,
    rik_do,
    cinema,
    only_awarded
)

# Узагальнення за фільмами без подвоєння нагород
film_info = (
    events[
        [
            "film_id",
            "title",
            "year",
            "director",
            "duration_min",
            "awards_count"
        ]
    ]
    .drop_duplicates(subset=["film_id"])
)

view_stats = (
    events.groupby("film_id", as_index=False)
    .agg(
        pereglyadiv=("view_id", "count"),
        glyadachiv=("viewers", "sum")
    )
)

stats = film_info.merge(
    view_stats,
    on="film_id",
    how="left",
    validate="one_to_one"
)

stats = stats.sort_values(
    ["director", "title"],
    ascending=[True, True]
)

# Метрики
films_count = len(stats)

awarded_count = int(
    (stats["awards_count"] > 0).sum()
)

share = (
    awarded_count / films_count * 100
    if films_count
    else 0.0
)

viewers_total = int(
    stats["glyadachiv"].sum()
)

st.subheader("Основні показники")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Фільмів у вибірці",
    films_count
)

c2.metric(
    "Фільмів із записами awards",
    awarded_count
)

c3.metric(
    "Частка із записами awards",
    f"{share:.1f}%"
)

st.metric(
    "Сумарна кількість глядачів",
    f"{viewers_total:,}".replace(",", " ")
)

# Додаткова характеристика базового варіанта
durations = stats.loc[
    stats["duration_min"].between(75, 95),
    "duration_min"
]

median_duration = durations.median()

if pd.notna(median_duration):
    st.caption(
        "Медіанна тривалість фільмів "
        "із хронометражем 75–95 хв: "
        f"{median_duration:.1f} хв"
    )

# Таблиця
st.subheader("Фільми за вибраними умовами")

columns = {
    "title": "Назва",
    "year": "Рік",
    "director": "Режисер",
    "duration_min": "Тривалість, хв",
    "awards_count": "Записів awards",
    "pereglyadiv": "Переглядів",
    "glyadachiv": "Глядачів"
}

if stats.empty:
    st.info("За вибраними умовами фільмів немає.")
else:
    st.dataframe(
        stats[list(columns)].rename(columns=columns),
        width="stretch",
        hide_index=True
    )

print(
    f"ФІЛЬТРИ: {rik_vid}-{rik_do}, "
    f"кінотеатр={cinema}, "
    f"тільки_з_нагородами={only_awarded}, "
    f"фільмів={films_count}, "
    f"глядачів={viewers_total}, "
    f"частка={share:.1f}%",
    flush=True
)

st.caption(
    "Перегляди — синтетичні навчальні дані. "
    "Фестивальні відзнаки збережено у таблиці awards."
)


# === PR06-C6P: CHARTS V1 ===

import matplotlib.pyplot as plt

st.divider()
st.subheader("Аналітика переглядів")

# Виключаємо фільми без записів про перегляди.
# LEFT JOIN може залишати для них порожні поля views.
valid_events = events.loc[
    events["view_id"].notna()
].copy()

valid_events["viewed_on"] = pd.to_datetime(
    valid_events["viewed_on"],
    errors="coerce"
)

valid_events["viewers"] = pd.to_numeric(
    valid_events["viewers"],
    errors="coerce"
)

valid_events = valid_events.dropna(
    subset=["viewed_on", "viewers"]
)

if valid_events.empty:
    st.info(
        "Для вибраних фільтрів немає переглядів. "
        "Графіки не відображаються."
    )

else:
    # ГРАФІК 1 — накопичені глядачі за місяцями
    monthly = (
        valid_events
        .groupby(
            valid_events["viewed_on"].dt.to_period("M")
        )["viewers"]
        .sum()
        .sort_index()
    )

    # Перетворюємо місячні періоди на дати
    monthly.index = monthly.index.to_timestamp()

    # Додаємо місяці, у яких не було переглядів
    all_months = pd.date_range(
        start=monthly.index.min(),
        end=monthly.index.max(),
        freq="MS"
    )

    monthly = monthly.reindex(
        all_months,
        fill_value=0
    )

    cumulative = monthly.cumsum().to_frame(
        name="Накопичені глядачі"
    )

    # ГРАФІК 2 — гістограма глядачів за сеанс
    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.hist(
        valid_events["viewers"],
        bins=24,
        edgecolor="white",
        linewidth=0.6
    )

    ax.set_xlabel("Глядачів на один перегляд")
    ax.set_ylabel("Кількість переглядів")
    ax.set_title("Розподіл відвідуваності")
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    # Виводимо графіки поруч
    left, right = st.columns(2)

    with left:
        st.markdown(
            "**Накопичені глядачі за місяцями**"
        )
        st.area_chart(
            cumulative,
            height=330
        )

    with right:
        st.markdown(
            "**Глядачі на один перегляд**"
        )
        st.pyplot(fig)

    plt.close(fig)

    # Контроль даних графіків
    graph_total = int(cumulative.iloc[-1, 0])

    assert graph_total == viewers_total

    print(
        f"ГРАФІКИ: місяців={len(cumulative)}, "
        f"переглядів={len(valid_events)}, "
        f"глядачів={graph_total}",
        flush=True
    )

    st.caption(
        f"У вибірці {len(valid_events):,} переглядів. "
        f"Накопичена кількість глядачів: "
        f"{graph_total:,}."
        .replace(",", " ")
    )


# === PR06-C6P: AWARDS FORM V1 ===

st.divider()
st.subheader("Додавання фестивального запису")

st.caption(
    "Форма додає запис до таблиці awards. "
    "Значення won = 1 означає отриману відзнаку, "
    "won = 0 — участь без отриманої відзнаки."
)

# Список фільмів завантажується безпосередньо з БД
db_conn, db_lock = zyednannya()

with db_lock:
    film_rows = db_conn.execute("""
        SELECT id, title, year
        FROM films
        ORDER BY title, id
    """).fetchall()

film_labels = {
    film_id: f"{title} ({year})"
    for film_id, title, year in film_rows
}

# Стан користувацької сесії
if "awards_added" not in st.session_state:
    st.session_state["awards_added"] = 0

if "award_message" not in st.session_state:
    st.session_state["award_message"] = ""

if "test_award" not in st.session_state:
    st.session_state["test_award"] = None

if st.session_state["award_message"]:
    st.success(st.session_state["award_message"])

# Форма введення
with st.form("new_award_form", clear_on_submit=True):

    selected_film_id = st.selectbox(
        "Фільм",
        options=list(film_labels),
        format_func=lambda film_id: film_labels[film_id]
    )

    festival = st.text_input(
        "Назва фестивалю",
        placeholder="Наприклад, МКФ Карлові Вари"
    )

    award_year = st.number_input(
        "Рік фестивалю",
        min_value=1920,
        max_value=2026,
        value=2020,
        step=1
    )

    won = st.checkbox(
        "Отримано нагороду (won = 1)",
        value=False
    )

    submitted = st.form_submit_button(
        "Додати запис",
        type="primary"
    )

# Зберігання після натискання кнопки
if submitted:

    festival_clean = festival.strip()

    if not festival_clean:
        st.error("Вкажіть назву фестивалю.")

    else:
        try:
            with db_lock:
                with db_conn:
                    cursor = db_conn.execute("""
                        INSERT INTO awards
                            (film_id, festival, year, won)
                        VALUES (?, ?, ?, ?)
                    """, (
                        int(selected_film_id),
                        festival_clean,
                        int(award_year),
                        int(won)
                    ))

                    new_id = cursor.lastrowid

        except sqlite3.IntegrityError as exc:
            st.error(f"Помилка цілісності SQLite: {exc}")

        except sqlite3.Error as exc:
            st.error(f"Помилка бази даних: {exc}")

        else:
            # Скидаємо кеш після зміни даних
            zavantazhyty.clear()

            st.session_state["awards_added"] += 1
            st.session_state["award_message"] = (
                f"Запис #{new_id} додано: "
                f"{film_labels[selected_film_id]}, "
                f"фестиваль «{festival_clean}»."
            )

            # Запам'ятовуємо лише навчальний тест
            test_prefix = "[ТЕСТ PR06-C6P]"

            if festival_clean.startswith(test_prefix):
                st.session_state["test_award"] = (
                    new_id,
                    festival_clean
                )

            print(
                f"ФОРМА: INSERT awards id={new_id}, "
                f"film_id={selected_film_id}, "
                f"year={award_year}, won={int(won)}",
                flush=True
            )

            st.rerun()

# Можливість безпечно прибрати навчальний тест
test_award = st.session_state["test_award"]

if test_award is not None:

    st.info(
        "У базі є навчальний тестовий запис, "
        "доданий під час цієї сесії."
    )

    if st.button("Видалити навчальний тестовий запис"):

        test_id, test_festival = test_award

        with db_lock:
            with db_conn:
                deleted = db_conn.execute("""
                    DELETE FROM awards
                    WHERE id = ?
                      AND festival = ?
                """, (
                    test_id,
                    test_festival
                )).rowcount

        if deleted == 1:
            zavantazhyty.clear()

            st.session_state["test_award"] = None
            st.session_state["award_message"] = (
                f"Тестовий запис #{test_id} видалено."
            )

            print(
                f"ФОРМА: DELETE test_award id={test_id}",
                flush=True
            )

            st.rerun()

        else:
            st.warning(
                "Тестовий запис не знайдено. "
                "Інші нагороди не змінено."
            )

st.caption(
    "Записів додано в цій сесії: "
    f"{st.session_state['awards_added']}"
)
