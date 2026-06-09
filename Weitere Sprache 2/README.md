# CinePalast Java SQLite Client

Dieses Verzeichnis enthält eine Java-Implementierung eines SQLite-Datenbank-Clients zur Abfrage der `cinepalast.db` des CinePalast Managers.

## Voraussetzungen
* [JDK (Java Development Kit)](https://adoptium.net/) (Version 11 oder neuer)

## Ausführen des Java-Clients

Da Java für die Verbindung mit SQLite einen JDBC-Treiber benötigt, müssen Sie die JDBC-Treiber-JAR-Datei herunterladen.

1. **SQLite-JDBC-Treiber herunterladen:**
   Laden Sie die neueste `.jar` Datei von [Xerial SQLite JDBC](https://github.com/xerial/sqlite-jdbc/releases) herunter (z.B. `sqlite-jdbc-3.45.1.0.jar`) und speichern Sie sie in diesem Ordner ab.

2. **Kompilieren:**
   Kompilieren Sie die Java-Datei unter Angabe des Klassenpfads:
   ```bash
   javac -cp "sqlite-jdbc-3.45.1.0.jar;." CinePalastClient.java
   ```
   *(Ersetzen Sie unter macOS/Linux das Semikolon `;` im Klassenpfad durch einen Doppelpunkt `:`)*

3. **Ausführen:**
   Führen Sie das kompilierte Java-Programm aus:
   ```bash
   java -cp "sqlite-jdbc-3.45.1.0.jar;." CinePalastClient "../../CinePalast/cinepalast.db"
   ```
