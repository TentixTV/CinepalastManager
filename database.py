import os
import sqlite3

DB_FILE = "cinepalast.db"

def initialize_db(db_file=DB_FILE):
    """Initializes the SQLite database and creates the 'media' table with all required fields."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create the media table with exactly the fields requested by the user
    cursor.execute("""
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
    """)
    conn.commit()
    conn.close()

def add_movie(data_dict: dict, db_file=DB_FILE) -> int:
    """
    Inserts a movie into the 'media' table.
    Expects a dictionary containing fields matching the table columns.
    Returns the ID of the newly inserted movie.
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    query = """
    INSERT INTO media (
        Name, Jahr, Schauspieler, Genre, Laufzeit_min, Beschreibung, FSK,
        Produktionsfirma, Regisseur, Filmreihe, Produktionsland,
        Deutsche_Synchronsprecher, Poster_Pfad, Banner_Pfad
    ) VALUES (
        :Name, :Jahr, :Schauspieler, :Genre, :Laufzeit_min, :Beschreibung, :FSK,
        :Produktionsfirma, :Regisseur, :Filmreihe, :Produktionsland,
        :Deutsche_Synchronsprecher, :Poster_Pfad, :Banner_Pfad
    );
    """
    try:
        cursor.execute(query, data_dict)
        conn.commit()
        last_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return last_id

def search_movies_realtime(search_query: str, db_file=DB_FILE) -> list:
    """
    Searches the database in real-time for movies matching the search string.
    Checks Name, Schauspieler, Genre, Regisseur, and Filmreihe.
    Returns a list of dictionaries representing the matching movies.
    """
    if not search_query.strip():
        return get_all_movies(db_file)
        
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sql = """
    SELECT * FROM media
    WHERE Name LIKE ?
       OR Schauspieler LIKE ?
       OR Genre LIKE ?
       OR Regisseur LIKE ?
       OR Filmreihe LIKE ?
    ORDER BY Name ASC;
    """
    like_query = f"%{search_query}%"
    params = (like_query, like_query, like_query, like_query, like_query)
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results

def get_all_movies(db_file=DB_FILE) -> list:
    """
    Retrieves all movies from the 'media' table sorted alphabetically by Name.
    Returns a list of dictionaries representing each movie.
    """
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM media ORDER BY Name ASC;")
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results

def get_movie_by_id(movie_id: int, db_file=DB_FILE) -> dict:
    """
    Retrieves a single movie by its ID from the 'media' table.
    Returns a dictionary or None if not found.
    """
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM media WHERE ID = ?;", (movie_id,))
    row = cursor.fetchone()
    result = dict(row) if row else None
    conn.close()
    return result

def delete_movie_by_id(movie_id: int, db_file=DB_FILE):
    """Deletes a movie record from the database by ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM media WHERE ID = ?;", (movie_id,))
    conn.commit()
    conn.close()

def update_movie_by_id(movie_id: int, data_dict: dict, db_file=DB_FILE):
    """Updates an existing movie record in the database by ID."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Exclude ID from keys to update
    data = {k: v for k, v in data_dict.items() if k.upper() != "ID"}
    set_clause = ", ".join([f"{key} = :{key}" for key in data.keys()])
    
    query = f"UPDATE media SET {set_clause} WHERE ID = :movie_id;"
    data["movie_id"] = movie_id
    
    try:
        cursor.execute(query, data)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

class DatabaseManager:
    """
    Class implementation of database coordinator used by ui.py and main.py.
    Provides schema translation between UI dictionary keys and DB column names.
    """
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        initialize_db(self.db_path)

    def _ui_to_db(self, movie_dict: dict) -> dict:
        """Translates UI representation to SQLite column names."""
        return {
            "Name": movie_dict.get("titel", ""),
            "Jahr": movie_dict.get("jahr"),
            "Schauspieler": movie_dict.get("schauspieler_cast", ""),
            "Genre": movie_dict.get("genre_richtung", ""),
            "Laufzeit_min": movie_dict.get("laufzeit_min", 0),
            "Beschreibung": movie_dict.get("handlung_beschreibung", ""),
            "FSK": movie_dict.get("fsk", "k.A."),
            "Produktionsfirma": movie_dict.get("produktionsfirma_studio", ""),
            "Regisseur": movie_dict.get("regisseur", ""),
            "Filmreihe": movie_dict.get("filmreihe", ""),
            "Produktionsland": movie_dict.get("produktionsland", ""),
            "Deutsche_Synchronsprecher": movie_dict.get("deutsche_synchronsprecher", ""),
            "Poster_Pfad": movie_dict.get("poster_pfad", ""),
            "Banner_Pfad": movie_dict.get("banner_pfad", "")
        }

    def _db_to_ui(self, db_row: dict) -> dict:
        """Translates SQLite columns to UI representation."""
        if not db_row:
            return {}
        return {
            "id": db_row.get("ID"),
            "titel": db_row.get("Name"),
            "jahr": db_row.get("Jahr"),
            "schauspieler_cast": db_row.get("Schauspieler"),
            "genre_richtung": db_row.get("Genre"),
            "laufzeit_min": db_row.get("Laufzeit_min"),
            "handlung_beschreibung": db_row.get("Beschreibung"),
            "fsk": db_row.get("FSK"),
            "produktionsfirma_studio": db_row.get("Produktionsfirma"),
            "regisseur": db_row.get("Regisseur"),
            "filmreihe": db_row.get("Filmreihe"),
            "produktionsland": db_row.get("Produktionsland"),
            "deutsche_synchronsprecher": db_row.get("Deutsche_Synchronsprecher"),
            "poster_pfad": db_row.get("Poster_Pfad"),
            "banner_pfad": db_row.get("Banner_Pfad")
        }

    def add_movie(self, movie_dict: dict) -> int:
        db_data = self._ui_to_db(movie_dict)
        return add_movie(db_data, self.db_path)

    def search_movies(self, query: str) -> list:
        results = search_movies_realtime(query, self.db_path)
        return [self._db_to_ui(row) for row in results]

    def get_all_movies(self) -> list:
        results = get_all_movies(self.db_path)
        return [self._db_to_ui(row) for row in results]

    def get_movie(self, movie_id: int) -> dict:
        row = get_movie_by_id(movie_id, self.db_path)
        if row:
            return self._db_to_ui(row)
        return {}

    def update_movie(self, movie_id: int, movie_dict: dict):
        db_data = self._ui_to_db(movie_dict)
        update_movie_by_id(movie_id, db_data, self.db_path)

    def delete_movie(self, movie_id: int):
        delete_movie_by_id(movie_id, self.db_path)
