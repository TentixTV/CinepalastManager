import os
import json
import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

import sys

def get_app_dir() -> str:
    """Returns absolute path to the application directory."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_config_path() -> str:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        cfg_dir = os.path.join(local_appdata, "CinePalast Manager")
        os.makedirs(cfg_dir, exist_ok=True)
        cfg_path = os.path.join(cfg_dir, "config.json")
        
        # 1. If config already exists in AppData, use it
        if os.path.exists(cfg_path):
            return cfg_path
            
        # 2. Check old V2 location in AppData (under 'app' subfolder)
        old_v2_cfg = os.path.join(local_appdata, "CinePalast Manager", "app", "config.json")
        if os.path.exists(old_v2_cfg):
            try:
                import shutil
                shutil.copy2(old_v2_cfg, cfg_path)
                try:
                    os.remove(old_v2_cfg)
                except Exception:
                    pass
                return cfg_path
            except Exception as e:
                print("Error migrating old V2 config to AppData:", e)
                
        # 3. Check application executable directory
        app_cfg = os.path.join(get_app_dir(), "config.json")
        if os.path.exists(app_cfg):
            try:
                import shutil
                shutil.copy2(app_cfg, cfg_path)
                return cfg_path
            except Exception as e:
                print("Error migrating config from app folder to AppData:", e)
                
        return cfg_path
    return "config.json"

CONFIG_FILE = get_config_path()

def load_config() -> dict:
    """Loads the config dictionary from config.json. Returns default config if the file does not exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
            
    # Initialize config.json with the default TMDB API key if it doesn't exist
    default_config = {"api_key": "c137e57399018df3c480f56ce1db17f8"}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass
    return default_config

