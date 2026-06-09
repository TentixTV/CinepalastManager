import os
import sys
import socket
import threading
import webview
import server
import backend_api
import database
import api

def get_free_port():
    """Returns a free local port number."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def migrate_old_v2_assets():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return
        
    old_app_dir = os.path.join(local_appdata, "CinePalast Manager", "app")
    new_app_dir = os.path.join(local_appdata, "CinePalast Manager")
    
    if os.path.exists(old_app_dir) and os.path.isdir(old_app_dir):
        import shutil
        # Migrate posters and banners
        for sub in ["posters", "banners"]:
            old_sub = os.path.join(old_app_dir, "assets", sub)
            new_sub = os.path.join(new_app_dir, "assets", sub)
            if os.path.exists(old_sub) and os.path.isdir(old_sub):
                os.makedirs(new_sub, exist_ok=True)
                for item in os.listdir(old_sub):
                    src = os.path.join(old_sub, item)
                    dest = os.path.join(new_sub, item)
                    if os.path.isfile(src) and not os.path.exists(dest):
                        try:
                            shutil.copy2(src, dest)
                        except Exception as e:
                            print(f"Error migrating asset {item}: {e}")
        # Clean up old app dir
        try:
            shutil.rmtree(old_app_dir)
        except Exception:
            pass

def main():
    # 1. Migrate old V2 assets if upgrade occurred
    migrate_old_v2_assets()
    
    # 2. Initialize SQLite Database
    database.initialize_db()
    
    # 3. Ensure FSK logo assets are downloaded
    import main as main_module
    main_module.ensure_fsk_icons()
    
    # 2. Find a free port and start the local Bottle server
    port = get_free_port()
    
    # Run the bottle server in a daemon thread so it terminates when the main window closes
    server_thread = threading.Thread(
        target=server.run_server, 
        args=(port,), 
        daemon=True
    )
    server_thread.start()
    
    # 3. Create the Python-to-JS API Bridge
    app_api = backend_api.CinePalastAPI()
    
    # 4. Load config to determine window settings or initial theme
    config = api.load_config()
    theme = config.get("theme", "cyan")
    
    # Map theme to title bar colors or accent color if supported by pywebview
    accent_color = "#00F0FF"
    if theme == "red":
        accent_color = "#EF4444"
    elif theme == "blue":
        accent_color = "#3B82F6"
    elif theme == "purple":
        accent_color = "#A855F7"
    elif theme == "black":
        accent_color = "#FFFFFF"

    # 5. Create webview window
    # Window width & height matches the Tkinter UI layout
    window = webview.create_window(
        title="CinePalast Manager — Mannis Kinopalast",
        url=f"http://127.0.0.1:{port}",
        js_api=app_api,
        width=1280,
        height=720,
        min_size=(900, 600),
        background_color="#09090e"
    )
    
    # Set the window instance in the API bridge so it can call file dialogs
    app_api.set_window(window)
    
    # 6. Start the native webview window loop
    # On Windows, pywebview automatically loads WebView2 (Edge Chromium-based)
    debug_mode = "--debug" in sys.argv
    webview.start(debug=debug_mode)

if __name__ == '__main__':
    # Make sure execution directory is correct
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    main()
