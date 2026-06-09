-- CinePalast Datenbank-Schema (Standard-SQL / SQLite)
-- Dieses Skript erstellt die Tabelle 'media' für die Filmdatenbank.

CREATE TABLE IF NOT EXISTS media (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Jahr INTEGER,
    Schauspieler TEXT,
    Genre TEXT,
    Laufzeit_min INTEGER,
    Beschreibung TEXT,
    FSK TEXT,
    Produktionsfirma TEXT,
    Regisseur TEXT,
    Filmreihe TEXT,
    Produktionsland TEXT,
    Deutsche_Synchronsprecher TEXT,
    Poster_Pfad TEXT,
    Banner_Pfad TEXT
);
