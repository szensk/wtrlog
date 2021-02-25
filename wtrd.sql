CREATE TABLE IF NOT EXISTS Reading
(
    Time INTEGER NOT NULL,
    Temperature REAL NOT NULL,
    Humidity REAL NOT NULL,
    Pressure REAL NOT NULL,
    Source TEXT
);

CREATE TABLE IF NOT EXISTS Switch
(
    Time INTEGER NOT NULL,
    State INTEGER NOT NULL,
    Device TEXT NOT NULL
);