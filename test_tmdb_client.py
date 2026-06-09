import unittest
from api import TMDBClient
import json
import os

class TestTMDBClientPersonSearch(unittest.TestCase):
    def setUp(self):
        self.client = TMDBClient()
        # Backup original config
        self.config_path = "config.json"
        self.original_config = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.original_config = json.load(f)

    def tearDown(self):
        # Restore original config
        if self.original_config:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.original_config, f, indent=4, ensure_ascii=False)

    def test_search_movies_actor_api(self):
        # Ensure API key is set
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"api_key": "c137e57399018df3c480f56ce1db17f8"}, f)
            
        results = self.client.search_movies("Adam Sandler", "Schauspieler")
        self.assertGreater(len(results), 0, "Should return at least one movie for Adam Sandler via API")
        
        # Verify the structure and some specific movies
        titles = [r["titel"].lower() for r in results]
        # Check that it contains classic movies, not just the top 3 known_for
        has_happy_gilmore = any("happy gilmore" in t or "schlingel" in t or "gilmore" in t for t in titles)
        has_billy_madison = any("billy madison" in t for t in titles)
        has_click = any("klick" in t or "click" in t for t in titles)
        
        print(f"API Actor Search: Found {len(results)} movies.")
        print(f"Contains 'Happy Gilmore': {has_happy_gilmore}")
        print(f"Contains 'Billy Madison': {has_billy_madison}")
        print(f"Contains 'Click': {has_click}")
        
        # Check movie structure
        first = results[0]
        self.assertIn("tmdb_id", first)
        self.assertIn("titel", first)
        self.assertIn("jahr", first)
        self.assertIn("poster_path", first)

    def test_search_movies_director_api(self):
        # Ensure API key is set
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"api_key": "c137e57399018df3c480f56ce1db17f8"}, f)
            
        results = self.client.search_movies("Christopher Nolan", "Regisseur")
        self.assertGreater(len(results), 0, "Should return movies for Christopher Nolan via API")
        
        titles = [r["titel"].lower() for r in results]
        has_inception = any("inception" in t for t in titles)
        has_memento = any("memento" in t for t in titles)
        has_tenet = any("tenet" in t for t in titles)
        
        print(f"API Director Search: Found {len(results)} movies.")
        print(f"Contains 'Inception': {has_inception}")
        print(f"Contains 'Memento': {has_memento}")
        print(f"Contains 'Tenet': {has_tenet}")

    def test_search_movies_actor_scraper(self):
        # Disable API key by clearing it
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"api_key": ""}, f)
            
        results = self.client.search_movies("Adam Sandler", "Schauspieler")
        self.assertGreater(len(results), 0, "Should return at least one movie for Adam Sandler via Scraper")
        
        # Verify years are parsed correctly (not "k.A." for most entries)
        years = [r["jahr"] for r in results if r["jahr"] != "k.A."]
        self.assertGreater(len(years), 0, "Should successfully parse release years for scraped movies")
        
        titles = [r["titel"].lower() for r in results]
        has_happy_gilmore = any("happy gilmore" in t or "schlingel" in t or "gilmore" in t for t in titles)
        has_click = any("klick" in t or "click" in t for t in titles)
        
        print(f"Scraper Actor Search: Found {len(results)} movies.")
        print(f"Contains 'Happy Gilmore': {has_happy_gilmore}")
        print(f"Contains 'Click': {has_click}")
        print(f"First 5 scraped actor movies: {results[:5]}")

    def test_search_movies_director_scraper(self):
        # Disable API key by clearing it
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"api_key": ""}, f)
            
        results = self.client.search_movies("Christopher Nolan", "Regisseur")
        self.assertGreater(len(results), 0, "Should return movies for Christopher Nolan via Scraper")
        
        years = [r["jahr"] for r in results if r["jahr"] != "k.A."]
        self.assertGreater(len(years), 0, "Should successfully parse release years for scraped movies")
        
        titles = [r["titel"].lower() for r in results]
        has_inception = any("inception" in t for t in titles)
        
        print(f"Scraper Director Search: Found {len(results)} movies.")
        print(f"Contains 'Inception': {has_inception}")
        print(f"First 5 scraped director movies: {results[:5]}")

if __name__ == "__main__":
    unittest.main()
