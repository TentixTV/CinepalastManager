# CinePalast Manager 🎬

**CinePalast Manager** ist eine serverlose, lokale Desktop-Anwendung zur Archivierung von Filmmedien für **"Mannis Kinopalast"** (Konzept/Idee von Martin K.). Die Anwendung kombiniert eine moderne Benutzeroberfläche (Kino-Darkmode mit cyanfarbenen Akzenten) mit lokaler SQLite-Speicherung und automatischer Metadaten-Abfrage über die TMDB API in deutscher Sprache.

---

## 🚀 Features

- **Modernes Kino-Design**: Dunkles Farbschema mit leuchtenden Cyan/Teal-Akzenten und flüssigen Hover-Effekten (CustomTkinter).
- **Responsive Film-Galerie**: Dynamisches Raster-Layout, das sich beim Verändern der Fenstergröße automatisch anpasst.
- **Echtzeit-Offline-Suche**: Schnelle Suche über Titel, Schauspieler, Genre, Regisseur oder Filmreihe direkt aus der lokalen SQLite-Datenbank.
- **TMDB Scraper (Deutsch)**: Vollautomatische Metadaten-Abfrage der Filminformationen und FSK-Freigaben für Deutschland.
- **Lokale Bild-Cache-Archivierung**: Automatischer Download von hochauflösenden Plakaten und Bannern in lokale Verzeichnisse (`assets/posters/` und `assets/banners/`), um Bandbreite zu sparen und eine dauerhafte Offline-Nutzung zu sichern.
- **Lokale Fallback-Bilder**: Bei fehlender Internetverbindung oder manuell hinzugefügten Filmen ohne Bild werden mithilfe von Pillow ansprechende Platzhalter-Bilder generiert.
- **Synchronsprecher-Einträge**: Manuelle Erfassung deutscher Synchronsprecher direkt über die in-App Filmdetails-Bearbeitung.

---

## 🛠️ Technische Voraussetzungen

- **Python**: Version 3.11 oder höher
- **Betriebssystem**: Windows (kompilierbar als Standalone `.exe`)
- **Datenbank**: SQLite 3 (integriert, keine Server-Installation nötig)

---

## 📦 Installation und Setup

1. **Repository klonen**
   ```bash
   git clone https://github.com/TentixTV/CinepalastManager.git
   cd CinepalastManager
   ```

2. **Abhängigkeiten installieren**
   Stellen Sie sicher, dass Sie die benötigten Python-Bibliotheken installiert haben:
   ```bash
   pip install customtkinter requests pillow
   ```

3. **Anwendung ausführen**
   Starten Sie die App über das Terminal:
   ```bash
   python main.py
   ```
   *(Alternativ: `py main.py` unter Windows)*

4. **TMDB API konfigurieren**
   - Gehen Sie in der App auf **Einstellungen**.
   - Tragen Sie Ihren TMDB API-Schlüssel ein und klicken Sie auf **Testen** und **Speichern**.
   - Nun können Sie über **Film hinzufügen** die Online-Suche nutzen!

---

## 🗃️ Lokale Datenbank (SQLite)

Beim ersten Start der Anwendung wird automatisch die Datenbank-Datei `cinepalast.db` angelegt. Die Tabelle `filme` wird mit folgendem Schema initialisiert:

- **ID**: `INTEGER PRIMARY KEY AUTOINCREMENT`
- **Name / Titel**: `titel (TEXT)`
- **Jahr**: `jahr (INTEGER)`
- **Schauspieler / Cast**: `schauspieler_cast (TEXT)` (Kommagetrennte Liste)
- **Genre / Richtung**: `genre_richtung (TEXT)`
- **Laufzeit in min**: `laufzeit_min (INTEGER)`
- **Handlung / Beschreibung**: `handlung_beschreibung (TEXT)`
- **FSK**: `fsk (TEXT)`
- **Produktionsfirma / Studio**: `produktionsfirma_studio (TEXT)`
- **Regisseur**: `regisseur (TEXT)`
- **Filmreihe**: `filmreihe (TEXT)`
- **Produktionsland**: `produktionsland (TEXT)`
- **Deutsche Synchronsprecher**: `deutsche_synchronsprecher (TEXT)`
- **Poster_Pfad**: `poster_pfad (TEXT)` (Lokaler relativer Dateipfad)
- **Banner_Pfad**: `banner_pfad (TEXT)` (Lokaler relativer Dateipfad)

---

## 🛠️ Kompilierung mit PyInstaller (.exe erstellen)

Die Anwendung ist dafür optimiert, als eigenständige Windows-Executable gebündelt zu werden. 

### Vorbereitung
1. Installieren Sie PyInstaller (falls noch nicht vorhanden):
   ```bash
   pip install pyinstaller
   ```
2. Fügen Sie optional eine `icon.ico`-Datei im Projekt-Root-Verzeichnis hinzu. Die Anwendung bindet dieses Icon beim Start nativ als Anwendungsfenster-Symbol ein und PyInstaller nutzt es für das App-Icon.

### Kompilier-Befehl
Führen Sie folgenden Befehl im Projektordner aus, um eine einzige, saubere `.exe` ohne Konsolenfenster im Hintergrund zu erstellen:

```bash
pyinstaller --noconfirm --onefile --windowed --icon=icon.ico --name "CinePalast" main.py
```

*Hinweis:* Nach erfolgreichem Durchlauf finden Sie die fertige ausführbare Datei `CinePalast.exe` im Ordner `dist/`. Legen Sie diese an einem beliebigen Ort auf Ihrem PC ab. Die Ordner `assets/` und die Datei `cinepalast.db` werden automatisch relativ zur `.exe` angelegt, sobald diese gestartet wird.
