import os
import shutil
import sqlite3
import webview
import time
import sys
from typing import Optional, Dict, List
import database
import api

class CinePalastAPI:
    def __init__(self):
        self.tmdb_client = api.TMDBClient()
        self._window = None

    def set_window(self, window):
        self._window = window

    def get_app_dir(self):
        """Returns absolute path to the application directory."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def get_all_movies(self) -> List[Dict]:
        try:
            return database.get_all_movies()
        except Exception as e:
            print("Error get_all_movies:", e)
            return []

    def search_movies(self, query: str, search_filter: str = "Alles") -> List[Dict]:
        try:
            return database.search_movies_realtime(query, search_filter)
        except Exception as e:
            print("Error search_movies:", e)
            return []

    def search_online(self, query: str, search_filter: str = "Alles") -> List[Dict]:
        try:
            return self.tmdb_client.search_movies(query, search_filter)
        except Exception as e:
            print("Error search_online:", e)
            return []

    def get_movie_details(self, tmdb_id: int) -> Dict:
        try:
            return self.tmdb_client.fetch_movie_preview(tmdb_id)
        except Exception as e:
            print("Error get_movie_details:", e)
            return {}

    def add_movie(self, movie_data: Dict) -> Dict:
        try:
            # Download images if they are TMDB paths
            poster_path = movie_data.get("Poster_Pfad", "")
            banner_path = movie_data.get("Banner_Pfad", "")
            tmdb_id = movie_data.get("tmdb_id")
            movie_title = movie_data.get("Name", "")
            movie_year = movie_data.get("Jahr")
            
            if poster_path and poster_path.startswith("/"):
                poster_path = self.tmdb_client.download_and_cache_image(poster_path, tmdb_id, "poster", movie_title, movie_year)
            if banner_path and banner_path.startswith("/"):
                banner_path = self.tmdb_client.download_and_cache_image(banner_path, tmdb_id, "banner", movie_title, movie_year)
                
            movie_data["Poster_Pfad"] = poster_path
            movie_data["Banner_Pfad"] = banner_path
            
            movie_id = database.add_movie(movie_data)
            return {"success": True, "movie_id": movie_id}
        except Exception as e:
            return {"error": str(e)}

    def update_movie(self, movie_id: int, movie_data: Dict) -> Dict:
        try:
            database.update_movie_by_id(movie_id, movie_data)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def delete_movie(self, movie_id: int) -> Dict:
        try:
            database.delete_movie_by_id(movie_id)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def load_config(self) -> Dict:
        return api.load_config()

    def save_config(self, new_config: Dict) -> Dict:
        try:
            api.save_config(new_config)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def select_folder(self) -> Optional[str]:
        if not self._window:
            return None
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

    def select_image_file(self) -> Optional[str]:
        if not self._window:
            return None
        file_types = ('Bilder (*.jpg;*.jpeg;*.png;*.webp;*.gif)', 'All files (*.*)')
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            return result[0]
        return None

    def copy_image_to_media(self, file_path: str, img_type: str, movie_title: str = "", movie_year: Optional[int] = None) -> Dict:
        try:
            import re
            safe_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', movie_title or "Unbekannt")
            safe_title = " ".join(safe_title.split())
            year_str = f" ({movie_year})" if movie_year else ""
            suffix = "_PT" if img_type == "poster" else "_WP"
            local_filename = f"{safe_title}{year_str}{suffix}.png"
            
            config = api.load_config()
            custom_path = config.get("custom_media_path", "").strip()
            if custom_path and os.path.isdir(custom_path):
                folder = custom_path
                dest_path = os.path.join(folder, local_filename)
                db_path = dest_path
            else:
                local_appdata = os.environ.get("LOCALAPPDATA")
                if local_appdata:
                    folder = os.path.join(local_appdata, "CinePalast Manager", "assets", "posters" if img_type == "poster" else "banners")
                else:
                    folder = os.path.join(self.get_app_dir(), "assets", "posters" if img_type == "poster" else "banners")
                dest_path = os.path.join(folder, local_filename)
                db_path = f"assets/{'posters' if img_type == 'poster' else 'banners'}/{local_filename}"
                
            os.makedirs(folder, exist_ok=True)
            
            from PIL import Image
            img = Image.open(file_path)
            if img.mode == "CMYK":
                img = img.convert("RGB")
            img.save(dest_path, format="PNG")
            
            return {"success": True, "path": db_path}
        except Exception as e:
            return {"error": str(e)}

    def copy_existing_media_files(self, new_path: str) -> Dict:
        try:
            config = api.load_config()
            old_path = config.get("custom_media_path", "").strip()
            
            src_dirs = []
            if old_path and os.path.isdir(old_path):
                src_dirs.append((old_path, ""))
                src_dirs.append((os.path.join(old_path, "posters"), ""))
                src_dirs.append((os.path.join(old_path, "banners"), ""))
            
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                src_dirs.append((os.path.join(local_appdata, "CinePalast Manager", "assets", "posters"), ""))
                src_dirs.append((os.path.join(local_appdata, "CinePalast Manager", "assets", "banners"), ""))
                
            src_dirs.append((os.path.join(self.get_app_dir(), "assets", "posters"), ""))
            src_dirs.append((os.path.join(self.get_app_dir(), "assets", "banners"), ""))
            
            copied = 0
            for src_dir, _ in src_dirs:
                if os.path.isdir(src_dir):
                    os.makedirs(new_path, exist_ok=True)
                    for item in os.listdir(src_dir):
                        src_file = os.path.join(src_dir, item)
                        if os.path.isfile(src_file):
                            dest_file = os.path.join(new_path, item)
                            if os.path.abspath(src_file) != os.path.abspath(dest_file):
                                if not os.path.exists(dest_file):
                                    shutil.copy2(src_file, dest_file)
                                    copied += 1
                                
            return {"success": True, "copied": copied}
        except Exception as e:
            return {"error": str(e)}

    def backup_database(self) -> Dict:
        try:
            if not self._window:
                return {"error": "No window"}
            dest_file = self._window.create_file_dialog(webview.SAVE_DIALOG, save_filename="cinepalast_backup.db")
            if dest_file:
                shutil.copy2(database.DB_FILE, dest_file)
                return {"success": True, "path": dest_file}
            return {"cancelled": True}
        except Exception as e:
            return {"error": str(e)}

    def restore_database(self) -> Dict:
        try:
            if not self._window:
                return {"error": "No window"}
            file_types = ('SQLite Datenbank (*.db)', 'All files (*.*)')
            src_files = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
            if src_files and len(src_files) > 0:
                src_file = src_files[0]
                shutil.copy2(src_file, database.DB_FILE)
                return {"success": True}
            return {"cancelled": True}
        except Exception as e:
            return {"error": str(e)}

    def reset_database(self) -> Dict:
        try:
            conn = sqlite3.connect(database.DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM media;")
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def get_popular_movies(self) -> List[Dict]:
        try:
            return self.tmdb_client.get_popular_movies()
        except Exception as e:
            print("Error get_popular_movies in api:", e)
            return []

    def download_image_to_desktop(self, movie_title: str, file_path: str, img_type: str, movie_year: Optional[int] = None) -> Dict:
        try:
            if not file_path:
                return {"error": "Kein Bild vorhanden."}
                
            # If it's a relative path, resolve it absolutely
            abs_path = file_path
            if not os.path.isabs(file_path):
                config = api.load_config()
                custom_path = config.get("custom_media_path", "").strip()
                filename = os.path.basename(file_path)
                sub = "posters" if img_type == "poster" else "banners"
                
                resolved = False
                if custom_path and os.path.isdir(custom_path):
                    test_path = os.path.join(custom_path, filename)
                    if os.path.exists(test_path):
                        abs_path = test_path
                        resolved = True
                    else:
                        test_path2 = os.path.join(custom_path, sub, filename)
                        if os.path.exists(test_path2):
                            abs_path = test_path2
                            resolved = True
                
                if not resolved:
                    local_appdata = os.environ.get("LOCALAPPDATA")
                    if local_appdata:
                        test_path = os.path.join(local_appdata, "CinePalast Manager", "assets", sub, filename)
                        if os.path.exists(test_path):
                            abs_path = test_path
                            resolved = True
                            
                if not resolved:
                    abs_path = os.path.join(self.get_app_dir(), "assets", sub, filename)
            else:
                if not os.path.exists(abs_path):
                    filename = os.path.basename(file_path)
                    config = api.load_config()
                    custom_path = config.get("custom_media_path", "").strip()
                    if custom_path and os.path.isdir(custom_path):
                        test_path = os.path.join(custom_path, filename)
                        if os.path.exists(test_path):
                            abs_path = test_path
            
            if not os.path.exists(abs_path):
                return {"error": f"Die Bilddatei wurde lokal nicht gefunden: {abs_path}"}
                
            import re
            safe_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', movie_title or "Unbekannt")
            safe_title = " ".join(safe_title.split())
            year_str = f" ({movie_year})" if movie_year else ""
            suffix = "_PT" if img_type == "poster" else "_WP"
            dest_filename = f"{safe_title}{year_str}{suffix}.png"
            
            # Check if there is a custom media path
            config = api.load_config()
            custom_path = config.get("custom_media_path", "").strip()
            
            is_custom = False
            if custom_path and os.path.isdir(custom_path):
                dest_dir = custom_path
                is_custom = True
            else:
                # Desktop dir
                dest_dir = os.path.join(os.environ["USERPROFILE"], "Desktop") if "USERPROFILE" in os.environ else os.path.expanduser("~/Desktop")
                
            dest_path = os.path.join(dest_dir, dest_filename)
            
            from PIL import Image
            img = Image.open(abs_path)
            if img.mode == "CMYK":
                img = img.convert("RGB")
            img.save(dest_path, format="PNG")
            
            return {"success": True, "filename": dest_filename, "is_custom_path": is_custom, "custom_path": dest_dir}
        except Exception as e:
            return {"error": str(e)}
