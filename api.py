import os
import json
import requests
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

CONFIG_FILE = "config.json"

def load_api_key() -> str:
    """Loads the TMDB API key from config.json. Returns empty string if not set."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key", "").strip()
        except Exception:
            pass
    return ""

def save_api_key(api_key: str):
    """Saves the TMDB API key to config.json."""
    data = {"api_key": api_key.strip()}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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

    def has_valid_key(self) -> bool:
        key = self.get_api_key()
        if not key:
            return False
        # Test the key briefly with a lightweight request
        try:
            url = f"{self.BASE_URL}/configuration"
            response = requests.get(url, params={"api_key": key}, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def search_movies(self, query: str) -> List[Dict]:
        """
        Searches TMDB for movies by title query.
        Returns a list of search results.
        """
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError("Kein TMDB API-Schlüssel konfiguriert.")

        url = f"{self.BASE_URL}/search/movie"
        params = {
            "api_key": api_key,
            "query": query,
            "language": "de-DE",
            "page": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
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

    def fetch_movie_preview(self, tmdb_id: int) -> Dict:
        """
        Fetches metadata for previewing a movie without downloading image assets to disk.
        Returns a dictionary with raw URLs for poster and banner.
        """
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError("Kein TMDB API-Schlüssel konfiguriert.")

        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        params = {
            "api_key": api_key,
            "language": "de-DE",
            "append_to_response": "credits,release_dates"
        }
        
        response = requests.get(url, params=params, timeout=10)
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
            raise ValueError("Kein TMDB API-Schlüssel konfiguriert.")

        url = f"{self.BASE_URL}/movie/{tmdb_id}"
        params = {
            "api_key": api_key,
            "language": "de-DE",
            "append_to_response": "credits,release_dates"
        }
        
        response = requests.get(url, params=params, timeout=10)
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
        and saves it to assets/posters or assets/banners.
        """
        if not remote_path:
            return ""

        extension = os.path.splitext(remote_path)[1]
        if not extension:
            extension = ".jpg"

        folder = "assets/posters" if image_type == "poster" else "assets/banners"
        local_filename = f"{tmdb_id}{extension}"
        local_relative_path = f"{folder}/{local_filename}"

        if os.path.exists(local_relative_path) and os.path.getsize(local_relative_path) > 0:
            return local_relative_path

        size = "w500" if image_type == "poster" else "w1280"
        download_url = f"{self.IMAGE_BASE_URL}/{size}{remote_path}"

        try:
            os.makedirs(folder, exist_ok=True)
            response = requests.get(download_url, stream=True, timeout=15)
            if response.status_code == 200:
                with open(local_relative_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return local_relative_path
        except Exception as e:
            print(f"Error downloading image {download_url}: {e}")
            
        return ""

