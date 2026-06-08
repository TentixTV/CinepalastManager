import sys
import os
from PIL import Image
from database import DatabaseManager
from api import TMDBClient
from ui import CinePalastApp

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

def main():
    """
    Main application entry point.
    Initializes local SQLite database, sets up TMDB client, and runs the CustomTkinter app.
    """
    ensure_ico_exists()
    try:
        # Initialize Database Manager (creates db and asset folders if needed)
        db_manager = DatabaseManager(db_path="cinepalast.db")
        
        # Initialize TMDB API Client
        tmdb_client = TMDBClient()
        
        # Create and run the CustomTkinter App
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
