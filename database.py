import os
import sqlite3

class DatabaseManager:
    """
    Manages the local SQLite database for storing movie metadata.
    Handles table initialization, inserts, updates, deletions, and real-time searching.
    """
    def __init__(self, db_path="cinepalast.db"):
        self.db_path = db_path
        self._ensure_asset_directories()
        self.init_db()

    def _ensure_asset_directories(self):
        """Creates assets directories if they do not exist."""
        os.makedirs("assets/posters", exist_ok=True)
        os.makedirs("assets/banners", exist_ok=True)
        # Create .gitkeep files to allow keeping folders in git if needed
        for folder in ["assets/posters", "assets/banners"]:
            gitkeep_path = os.path.join(folder, ".gitkeep")
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, "w") as f:
                    pass

    def _get_connection(self):
        """Returns a sqlite3 connection with row factory enabled for dictionary-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes the database schema if it doesn't already exist."""
        query = """
        CREATE TABLE IF NOT EXISTS filme (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT NOT NULL,
            jahr INTEGER,
            schauspieler_cast TEXT,
            genre_richtung TEXT,
            laufzeit_min INTEGER,
            handlung_beschreibung TEXT,
            fsk TEXT,
            produktionsfirma_studio TEXT,
            regisseur TEXT,
            filmreihe TEXT,
            produktionsland TEXT,
            deutsche_synchronsprecher TEXT,
            poster_pfad TEXT,
            banner_pfad TEXT
        );
        """
        with self._get_connection() as conn:
            conn.execute(query)
            conn.commit()

    def add_movie(self, movie_data: dict) -> int:
        """
        Inserts a new movie record into the database.
        
        :param movie_data: A dictionary containing movie metadata matching the columns.
        :return: The ID of the inserted record.
        """
        query = """
        INSERT INTO filme (
            titel, jahr, schauspieler_cast, genre_richtung, laufzeit_min,
            handlung_beschreibung, fsk, produktionsfirma_studio, regisseur,
            filmreihe, produktionsland, deutsche_synchronsprecher, poster_pfad, banner_pfad
        ) VALUES (
            :titel, :jahr, :schauspieler_cast, :genre_richtung, :laufzeit_min,
            :handlung_beschreibung, :fsk, :produktionsfirma_studio, :regisseur,
            :filmreihe, :produktionsland, :deutsche_synchronsprecher, :poster_pfad, :banner_pfad
        );
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, movie_data)
            conn.commit()
            return cursor.lastrowid

    def update_movie(self, movie_id: int, movie_data: dict):
        """
        Updates an existing movie record in the database.
        
        :param movie_id: The ID of the movie to update.
        :param movie_data: A dictionary containing fields to be updated.
        """
        # Exclude 'id' if present in dictionary keys to avoid SQL constraints
        data = {k: v for k, v in movie_data.items() if k != "id"}
        set_clause = ", ".join([f"{key} = :{key}" for key in data.keys()])
        
        query = f"UPDATE filme SET {set_clause} WHERE id = :movie_id;"
        data["movie_id"] = movie_id

        with self._get_connection() as conn:
            conn.execute(query, data)
            conn.commit()

    def delete_movie(self, movie_id: int):
        """
        Deletes a movie record from the database.
        
        :param movie_id: The ID of the movie to delete.
        """
        with self._get_connection() as conn:
            # We fetch poster and banner paths first to clean up files if desired
            movie = self.get_movie(movie_id)
            if movie:
                # Clean up local asset files if they exist
                for key in ["poster_pfad", "banner_pfad"]:
                    path = movie[key]
                    if path and os.path.exists(path) and not path.endswith(".gitkeep"):
                        try:
                            # Let's verify we only delete within our assets directory for safety
                            if path.startswith("assets/"):
                                os.remove(path)
                        except Exception as e:
                            print(f"Error removing asset {path}: {e}")

            conn.execute("DELETE FROM filme WHERE id = ?;", (movie_id,))
            conn.commit()

    def get_movie(self, movie_id: int) -> dict:
        """
        Retrieves a single movie by its ID.
        
        :param movie_id: The ID of the movie.
        :return: A dictionary representing the movie record or None.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM filme WHERE id = ?;", (movie_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_movies(self) -> list:
        """
        Retrieves all movies sorted by title.
        
        :return: A list of dictionaries representing movie records.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM filme ORDER BY titel ASC;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search_movies(self, query_text: str) -> list:
        """
        Queries the database for movies matching the search string in title, cast, genre, director, or collection.
        Uses SQLite LIKE operator.
        
        :param query_text: Search query string.
        :return: A list of dictionaries representing matching movie records.
        """
        if not query_text.strip():
            return self.get_all_movies()
            
        sql = """
        SELECT * FROM filme 
        WHERE titel LIKE ? 
           OR schauspieler_cast LIKE ? 
           OR genre_richtung LIKE ? 
           OR regisseur LIKE ?
           OR filmreihe LIKE ?
        ORDER BY titel ASC;
        """
        like_query = f"%{query_text}%"
        params = (like_query, like_query, like_query, like_query, like_query)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
