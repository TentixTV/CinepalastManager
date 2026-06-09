-- CinePalast Datenbank-Schema & Gespeicherte Prozeduren für Microsoft SQL Server (T-SQL)
-- Erstellt die Tabelle 'media' mit SQL-Server kompatiblen Datentypen und Prozeduren.

-- 1. Tabelle erstellen falls nicht existent
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[media]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[media] (
        [ID] INT IDENTITY(1,1) PRIMARY KEY,
        [Name] NVARCHAR(255) NOT NULL,
        [Jahr] INT NULL,
        [Schauspieler] NVARCHAR(MAX) NULL,
        [Genre] NVARCHAR(255) NULL,
        [Laufzeit_min] INT NULL,
        [Beschreibung] NVARCHAR(MAX) NULL,
        [FSK] NVARCHAR(50) NULL,
        [Produktionsfirma] NVARCHAR(255) NULL,
        [Regisseur] NVARCHAR(255) NULL,
        [Filmreihe] NVARCHAR(255) NULL,
        [Produktionsland] NVARCHAR(255) NULL,
        [Deutsche_Synchronsprecher] NVARCHAR(MAX) NULL,
        [Poster_Pfad] NVARCHAR(500) NULL,
        [Banner_Pfad] NVARCHAR(500) NULL
    );
END;
GO

-- 2. Gespeicherte Prozedur zum Hinzufügen eines Films
IF OBJECT_ID('dbo.sp_AddMovie', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_AddMovie;
GO

CREATE PROCEDURE [dbo].[sp_AddMovie]
    @Name NVARCHAR(255),
    @Jahr INT = NULL,
    @Schauspieler NVARCHAR(MAX) = NULL,
    @Genre NVARCHAR(255) = NULL,
    @Laufzeit_min INT = NULL,
    @Beschreibung NVARCHAR(MAX) = NULL,
    @FSK NVARCHAR(50) = NULL,
    @Produktionsfirma NVARCHAR(255) = NULL,
    @Regisseur NVARCHAR(255) = NULL,
    @Filmreihe NVARCHAR(255) = NULL,
    @Produktionsland NVARCHAR(255) = NULL,
    @Deutsche_Synchronsprecher NVARCHAR(MAX) = NULL,
    @Poster_Pfad NVARCHAR(500) = NULL,
    @Banner_Pfad NVARCHAR(500) = NULL,
    @NewID INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO [dbo].[media] (
        [Name], [Jahr], [Schauspieler], [Genre], [Laufzeit_min], 
        [Beschreibung], [FSK], [Produktionsfirma], [Regisseur], 
        [Filmreihe], [Produktionsland], [Deutsche_Synchronsprecher], 
        [Poster_Pfad], [Banner_Pfad]
    )
    VALUES (
        @Name, @Jahr, @Schauspieler, @Genre, @Laufzeit_min, 
        @Beschreibung, @FSK, @Produktionsfirma, @Regisseur, 
        @Filmreihe, @Produktionsland, @Deutsche_Synchronsprecher, 
        @Poster_Pfad, @Banner_Pfad
    );
    
    SET @NewID = SCOPE_IDENTITY();
END;
GO

-- 3. Gespeicherte Prozedur zur Suche nach Filmen
IF OBJECT_ID('dbo.sp_SearchMovies', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_SearchMovies;
GO

CREATE PROCEDURE [dbo].[sp_SearchMovies]
    @SearchQuery NVARCHAR(255),
    @SearchFilter NVARCHAR(50) = 'Alles'
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @LikeQuery NVARCHAR(257) = '%' + @SearchQuery + '%';
    
    IF @SearchFilter = 'Film'
    BEGIN
        SELECT * FROM [dbo].[media]
        WHERE [Name] LIKE @LikeQuery OR [Filmreihe] LIKE @LikeQuery
        ORDER BY [Name] ASC;
    END
    ELSE IF @SearchFilter = 'Schauspieler'
    BEGIN
        SELECT * FROM [dbo].[media]
        WHERE [Schauspieler] LIKE @LikeQuery
        ORDER BY [Name] ASC;
    END
    ELSE IF @SearchFilter = 'Regisseur'
    BEGIN
        SELECT * FROM [dbo].[media]
        WHERE [Regisseur] LIKE @LikeQuery
        ORDER BY [Name] ASC;
    END
    ELSE
    BEGIN
        SELECT * FROM [dbo].[media]
        WHERE [Name] LIKE @LikeQuery
           OR [Schauspieler] LIKE @LikeQuery
           OR [Genre] LIKE @LikeQuery
           OR [Regisseur] LIKE @LikeQuery
           OR [Filmreihe] LIKE @LikeQuery
        ORDER BY [Name] ASC;
    END
END;
GO

-- 4. Gespeicherte Prozedur für Statistiken und Berichte
IF OBJECT_ID('dbo.sp_GetMovieStats', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_GetMovieStats;
GO

CREATE PROCEDURE [dbo].[sp_GetMovieStats]
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Gesamtstatistiken ausgeben
    SELECT 
        COUNT(*) AS GesamtFilme,
        SUM([Laufzeit_min]) AS GesamtLaufzeitMinuten,
        AVG([Laufzeit_min]) AS DurchschnittlicheLaufzeitMinuten,
        MIN([Jahr]) AS AeltesterFilmJahr,
        MAX([Jahr]) AS NeuesterFilmJahr
    FROM [dbo].[media];
    
    -- Anzahl Filme nach Genre
    SELECT [Genre], COUNT(*) AS AnzahlFilme
    FROM [dbo].[media]
    WHERE [Genre] IS NOT NULL
    GROUP BY [Genre]
    ORDER BY AnzahlFilme DESC;
    
    -- Anzahl Filme nach FSK-Freigabe
    SELECT [FSK], COUNT(*) AS AnzahlFilme
    FROM [dbo].[media]
    WHERE [FSK] IS NOT NULL
    GROUP BY [FSK]
    ORDER BY [FSK] ASC;
END;
GO
