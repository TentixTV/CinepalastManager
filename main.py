import sys
from database import DatabaseManager
from api import TMDBClient
from ui import CinePalastApp

def main():
    """
    Main application entry point.
    Initializes local SQLite database, sets up TMDB client, and runs the CustomTkinter app.
    """
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
