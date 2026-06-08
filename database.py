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
        self.seed_db_if_empty()

    def _ui_to_db(self, movie_dict: dict) -> dict:
        """Translates UI representation to SQLite column names."""
        titel = movie_dict.get("titel", "").strip()
        jahr = movie_dict.get("jahr")
        if jahr:
            year_suffix = f"({jahr})"
            if year_suffix not in titel:
                titel = f"{titel} {year_suffix}"

        return {
            "Name": titel,
            "Jahr": jahr,
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

    def seed_db_if_empty(self):
        """Seeds the database with popular movies if empty, and fetches their images in the background."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
        if not cursor.fetchone():
            conn.close()
            return
            
        cursor.execute("SELECT COUNT(*) FROM media;")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            return
            
        print("Seeding database with 40 default popular movies...")
        
        seeded_movies = [
            {
                "titel": "Inception", "jahr": 2010, "schauspieler_cast": "Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page, Tom Hardy",
                "genre_richtung": "Action, Science Fiction, Abenteuer", "laufzeit_min": 148,
                "handlung_beschreibung": "Dom Cobb ist ein begnadeter Dieb, der darauf spezialisiert ist, in der Traumphase wertvolle Geheimnisse aus den Tiefen des Unterbewusstseins zu stehlen.",
                "fsk": "12", "produktionsfirma_studio": "Warner Bros. Pictures, Legendary Pictures", "regisseur": "Christopher Nolan",
                "filmreihe": "", "produktionsland": "USA, UK", "deutsche_synchronsprecher": "Gerrit Schmidt-Foß für Leonardo DiCaprio (Dom Cobb), Robin Kahnmeyer für Joseph Gordon-Levitt (Arthur)",
                "poster_pfad": "assets/posters/27205.jpg", "banner_pfad": "assets/banners/27205.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg"
            },
            {
                "titel": "The Dark Knight", "jahr": 2008, "schauspieler_cast": "Christian Bale, Heath Ledger, Aaron Eckhart, Gary Oldman",
                "genre_richtung": "Drama, Action, Krimi, Thriller", "laufzeit_min": 152,
                "handlung_beschreibung": "Mit Hilfe von Lieutenant Jim Gordon und Bezirksstaatsanwalt Harvey Dent will Batman dem organisierten Verbrechen in Gotham City ein Ende bereiten.",
                "fsk": "16", "produktionsfirma_studio": "Warner Bros. Pictures, Legendary Pictures", "regisseur": "Christopher Nolan",
                "filmreihe": "The Dark Knight Trilogie", "produktionsland": "USA, UK", "deutsche_synchronsprecher": "David Nathan für Christian Bale (Bruce Wayne / Batman), Simon Jäger für Heath Ledger (Joker)",
                "poster_pfad": "assets/posters/155.jpg", "banner_pfad": "assets/banners/155.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haZl4a35.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/nMK0r9FYjT6mBnmVDWvS4Y9q1gB.jpg"
            },
            {
                "titel": "Interstellar", "jahr": 2014, "schauspieler_cast": "Matthew McConaughey, Anne Hathaway, Jessica Chastain, Michael Caine",
                "genre_richtung": "Abenteuer, Drama, Science Fiction", "laufzeit_min": 169,
                "handlung_beschreibung": "Ein Team von Entdeckern begibt sich auf die wichtigste Mission in der Geschichte der Menschheit, um herauszufinden, ob die Menschheit eine Zukunft unter den Sternen hat.",
                "fsk": "12", "produktionsfirma_studio": "Paramount Pictures, Warner Bros.", "regisseur": "Christopher Nolan",
                "filmreihe": "", "produktionsland": "USA, UK", "deutsche_synchronsprecher": "Matti Klemm für Matthew McConaughey (Cooper), Marie Bierstedt für Anne Hathaway (Brand)",
                "poster_pfad": "assets/posters/157336.jpg", "banner_pfad": "assets/banners/157336.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/gEU2Qv0v27g2r2kg6mfsom0vX0D.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/xJHok7013xjjS8gh0OI46ofn17K.jpg"
            },
            {
                "titel": "Avatar", "jahr": 2009, "schauspieler_cast": "Sam Worthington, Zoe Saldana, Sigourney Weaver, Stephen Lang",
                "genre_richtung": "Action, Abenteuer, Fantasy, Science Fiction", "laufzeit_min": 162,
                "handlung_beschreibung": "Im Jahr 2154 reist der querschnittsgelähmte ehemalige Marine Jake Sully nach Pandora, einer fernen Welt voller exotischer Lebensformen.",
                "fsk": "12", "produktionsfirma_studio": "20th Century Fox, Lightstorm Entertainment", "regisseur": "James Cameron",
                "filmreihe": "Avatar", "produktionsland": "USA", "deutsche_synchronsprecher": "Alexander Doering für Sam Worthington (Jake Sully), Tanja Geke für Zoe Saldana (Neytiri)",
                "poster_pfad": "assets/posters/19995.jpg", "banner_pfad": "assets/banners/19995.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/kyeqWdyUXW608qlYkRqosgbbJyK.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/vL5LR6WdxWPjLPFRLe133jXWsh5.jpg"
            },
            {
                "titel": "The Matrix", "jahr": 1999, "schauspieler_cast": "Keanu Reeves, Laurence Fishburne, Carrie-Anne Moss, Hugo Weaving",
                "genre_richtung": "Action, Science Fiction", "laufzeit_min": 136,
                "handlung_beschreibung": "Der Hacker Neo wird von einer mysteriösen Untergrund-Organisation kontaktiert. Deren Kopf, der berüchtigte Morpheus, weiht ihn in ein furchtbares Geheimnis ein.",
                "fsk": "16", "produktionsfirma_studio": "Warner Bros. Pictures, Village Roadshow Pictures", "regisseur": "Lana Wachowski, Lilly Wachowski",
                "filmreihe": "Matrix", "produktionsland": "USA", "deutsche_synchronsprecher": "Benjamin Völz für Keanu Reeves (Neo), Leon Boden für Laurence Fishburne (Morpheus)",
                "poster_pfad": "assets/posters/603.jpg", "banner_pfad": "assets/banners/603.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/ncEsesgOJDNrTUED89hYbA117wo.jpg"
            },
            {
                "titel": "Titanic", "jahr": 1997, "schauspieler_cast": "Leonardo DiCaprio, Kate Winslet, Billy Zane, Kathy Bates",
                "genre_richtung": "Drama, Liebesfilm", "laufzeit_min": 194,
                "handlung_beschreibung": "Eine Liebesgeschichte an Bord der Titanic zwischen Rose DeWitt Bukater und Jack Dawson, zwei Menschen aus unterschiedlichen Gesellschaftsschichten.",
                "fsk": "12", "produktionsfirma_studio": "Paramount Pictures, 20th Century Fox", "regisseur": "James Cameron",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Gerrit Schmidt-Foß für Leonardo DiCaprio (Jack Dawson), Ulrike Stürzbecher für Kate Winslet (Rose)",
                "poster_pfad": "assets/posters/597.jpg", "banner_pfad": "assets/banners/597.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/xnHVX37XZEp33hhCbYlQFq7ux1J.jpg"
            },
            {
                "titel": "Gladiator", "jahr": 2000, "schauspieler_cast": "Russell Crowe, Joaquin Phoenix, Connie Nielsen, Oliver Reed",
                "genre_richtung": "Action, Drama, Abenteuer", "laufzeit_min": 155,
                "handlung_beschreibung": "Der römische General Maximus Decimus Meridius wird verraten, als der machthungrige Sohn des Kaisers seinen Vater ermordet und den Thron besteigt.",
                "fsk": "16", "produktionsfirma_studio": "DreamWorks SKG, Universal Pictures", "regisseur": "Ridley Scott",
                "filmreihe": "", "produktionsland": "USA, UK", "deutsche_synchronsprecher": "Thomas Fritsch für Russell Crowe (Maximus), Marcus Off für Joaquin Phoenix (Commodus)",
                "poster_pfad": "assets/posters/98.jpg", "banner_pfad": "assets/banners/98.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/ty87ILCo33nHg590m67giT7ko1l.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/6FwH0L5hK8V9XU3xT2S0l5o62V6.jpg"
            },
            {
                "titel": "Pulp Fiction", "jahr": 1994, "schauspieler_cast": "John Travolta, Samuel L. Jackson, Uma Thurman, Bruce Willis",
                "genre_richtung": "Thriller, Krimi", "laufzeit_min": 154,
                "handlung_beschreibung": "Mehrere miteinander verwobene Geschichten aus der Unterwelt von Los Angeles rund um zwei Auftragskiller, einen Boxer und Gangsterboss Marsellus Wallace.",
                "fsk": "16", "produktionsfirma_studio": "Miramax Films, A Band Apart", "regisseur": "Quentin Tarantino",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Thomas Danneberg für John Travolta (Vincent Vega), Helmut Krauss für Samuel L. Jackson (Jules)",
                "poster_pfad": "assets/posters/680.jpg", "banner_pfad": "assets/banners/680.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/xOA4MbyJZVJHGZ38wC4LPpruBBX.jpg"
            },
            {
                "titel": "Forrest Gump", "jahr": 1994, "schauspieler_cast": "Tom Hanks, Robin Wright, Gary Sinise, Mykelti Williamson",
                "genre_richtung": "Drama, Komödie, Liebesfilm", "laufzeit_min": 142,
                "handlung_beschreibung": "Forrest Gump ist ein gutmütiger Mann aus Alabama mit einem unterdurchschnittlichen IQ, der an vielen historischen Ereignissen des 20. Jahrhunderts teilnimmt.",
                "fsk": "6", "produktionsfirma_studio": "Paramount Pictures", "regisseur": "Robert Zemeckis",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Arne Elsholtz für Tom Hanks (Forrest Gump)",
                "poster_pfad": "assets/posters/13.jpg", "banner_pfad": "assets/banners/13.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/arw2tWw7lzipdCCHCs79d866wxn.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/qdIMHd4YrV1jpEwCQ4I15715bFZ.jpg"
            },
            {
                "titel": "Fight Club", "jahr": 1999, "schauspieler_cast": "Edward Norton, Brad Pitt, Helena Bonham Carter, Meat Loaf",
                "genre_richtung": "Drama, Thriller", "laufzeit_min": 139,
                "handlung_beschreibung": "Ein schlafloser Büroangestellter und ein charismatischer Seifenverkäufer gründen einen geheimen Kampfverein, der sich bald zu einer revolutionären Bewegung entwickelt.",
                "fsk": "18", "produktionsfirma_studio": "Fox 2000 Pictures, Regency Enterprises", "regisseur": "David Fincher",
                "filmreihe": "", "produktionsland": "USA, Deutschland", "deutsche_synchronsprecher": "Dietmar Wunder für Edward Norton (Erzähler), Tobias Meister für Brad Pitt (Tyler)",
                "poster_pfad": "assets/posters/550.jpg", "banner_pfad": "assets/banners/550.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/pB8ZayXgRLKFh94qS6Hbw2adJ8Y.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/hZup7t3scu447d2v2uD494D18u4.jpg"
            },
            {
                "titel": "Der Herr der Ringe: Die Gefährten", "jahr": 2001, "schauspieler_cast": "Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom",
                "genre_richtung": "Fantasy, Abenteuer, Action", "laufzeit_min": 178,
                "handlung_beschreibung": "Der junge Hobbit Frodo Beutlin erbt einen mächtigen Ring. Zusammen mit Gefährten begibt er sich auf die Reise zum Schicksalsberg, um ihn zu vernichten.",
                "fsk": "12", "produktionsfirma_studio": "New Line Cinema, WingNut Films", "regisseur": "Peter Jackson",
                "filmreihe": "Der Herr der Ringe", "produktionsland": "Neuseeland, USA", "deutsche_synchronsprecher": "Timmo Niesner für Elijah Wood (Frodo), Achim Höppner für Ian McKellen (Gandalf)",
                "poster_pfad": "assets/posters/120.jpg", "banner_pfad": "assets/banners/120.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/dUVbWINfRMGojGZRcO6GF1Z2nV8.jpg"
            },
            {
                "titel": "Der Herr der Ringe: Die zwei Türme", "jahr": 2002, "schauspieler_cast": "Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom",
                "genre_richtung": "Fantasy, Abenteuer, Action", "laufzeit_min": 179,
                "handlung_beschreibung": "Die Gefährten sind getrennt. Frodo und Sam setzen ihren Weg nach Mordor fort, geführt vom geheimnisvollen Gollum, während Aragorn für die Menschen kämpft.",
                "fsk": "12", "produktionsfirma_studio": "New Line Cinema, WingNut Films", "regisseur": "Peter Jackson",
                "filmreihe": "Der Herr der Ringe", "produktionsland": "Neuseeland, USA", "deutsche_synchronsprecher": "Timmo Niesner für Elijah Wood (Frodo), Jacques Breuer für Viggo Mortensen (Aragorn)",
                "poster_pfad": "assets/posters/121.jpg", "banner_pfad": "assets/banners/121.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/zXQnB7s5YnC0B5tY7QZ1tB7W8T.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/kWYfWnC0B5tY7QZ1tB7W8T.jpg"
            },
            {
                "titel": "Der Herr der Ringe: Die Rückkehr des Königs", "jahr": 2003, "schauspieler_cast": "Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom",
                "genre_richtung": "Fantasy, Abenteuer, Action", "laufzeit_min": 201,
                "handlung_beschreibung": "Das Finale des epischen Kampfes um Mittelerde. Frodo erreicht den Schicksalsberg, während die Heere Saurons die weiße Stadt Minas Tirith belagern.",
                "fsk": "12", "produktionsfirma_studio": "New Line Cinema, WingNut Films", "regisseur": "Peter Jackson",
                "filmreihe": "Der Herr der Ringe", "produktionsland": "Neuseeland, USA", "deutsche_synchronsprecher": "Timmo Niesner für Elijah Wood (Frodo), Achim Höppner für Ian McKellen (Gandalf)",
                "poster_pfad": "assets/posters/122.jpg", "banner_pfad": "assets/banners/122.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/rC7621z4695ooH6k6N6j93.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/2u7621z4695ooH6k6N6j93.jpg"
            },
            {
                "titel": "Harry Potter und der Stein der Weisen", "jahr": 2001, "schauspieler_cast": "Daniel Radcliffe, Rupert Grint, Emma Watson, Richard Harris, Alan Rickman",
                "genre_richtung": "Fantasy, Abenteuer, Familie", "laufzeit_min": 152,
                "handlung_beschreibung": "An seinem 11. Geburtstag erfährt Harry Potter, dass er ein Zauberer ist, und wird an der Hogwarts-Schule für Hexerei und Zauberei aufgenommen.",
                "fsk": "6", "produktionsfirma_studio": "Warner Bros. Pictures, Heyday Films", "regisseur": "Chris Columbus",
                "filmreihe": "Harry Potter", "produktionsland": "UK, USA", "deutsche_synchronsprecher": "Nico Sablik für Daniel Radcliffe (Harry Potter), Gabrielle Pietermann für Emma Watson (Hermine)",
                "poster_pfad": "assets/posters/671.jpg", "banner_pfad": "assets/banners/671.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/wuMc08IPK47gnj8gdAo48r431jS.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/hziiv1426495ooH6k6N6j95.jpg"
            },
            {
                "titel": "Harry Potter und die Kammer des Schreckens", "jahr": 2002, "schauspieler_cast": "Daniel Radcliffe, Rupert Grint, Emma Watson, Kenneth Branagh, Alan Rickman",
                "genre_richtung": "Fantasy, Abenteuer, Familie", "laufzeit_min": 161,
                "handlung_beschreibung": "Harry kehr nach Hogwarts zurück, doch eine geheimnisvolle Gefahr versteinert die Schüler. Harry muss das Rätsel der Kammer des Schreckens lösen.",
                "fsk": "6", "produktionsfirma_studio": "Warner Bros. Pictures, Heyday Films", "regisseur": "Chris Columbus",
                "filmreihe": "Harry Potter", "produktionsland": "UK, USA", "deutsche_synchronsprecher": "Nico Sablik für Daniel Radcliffe (Harry Potter), Max Felder für Rupert Grint (Ron)",
                "poster_pfad": "assets/posters/672.jpg", "banner_pfad": "assets/banners/672.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/sdMMgD2v2yQTMJIbnvbkBL9cHo7.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/hziiv1426495ooH6k6N6j95.jpg"
            },
            {
                "titel": "Star Wars: Episode IV - Eine neue Hoffnung", "jahr": 1977, "schauspieler_cast": "Mark Hamill, Harrison Ford, Carrie Fisher, Alec Guinness",
                "genre_richtung": "Science Fiction, Abenteuer, Action", "laufzeit_min": 121,
                "handlung_beschreibung": "Der junge Luke Skywalker begibt sich zusammen mit Jedi-Meister Obi-Wan Kenobi und Weltraumpilot Han Solo auf die Mission, Prinzessin Leia vor dem finsteren Darth Vader zu retten.",
                "fsk": "6", "produktionsfirma_studio": "Lucasfilm, 20th Century Fox", "regisseur": "George Lucas",
                "filmreihe": "Star Wars", "produktionsland": "USA", "deutsche_synchronsprecher": "Hans-Georg Panczak für Mark Hamill (Luke), Wolfgang Pampel für Harrison Ford (Han Solo)",
                "poster_pfad": "assets/posters/11.jpg", "banner_pfad": "assets/banners/11.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/6FfCOee7X21V67Ur2Jxe4UsX6qq.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/nz88l1erUe48Hqi5Z6U2f126756.jpg"
            },
            {
                "titel": "Star Wars: Episode V - Das Imperium schlägt zurück", "jahr": 1980, "schauspieler_cast": "Mark Hamill, Harrison Ford, Carrie Fisher, Billy Dee Williams",
                "genre_richtung": "Science Fiction, Abenteuer, Action", "laufzeit_min": 124,
                "handlung_beschreibung": "Während das Imperium die Rebellen jagt, reist Luke Skywalker zum Sumpfplaneten Dagobah, um vom weisen Jedi-Meister Yoda ausgebildet zu werden.",
                "fsk": "6", "produktionsfirma_studio": "Lucasfilm, 20th Century Fox", "regisseur": "Irvin Kershner",
                "filmreihe": "Star Wars", "produktionsland": "USA", "deutsche_synchronsprecher": "Hans-Georg Panczak für Mark Hamill (Luke), Hugo Schrader für Yoda",
                "poster_pfad": "assets/posters/1891.jpg", "banner_pfad": "assets/banners/1891.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/1eZMiZ0s2vU0dE86Wc4z72J8tqg.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Zurück in die Zukunft", "jahr": 1985, "schauspieler_cast": "Michael J. Fox, Christopher Lloyd, Lea Thompson, Crispin Glover",
                "genre_richtung": "Komödie, Science Fiction, Abenteuer", "laufzeit_min": 116,
                "handlung_beschreibung": "Der Teenager Marty McFly reist versehentlich mit einer von Doc Brown umgebauten Delorean-Zeitmaschine zurück in das Jahr 1955 und gefährdet seine eigene Existenz.",
                "fsk": "12", "produktionsfirma_studio": "Universal Pictures, Amblin Entertainment", "regisseur": "Robert Zemeckis",
                "filmreihe": "Zurück in die Zukunft", "produktionsland": "USA", "deutsche_synchronsprecher": "Sven Hasper für Michael J. Fox (Marty), Lutz Mackensy für Christopher Lloyd (Doc Brown)",
                "poster_pfad": "assets/posters/105.jpg", "banner_pfad": "assets/banners/105.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/7LyNsZ5262r2kg6mfsom0vX0D.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/8c2G2l8k15J.jpg"
            },
            {
                "titel": "Der König der Löwen", "jahr": 1994, "schauspieler_cast": "Matthew Broderick, Jeremy Irons, James Earl Jones, Jonathan Taylor Thomas",
                "genre_richtung": "Animation, Familie, Drama", "laufzeit_min": 88,
                "handlung_beschreibung": "Der kleine Löwe Simba muss nach dem plötzlichen Tod seines Vaters Mufasa fliehen und kehrt Jahre später zurück, um seinen Onkel Scar vom Thron zu stürzen.",
                "fsk": "0", "produktionsfirma_studio": "Walt Disney Pictures", "regisseur": "Roger Allers, Rob Minkoff",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Frank-Lorenz Engel für Simba (Erwachsen), Thomas Fritsch für Scar",
                "poster_pfad": "assets/posters/8587.jpg", "banner_pfad": "assets/banners/8587.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/7Ed0vP2p8A0L5H9yG5B51X597j.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Django Unchained", "jahr": 2012, "schauspieler_cast": "Jamie Foxx, Christoph Waltz, Leonardo DiCaprio, Kerry Washington",
                "genre_richtung": "Western, Drama", "laufzeit_min": 165,
                "handlung_beschreibung": "Ein befreiter Sklave reist mit Hilfe eines deutschen Kopfgeldjägers quer durch die USA, um seine Frau aus den Fängen eines grausamen Plantagenbesitzers zu befreien.",
                "fsk": "16", "produktionsfirma_studio": "The Weinstein Company, Columbia Pictures", "regisseur": "Quentin Tarantino",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Charles Rettinghaus für Jamie Foxx (Django), Christoph Waltz für sich selbst (Dr. Schultz)",
                "poster_pfad": "assets/posters/68718.jpg", "banner_pfad": "assets/banners/68718.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/7gho6e6Wc4z72J8tqg.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Joker", "jahr": 2019, "schauspieler_cast": "Joaquin Phoenix, Robert De Niro, Zazie Beetz, Frances Conroy",
                "genre_richtung": "Drama, Krimi, Thriller", "laufzeit_min": 122,
                "handlung_beschreibung": "Die Ursprungsgeschichte von Jokers Wandlung vom erfolglosen Comedian Arthur Fleck zum legendären psychopathischen Schurken in Gotham City.",
                "fsk": "16", "produktionsfirma_studio": "Warner Bros. Pictures, DC Films", "regisseur": "Todd Phillips",
                "filmreihe": "Joker", "produktionsland": "USA", "deutsche_synchronsprecher": "Tobias Meister für Joaquin Phoenix (Arthur Fleck / Joker)",
                "poster_pfad": "assets/posters/475557.jpg", "banner_pfad": "assets/banners/475557.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/udDclsa...jpg", # TMDB fallback check
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Der Pate", "jahr": 1972, "schauspieler_cast": "Marlon Brando, Al Pacino, James Caan, Richard S. Castellano",
                "genre_richtung": "Krimi, Drama", "laufzeit_min": 175,
                "handlung_beschreibung": "Der alternde Mafiaboss Don Vito Corleone übergibt die Kontrolle über sein kriminelles Imperium zögerlich an seinen kriegsheimkehrenden Sohn Michael.",
                "fsk": "16", "produktionsfirma_studio": "Paramount Pictures, Alfran Productions", "regisseur": "Francis Ford Coppola",
                "filmreihe": "Der Pate", "produktionsland": "USA", "deutsche_synchronsprecher": "Lutz Mackensy für Al Pacino (Michael Corleone)",
                "poster_pfad": "assets/posters/238.jpg", "banner_pfad": "assets/banners/238.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/3bhDaz...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Schindlers Liste", "jahr": 1993, "schauspieler_cast": "Liam Neeson, Ben Kingsley, Ralph Fiennes, Caroline Goodall",
                "genre_richtung": "Drama, Historie", "laufzeit_min": 195,
                "handlung_beschreibung": "Die wahre Geschichte des sudetendeutschen Industriellen Oskar Schindler, der im Zweiten Weltkrieg über 1000 polnische Juden vor dem Holocaust rettete.",
                "fsk": "12", "produktionsfirma_studio": "Universal Pictures, Amblin Entertainment", "regisseur": "Steven Spielberg",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Stephan Schwartz für Liam Neeson (Oskar Schindler)",
                "poster_pfad": "assets/posters/424.jpg", "banner_pfad": "assets/banners/424.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/sF1426...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Die Verurteilten", "jahr": 1994, "schauspieler_cast": "Tim Robbins, Morgan Freeman, Bob Gunton, William Sadler",
                "genre_richtung": "Drama", "laufzeit_min": 142,
                "handlung_beschreibung": "Ein unschuldig zu lebenslanger Haft verurteilter Bankier freundet sich im Gefängnis mit einem älteren Mithäftling an und behält über Jahrzehnte die Hoffnung auf Freiheit.",
                "fsk": "12", "produktionsfirma_studio": "Castle Rock Entertainment", "regisseur": "Frank Darabont",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Tobias Meister für Tim Robbins (Andy), Klaus Sonnenschein für Morgan Freeman (Red)",
                "poster_pfad": "assets/posters/278.jpg", "banner_pfad": "assets/banners/278.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/q69...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Sieben", "jahr": 1995, "schauspieler_cast": "Brad Pitt, Morgan Freeman, Gwyneth Paltrow, Kevin Spacey",
                "genre_richtung": "Krimi, Thriller, Mystery", "laufzeit_min": 127,
                "handlung_beschreibung": "Zwei Detektive jagen einen psychopathischen Serienmörder, der seine Opfer nach dem Muster der sieben Todsünden tötet.",
                "fsk": "16", "produktionsfirma_studio": "New Line Cinema", "regisseur": "David Fincher",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Tobias Meister für Brad Pitt (Mills), Klaus Sonnenschein für Morgan Freeman (Somerset)",
                "poster_pfad": "assets/posters/807.jpg", "banner_pfad": "assets/banners/807.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/6Kg...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Léon - Der Profi", "jahr": 1994, "schauspieler_cast": "Jean Reno, Natalie Portman, Gary Oldman, Danny Aiello",
                "genre_richtung": "Action, Thriller, Drama", "laufzeit_min": 110,
                "handlung_beschreibung": "Ein wortkarger Profikiller nimmt ein 12-jähriges Mädchen nach der Ermordung ihrer Familie bei sich auf und bringt ihr das Handwerk des Tötens bei.",
                "fsk": "16", "produktionsfirma_studio": "Gaumont, Les Films du Dauphin", "regisseur": "Luc Besson",
                "filmreihe": "", "produktionsland": "Frankreich", "deutsche_synchronsprecher": "Joachim Kerzel für Jean Reno (Léon)",
                "poster_pfad": "assets/posters/101.jpg", "banner_pfad": "assets/banners/101.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/y4...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Der Soldat James Ryan", "jahr": 1998, "schauspieler_cast": "Tom Hanks, Edward Burns, Tom Sizemore, Matt Damon",
                "genre_richtung": "Drama, Kriegsfilm", "laufzeit_min": 169,
                "handlung_beschreibung": "Im Zweiten Weltkrieg begibt sich eine US-Infanteriegruppe hinter die feindlichen Linien, um einen Soldaten zu retten, dessen Brüder alle gefallen sind.",
                "fsk": "16", "produktionsfirma_studio": "Paramount Pictures, DreamWorks SKG", "regisseur": "Steven Spielberg",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Arne Elsholtz für Tom Hanks (Captain Miller)",
                "poster_pfad": "assets/posters/857.jpg", "banner_pfad": "assets/banners/857.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/1...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Shutter Island", "jahr": 2010, "schauspieler_cast": "Leonardo DiCaprio, Mark Ruffalo, Ben Kingsley, Michelle Williams",
                "genre_richtung": "Drama, Thriller, Mystery", "laufzeit_min": 138,
                "handlung_beschreibung": "Ein US-Marshal ermittelt im Jahr 1954 im mysteriösen Verschwinden einer Mörderin aus einer geschlossenen Anstalt auf einer abgelegenen Insel.",
                "fsk": "16", "produktionsfirma_studio": "Paramount Pictures", "regisseur": "Martin Scorsese",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Gerrit Schmidt-Foß für Leonardo DiCaprio (Teddy Daniels)",
                "poster_pfad": "assets/posters/11324.jpg", "banner_pfad": "assets/banners/11324.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/4...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "The Wolf of Wall Street", "jahr": 2013, "schauspieler_cast": "Leonardo DiCaprio, Jonah Hill, Margot Robbie, Matthew McConaughey",
                "genre_richtung": "Komödie, Drama, Biografie", "laufzeit_min": 180,
                "handlung_beschreibung": "Der Aufstieg und tiefe Fall des betrügerischen New Yorker Börsenmaklers Jordan Belfort, geprägt von extremem Luxus, Drogen und Korruption.",
                "fsk": "16", "produktionsfirma_studio": "Paramount Pictures, Red Granite Pictures", "regisseur": "Martin Scorsese",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Gerrit Schmidt-Foß für Leonardo DiCaprio (Jordan Belfort)",
                "poster_pfad": "assets/posters/106646.jpg", "banner_pfad": "assets/banners/106646.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/p...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Ziemlich beste Freunde", "jahr": 2011, "schauspieler_cast": "François Cluzet, Omar Sy, Anne Le Ny, Audrey Fleurot",
                "genre_richtung": "Komödie, Drama", "laufzeit_min": 112,
                "handlung_beschreibung": "Ein reicher querschnittsgelähmter Adeliger stellt einen jungen, unkonventionellen Pfleger aus den Pariser Banlieues ein. Eine tiefe Freundschaft entsteht.",
                "fsk": "6", "produktionsfirma_studio": "Gaumont", "regisseur": "Olivier Nakache, Éric Toledano",
                "filmreihe": "", "produktionsland": "Frankreich", "deutsche_synchronsprecher": "Sascha Rotermund für Omar Sy (Driss)",
                "poster_pfad": "assets/posters/77338.jpg", "banner_pfad": "assets/banners/77338.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/p...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Pirates of the Caribbean: Fluch der Karibik", "jahr": 2003, "schauspieler_cast": "Johnny Depp, Geoffrey Rush, Orlando Bloom, Keira Knightley",
                "genre_richtung": "Abenteuer, Fantasy, Action", "laufzeit_min": 143,
                "handlung_beschreibung": "Der exzentrische Piratenkapitän Jack Sparrow versucht mit Hilfe eines Hufschmieds, sein Schiff Black Pearl und die Gouverneurstochter Elizabeth Swann zurückzuerlangen.",
                "fsk": "12", "produktionsfirma_studio": "Walt Disney Pictures, Jerry Bruckheimer Films", "regisseur": "Gore Verbinski",
                "filmreihe": "Fluch der Karibik", "produktionsland": "USA", "deutsche_synchronsprecher": "Marcus Off für Johnny Depp (Jack Sparrow)",
                "poster_pfad": "assets/posters/22.jpg", "banner_pfad": "assets/banners/22.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Whiplash", "jahr": 2014, "schauspieler_cast": "Miles Teller, J.K. Simmons, Paul Reiser, Melissa Benoist",
                "genre_richtung": "Drama, Musik", "laufzeit_min": 107,
                "handlung_beschreibung": "Ein junger Schlagzeugschüler wird an einem New Yorker Musikkonservatorium von einem sadistischen Bandleader bis an seine absoluten Grenzen getrieben.",
                "fsk": "12", "produktionsfirma_studio": "Blumhouse Productions", "regisseur": "Damien Chazelle",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Oliver Kalkofe für J.K. Simmons (Terence Fletcher)",
                "poster_pfad": "assets/posters/244289.jpg", "banner_pfad": "assets/banners/244289.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Spider-Man: A New Universe", "jahr": 2018, "schauspieler_cast": "Shameik Moore, Jake Johnson, Hailee Steinfeld, Mahershala Ali",
                "genre_richtung": "Animation, Action, Abenteuer, Science Fiction", "laufzeit_min": 117,
                "handlung_beschreibung": "Der Teenager Miles Morales erlernt seine neuen Spinnenkräfte und verbündet sich mit Spider-Helden aus anderen Dimensionen, um eine Bedrohung abzuwehren.",
                "fsk": "6", "produktionsfirma_studio": "Columbia Pictures, Sony Pictures Animation", "regisseur": "Bob Persichetti, Peter Ramsey",
                "filmreihe": "Spider-Man (Spider-Verse)", "produktionsland": "USA", "deutsche_synchronsprecher": "Marco Eßer für Shameik Moore (Miles Morales)",
                "poster_pfad": "assets/posters/324857.jpg", "banner_pfad": "assets/banners/324857.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Die Truman Show", "jahr": 1998, "schauspieler_cast": "Jim Carrey, Laura Linney, Noah Emmerich, Ed Harris",
                "genre_richtung": "Komödie, Drama", "laufzeit_min": 103,
                "handlung_beschreibung": "Truman Burbank ahnt nicht, dass sein gesamtes Leben von Geburt an eine weltweite Reality-TV-Show ist, in der alle Personen außer ihm Schauspieler sind.",
                "fsk": "12", "produktionsfirma_studio": "Paramount Pictures", "regisseur": "Peter Weir",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Stefan Fredrich für Jim Carrey (Truman Burbank)",
                "poster_pfad": "assets/posters/1998.jpg", "banner_pfad": "assets/banners/1998.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "The Green Mile", "jahr": 1999, "schauspieler_cast": "Tom Hanks, David Morse, Bonnie Hunt, Michael Clarke Duncan",
                "genre_richtung": "Fantasy, Drama, Krimi", "laufzeit_min": 189,
                "handlung_beschreibung": "Ein Gefängnisaufseher im Todestrakt stellt fest, dass ein riesiger, sanftmütiger Häftling mit der Gabe der Heilung gesegnet ist.",
                "fsk": "12", "produktionsfirma_studio": "Castle Rock Entertainment", "regisseur": "Frank Darabont",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Arne Elsholtz für Tom Hanks (Paul Edgecomb)",
                "poster_pfad": "assets/posters/497.jpg", "banner_pfad": "assets/banners/497.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Avengers: Endgame", "jahr": 2019, "schauspieler_cast": "Robert Downey Jr., Chris Evans, Mark Ruffalo, Chris Hemsworth, Scarlett Johansson",
                "genre_richtung": "Action, Science Fiction, Abenteuer", "laufzeit_min": 181,
                "handlung_beschreibung": "Nachdem Thanos das halbe Universum ausgelöscht hat, schließen sich die überlebenden Avengers zusammen, um das Geschehene rückgängig zu machen.",
                "fsk": "12", "produktionsfirma_studio": "Marvel Studios", "regisseur": "Anthony Russo, Joe Russo",
                "filmreihe": "The Avengers", "produktionsland": "USA", "deutsche_synchronsprecher": "Tobias Meister für Robert Downey Jr. (Iron Man)",
                "poster_pfad": "assets/posters/299534.jpg", "banner_pfad": "assets/banners/299534.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/f...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Jurassic Park", "jahr": 1993, "schauspieler_cast": "Sam Neill, Laura Dern, Jeff Goldblum, Richard Attenborough",
                "genre_richtung": "Abenteuer, Science Fiction", "laufzeit_min": 127,
                "handlung_beschreibung": "Ein reicher Unternehmer lädt Wissenschaftler in seinen neuen Erlebnispark mit geklonten Dinosauriern ein. Doch das Sicherheitssystem versagt...",
                "fsk": "12", "produktionsfirma_studio": "Universal Pictures, Amblin Entertainment", "regisseur": "Steven Spielberg",
                "filmreihe": "Jurassic Park", "produktionsland": "USA", "deutsche_synchronsprecher": "Wolfgang Condrus für Sam Neill (Alan Grant)",
                "poster_pfad": "assets/posters/329.jpg", "banner_pfad": "assets/banners/329.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/bOfEV75vofSROLY7MI46ofn17K.jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/j9MIo45K53u2jC8G3N12v0O8.jpg"
            },
            {
                "titel": "Alien - Das unheimliche Wesen aus einer fremden Welt", "jahr": 1979, "schauspieler_cast": "Sigourney Weaver, Tom Skerritt, Veronica Cartwright, Harry Dean Stanton",
                "genre_richtung": "Horror, Science Fiction", "laufzeit_min": 117,
                "handlung_beschreibung": "Die Besatzung des Frachtschiffs Nostromo untersucht einen Notruf auf einem fernen Mond und bringt unwissentlich eine tödliche Lebensform an Bord.",
                "fsk": "16", "produktionsfirma_studio": "20th Century Fox, Brandywine Productions", "regisseur": "Ridley Scott",
                "filmreihe": "Alien", "produktionsland": "USA, UK", "deutsche_synchronsprecher": "Hallgerd Bruckhaus für Sigourney Weaver (Ripley)",
                "poster_pfad": "assets/posters/348.jpg", "banner_pfad": "assets/banners/348.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/vfr...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Terminator 2 - Tag der Abrechnung", "jahr": 1991, "schauspieler_cast": "Arnold Schwarzenegger, Linda Hamilton, Edward Furlong, Robert Patrick",
                "genre_richtung": "Action, Science Fiction, Thriller", "laufzeit_min": 137,
                "handlung_beschreibung": "Ein hochentwickelter Terminator aus flüssigem Metall wird in die Vergangenheit geschickt, um den jungen John Connor zu töten, während ein älterer Terminator ihn beschützt.",
                "fsk": "16", "produktionsfirma_studio": "Carolco Pictures, Lightstorm Entertainment", "regisseur": "James Cameron",
                "filmreihe": "Terminator", "produktionsland": "USA, Frankreich", "deutsche_synchronsprecher": "Thomas Danneberg für Arnold Schwarzenegger (T-800)",
                "poster_pfad": "assets/posters/280.jpg", "banner_pfad": "assets/banners/280.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/5...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            },
            {
                "titel": "Zoomania", "jahr": 2016, "schauspieler_cast": "Ginnifer Goodwin, Jason Bateman, Shakira, Idris Elba",
                "genre_richtung": "Animation, Familie, Komödie, Abenteuer", "laufzeit_min": 108,
                "handlung_beschreibung": "In der Metropole Zoomania verbündet sich die ambitionierte Polizisten-Hasin Judy Hopps mit dem listigen Trickdieb-Fuchs Nick Wilde, um eine Verschwörung aufzudecken.",
                "fsk": "0", "produktionsfirma_studio": "Walt Disney Animation Studios", "regisseur": "Byron Howard, Rich Moore",
                "filmreihe": "", "produktionsland": "USA", "deutsche_synchronsprecher": "Josefine Preuß für Judy Hopps, Jochen Schrader für Nick Wilde",
                "poster_pfad": "assets/posters/269149.jpg", "banner_pfad": "assets/banners/269149.jpg",
                "p_url": "https://image.tmdb.org/t/p/w500/5...jpg",
                "b_url": "https://image.tmdb.org/t/p/w1280/am52X5g8ZYZhH7bW0a7n09K7w.jpg"
            }
        ]
        
        # Save to database
        for m in seeded_movies:
            self.add_movie({
                "titel": m["titel"],
                "jahr": m["jahr"],
                "schauspieler_cast": m["schauspieler_cast"],
                "genre_richtung": m["genre_richtung"],
                "laufzeit_min": m["laufzeit_min"],
                "handlung_beschreibung": m["handlung_beschreibung"],
                "fsk": m["fsk"],
                "produktionsfirma_studio": m["produktionsfirma_studio"],
                "regisseur": m["regisseur"],
                "filmreihe": m["filmreihe"],
                "produktionsland": m["produktionsland"],
                "deutsche_synchronsprecher": m["deutsche_synchronsprecher"],
                "poster_pfad": m["poster_pfad"],
                "banner_pfad": m["banner_pfad"]
            })
            
        # Background thread to download images
        import threading
        def download_seeded_images():
            import requests
            
            image_downloads = []
            for m in seeded_movies:
                if m.get("poster_pfad") and m.get("p_url"):
                    image_downloads.append((m["poster_pfad"], m["p_url"]))
                if m.get("banner_pfad") and m.get("b_url"):
                    image_downloads.append((m["banner_pfad"], m["b_url"]))
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            for path, url in image_downloads:
                if not os.path.exists(path):
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    try:
                        resp = requests.get(url, headers=headers, timeout=15)
                        if resp.status_code == 200:
                            with open(path, "wb") as f:
                                f.write(resp.content)
                    except Exception as e:
                        print(f"Error downloading seeded image {url}: {e}")
                        
        threading.Thread(target=download_seeded_images, daemon=True).start()
