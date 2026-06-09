-- CinePalast Manager - Nützliche SQL-Abfragen & Datenpflege-Skripte
-- Dieses Skript enthält Standard-SQL-Abfragen für den alltäglichen Gebrauch.

-- 1. Demo-Daten einfügen (Seeding)
INSERT INTO media (Name, Jahr, Regisseur, Schauspieler, Genre, Laufzeit_min, FSK, Beschreibung)
VALUES 
('Inception', 2010, 'Christopher Nolan', 'Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page', 'Sci-Fi, Action', 148, '12', 'Ein Dieb, der Geheimnisse aus dem Unterbewusstsein stiehlt, bekommt die Chance, seine Sünden reinzuwaschen.'),
('Interstellar', 2014, 'Christopher Nolan', 'Matthew McConaughey, Anne Hathaway, Jessica Chastain', 'Sci-Fi, Drama', 169, '12', 'Eine Gruppe von Entdeckern reist durch ein Wurmloch im Weltraum, um das Überleben der Menschheit zu sichern.'),
('Grown Ups', 2010, 'Dennis Dugan', 'Adam Sandler, Kevin James, Chris Rock, David Spade', 'Komödie', 102, '6', 'Fünf gute Freunde treffen sich nach vielen Jahren beim Begräbnis ihres ehemaligen Basketball-Trainers wieder.');

-- 2. Einfache Suchen (LIKE-Queries)
-- Suche nach Filmtitel oder Filmreihe
SELECT * FROM media 
WHERE Name LIKE '%Inception%' OR Filmreihe LIKE '%Inception%'
ORDER BY Name ASC;

-- Suche nach Schauspielern
SELECT * FROM media 
WHERE Schauspieler LIKE '%Adam Sandler%'
ORDER BY Name ASC;

-- Suche nach Regisseuren
SELECT * FROM media 
WHERE Regisseur LIKE '%Christopher Nolan%'
ORDER BY Name ASC;

-- Globale Suche (Titel, Schauspieler, Regisseur, Genre, Filmreihe)
SELECT * FROM media 
WHERE Name LIKE '%2010%' 
   OR Schauspieler LIKE '%2010%' 
   OR Genre LIKE '%2010%' 
   OR Regisseur LIKE '%2010%' 
   OR Filmreihe LIKE '%2010%'
ORDER BY Name ASC;

-- 3. Datenpflege (Updates & Deletes)
-- Filmdaten aktualisieren
UPDATE media 
SET Laufzeit_min = 148, FSK = '12', Genre = 'Sci-Fi, Thriller' 
WHERE Name = 'Inception';

-- Film löschen
DELETE FROM media WHERE ID = 3;

-- 4. Auswertungen und Statistiken
-- Anzahl Filme nach FSK-Freigabe gruppieren
SELECT FSK, COUNT(*) AS Anzahl_Filme 
FROM media 
GROUP BY FSK 
ORDER BY FSK ASC;

-- Genres auswerten (grobe Auflistung)
SELECT Genre, COUNT(*) AS Anzahl 
FROM media 
GROUP BY Genre 
ORDER BY Anzahl DESC;

-- Durchschnittliche Filmlänge ermitteln
SELECT AVG(Laufzeit_min) AS Durchschnitts_Laufzeit, 
       SUM(Laufzeit_min) AS Gesamt_Laufzeit_aller_Filme,
       MAX(Laufzeit_min) AS Laengster_Film,
       MIN(Laufzeit_min) AS Kuerzester_Film
FROM media;
