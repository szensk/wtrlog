CREATE TABLE IF NOT EXISTS Source
(
    SourceId INTEGER PRIMARY KEY AUTOINCREMENT,
    SourceName TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Reading
(
    Time INTEGER NOT NULL,
    Temperature REAL NOT NULL,
    Humidity REAL NOT NULL,
    Pressure REAL NOT NULL,
    SourceId INTEGER,
    FOREIGN KEY (SourceId) REFERENCES Source(SourceId)
);

CREATE TABLE IF NOT EXISTS Switch
(
    Time INTEGER NOT NULL,
    State INTEGER NOT NULL,
    SourceId INTEGER,
    FOREIGN KEY (SourceId) REFERENCES Source(SourceId)
);

CREATE INDEX IF NOT EXISTS TimeSourceHumidity ON Reading(SourceId, Time, Humidity);
CREATE UNIQUE INDEX IF NOT EXISTS SourceName ON Source(SourceName);