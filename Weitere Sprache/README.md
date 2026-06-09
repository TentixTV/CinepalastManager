# CinePalast C# SQLite Client

Dieses Verzeichnis enthält eine C#-Implementierung eines SQLite-Datenbank-Clients zur Abfrage der `cinepalast.db` des CinePalast Managers.

## Voraussetzungen
* [.NET SDK](https://dotnet.microsoft.com/download) (Version 6.0, 7.0 oder 8.0)

## Projekt einrichten und ausführen

1. **Neues Konsolenprojekt erstellen:**
   Führen Sie folgende Befehle in Ihrem Terminal/PowerShell in diesem Ordner aus:
   ```bash
   dotnet new console -n CinePalastClientProj
   ```

2. **Kopieren Sie die Client-Datei:**
   Verschieben oder kopieren Sie die `CinePalastClient.cs` in den neu erstellten Projektordner `CinePalastClientProj/` und löschen Sie dort die automatisch generierte `Program.cs`.

3. **SQLite-Paket hinzufügen:**
   Navigieren Sie in den Projektordner und fügen Sie das Microsoft SQLite NuGet-Paket hinzu:
   ```bash
   cd CinePalastClientProj
   dotnet add package Microsoft.Data.Sqlite
   ```

4. **Projekt erstellen und ausführen:**
   Führen Sie das Projekt aus und übergeben Sie optional den Pfad zur `cinepalast.db` als Argument (Standardwert zeigt auf den übergeordneten App-Ordner):
   ```bash
   dotnet run -- "../../CinePalast/cinepalast.db"
   ```
