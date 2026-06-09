#include <iostream>
#include <string>
#include <vector>
#include <sqlite3.h>

struct MediaItem {
    int id;
    std::string name;
    int jahr;
    std::string schauspieler;
    std::string genre;
    int laufzeit_min;
    std::string beschreibung;
    std::string fsk;
    std::string produktionsfirma;
    std::string regisseur;
    std::string filmreihe;
    std::string produktionsland;
    std::string deutsche_synchronsprecher;
    std::string poster_pfad;
    std::string banner_pfad;
};

// Callback function for sqlite3_exec (not strictly needed if using sqlite3_prepare_v2, which is preferred)
static int callback(void* data, int argc, char** argv, char** azColName) {
    for (int i = 0; i < argc; i++) {
        std::cout << azColName[i] << " = " << (argv[i] ? argv[i] : "NULL") << "\n";
    }
    std::cout << "\n";
    return 0;
}

int main(int argc, char* argv[]) {
    std::string dbPath = (argc > 1) ? argv[1] : "../CinePalast/cinepalast.db";
    std::string searchQuery = (argc > 2) ? argv[2] : "";
    std::string searchFilter = (argc > 3) ? argv[3] : "Alles";

    std::cout << "==================================================\n";
    std::cout << "CinePalast Manager \x97 C++ Datenbank Client\n";
    std::cout << "Verbindung mit Datenbank: " << dbPath << "\n";
    if (!searchQuery.empty()) {
        std::cout << "Suchbegriff:            \"" << searchQuery << "\" (Filter: " << searchFilter << ")\n";
    }
    std::cout << "==================================================\n\n";

    sqlite3* db;
    int rc;

    rc = sqlite3_open(dbPath.c_str(), &db);

    if (rc) {
        std::cerr << "Kann Datenbank nicht oeffnen: " << sqlite3_errmsg(db) << "\n";
        return(0);
    } else {
        std::cout << "Erfolgreich mit der Datenbank verbunden.\n\n";
    }

    std::string sql;
    if (searchQuery.empty()) {
        sql = "SELECT ID, Name, Jahr, Regisseur, Genre, Schauspieler FROM media ORDER BY Name ASC;";
    } else if (searchFilter == "Film") {
        sql = "SELECT ID, Name, Jahr, Regisseur, Genre, Schauspieler FROM media WHERE Name LIKE ? OR Filmreihe LIKE ? ORDER BY Name ASC;";
    } else if (searchFilter == "Schauspieler") {
        sql = "SELECT ID, Name, Jahr, Regisseur, Genre, Schauspieler FROM media WHERE Schauspieler LIKE ? ORDER BY Name ASC;";
    } else if (searchFilter == "Regisseur") {
        sql = "SELECT ID, Name, Jahr, Regisseur, Genre, Schauspieler FROM media WHERE Regisseur LIKE ? ORDER BY Name ASC;";
    } else {
        sql = "SELECT ID, Name, Jahr, Regisseur, Genre, Schauspieler FROM media WHERE Name LIKE ? OR Schauspieler LIKE ? OR Genre LIKE ? OR Regisseur LIKE ? OR Filmreihe LIKE ? ORDER BY Name ASC;";
    }
    
    sqlite3_stmt* stmt;
    rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, NULL);
    
    if (rc != SQLITE_OK) {
        std::cerr << "SQL-Fehler beim Vorbereiten: " << sqlite3_errmsg(db) << "\n";
        sqlite3_close(db);
        return 1;
    }

    if (!searchQuery.empty()) {
        std::string likeQuery = "%" + searchQuery + "%";
        int paramCount = sqlite3_bind_parameter_count(stmt);
        for (int i = 1; i <= paramCount; i++) {
            sqlite3_bind_text(stmt, i, likeQuery.c_str(), -1, SQLITE_TRANSIENT);
        }
    }

    int count = 0;
    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        count++;
        int id = sqlite3_column_int(stmt, 0);
        
        const unsigned char* name_val = sqlite3_column_text(stmt, 1);
        std::string name = name_val ? reinterpret_cast<const char*>(name_val) : "k.A.";
        
        int jahr = sqlite3_column_int(stmt, 2);
        
        const unsigned char* reg_val = sqlite3_column_text(stmt, 3);
        std::string regisseur = reg_val ? reinterpret_cast<const char*>(reg_val) : "";
        
        const unsigned char* genre_val = sqlite3_column_text(stmt, 4);
        std::string genre = genre_val ? reinterpret_cast<const char*>(genre_val) : "";
        
        const unsigned char* cast_val = sqlite3_column_text(stmt, 5);
        std::string cast = cast_val ? reinterpret_cast<const char*>(cast_val) : "";

        std::cout << "[" << id << "] " << name << " (" << (jahr > 0 ? std::to_string(jahr) : "N/A") << ")\n";
        if (!regisseur.empty()) {
            std::cout << "    Regisseur: " << regisseur << "\n";
        }
        if (!genre.empty()) {
            std::cout << "    Genre:     " << genre << "\n";
        }
        if (!cast.empty()) {
            std::cout << "    Cast:      " << cast << "\n";
        }
        std::cout << "    ------------------------------------------\n";
    }

    if (count == 0) {
        std::cout << "Keine passenden Filme in der Datenbank gefunden.\n";
    } else {
        std::cout << "\nInsgesamt gefundene Filme: " << count << "\n";
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);
    return 0;
}
