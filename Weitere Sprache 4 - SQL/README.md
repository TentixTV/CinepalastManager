# CinePalast SQL & T-SQL Datenbank-Skripte

Dieses Verzeichnis enthält SQL- und T-SQL-Skripte zur Erstellung der Tabellenstruktur, zum Seeding von Demo-Daten sowie gespeicherte Prozeduren (Stored Procedures) für Microsoft SQL Server (T-SQL).

## Verzeichnisstruktur

*   **`schema.sql`**: Standard-SQL / SQLite-Skript zur Erstellung der Tabelle `media`.
*   **`tsql_procedures.sql`**: Microsoft SQL Server (T-SQL) Skript zur Tabellenerstellung und Definition von optimierten stored procedures:
    *   `sp_AddMovie`: Hinzufügen von neuen Filmeinträgen inklusive Rückgabe der neuen ID.
    *   `sp_SearchMovies`: Suche nach Filmen, Regisseuren oder Schauspielern mit Wildcards.
    *   `sp_GetMovieStats`: Aggregationsstatistiken über Filmlängen, Genres und FSK-Verteilungen.
*   **`queries.sql`**: Eine Sammlung nützlicher Standard-Abfragen (Select, Search, Update, Delete, Aggregationen).

## Verwendung mit SQLite (Standard SQL)

Sie können die Standard-Skripte direkt in SQLite (z.B. über das Python-Backend oder Tools wie DB Browser for SQLite) ausführen:

```sql
-- Erstellen der Tabelle
.read schema.sql

-- Einfügen der Demodaten und Abfragen
.read queries.sql
```

## Verwendung mit Microsoft SQL Server (T-SQL)

1. Verbinden Sie sich mit Ihrer SQL Server Instanz (z. B. über SQL Server Management Studio oder VS Code SQL Extension).
2. Führen Sie das Skript `tsql_procedures.sql` aus, um die Tabelle `media` und die Stored Procedures in Ihrer Zieldatenbank anzulegen.
3. Rufen Sie die Prozeduren über Transact-SQL ab:

### Beispiele:

*   **Film hinzufügen:**
    ```sql
    DECLARE @GeneratedID INT;
    EXEC dbo.sp_AddMovie 
        @Name = N'The Dark Knight', 
        @Jahr = 2008, 
        @Regisseur = N'Christopher Nolan', 
        @Genre = N'Action, Thriller', 
        @Laufzeit_min = 152, 
        @FSK = N'16',
        @NewID = @GeneratedID OUTPUT;
    SELECT @GeneratedID AS NeueFilmID;
    ```

*   **Suchen nach Schauspielern:**
    ```sql
    EXEC dbo.sp_SearchMovies @SearchQuery = N'Adam Sandler', @SearchFilter = N'Schauspieler';
    ```

*   **Berichte und Statistiken laden:**
    ```sql
    EXEC dbo.sp_GetMovieStats;
    ```
