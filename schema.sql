-- Практична робота №06
-- Варіанти: PY-D6P / PR06-C6P
-- База даних: kino.db

-- Видалення таблиць у зворотному порядку залежностей
DROP TABLE IF EXISTS awards;
DROP TABLE IF EXISTS views;
DROP TABLE IF EXISTS films;

-- 1. Таблиця фільмів
CREATE TABLE films (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER NOT NULL
        CHECK (year BETWEEN 1890 AND 2100),
    director TEXT NOT NULL DEFAULT 'невідомо',
    duration_min INTEGER
        CHECK (duration_min IS NULL OR duration_min > 0)
);

-- 2. Таблиця переглядів
CREATE TABLE views (
    id INTEGER PRIMARY KEY,
    film_id INTEGER NOT NULL REFERENCES films(id),
    viewed_on TEXT NOT NULL,
    cinema TEXT NOT NULL,
    viewers INTEGER NOT NULL CHECK (viewers > 0)
);

-- 3. Таблиця нагород — індивідуальний варіант PR06-C6P
CREATE TABLE awards (
    id INTEGER PRIMARY KEY,
    film_id INTEGER NOT NULL REFERENCES films(id),
    festival TEXT NOT NULL,
    year INTEGER NOT NULL
        CHECK (year BETWEEN 1920 AND 2026),
    won INTEGER NOT NULL DEFAULT 0
        CHECK (won IN (0, 1))
);

-- Індекси зовнішніх ключів
CREATE INDEX idx_views_film ON views(film_id);
CREATE INDEX idx_awards_film ON awards(film_id);
