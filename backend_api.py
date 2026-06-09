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
            return self.tmdb_client.fetch_movie_details(tmdb_id)
        except Exception as e:
            print("Error get_movie_details:", e)
            return {}

    def add_movie(self, movie_data: Dict) -> Dict:
        try:
            # Download images if they are TMDB paths
            poster_path = movie_data.get("Poster_Pfad", "")
            banner_path = movie_data.get("Banner_Pfad", "")
            tmdb_id = movie_data.get("tmdb_id")
            
            if poster_path and poster_path.startswith("/"):
                poster_path = self.tmdb_client.download_and_cache_image(poster_path, tmdb_id, "poster")
            if banner_path and banner_path.startswith("/"):
                banner_path = self.tmdb_client.download_and_cache_image(banner_path, tmdb_id, "banner")
                
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

    def copy_image_to_media(self, file_path: str, img_type: str) -> Dict:
        try:
            filename = os.path.basename(file_path)
            unique_name = f"{int(time.time())}_{filename}"
            
            config = api.load_config()
            custom_path = config.get("custom_media_path", "").strip()
            if custom_path and os.path.isdir(custom_path):
                folder = os.path.join(custom_path, "posters" if img_type == "poster" else "banners")
            else:
                local_appdata = os.environ.get("LOCALAPPDATA")
                if local_appdata:
                    folder = os.path.join(local_appdata, "CinePalast Manager", "assets", "posters" if img_type == "poster" else "banners")
                else:
                    folder = os.path.join(self.get_app_dir(), "assets", "posters" if img_type == "poster" else "banners")
                
            os.makedirs(folder, exist_ok=True)
            dest_path = os.path.join(folder, unique_name)
            shutil.copy2(file_path, dest_path)
            
            db_path = f"assets/{'posters' if img_type == 'poster' else 'banners'}/{unique_name}"
            return {"success": True, "path": db_path}
        except Exception as e:
            return {"error": str(e)}

    def copy_existing_media_files(self, new_path: str) -> Dict:
        try:
            config = api.load_config()
            old_path = config.get("custom_media_path", "").strip()
            
            src_dirs = []
            if old_path and os.path.isdir(old_path):
                src_dirs.append((os.path.join(old_path, "posters"), "posters"))
                src_dirs.append((os.path.join(old_path, "banners"), "banners"))
            
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                src_dirs.append((os.path.join(local_appdata, "CinePalast Manager", "assets", "posters"), "posters"))
                src_dirs.append((os.path.join(local_appdata, "CinePalast Manager", "assets", "banners"), "banners"))
                
            src_dirs.append((os.path.join(self.get_app_dir(), "assets", "posters"), "posters"))
            src_dirs.append((os.path.join(self.get_app_dir(), "assets", "banners"), "banners"))
            
            copied = 0
            for src_dir, sub in src_dirs:
                if os.path.isdir(src_dir):
                    dest_dir = os.path.join(new_path, sub)
                    os.makedirs(dest_dir, exist_ok=True)
                    for item in os.listdir(src_dir):
                        src_file = os.path.join(src_dir, item)
                        if os.path.isfile(src_file):
                            dest_file = os.path.join(dest_dir, item)
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

    def download_image_to_desktop(self, movie_title: str, file_path: str, img_type: str) -> Dict:
        try:
            if not file_path:
                return {"error": "Kein Bild vorhanden."}
                
            # If it's a relative path starting with assets/, resolve it absolutely
            abs_path = file_path
            if not os.path.isabs(file_path):
                # Check custom path first
                config = api.load_config()
                custom_path = config.get("custom_media_path", "").strip()
                filename = os.path.basename(file_path)
                
                # Determine folder name
                sub = "posters" if img_type == "poster" else "banners"
                
                resolved = False
                if custom_path and os.path.isdir(custom_path):
                    test_path = os.path.join(custom_path, sub, filename)
                    if os.path.exists(test_path):
                        abs_path = test_path
                        resolved = True
                
                if not resolved:
                    # Check AppData path
                    local_appdata = os.environ.get("LOCALAPPDATA")
                    if local_appdata:
                        test_path = os.path.join(local_appdata, "CinePalast Manager", "assets", sub, filename)
                        if os.path.exists(test_path):
                            abs_path = test_path
                            resolved = True
                            
                if not resolved:
                    # Fallback to installation folder
                    abs_path = os.path.join(self.get_app_dir(), "assets", sub, filename)
            
            if not os.path.exists(abs_path):
                return {"error": f"Die Bilddatei wurde lokal nicht gefunden: {abs_path}"}
                
            import re
            # Clean title
            clean_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', movie_title)
            clean_title = clean_title.replace(" ", "_")
            
            # Desktop dir
            desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop") if "USERPROFILE" in os.environ else os.path.expanduser("~/Desktop")
            
            ext = os.path.splitext(abs_path)[1]
            if not ext:
                ext = ".jpg"
                
            dest_filename = f"{clean_title}_{img_type}{ext}"
            dest_path = os.path.join(desktop_dir, dest_filename)
            
            shutil.copy2(abs_path, dest_path)
            return {"success": True, "filename": dest_filename}
        except Exception as e:
            return {"error": str(e)}