def save_config(config_data: dict):
    """Saves the config dictionary to config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

def load_api_key() -> str:
    """Loads the TMDB API key from config.json."""
    cfg = load_config()
    if "api_key" not in cfg:
        cfg["api_key"] = "c137e57399018df3c480f56ce1db17f8"
        save_config(cfg)
    return cfg.get("api_key", "").strip()

def save_api_key(api_key: str):
    """Saves the TMDB API key to config.json, preserving other settings."""
    cfg = load_config()
    cfg["api_key"] = api_key.strip()
    save_config(cfg)

def load_github_token() -> str:
    """Loads the GitHub token from config.json."""
    return load_config().get("github_token", "").strip()

def save_github_token(github_token: str):
    """Saves the GitHub token to config.json, preserving other settings."""
    cfg = load_config()
    cfg["github_token"] = github_token.strip()
    save_config(cfg)

POPULAR_MOVIES_FALLBACK = [
    {'titel': 'Inception', 'jahr': 2010, 'schauspieler_cast': 'Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page, Tom Hardy', 'genre_richtung': 'Action, Science Fiction, Abenteuer', 'laufzeit_min': 148, 'handlung_beschreibung': 'Dom Cobb ist ein begnadeter Dieb, der darauf spezialisiert ist, in der Traumphase wertvolle Geheimnisse aus den Tiefen des Unterbewusstseins zu stehlen.', 'fsk': '12', 'produktionsfirma_studio': 'Warner Bros. Pictures, Legendary Pictures', 'regisseur': 'Christopher Nolan', 'filmreihe': '', 'produktionsland': 'USA, UK', 'deutsche_synchronsprecher': 'Gerrit Schmidt-Foß für Leonardo DiCaprio (Dom Cobb), Robin Kahnmeyer für Joseph Gordon-Levitt (Arthur)', 'poster_pfad': 'assets/posters/27205.jpg', 'banner_pfad': 'assets/banners/27205.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg', 'tmdb_id': 27205},
    {'titel': 'The Dark Knight', 'jahr': 2008, 'schauspieler_cast': 'Christian Bale, Heath Ledger, Aaron Eckhart, Gary Oldman', 'genre_richtung': 'Drama, Action, Krimi, Thriller', 'laufzeit_min': 152, 'handlung_beschreibung': 'Mit Hilfe von Lieutenant Jim Gordon und Bezirksstaatsanwalt Harvey Dent will Batman dem organisierten Verbrechen in Gotham City ein Ende bereiten.', 'fsk': '16', 'produktionsfirma_studio': 'Warner Bros. Pictures, Legendary Pictures', 'regisseur': 'Christopher Nolan', 'filmreihe': 'The Dark Knight Trilogie', 'produktionsland': 'USA, UK', 'deutsche_synchronsprecher': 'David Nathan für Christian Bale (Bruce Wayne / Batman), Simon Jäger für Heath Ledger (Joker)', 'poster_pfad': 'assets/posters/155.jpg', 'banner_pfad': 'assets/banners/155.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/cfT29Im5VDvjE0RpyKOSdCKZal7.jpg', 'tmdb_id': 155},
    {'titel': 'Interstellar', 'jahr': 2014, 'schauspieler_cast': 'Matthew McConaughey, Anne Hathaway, Jessica Chastain, Michael Caine', 'genre_richtung': 'Abenteuer, Drama, Science Fiction', 'laufzeit_min': 169, 'handlung_beschreibung': 'Ein Team von Entdeckern begibt sich auf die wichtigste Mission in der Geschichte der Menschheit, um herauszufinden, ob die Menschheit eine Zukunft unter den Sternen hat.', 'fsk': '12', 'produktionsfirma_studio': 'Paramount Pictures, Warner Bros.', 'regisseur': 'Christopher Nolan', 'filmreihe': '', 'produktionsland': 'USA, UK', 'deutsche_synchronsprecher': 'Matti Klemm für Matthew McConaughey (Cooper), Marie Bierstedt für Anne Hathaway (Brand)', 'poster_pfad': 'assets/posters/157336.jpg', 'banner_pfad': 'assets/banners/157336.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/2ssWTSVklAEc98frZUQhgtGHx7s.jpg', 'tmdb_id': 157336},
    {'titel': 'Avatar', 'jahr': 2009, 'schauspieler_cast': 'Sam Worthington, Zoe Saldana, Sigourney Weaver, Stephen Lang', 'genre_richtung': 'Action, Abenteuer, Fantasy, Science Fiction', 'laufzeit_min': 162, 'handlung_beschreibung': 'Im Jahr 2154 reist der querschnittsgelähmte ehemalige Marine Jake Sully nach Pandora, einer fernen Welt voller exotischer Lebensformen.', 'fsk': '12', 'produktionsfirma_studio': '20th Century Fox, Lightstorm Entertainment', 'regisseur': 'James Cameron', 'filmreihe': 'Avatar', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Alexander Doering für Sam Worthington (Jake Sully), Tanja Geke für Zoe Saldana (Neytiri)', 'poster_pfad': 'assets/posters/19995.jpg', 'banner_pfad': 'assets/banners/19995.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/gKY6q7SjCkAU6FqvqWybDYgUKIF.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/vL5LR6WdxWPjLPFRLe133jXWsh5.jpg', 'tmdb_id': 19995},
    {'titel': 'The Matrix', 'jahr': 1999, 'schauspieler_cast': 'Keanu Reeves, Laurence Fishburne, Carrie-Anne Moss, Hugo Weaving', 'genre_richtung': 'Action, Science Fiction', 'laufzeit_min': 136, 'handlung_beschreibung': 'Der Hacker Neo wird von einer mysteriösen Untergrund-Organisation kontaktiert. Deren Kopf, der berüchtigte Morpheus, weiht ihn in ein furchtbares Geheimnis ein.', 'fsk': '16', 'produktionsfirma_studio': 'Warner Bros. Pictures, Village Roadshow Pictures', 'regisseur': 'Lana Wachowski, Lilly Wachowski', 'filmreihe': 'Matrix', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Benjamin Völz für Keanu Reeves (Neo), Leon Boden für Laurence Fishburne (Morpheus)', 'poster_pfad': 'assets/posters/603.jpg', 'banner_pfad': 'assets/banners/603.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/aOIuZAjPaRIE6CMzbazvcHuHXDc.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/tlm8UkiQsitc8rSuIAscQDCnP8d.jpg', 'tmdb_id': 603},
    {'titel': 'Titanic', 'jahr': 1997, 'schauspieler_cast': 'Leonardo DiCaprio, Kate Winslet, Billy Zane, Kathy Bates', 'genre_richtung': 'Drama, Liebesfilm', 'laufzeit_min': 194, 'handlung_beschreibung': 'Eine Liebesgeschichte an Bord der Titanic zwischen Rose DeWitt Bukater und Jack Dawson, zwei Menschen aus unterschiedlichen Gesellschaftsschichten.', 'fsk': '12', 'produktionsfirma_studio': 'Paramount Pictures, 20th Century Fox', 'regisseur': 'James Cameron', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Gerrit Schmidt-Foß für Leonardo DiCaprio (Jack Dawson), Ulrike Stürzbecher für Kate Winslet (Rose)', 'poster_pfad': 'assets/posters/597.jpg', 'banner_pfad': 'assets/banners/597.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/xnHVX37XZEp33hhCbYlQFq7ux1J.jpg', 'tmdb_id': 597},
    {'titel': 'Gladiator', 'jahr': 2000, 'schauspieler_cast': 'Russell Crowe, Joaquin Phoenix, Connie Nielsen, Oliver Reed', 'genre_richtung': 'Action, Drama, Abenteuer', 'laufzeit_min': 155, 'handlung_beschreibung': 'Der römische General Maximus Decimus Meridius wird verraten, als der machthungrige Sohn des Kaisers seinen Vater ermordet und den Thron besteigt.', 'fsk': '16', 'produktionsfirma_studio': 'DreamWorks SKG, Universal Pictures', 'regisseur': 'Ridley Scott', 'filmreihe': '', 'produktionsland': 'USA, UK', 'deutsche_synchronsprecher': 'Thomas Fritsch für Russell Crowe (Maximus), Marcus Off für Joaquin Phoenix (Commodus)', 'poster_pfad': 'assets/posters/98.jpg', 'banner_pfad': 'assets/banners/98.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/wN2xWp1eIwCKOD0BHTcErTBv1Uq.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/jhk6D8pim3yaByu1801kMoxXFaX.jpg', 'tmdb_id': 98},
    {'titel': 'Pulp Fiction', 'jahr': 1994, 'schauspieler_cast': 'John Travolta, Samuel L. Jackson, Uma Thurman, Bruce Willis', 'genre_richtung': 'Thriller, Krimi', 'laufzeit_min': 154, 'handlung_beschreibung': 'Mehrere miteinander verwobene Geschichten aus der Unterwelt von Los Angeles rund um zwei Auftragskiller, einen Boxer und Gangsterboss Marsellus Wallace.', 'fsk': '16', 'produktionsfirma_studio': 'Miramax Films, A Band Apart', 'regisseur': 'Quentin Tarantino', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Thomas Danneberg für John Travolta (Vincent Vega), Helmut Krauss für Samuel L. Jackson (Jules)', 'poster_pfad': 'assets/posters/680.jpg', 'banner_pfad': 'assets/banners/680.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/vQWk5YBFWF4bZaofAbv0tShwBvQ.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg', 'tmdb_id': 680},
    {'titel': 'Forrest Gump', 'jahr': 1994, 'schauspieler_cast': 'Tom Hanks, Robin Wright, Gary Sinise, Mykelti Williamson', 'genre_richtung': 'Drama, Komödie, Liebesfilm', 'laufzeit_min': 142, 'handlung_beschreibung': 'Forrest Gump ist ein gutmütiger Mann aus Alabama mit einem unterdurchschnittlichen IQ, der an vielen historischen Ereignissen des 20. Jahrhunderts teilnimmt.', 'fsk': '6', 'produktionsfirma_studio': 'Paramount Pictures', 'regisseur': 'Robert Zemeckis', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Arne Elsholtz für Tom Hanks (Forrest Gump)', 'poster_pfad': 'assets/posters/13.jpg', 'banner_pfad': 'assets/banners/13.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/Cw4hIUIAmSYfK9QfaUW5igp9La.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/66Kn4XWhkuPkJxOJyPEx4U2CUfN.jpg', 'tmdb_id': 13},
    {'titel': 'Fight Club', 'jahr': 1999, 'schauspieler_cast': 'Edward Norton, Brad Pitt, Helena Bonham Carter, Meat Loaf', 'genre_richtung': 'Drama, Thriller', 'laufzeit_min': 139, 'handlung_beschreibung': 'Ein schlafloser Büroangestellter und ein charismatischer Seifenverkäufer gründen einen geheimen Kampfverein, der sich bald zu einer revolutionären Bewegung entwickelt.', 'fsk': '18', 'produktionsfirma_studio': 'Fox 2000 Pictures, Regency Enterprises', 'regisseur': 'David Fincher', 'filmreihe': '', 'produktionsland': 'USA, Deutschland', 'deutsche_synchronsprecher': 'Dietmar Wunder für Edward Norton (Erzähler), Tobias Meister für Brad Pitt (Tyler)', 'poster_pfad': 'assets/posters/550.jpg', 'banner_pfad': 'assets/banners/550.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/jSziioSwPVrOy9Yow3XhWIBDjq1.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/xRyINp9KfMLVjRiO5nCsoRDdvvF.jpg', 'tmdb_id': 550},
    {'titel': 'Der Herr der Ringe: Die Gefährten', 'jahr': 2001, 'schauspieler_cast': 'Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom', 'genre_richtung': 'Fantasy, Abenteuer, Action', 'laufzeit_min': 178, 'handlung_beschreibung': 'Der junge Hobbit Frodo Beutlin erbt einen mächtigen Ring. Zusammen mit Gefährten begibt er sich auf die Reise zum Schicksalsberg, um ihn zu vernichten.', 'fsk': '12', 'produktionsfirma_studio': 'New Line Cinema, WingNut Films', 'regisseur': 'Peter Jackson', 'filmreihe': 'Der Herr der Ringe', 'produktionsland': 'Neuseeland, USA', 'deutsche_synchronsprecher': 'Timmo Niesner für Elijah Wood (Frodo), Achim Höppner für Ian McKellen (Gandalf)', 'poster_pfad': 'assets/posters/120.jpg', 'banner_pfad': 'assets/banners/120.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/oiwc338EoBgS4sEI2ixAny4KQKg.jpg', 'tmdb_id': 120},
    {'titel': 'Der Herr der Ringe: Die zwei Türme', 'jahr': 2002, 'schauspieler_cast': 'Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom', 'genre_richtung': 'Fantasy, Abenteuer, Action', 'laufzeit_min': 179, 'handlung_beschreibung': 'Die Gefährten sind getrennt. Frodo und Sam setzen ihren Weg nach Mordor fort, geführt vom geheimnisvollen Gollum, während Aragorn für die Menschen kämpft.', 'fsk': '12', 'produktionsfirma_studio': 'New Line Cinema, WingNut Films', 'regisseur': 'Peter Jackson', 'filmreihe': 'Der Herr der Ringe', 'produktionsland': 'Neuseeland, USA', 'deutsche_synchronsprecher': 'Timmo Niesner für Elijah Wood (Frodo), Jacques Breuer für Viggo Mortensen (Aragorn)', 'poster_pfad': 'assets/posters/121.jpg', 'banner_pfad': 'assets/banners/121.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/5VTN0pR8gcqV3EPUHHfMGnJYN9L.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/6G73mNyooWAEQTpckPSnFxFoNmc.jpg', 'tmdb_id': 121},
    {'titel': 'Der Herr der Ringe: Die Rückkehr des Königs', 'jahr': 2003, 'schauspieler_cast': 'Elijah Wood, Ian McKellen, Viggo Mortensen, Sean Astin, Orlando Bloom', 'genre_richtung': 'Fantasy, Abenteuer, Action', 'laufzeit_min': 201, 'handlung_beschreibung': 'Das Finale des epischen Kampfes um Mittelerde. Frodo erreicht den Schicksalsberg, während die Heere Saurons die weiße Stadt Minas Tirith belagern.', 'fsk': '12', 'produktionsfirma_studio': 'New Line Cinema, WingNut Films', 'regisseur': 'Peter Jackson', 'filmreihe': 'Der Herr der Ringe', 'produktionsland': 'Neuseeland, USA', 'deutsche_synchronsprecher': 'Timmo Niesner für Elijah Wood (Frodo), Achim Höppner für Ian McKellen (Gandalf)', 'poster_pfad': 'assets/posters/122.jpg', 'banner_pfad': 'assets/banners/122.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/rCzpDGLbOoPwLjy3OAm5NUPOTrC.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/ctiw6FZK4N36LmkjSklWEbuvlq9.jpg', 'tmdb_id': 122},
    {'titel': 'Harry Potter und der Stein der Weisen', 'jahr': 2001, 'schauspieler_cast': 'Daniel Radcliffe, Rupert Grint, Emma Watson, Richard Harris, Alan Rickman', 'genre_richtung': 'Fantasy, Abenteuer, Familie', 'laufzeit_min': 152, 'handlung_beschreibung': 'An seinem 11. Geburtstag erfährt Harry Potter, dass er ein Zauberer ist, und wird an der Hogwarts-Schule für Hexerei und Zauberei aufgenommen.', 'fsk': '6', 'produktionsfirma_studio': 'Warner Bros. Pictures, Heyday Films', 'regisseur': 'Chris Columbus', 'filmreihe': 'Harry Potter', 'produktionsland': 'UK, USA', 'deutsche_synchronsprecher': 'Nico Sablik für Daniel Radcliffe (Harry Potter), Gabrielle Pietermann für Emma Watson (Hermine)', 'poster_pfad': 'assets/posters/671.jpg', 'banner_pfad': 'assets/banners/671.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/1XAC6RPT01UX9EQGy2JVn5c8pgy.jpg', 'tmdb_id': 671},
    {'titel': 'Harry Potter und die Kammer des Schreckens', 'jahr': 2002, 'schauspieler_cast': 'Daniel Radcliffe, Rupert Grint, Emma Watson, Kenneth Branagh, Alan Rickman', 'genre_richtung': 'Fantasy, Abenteuer, Familie', 'laufzeit_min': 161, 'handlung_beschreibung': 'Harry kehr nach Hogwarts zurück, doch eine geheimnisvolle Gefahr versteinert die Schüler. Harry muss das Rätsel der Kammer des Schreckens lösen.', 'fsk': '6', 'produktionsfirma_studio': 'Warner Bros. Pictures, Heyday Films', 'regisseur': 'Chris Columbus', 'filmreihe': 'Harry Potter', 'produktionsland': 'UK, USA', 'deutsche_synchronsprecher': 'Nico Sablik für Daniel Radcliffe (Harry Potter), Max Felder für Rupert Grint (Ron)', 'poster_pfad': 'assets/posters/672.jpg', 'banner_pfad': 'assets/banners/672.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/sdEOH0992YZ0QSxgXNIGLq1ToUi.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/1stUIsjawROZxjiCMtqqXqgfZWC.jpg', 'tmdb_id': 672},
    {'titel': 'Star Wars: Episode IV - Eine neue Hoffnung', 'jahr': 1977, 'schauspieler_cast': 'Mark Hamill, Harrison Ford, Carrie Fisher, Alec Guinness', 'genre_richtung': 'Science Fiction, Abenteuer, Action', 'laufzeit_min': 121, 'handlung_beschreibung': 'Der junge Luke Skywalker begibt sich zusammen mit Jedi-Meister Obi-Wan Kenobi und Weltraumpilot Han Solo auf die Mission, Prinzessin Leia vor dem finsteren Darth Vader zu retten.', 'fsk': '6', 'produktionsfirma_studio': 'Lucasfilm, 20th Century Fox', 'regisseur': 'George Lucas', 'filmreihe': 'Star Wars', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Hans-Georg Panczak für Mark Hamill (Luke), Wolfgang Pampel für Harrison Ford (Han Solo)', 'poster_pfad': 'assets/posters/11.jpg', 'banner_pfad': 'assets/banners/11.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/6FfCtAuVAW8XJjZ7eWeLibRLWTw.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/yUiXA68FfQeA8cRBhd0Ao0jIRZt.jpg', 'tmdb_id': 11},
    {'titel': 'Star Wars: Episode V - Das Imperium schlägt zurück', 'jahr': 1980, 'schauspieler_cast': 'Mark Hamill, Harrison Ford, Carrie Fisher, Billy Dee Williams', 'genre_richtung': 'Science Fiction, Abenteuer, Action', 'laufzeit_min': 124, 'handlung_beschreibung': 'Während das Imperium die Rebellen jagt, reist Luke Skywalker zum Sumpfplaneten Dagobah, um vom weisen Jedi-Meister Yoda ausgebildet zu werden.', 'fsk': '6', 'produktionsfirma_studio': 'Lucasfilm, 20th Century Fox', 'regisseur': 'Irvin Kershner', 'filmreihe': 'Star Wars', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Hans-Georg Panczak für Mark Hamill (Luke), Hugo Schrader für Yoda', 'poster_pfad': 'assets/posters/1891.jpg', 'banner_pfad': 'assets/banners/1891.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/nNAeTmF4CtdSgMDplXTDPOpYzsX.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/aJCtkxLLzkk1pECehVjKHA2lBgw.jpg', 'tmdb_id': 1891},
    {'titel': 'Zurück in die Zukunft', 'jahr': 1985, 'schauspieler_cast': 'Michael J. Fox, Christopher Lloyd, Lea Thompson, Crispin Glover', 'genre_richtung': 'Komödie, Science Fiction, Abenteuer', 'laufzeit_min': 116, 'handlung_beschreibung': 'Der Teenager Marty McFly reist versehentlich mit einer von Doc Brown umgebauten Delorean-Zeitmaschine zurück in das Jahr 1955 und gefährdet seine eigene Existenz.', 'fsk': '12', 'produktionsfirma_studio': 'Universal Pictures, Amblin Entertainment', 'regisseur': 'Robert Zemeckis', 'filmreihe': 'Zurück in die Zukunft', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Sven Hasper für Michael J. Fox (Marty), Lutz Mackensy für Christopher Lloyd (Doc Brown)', 'poster_pfad': 'assets/posters/105.jpg', 'banner_pfad': 'assets/banners/105.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/vN5B5WgYscRGcQpVhHl6p9DDTP0.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/5bzPWQ2dFUl2aZKkp7ILJVVkRed.jpg', 'tmdb_id': 105},
    {'titel': 'Der König der Löwen', 'jahr': 1994, 'schauspieler_cast': 'Matthew Broderick, Jeremy Irons, James Earl Jones, Jonathan Taylor Thomas', 'genre_richtung': 'Animation, Familie, Drama', 'laufzeit_min': 88, 'handlung_beschreibung': 'Der kleine Löwe Simba muss nach dem plötzlichen Tod seines Vaters Mufasa fliehen und kehrt Jahre später zurück, um seinen Onkel Scar vom Thron zu stürzen.', 'fsk': '0', 'produktionsfirma_studio': 'Walt Disney Pictures', 'regisseur': 'Roger Allers, Rob Minkoff', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Frank-Lorenz Engel für Simba (Erwachsen), Thomas Fritsch für Scar', 'poster_pfad': 'assets/posters/8587.jpg', 'banner_pfad': 'assets/banners/8587.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/sKCr78MXSLixwmZ8DyJLrpMsd15.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/q00H8EqULYSK74lgevMkhmGGLHn.jpg', 'tmdb_id': 8587},
    {'titel': 'Django Unchained', 'jahr': 2012, 'schauspieler_cast': 'Jamie Foxx, Christoph Waltz, Leonardo DiCaprio, Kerry Washington', 'genre_richtung': 'Western, Drama', 'laufzeit_min': 165, 'handlung_beschreibung': 'Ein befreiter Sklave reist mit Hilfe eines deutschen Kopfgeldjägers quer durch die USA, um seine Frau aus den Fängen eines grausamen Plantagenbesitzers zu befreien.', 'fsk': '16', 'produktionsfirma_studio': 'The Weinstein Company, Columbia Pictures', 'regisseur': 'Quentin Tarantino', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Charles Rettinghaus für Jamie Foxx (Django), Christoph Waltz für sich selbst (Dr. Schultz)', 'poster_pfad': 'assets/posters/68718.jpg', 'banner_pfad': 'assets/banners/68718.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/mhf63wOnaLCnzxeHgngTH98WaVh.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/2oZklIzUbvZXXzIFzv7Hi68d6xf.jpg', 'tmdb_id': 68718},
    {'titel': 'Joker', 'jahr': 2019, 'schauspieler_cast': 'Joaquin Phoenix, Robert De Niro, Zazie Beetz, Frances Conroy', 'genre_richtung': 'Drama, Krimi, Thriller', 'laufzeit_min': 122, 'handlung_beschreibung': 'Die Ursprungsgeschichte von Jokers Wandlung vom erfolglosen Comedian Arthur Fleck zum legendären psychopathischen Schurken in Gotham City.', 'fsk': '16', 'produktionsfirma_studio': 'Warner Bros. Pictures, DC Films', 'regisseur': 'Todd Phillips', 'filmreihe': 'Joker', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Tobias Meister für Joaquin Phoenix (Arthur Fleck / Joker)', 'poster_pfad': 'assets/posters/475557.jpg', 'banner_pfad': 'assets/banners/475557.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/hO7KbdvGOtDdeg0W4Y5nKEHeDDh.jpg', 'tmdb_id': 475557},
    {'titel': 'Der Pate', 'jahr': 1972, 'schauspieler_cast': 'Marlon Brando, Al Pacino, James Caan, Richard S. Castellano', 'genre_richtung': 'Krimi, Drama', 'laufzeit_min': 175, 'handlung_beschreibung': 'Der alternde Mafiaboss Don Vito Corleone übergibt die Kontrolle über sein kriminelles Imperium zögerlich an seinen kriegsheimkehrenden Sohn Michael.', 'fsk': '16', 'produktionsfirma_studio': 'Paramount Pictures, Alfran Productions', 'regisseur': 'Francis Ford Coppola', 'filmreihe': 'Der Pate', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Lutz Mackensy für Al Pacino (Michael Corleone)', 'poster_pfad': 'assets/posters/238.jpg', 'banner_pfad': 'assets/banners/238.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/tSPT36ZKlP2WVHJLM4cQPLSzv3b.jpg', 'tmdb_id': 238},
    {'titel': 'Schindlers Liste', 'jahr': 1993, 'schauspieler_cast': 'Liam Neeson, Ben Kingsley, Ralph Fiennes, Caroline Goodall', 'genre_richtung': 'Drama, Historie', 'laufzeit_min': 195, 'handlung_beschreibung': 'Die wahre Geschichte des sudetendeutschen Industriellen Oskar Schindler, der im Zweiten Weltkrieg über 1000 polnische Juden vor dem Holocaust rettete.', 'fsk': '12', 'produktionsfirma_studio': 'Universal Pictures, Amblin Entertainment', 'regisseur': 'Steven Spielberg', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Stephan Schwartz für Liam Neeson (Oskar Schindler)', 'poster_pfad': 'assets/posters/424.jpg', 'banner_pfad': 'assets/banners/424.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/sF1U4EUQS8YHUYjNl3pMGNIQyr0.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/zb6fM1CX41D9rF9hdgclu0peUmy.jpg', 'tmdb_id': 424},
    {'titel': 'Die Verurteilten', 'jahr': 1994, 'schauspieler_cast': 'Tim Robbins, Morgan Freeman, Bob Gunton, William Sadler', 'genre_richtung': 'Drama', 'laufzeit_min': 142, 'handlung_beschreibung': 'Ein unschuldig zu lebenslanger Haft verurteilter Bankier freundet sich im Gefängnis mit einem älteren Mithäftling an und behält über Jahrzehnte die Hoffnung auf Freiheit.', 'fsk': '12', 'produktionsfirma_studio': 'Castle Rock Entertainment', 'regisseur': 'Frank Darabont', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Tobias Meister für Tim Robbins (Andy), Klaus Sonnenschein für Morgan Freeman (Red)', 'poster_pfad': 'assets/posters/278.jpg', 'banner_pfad': 'assets/banners/278.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/zfbjgQE1uSd9wiPTX4VzsLi0rGG.jpg', 'tmdb_id': 278},
    {'titel': 'Sieben', 'jahr': 1995, 'schauspieler_cast': 'Brad Pitt, Morgan Freeman, Gwyneth Paltrow, Kevin Spacey', 'genre_richtung': 'Krimi, Thriller, Mystery', 'laufzeit_min': 127, 'handlung_beschreibung': 'Zwei Detektive jagen einen psychopathischen Serienmörder, der seine Opfer nach dem Muster der sieben Todsünden tötet.', 'fsk': '16', 'produktionsfirma_studio': 'New Line Cinema', 'regisseur': 'David Fincher', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Tobias Meister für Brad Pitt (Mills), Klaus Sonnenschein für Morgan Freeman (Somerset)', 'poster_pfad': 'assets/posters/807.jpg', 'banner_pfad': 'assets/banners/807.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/191nKfP0ehp3uIvWqgPbFmI4lv9.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/i5H7zusQGsysGQ8i6P361Vnr0n2.jpg', 'tmdb_id': 807},
    {'titel': 'Léon - Der Profi', 'jahr': 1994, 'schauspieler_cast': 'Jean Reno, Natalie Portman, Gary Oldman, Danny Aiello', 'genre_richtung': 'Action, Thriller, Drama', 'laufzeit_min': 110, 'handlung_beschreibung': 'Ein wortkarger Profikiller nimmt ein 12-jähriges Mädchen nach der Ermordung ihrer Familie bei sich auf und bringt ihr das Handwerk des Tötens bei.', 'fsk': '16', 'produktionsfirma_studio': 'Gaumont, Les Films du Dauphin', 'regisseur': 'Luc Besson', 'filmreihe': '', 'produktionsland': 'Frankreich', 'deutsche_synchronsprecher': 'Joachim Kerzel für Jean Reno (Léon)', 'poster_pfad': 'assets/posters/101.jpg', 'banner_pfad': 'assets/banners/101.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/bxB2q91nKYp8JNzqE7t7TWBVupB.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/fj0hwDJEOOHllRim2BMt5L7tbjf.jpg', 'tmdb_id': 101},
    {'titel': 'Der Soldat James Ryan', 'jahr': 1998, 'schauspieler_cast': 'Tom Hanks, Edward Burns, Tom Sizemore, Matt Damon', 'genre_richtung': 'Drama, Kriegsfilm', 'laufzeit_min': 169, 'handlung_beschreibung': 'Im Zweiten Weltkrieg begibt sich eine US-Infanteriegruppe hinter die feindlichen Linien, um einen Soldaten zu retten, dessen Brüder alle gefallen sind.', 'fsk': '16', 'produktionsfirma_studio': 'Paramount Pictures, DreamWorks SKG', 'regisseur': 'Steven Spielberg', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Arne Elsholtz für Tom Hanks (Captain Miller)', 'poster_pfad': 'assets/posters/857.jpg', 'banner_pfad': 'assets/banners/857.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/uqx37cS8cpHg8U35f9U5IBlrCV3.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/bdD39MpSVhKjxarTxLSfX6baoMP.jpg', 'tmdb_id': 857},
    {'titel': 'Shutter Island', 'jahr': 2010, 'schauspieler_cast': 'Leonardo DiCaprio, Mark Ruffalo, Ben Kingsley, Michelle Williams', 'genre_richtung': 'Drama, Thriller, Mystery', 'laufzeit_min': 138, 'handlung_beschreibung': 'Ein US-Marshal ermittelt im Jahr 1954 im mysteriösen Verschwinden einer Mörderin aus einer geschlossenen Anstalt auf einer abgelegenen Insel.', 'fsk': '16', 'produktionsfirma_studio': 'Paramount Pictures', 'regisseur': 'Martin Scorsese', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Gerrit Schmidt-Foß für Leonardo DiCaprio (Teddy Daniels)', 'poster_pfad': 'assets/posters/11324.jpg', 'banner_pfad': 'assets/banners/11324.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/nrmXQ0zcZUL8jFLrakWc90IR8z9.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/rbZvGN1A1QyZuoKzhCw8QPmf2q0.jpg', 'tmdb_id': 11324},
    {'titel': 'The Wolf of Wall Street', 'jahr': 2013, 'schauspieler_cast': 'Leonardo DiCaprio, Jonah Hill, Margot Robbie, Matthew McConaughey', 'genre_richtung': 'Komödie, Drama, Biografie', 'laufzeit_min': 180, 'handlung_beschreibung': 'Der Aufstieg und tiefe Fall des betrügerischen New Yorker Börsenmaklers Jordan Belfort, geprägt von extremem Luxus, Drogen und Korruption.', 'fsk': '16', 'produktionsfirma_studio': 'Paramount Pictures, Red Granite Pictures', 'regisseur': 'Martin Scorsese', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Gerrit Schmidt-Foß für Leonardo DiCaprio (Jordan Belfort)', 'poster_pfad': 'assets/posters/106646.jpg', 'banner_pfad': 'assets/banners/106646.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/kW9LmvYHAaS9iA0tHmZVq8hQYoq.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/7Nwnmyzrtd0FkcRyPqmdzTPppQa.jpg', 'tmdb_id': 106646},
    {'titel': 'Ziemlich beste Freunde', 'jahr': 2011, 'schauspieler_cast': 'François Cluzet, Omar Sy, Anne Le Ny, Audrey Fleurot', 'genre_richtung': 'Komödie, Drama', 'laufzeit_min': 112, 'handlung_beschreibung': 'Ein reicher querschnittsgelähmter Adeliger stellt einen jungen, unkonventionellen Pfleger aus den Pariser Banlieues ein. Eine tiefe Freundschaft entsteht.', 'fsk': '6', 'produktionsfirma_studio': 'Gaumont', 'regisseur': 'Olivier Nakache, Éric Toledano', 'filmreihe': '', 'produktionsland': 'Frankreich', 'deutsche_synchronsprecher': 'Sascha Rotermund für Omar Sy (Driss)', 'poster_pfad': 'assets/posters/77338.jpg', 'banner_pfad': 'assets/banners/77338.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/1QU7HKgsQbGpzsJbJK4pAVQV9F5.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/cK070s3Qdn1Ib7Gq8RgIyJKgvu3.jpg', 'tmdb_id': 77338},
    {'titel': 'Pirates of the Caribbean: Fluch der Karibik', 'jahr': 2003, 'schauspieler_cast': 'Johnny Depp, Geoffrey Rush, Orlando Bloom, Keira Knightley', 'genre_richtung': 'Abenteuer, Fantasy, Action', 'laufzeit_min': 143, 'handlung_beschreibung': 'Der exzentrische Piratenkapitän Jack Sparrow versucht mit Hilfe eines Hufschmieds, sein Schiff Black Pearl und die Gouverneurstochter Elizabeth Swann zurückzuerlangen.', 'fsk': '12', 'produktionsfirma_studio': 'Walt Disney Pictures, Jerry Bruckheimer Films', 'regisseur': 'Gore Verbinski', 'filmreihe': 'Fluch der Karibik', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Marcus Off für Johnny Depp (Jack Sparrow)', 'poster_pfad': 'assets/posters/22.jpg', 'banner_pfad': 'assets/banners/22.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/kvDwL2gTf6yxujbsWbsGQB3Z9Wa.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/uRNgkJSkNBFbbn9fPsEjDIy8Sh3.jpg', 'tmdb_id': 22},
    {'titel': 'Whiplash', 'jahr': 2014, 'schauspieler_cast': 'Miles Teller, J.K. Simmons, Paul Reiser, Melissa Benoist', 'genre_richtung': 'Drama, Musik', 'laufzeit_min': 107, 'handlung_beschreibung': 'Ein junger Schlagzeugschüler wird an einem New Yorker Musikkonservatorium von einem sadistischen Bandleader bis an seine absoluten Grenzen getrieben.', 'fsk': '12', 'produktionsfirma_studio': 'Blumhouse Productions', 'regisseur': 'Damien Chazelle', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Oliver Kalkofe für J.K. Simmons (Terence Fletcher)', 'poster_pfad': 'assets/posters/244786.jpg', 'banner_pfad': 'assets/banners/244786.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/7fn624j5lj3xTme2SgiLCeuedmO.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/wbQa0EnWUyRzQ5d1pHLNRlmsCUP.jpg', 'tmdb_id': 244786},
    {'titel': 'Spider-Man: A New Universe', 'jahr': 2018, 'schauspieler_cast': 'Shameik Moore, Jake Johnson, Hailee Steinfeld, Mahershala Ali', 'genre_richtung': 'Animation, Action, Abenteuer, Science Fiction', 'laufzeit_min': 117, 'handlung_beschreibung': 'Der Teenager Miles Morales erlernt seine neuen Spinnenkräfte und verbündet sich mit Spider-Helden aus anderen Dimensionen, um eine Bedrohung abzuwehren.', 'fsk': '6', 'produktionsfirma_studio': 'Columbia Pictures, Sony Pictures Animation', 'regisseur': 'Bob Persichetti, Peter Ramsey', 'filmreihe': 'Spider-Man (Spider-Verse)', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Marco Eßer für Shameik Moore (Miles Morales)', 'poster_pfad': 'assets/posters/324857.jpg', 'banner_pfad': 'assets/banners/324857.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/iiZZdoQBEYBv6id8su7ImL0oCbD.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/8mnXR9rey5uQ08rZAvzojKWbDQS.jpg', 'tmdb_id': 324857},
    {'titel': 'Die Truman Show', 'jahr': 1998, 'schauspieler_cast': 'Jim Carrey, Laura Linney, Noah Emmerich, Ed Harris', 'genre_richtung': 'Komödie, Drama', 'laufzeit_min': 103, 'handlung_beschreibung': 'Truman Burbank ahnt nicht, dass sein gesamtes Leben von Geburt an eine weltweite Reality-TV-Show ist, in der alle Personen außer ihm Schauspieler sind.', 'fsk': '12', 'produktionsfirma_studio': 'Paramount Pictures', 'regisseur': 'Peter Weir', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Stefan Fredrich für Jim Carrey (Truman Burbank)', 'poster_pfad': 'assets/posters/1998.jpg', 'banner_pfad': 'assets/banners/1998.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/dG6ytJeEvQXQyCAZTsH9q82rgPS.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/dG6ytJeEvQXQyCAZTsH9q82rgPS.jpg', 'tmdb_id': 1998},
    {'titel': 'The Green Mile', 'jahr': 1999, 'schauspieler_cast': 'Tom Hanks, David Morse, Bonnie Hunt, Michael Clarke Duncan', 'genre_richtung': 'Fantasy, Drama, Krimi', 'laufzeit_min': 189, 'handlung_beschreibung': 'Ein Gefängnisaufseher im Todestrakt stellt fest, dass ein riesiger, sanftmütiger Häftling mit der Gabe der Heilung gesegnet ist.', 'fsk': '12', 'produktionsfirma_studio': 'Castle Rock Entertainment', 'regisseur': 'Frank Darabont', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Arne Elsholtz für Tom Hanks (Paul Edgecomb)', 'poster_pfad': 'assets/posters/497.jpg', 'banner_pfad': 'assets/banners/497.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/8VG8fDNiy50H4FedGwdSVUPoaJe.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/b6HWTOxn1xevvyHU2K9ICvaRU6g.jpg', 'tmdb_id': 497},
    {'titel': 'Avengers: Endgame', 'jahr': 2019, 'schauspieler_cast': 'Robert Downey Jr., Chris Evans, Mark Ruffalo, Chris Hemsworth, Scarlett Johansson', 'genre_richtung': 'Action, Science Fiction, Abenteuer', 'laufzeit_min': 181, 'handlung_beschreibung': 'Nachdem Thanos das halbe Universum ausgelöscht hat, schließen sich die überlebenden Avengers zusammen, um das Geschehene rückgängig zu machen.', 'fsk': '12', 'produktionsfirma_studio': 'Marvel Studios', 'regisseur': 'Anthony Russo, Joe Russo', 'filmreihe': 'The Avengers', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Tobias Meister für Robert Downey Jr. (Iron Man)', 'poster_pfad': 'assets/posters/299534.jpg', 'banner_pfad': 'assets/banners/299534.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/ulzhLuWrPK07P1YkdWQLZnQh1JL.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/7RyHsO4yDXtBv1zUU3mTpHeQ0d5.jpg', 'tmdb_id': 299534},
    {'titel': 'Jurassic Park', 'jahr': 1993, 'schauspieler_cast': 'Sam Neill, Laura Dern, Jeff Goldblum, Richard Attenborough', 'genre_richtung': 'Abenteuer, Science Fiction', 'laufzeit_min': 127, 'handlung_beschreibung': 'Ein reicher Unternehmer lädt Wissenschaftler in seinen neuen Erlebnispark mit geklonten Dinosauriern ein. Doch das Sicherheitssystem versagt...', 'fsk': '12', 'produktionsfirma_studio': 'Universal Pictures, Amblin Entertainment', 'regisseur': 'Steven Spielberg', 'filmreihe': 'Jurassic Park', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Wolfgang Condrus für Sam Neill (Alan Grant)', 'poster_pfad': 'assets/posters/329.jpg', 'banner_pfad': 'assets/banners/329.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/63viWuPfYQjRYLSZSZNq7dglJP5.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/o7LzVmlOSYc3EspyVMC9bsTTARc.jpg', 'tmdb_id': 329},
    {'titel': 'Alien - Das unheimliche Wesen aus einer fremden Welt', 'jahr': 1979, 'schauspieler_cast': 'Sigourney Weaver, Tom Skerritt, Veronica Cartwright, Harry Dean Stanton', 'genre_richtung': 'Horror, Science Fiction', 'laufzeit_min': 117, 'handlung_beschreibung': 'Die Besatzung des Frachtschiffs Nostromo untersucht einen Notruf auf einem fernen Mond und bringt unwissentlich eine tödliche Lebensform an Bord.', 'fsk': '16', 'produktionsfirma_studio': '20th Century Fox, Brandywine Productions', 'regisseur': 'Ridley Scott', 'filmreihe': 'Alien', 'produktionsland': 'USA, UK', 'deutsche_synchronsprecher': 'Hallgerd Bruckhaus für Sigourney Weaver (Ripley)', 'poster_pfad': 'assets/posters/348.jpg', 'banner_pfad': 'assets/banners/348.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/cEobq5QrnOJjO6giDs8q4RxmMKh.jpg', 'tmdb_id': 348},
    {'titel': 'Terminator 2 - Tag der Abrechnung', 'jahr': 1991, 'schauspieler_cast': 'Arnold Schwarzenegger, Linda Hamilton, Edward Furlong, Robert Patrick', 'genre_richtung': 'Action, Science Fiction, Thriller', 'laufzeit_min': 137, 'handlung_beschreibung': 'Ein hochentwickelter Terminator aus flüssigem Metall wird in die Vergangenheit geschickt, um den jungen John Connor zu töten, während ein älterer Terminator ihn beschützt.', 'fsk': '16', 'produktionsfirma_studio': 'Carolco Pictures, Lightstorm Entertainment', 'regisseur': 'James Cameron', 'filmreihe': 'Terminator', 'produktionsland': 'USA, Frankreich', 'deutsche_synchronsprecher': 'Thomas Danneberg für Arnold Schwarzenegger (T-800)', 'poster_pfad': 'assets/posters/280.jpg', 'banner_pfad': 'assets/banners/280.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/jFTVD4XoWQTcg7wdyJKa8PEds5q.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/izkMjmhauFx9DjoBQqM5sM5WAwE.jpg', 'tmdb_id': 280},
    {'titel': 'Zoomania', 'jahr': 2016, 'schauspieler_cast': 'Ginnifer Goodwin, Jason Bateman, Shakira, Idris Elba', 'genre_richtung': 'Animation, Familie, Komödie, Abenteuer', 'laufzeit_min': 108, 'handlung_beschreibung': 'In der Metropole Zoomania verbündet sich die ambitionierte Polizisten-Hasin Judy Hopps mit dem listigen Trickdieb-Fuchs Nick Wilde, um eine Verschwörung aufzudecken.', 'fsk': '0', 'produktionsfirma_studio': 'Walt Disney Animation Studios', 'regisseur': 'Byron Howard, Rich Moore', 'filmreihe': '', 'produktionsland': 'USA', 'deutsche_synchronsprecher': 'Josefine Preuß für Judy Hopps, Jochen Schrader für Nick Wilde', 'poster_pfad': 'assets/posters/269149.jpg', 'banner_pfad': 'assets/banners/269149.jpg', 'p_url': 'https://image.tmdb.org/t/p/w500/hlK0e0wAQ3VLuJcsfIYPvb4JVud.jpg', 'b_url': 'https://image.tmdb.org/t/p/w1280/9tOkjBEiiGcaClgJFtwocStZvIT.jpg', 'tmdb_id': 269149},
]

class TMDBClient:
    """
    HTTP client targeting TMDB API fetching metadata in German ('de-DE').
    """
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

    def __init__(self):
        pass

    def get_api_key(self) -> str:
        return load_api_key()

    def _get_auth(self, key: str) -> tuple:
        """
        Determines if the key is a v3 API Key or a v4 Bearer Token.
        Returns: (headers, params)
        """
        key = key.strip()
        if len(key) > 50 or key.startswith("eyJ"):
            return {"Authorization": f"Bearer {key}"}, {}
        return {}, {"api_key": key}

    def has_valid_key(self) -> bool:
        key = self.get_api_key()
        if not key:
            return False
        # Test the key briefly with a lightweight request
        try:
            url = f"{self.BASE_URL}/configuration"
            headers, params = self._get_auth(key)
            response = requests.get(url, headers=headers, params=params, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def search_movies(self, query: str, search_filter: str = "Alles") -> List[Dict]:
        """
        Searches TMDB for movies by title query, supporting actor and director filters.
        Uses TMDB API key if configured; otherwise, scrapes TMDB public search website.
        """
        api_key = self.get_api_key()
        if api_key:
            try:
                if search_filter in ["Schauspieler", "Regisseur"]:
                    # 1. Resolve the person name to their TMDB person ID
                    url = f"{self.BASE_URL}/search/person"
                    headers, params = self._get_auth(api_key)
                    params.update({
                        "query": query,
                        "language": "de-DE",
                        "page": 1
                    })
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    response.raise_for_status()
                    search_data = response.json()
                    
                    people = search_data.get("results", [])
                    if not people:
                        return []
                        
                    # Take the top match (most popular person)
                    person_id = people[0].get("id")
                    if not person_id:
                        return []
                        
                    # 2. Query the complete movie credits for that person
                    credits_url = f"{self.BASE_URL}/person/{person_id}/movie_credits"
                    c_headers, c_params = self._get_auth(api_key)
                    c_params.update({
                        "language": "de-DE"
                    })
                    
                    credits_resp = requests.get(credits_url, headers=c_headers, params=c_params, timeout=10)
                    credits_resp.raise_for_status()
                    credits_data = credits_resp.json()
                    
                    # 3. Extract cast or crew depending on the filter
                    results = []
                    movie_list = []
                    if search_filter == "Schauspieler":
                        movie_list = credits_data.get("cast", [])
                    elif search_filter == "Regisseur":
                        movie_list = [item for item in credits_data.get("crew", []) if item.get("job") == "Director"]
                        
                    for item in movie_list:
                        if item.get("media_type", "movie") == "movie":
                            release_date = item.get("release_date", "")
                            year = release_date.split("-")[0] if release_date else "k.A."
                            results.append({
                                "tmdb_id": item["id"],
                                "titel": item.get("title") or item.get("name") or "k.A.",
                                "original_titel": item.get("original_title", ""),
                                "jahr": year,
                                "poster_path": item.get("poster_path")
                            })
                            
                    # De-duplicate results
                    seen = set()
                    unique_results = []
                    for r in results:
                        if r["tmdb_id"] not in seen:
                            seen.add(r["tmdb_id"])
                            unique_results.append(r)
                    return unique_results
                else:
                    url = f"{self.BASE_URL}/search/movie"
                    headers, params = self._get_auth(api_key)
                    params.update({
                        "query": query,
                        "language": "de-DE",
                        "page": 1
                    })
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    results = []
                    for item in data.get("results", []):
                        release_date = item.get("release_date", "")
                        year = release_date.split("-")[0] if release_date else "k.A."
                        results.append({
                            "tmdb_id": item["id"],
                            "titel": item["title"],
                            "original_titel": item.get("original_title", ""),
                            "jahr": year,
                            "poster_path": item.get("poster_path")
                        })
                    return results
            except Exception as e:
                print(f"API search failed (falling back to web scraping): {e}")

        # Web Scraper Fallback (no API Key required)
        try:
            escaped_query = urllib.parse.quote(query)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
            }
            
            if search_filter in ["Schauspieler", "Regisseur"]:
                search_url = f"https://www.themoviedb.org/search/person?query={escaped_query}"
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                person_id = None
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    match = re.search(r'^/person/(\d+)', href)
                    if match:
                        person_id = match.group(1)
                        break
                        
                if not person_id:
                    return []
                    
                person_url = f"https://www.themoviedb.org/person/{person_id}"
                resp = requests.get(person_url, headers=headers, timeout=10)
                resp.raise_for_status()
                person_soup = BeautifulSoup(resp.text, 'html.parser')
                
                target_heading = "Darsteller" if search_filter == "Schauspieler" else "Regie"
                results = []
                found_table = False
                
                for h3 in person_soup.find_all("h3"):
                    if h3.text.strip() == target_heading:
                        table = h3.find_next_sibling("table")
                        if table:
                            found_table = True
                            for credit_table in table.find_all("table", class_="credit_group"):
                                year_td = credit_table.find("td", class_="year")
                                year = year_td.text.strip() if year_td else "k.A."
                                if not year or year == "—":
                                    year = "k.A."
                                else:
                                    year_match = re.search(r'\b(19\d\d|20\d\d)\b', year)
                                    if year_match:
                                        year = year_match.group(1)
                                    else:
                                        year = "k.A."
                                
                                for row in credit_table.find_all("tr"):
                                    role_td = row.find("td", class_="role")
                                    if role_td:
                                        link = role_td.find("a", href=True)
                                        if link:
                                            m_href = link["href"]
                                            m_match = re.search(r'^/movie/(\d+)', m_href)
                                            if m_match:
                                                tmdb_id = int(m_match.group(1))
                                                title = link.text.strip()
                                                results.append({
                                                    "tmdb_id": tmdb_id,
                                                    "titel": title,
                                                    "original_titel": title,
                                                    "jahr": year,
                                                    "poster_path": ""
                                                })
                            break
                            
                # Fallback to general links if specific table not found
                if not found_table:
                    seen = set()
                    for a in person_soup.find_all("a", href=True):
                        m_href = a["href"]
                        m_match = re.search(r'^/movie/(\d+)', m_href)
                        if m_match:
                            tmdb_id = int(m_match.group(1))
                            if tmdb_id not in seen:
                                seen.add(tmdb_id)
                                title = a.text.strip()
                                if title:
                                    results.append({
                                        "tmdb_id": tmdb_id,
                                        "titel": title,
                                        "original_titel": title,
                                        "jahr": "k.A.",
                                        "poster_path": ""
                                    })
                                    
                # De-duplicate results
                seen = set()
                unique_results = []
                for r in results:
                    if r["tmdb_id"] not in seen:
                        seen.add(r["tmdb_id"])
                        unique_results.append(r)
                return unique_results
                
            else:
                url = f"https://www.themoviedb.org/search?query={escaped_query}"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.find_all("div", class_="comp:media-card")
                
                results = []
                for card in cards:
                    link = card.find("a", href=True)
                    if link:
                        href = link["href"]
                        match = re.search(r'^/movie/(\d+)', href)
                        if match:
                            tmdb_id = int(match.group(1))
                            
                            title_el = card.find("h2")
                            title = title_el.text.strip() if title_el else ""
                            if not title:
                                title = link.text.strip()
                                
                            year_el = card.find("span", class_="release_date")
                            year_str = year_el.text.strip() if year_el else ""
                            year = None
                            year_match = re.search(r'\b(19\d\d|20\d\d)\b', year_str)
                            if year_match:
                                year = int(year_match.group(1))
                                
                            poster_path = ""
                            img = card.find("img")
                            if img:
                                src = img.get("src") or img.get("data-src") or ""
                                img_match = re.search(r'/t/p/w[^/]+/([^/]+\.(?:jpg|png|webp|jpeg))', src)
                                if img_match:
                                    poster_path = "/" + img_match.group(1)
                                    
                            results.append({
                                "tmdb_id": tmdb_id,
                                "titel": title,
                                "original_titel": title,
                                "jahr": year if year else "k.A.",
                                "poster_path": poster_path
                            })
                return results
        except Exception as e:
            print(f"Web scraper fallback failed: {e}")
            return []

    def get_popular_movies(self) -> List[Dict]:
        """
        Fetches currently popular movies from TMDB API.
        If no API key is set, returns a default set of popular movies.
        """
        api_key = self.get_api_key()
        if api_key:
            try:
                url = f"{self.BASE_URL}/movie/popular"
                headers, params = self._get_auth(api_key)
                params.update({
                    "language": "de-DE",
                    "page": 1
                })
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                results = []
                for item in data.get("results", []):
                    release_date = item.get("release_date", "")
                    year = release_date.split("-")[0] if release_date else "k.A."
                    results.append({
                        "tmdb_id": item["id"],
                        "titel": item.get("title") or item.get("name") or "k.A.",
                        "original_titel": item.get("original_title", ""),
                        "jahr": year,
                        "poster_path": item.get("poster_path")
                    })
                return results[:18]
            except Exception as e:
                print("Error get_popular_movies from TMDB API:", e)
                
        # Fallback list of popular movies if offline or no API key
        fallback_results = []
        for m in POPULAR_MOVIES_FALLBACK:
            fallback_results.append({
                "tmdb_id": m["tmdb_id"],
                "titel": m["titel"],
                "jahr": str(m["jahr"]),
                "poster_path": m["poster_pfad"]
            })
        return fallback_results[:18]

    def scrape_synchronsprecher(self, title: str, year: Optional[int] = None) -> str:
        """
        Scrapes German voice actors for a movie title and optional release year from synchronkartei.de.
        Fails gracefully and returns an empty string on error or if no matches exist.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            # 1. Search title
            escaped_title = urllib.parse.quote(title)
            search_url = f"https://www.synchronkartei.de/suche?q={escaped_title}"
            response = requests.get(search_url, headers=headers, timeout=8)
            if response.status_code != 200:
                return ""
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 2. Extract film links
            film_links = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/film/" in href:
                    film_links.append((link.text.strip(), href))
                    
            if not film_links:
                return ""
                
            # 3. Find the best matching link
            target_href = None
            if year:
                year_str = str(year)
                for link_text, href in film_links:
                    if year_str in link_text:
                        target_href = href
                        break
            
            # Fallback: use first link
            if not target_href:
                target_href = film_links[0][1]
                
            # 4. Fetch the film page
            if not target_href.startswith("https://"):
                film_url = f"https://www.synchronkartei.de/{target_href.lstrip('/')}"
            else:
                film_url = target_href
                
            response = requests.get(film_url, headers=headers, timeout=8)
            if response.status_code != 200:
                return ""
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 5. Extract tables and rows
            actors_info = []
            tables = soup.find_all("table", class_="table")
            for table in tables:
                for row in table.find_all("tr"):
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        # Columns layout: cols[0] = Actor, cols[1] = Voice Actor, cols[2] = Character/Role
                        actor = cols[0].text.strip()
                        voice_actor = cols[1].text.strip()
                        character = cols[2].text.strip()
                        
                        if voice_actor and actor:
                            # Clean unicode whitespaces
                            voice_actor = " ".join(voice_actor.split())
                            actor = " ".join(actor.split())
                            character = " ".join(character.split())
                            actors_info.append(f"{voice_actor} für {actor} ({character})")
                            
            if actors_info:
                return ", ".join(actors_info[:12]) # limit to top 12 entries
        except Exception as e:
            print(f"Error scraping Deutsche Synchronkartei for '{title}': {e}")
            
        return ""

    def _scrape_movie_page(self, tmdb_id: int) -> Dict:
        """
        Scrapes a movie detail page directly from the public TMDb website.
        """
        url = f"https://www.themoviedb.org/movie/{tmdb_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = ""
        year = None
        title_h2 = soup.find("h2")
        if title_h2:
            title_a = title_h2.find("a")
            if title_a:
                title = title_a.text.strip()
            else:
                title = title_h2.text.strip()
                title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
                
            year_span = title_h2.find("span", class_="release_date")
            if not year_span:
                year_span = soup.find("span", class_=re.compile("release_date"))
            if year_span:
                year_match = re.search(r'\b(19\d\d|20\d\d)\b', year_span.text)
                if year_match:
                    year = int(year_match.group(1))
                    
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "").replace(" - The Movie Database (TMDB)", "")
                
        overview = ""
        desc_div = soup.find("div", class_="overview")
        if desc_div:
            overview = desc_div.text.strip()
        if not overview:
            p_desc = soup.find("p", class_="overview")
            if p_desc:
                overview = p_desc.text.strip()
                
        genres = []
        genres_span = soup.find("span", class_="genres")
        if genres_span:
            for a in genres_span.find_all("a"):
                genres.append(a.text.strip())
        genre_richtung = ", ".join(genres) if genres else "k.A."
        
        runtime = 0
        runtime_span = soup.find("span", class_="runtime")
        if runtime_span:
            runtime_text = runtime_span.text.strip()
            m_match = re.search(r'(\d+)m', runtime_text)
            h_match = re.search(r'(\d+)h', runtime_text)
            if h_match:
                runtime += int(h_match.group(1)) * 60
            if m_match:
                runtime += int(m_match.group(1))
                
        director = "k.A."
        crew_list = soup.find_all("li", class_="profile")
        directors = []
        for crew in crew_list:
            role = crew.find("p", class_="character")
            if role and "Director" in role.text:
                name = crew.find("a")
                if name:
                    directors.append(name.text.strip())
        if directors:
            director = ", ".join(directors)
            
        actors = []
        people_ols = soup.find_all("ol", class_=re.compile("people"))
        for ol in people_ols:
            cards = ol.find_all("li", class_="card")
            for card in cards:
                p_tags = card.find_all("p")
                if p_tags:
                    actor_name = p_tags[0].text.strip()
                    actor_name = " ".join(actor_name.split())
                    if actor_name and actor_name not in actors:
                        actors.append(actor_name)
        schauspieler_cast = ", ".join(actors[:10]) if actors else "k.A."
        
        fsk = "k.A."
        certification_span = soup.find("span", class_="certification")
        if certification_span:
            cert = certification_span.text.strip().lower().replace("fsk", "").replace("ab", "").strip()
            if cert in ["0", "6", "12", "16", "18"]:
                fsk = cert
                
        poster_path = ""
        poster_meta = soup.find("meta", property="og:image")
        if poster_meta:
            content = poster_meta.get("content", "")
            match = re.search(r'/t/p/[^/]+/([^/]+\.(?:jpg|png|webp|jpeg))', content)
            if match:
                poster_path = "/" + match.group(1)
                
        backdrop_path = ""
        all_paths = re.findall(r'/t/p/[^"\')]+', response.text)
        for p in all_paths:
            if "face" in p and ("138" in p or "45" in p or "66" in p):
                continue
            if "poster_path" in p or "profile_path" in p or "logo_path" in p:
                continue
            if poster_path and poster_path in p:
                continue
            match = re.search(r'/t/p/(?:w1920_and_h800_multi_faces|original|w1000_and_h450_multi_faces|w1280|w780)/([^/]+\.(?:jpg|png|webp|jpeg))', p)
            if match:
                backdrop_path = "/" + match.group(1)
                break
                
        if not backdrop_path:
            for p in all_paths:
                if "face" in p:
                    match = re.search(r'/t/p/[^/]+/([^/]+\.(?:jpg|png|webp|jpeg))', p)
                    if match:
                        backdrop_path = "/" + match.group(1)
                        break
                        
        return {
            "titel": title if title else "Unbekannt",
            "jahr": year,
            "schauspieler_cast": schauspieler_cast,
            "genre_richtung": genre_richtung,
            "laufzeit_min": runtime,
            "handlung_beschreibung": overview if overview else "Keine deutsche Beschreibung vorhanden.",
            "fsk": fsk,
            "produktionsfirma_studio": "k.A.",
            "regisseur": director,
            "filmreihe": "",
            "produktionsland": "k.A.",
            "deutsche_synchronsprecher": "",
            "poster_path": poster_path,
            "backdrop_path": backdrop_path
        }

    def fetch_movie_preview(self, tmdb_id: int) -> Dict:
        """
        Fetches metadata for previewing a movie without downloading image assets to disk.
        Returns a dictionary with raw URLs for poster and banner.
        """
        api_key = self.get_api_key()
        if not api_key:
            try:
                details = self._scrape_movie_page(tmdb_id)
                poster_url = f"{self.IMAGE_BASE_URL}/w500{details['poster_path']}" if details['poster_path'] else ""
                banner_url = f"{self.IMAGE_BASE_URL}/w1280{details['backdrop_path']}" if details['backdrop_path'] else ""
                details["poster_url"] = poster_url
                details["banner_url"] = banner_url
                details["tmdb_id"] = tmdb_id
                return details
            except Exception as e:
                raise ValueError(f"Fehler beim Scraping der TMDb Movie-Vorschau: {e}")

        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        headers, params = self._get_auth(api_key)
        params.update({
            "language": "de-DE",
            "append_to_response": "credits,release_dates"
        })
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Parse fields
        titel = data.get("title", "Unbekannt")
        release_date = data.get("release_date", "")
        jahr = int(release_date.split("-")[0]) if release_date else None
        genres_list = [g.get("name") for g in data.get("genres", []) if g.get("name")]
        genre_richtung = ", ".join(genres_list) if genres_list else "k.A."
        laufzeit = data.get("runtime", 0)
        laufzeit_min = int(laufzeit) if laufzeit else 0
        handlung_beschreibung = data.get("overview", "") or "Keine deutsche Beschreibung vorhanden."
        fsk = self._extract_fsk(data.get("release_dates", {}))
        companies = [c.get("name") for c in data.get("production_companies", []) if c.get("name")]
        produktionsfirma_studio = ", ".join(companies) if companies else "k.A."
        
        credits = data.get("credits", {})
        cast = credits.get("cast", [])
        crew = credits.get("crew", [])
        actors = [member.get("name") for member in cast[:10] if member.get("name")]
        schauspieler_cast = ", ".join(actors) if actors else "k.A."
        directors = [member.get("name") for member in crew if member.get("job") == "Director"]
        regisseur = ", ".join(directors) if directors else "k.A."
        
        collection = data.get("belongs_to_collection")
        filmreihe = collection.get("name") if collection else ""
        countries = [country.get("name") for country in data.get("production_countries", []) if country.get("name")]
        produktionsland = ", ".join(countries) if countries else "k.A."
        
        poster_path = data.get("poster_path")
        banner_path = data.get("backdrop_path")
        
        poster_url = f"{self.IMAGE_BASE_URL}/w500{poster_path}" if poster_path else ""
        banner_url = f"{self.IMAGE_BASE_URL}/w1280{banner_path}" if banner_path else ""
        
        return {
            "titel": titel,
            "jahr": jahr,
            "schauspieler_cast": schauspieler_cast,
            "genre_richtung": genre_richtung,
            "laufzeit_min": laufzeit_min,
            "handlung_beschreibung": handlung_beschreibung,
            "fsk": fsk,
            "produktionsfirma_studio": produktionsfirma_studio,
            "regisseur": regisseur,
            "filmreihe": filmreihe,
            "produktionsland": produktionsland,
            "deutsche_synchronsprecher": "",
            "poster_url": poster_url,
            "banner_url": banner_url,
            "tmdb_id": tmdb_id
        }

    def fetch_movie_details(self, tmdb_id: int) -> Dict:
        """
        Fetches full details for a movie from TMDB including credits, release dates,
        downloads assets, scrapes Synchronkartei, and returns the complete DB dictionary.
        """
        import os
        
        # Helper to get local fallback details
        def get_local_fallback():
            for m in POPULAR_MOVIES_FALLBACK:
                if m.get("tmdb_id") == int(tmdb_id):
                    return {
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
                    }
            return None

        # If not running tests, try local cache first
        if os.environ.get("CINEPALAST_TEST_MODE") != "1":
            local_data = get_local_fallback()
            if local_data:
                return local_data

        api_key = self.get_api_key()
        if not api_key:
            try:
                details = self._scrape_movie_page(tmdb_id)
                titel = details["titel"]
                jahr = details["jahr"]
                details["deutsche_synchronsprecher"] = self.scrape_synchronsprecher(titel, jahr)
                
                details["poster_pfad"] = self.download_and_cache_image(details["poster_path"], tmdb_id, "poster")
                details["banner_pfad"] = self.download_and_cache_image(details["backdrop_path"], tmdb_id, "banner")
                
                del details["poster_path"]
                del details["backdrop_path"]
                return details
            except Exception as e:
                # If scraping fails and we are offline, try local fallback as last resort
                local_data = get_local_fallback()
                if local_data:
                    return local_data
                raise ValueError(f"Fehler beim Scraping der TMDb Movie-Details: {e}")

        # If we have API key
        try:
            url = f"{self.BASE_URL}/movie/{tmdb_id}"
            headers, params = self._get_auth(api_key)
            params.update({
                "language": "de-DE",
                "append_to_response": "credits,release_dates"
            })
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            titel = data.get("title", "Unbekannt")
            release_date = data.get("release_date", "")
            jahr = int(release_date.split("-")[0]) if release_date else None
            genres_list = [g.get("name") for g in data.get("genres", []) if g.get("name")]
            genre_richtung = ", ".join(genres_list) if genres_list else "k.A."
            laufzeit = data.get("runtime", 0)
            laufzeit_min = int(laufzeit) if laufzeit else 0
            handlung_beschreibung = data.get("overview", "") or "Keine deutsche Beschreibung vorhanden."
            fsk = self._extract_fsk(data.get("release_dates", {}))
            companies = [c.get("name") for c in data.get("production_companies", []) if c.get("name")]
            produktionsfirma_studio = ", ".join(companies) if companies else "k.A."

            credits = data.get("credits", {})
            cast = credits.get("cast", [])
            crew = credits.get("crew", [])
            actors = [member.get("name") for member in cast[:10] if member.get("name")]
            schauspieler_cast = ", ".join(actors) if actors else "k.A."
            directors = [member.get("name") for member in crew if member.get("job") == "Director"]
            regisseur = ", ".join(directors) if directors else "k.A."

            collection = data.get("belongs_to_collection")
            filmreihe = collection.get("name") if collection else ""
            countries = [country.get("name") for country in data.get("production_countries", []) if country.get("name")]
            produktionsland = ", ".join(countries) if countries else "k.A."

            # Scrape Synchronkartei dynamically
            deutsche_synchronsprecher = self.scrape_synchronsprecher(titel, jahr)

            poster_path = data.get("poster_path")
            banner_path = data.get("backdrop_path")

            # Download images
            poster_pfad = self.download_and_cache_image(poster_path, tmdb_id, "poster")
            banner_pfad = self.download_and_cache_image(banner_path, tmdb_id, "banner")

            return {
                "titel": titel,
                "jahr": jahr,
                "schauspieler_cast": schauspieler_cast,
                "genre_richtung": genre_richtung,
                "laufzeit_min": laufzeit_min,
                "handlung_beschreibung": handlung_beschreibung,
                "fsk": fsk,
                "produktionsfirma_studio": produktionsfirma_studio,
                "regisseur": regisseur,
                "filmreihe": filmreihe,
                "produktionsland": produktionsland,
                "deutsche_synchronsprecher": deutsche_synchronsprecher,
                "poster_pfad": poster_pfad,
                "banner_pfad": banner_pfad
            }
        except Exception as e:
            # If API request fails and we are offline, try local fallback as last resort
            local_data = get_local_fallback()
            if local_data:
                return local_data
            raise e

    def _extract_fsk(self, release_dates_data: Dict) -> str:
        """
        Extracts FSK rating from TMDB release dates for Germany (DE).
        Returns a string representation (e.g., '0', '6', '12', '16', '18') or 'k.A.'.
        """
        results = release_dates_data.get("results", [])
        for country_data in results:
            if country_data.get("iso_3166_1") == "DE":
                for date_info in country_data.get("release_dates", []):
                    cert = date_info.get("certification", "").strip()
                    if cert:
                        clean_cert = cert.lower().replace("fsk", "").replace("ab", "").strip()
                        if clean_cert in ["0", "6", "12", "16", "18"]:
                            return clean_cert
                        return cert
        return "k.A."

    def download_and_cache_image(self, remote_path: Optional[str], tmdb_id: int, image_type: str) -> str:
        """
        Downloads a poster or banner image from TMDB, checks if it is already cached locally,
        and saves it to the custom media directory if configured, or default folders.
        """
        if not remote_path:
            return ""

        extension = os.path.splitext(remote_path)[1]
        if not extension:
            extension = ".jpg"

        # Check if there is a custom media path
        custom_path = load_config().get("custom_media_path", "").strip()
        if custom_path and os.path.isdir(custom_path):
            folder = os.path.join(custom_path, "posters" if image_type == "poster" else "banners")
            os.makedirs(folder, exist_ok=True)
            local_filename = f"{tmdb_id}{extension}"
            local_path = os.path.join(folder, local_filename)
        else:
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                folder = os.path.join(local_appdata, "CinePalast Manager", "assets", "posters" if image_type == "poster" else "banners")
            else:
                folder = os.path.join(get_app_dir(), "assets", "posters" if image_type == "poster" else "banners")
            os.makedirs(folder, exist_ok=True)
            local_filename = f"{tmdb_id}{extension}"
            local_path = os.path.join(folder, local_filename)

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        size = "w500" if image_type == "poster" else "w1280"
        download_url = f"{self.IMAGE_BASE_URL}/{size}{remote_path}"

        try:
            response = requests.get(download_url, stream=True, timeout=15)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return local_path
        except Exception as e:
            print(f"Error downloading image {download_url}: {e}")
            
        return ""


def check_for_update(current_version: str) -> Optional[str]:
    """
    Checks if a newer version of CinePalast is available on GitHub.
    Returns the remote version string if an update is available, otherwise None.
    """
    token = load_github_token()
    if not token:
        return None
        
    url = "https://api.github.com/repos/TentixTV/CinepalastManager/contents/version.json?ref=main"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            remote_version = data.get("version", "").strip()
            if remote_version and remote_version != current_version:
                return remote_version
    except Exception as e:
        print(f"Error checking for updates on GitHub: {e}")
    return None


def download_update_installer(token: str, dest_path: str, progress_callback=None):
    """
    Downloads CinePalastSetup.exe from the private repository on GitHub.
    Uses the application/vnd.github.v3.raw Accept header to stream raw bytes.
    """
    url = "https://api.github.com/repos/TentixTV/CinepalastManager/contents/CinePalastSetup.exe?ref=main"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers, stream=True, timeout=60)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback(downloaded, total_size)


