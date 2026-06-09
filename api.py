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
                raise ValueError(f"Fehler beim Scraping der TMDb Movie-Details: {e}")

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


