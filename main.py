import sys
import os
import shutil
from PIL import Image

# Setup local user AppData directory for read/write data storage (prevents protected Program Files write errors)
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CinePalast Manager")
os.makedirs(os.path.join(DATA_DIR, "assets"), exist_ok=True)

# Copy DTB.png and FSK assets from read-only installation directory to AppData
src_assets = os.path.join(app_dir, "assets")
if os.path.exists(src_assets):
    for root, dirs, files in os.walk(src_assets):
        rel_path = os.path.relpath(root, app_dir)
        dest_root = os.path.join(DATA_DIR, rel_path)
        os.makedirs(dest_root, exist_ok=True)
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_root, file)
            if not os.path.exists(dest_file):
                try:
                    shutil.copy2(src_file, dest_file)
                except Exception as e:
                    print(f"Failed to copy asset {file}: {e}")

# Copy cinepalast.db from install directory to AppData if not exists in AppData
src_db = os.path.join(app_dir, "cinepalast.db")
dest_db = os.path.join(DATA_DIR, "cinepalast.db")
if os.path.exists(src_db) and not os.path.exists(dest_db):
    try:
        shutil.copy2(src_db, dest_db)
    except Exception as e:
        print(f"Failed to copy database {src_db}: {e}")

# Change current working directory to AppData, so all relative operations target AppData
os.chdir(DATA_DIR)

from database import DatabaseManager
from api import TMDBClient

def ensure_ico_exists():
    """Converts assets/DTB.png to icon.ico if it doesn't exist yet."""
    icon_ico = "icon.ico"
    png_source = "assets/DTB.png"
    if not os.path.exists(icon_ico) and os.path.exists(png_source):
        try:
            img = Image.open(png_source)
            icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(icon_ico, format="ICO", sizes=icon_sizes)
        except Exception as e:
            print(f"Fehler bei Konvertierung von assets/DTB.png zu icon.ico: {e}")

def ensure_fsk_icons():
    """Downloads official German FSK logos from Wikimedia if they do not exist locally."""
    fsk_urls = {
        "0": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/FSK_0.svg/500px-FSK_0.svg.png",
        "6": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/FSK_6.svg/500px-FSK_6.svg.png",
        "12": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/FSK_12.svg/500px-FSK_12.svg.png",
        "16": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/FSK_16.svg/500px-FSK_16.svg.png",
        "18": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/FSK_18.svg/500px-FSK_18.svg.png"
    }
    fsk_folder = "assets/fsk"
    os.makedirs(fsk_folder, exist_ok=True)
    
    def download_thread():
        import requests
        headers = {
            "User-Agent": "CinePalastManager/2.0 (contact@tentix.com)"
        }
        for fsk, url in fsk_urls.items():
            dest = os.path.join(fsk_folder, f"fsk{fsk}.png")
            if not os.path.exists(dest):
                try:
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        with open(dest, "wb") as f:
                            f.write(r.content)
                except Exception as e:
                    print(f"Failed to download FSK {fsk} logo: {e}")
                    
    import threading
    threading.Thread(target=download_thread, daemon=True).start()

def main():
    """
    Main application entry point.
    Initializes local SQLite database, sets up TMDB client, and runs the CustomTkinter app.
    """
    import sys
    if "--web" in sys.argv or os.environ.get("CINEPALAST_WEB") == "1":
        port = 8080
        if "--port" in sys.argv:
            try:
                idx = sys.argv.index("--port")
                port = int(sys.argv[idx + 1])
            except Exception:
                pass
        elif "CINEPALAST_PORT" in os.environ:
            try:
                port = int(os.environ["CINEPALAST_PORT"])
            except Exception:
                pass
                
        import database
        import api
        import server
        
        database.initialize_db()
        api.load_config()
        
        server.run_server(port)
        sys.exit(0)

    ensure_ico_exists()
    ensure_fsk_icons()
    try:
        # Initialize Database Manager (creates db and asset folders if needed)
        db_manager = DatabaseManager(db_path="cinepalast.db")
        
        # Initialize TMDB API Client
        tmdb_client = TMDBClient()
        
        # Create and run the CustomTkinter App
        from ui import CinePalastApp
        app = CinePalastApp(db_manager=db_manager, tmdb_client=tmdb_client)
        app.mainloop()
        
    except Exception as e:
        import traceback
        error_msg = f"Ein kritischer Fehler ist beim Start der App aufgetreten:\n\n{str(e)}\n\n"
        print(error_msg, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # If possible, show a Tkinter popup error dialog before crash
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Kritischer Fehler", error_msg + "Bitte prüfen Sie das Terminal für weitere Details.")
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
