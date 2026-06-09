# CinePalast C++ SQLite Client

Dieses Verzeichnis enthält eine C++-Implementierung eines SQLite-Datenbank-Clients zur Abfrage der `cinepalast.db` des CinePalast Managers.

## Voraussetzungen
* Ein C++-Compiler (z.B. GCC/g++, Clang oder MSVC)
* SQLite3 Entwicklungsbibliotheken (Header und Library)

## Kompilieren und Ausführen

### Unter Windows (mit MinGW / g++)
1. Installieren Sie MSYS2 oder ein MinGW-Paket, welches `sqlite3` enthält.
2. Kompilieren Sie den Client:
   ```bash
   g++ -o CinePalastClient.exe CinePalastClient.cpp -lsqlite3
   ```
3. Führen Sie die Exe-Datei aus:
   ```bash
   CinePalastClient.exe "../../CinePalast/cinepalast.db"
   ```

### Unter Debian/Ubuntu Linux
1. Installieren Sie die SQLite3-Entwicklungsbibliothek:
   ```bash
   sudo apt-get install libsqlite3-dev
   ```
2. Kompilieren Sie das Programm:
   ```bash
   g++ -o CinePalastClient CinePalastClient.cpp -lsqlite3
   ```
3. Starten Sie das Programm:
   ```bash
   ./CinePalastClient "../../CinePalast/cinepalast.db"
   ```

### Unter macOS
1. Kompilieren Sie das Programm (macOS bringt SQLite3 standardmäßig mit):
   ```bash
   clang++ -o CinePalastClient CinePalastClient.cpp -lsqlite3
   ```
2. Starten Sie das Programm:
   ```bash
   ./CinePalastClient "../../CinePalast/cinepalast.db"
   ```
