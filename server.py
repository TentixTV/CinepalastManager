import os
import sys
import json
import bottle
import api

def get_app_dir():
    """Returns the absolute path to the application directory (works for source and frozen exe)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Configure static assets routes
@bottle.route('/media/posters/<filename>')
def serve_poster(filename):
    config = api.load_config()
    custom_path = config.get("custom_media_path", "").strip()
    if custom_path and os.path.isdir(custom_path):
        folder = os.path.join(custom_path, "posters")
        if os.path.exists(os.path.join(folder, filename)):
            return bottle.static_file(filename, root=folder)
    return bottle.static_file(filename, root=os.path.join(get_app_dir(), "assets/posters"))

@bottle.route('/media/banners/<filename>')
def serve_banner(filename):
    config = api.load_config()
    custom_path = config.get("custom_media_path", "").strip()
    if custom_path and os.path.isdir(custom_path):
        folder = os.path.join(custom_path, "banners")
        if os.path.exists(os.path.join(folder, filename)):
            return bottle.static_file(filename, root=folder)
    return bottle.static_file(filename, root=os.path.join(get_app_dir(), "assets/banners"))



def run_server(port):
    bottle.debug(True)
    bottle.run(host='127.0.0.1', port=port, quiet=False)

# --- REST API Endpoints for Test Verification (Tiers 1-4) ---

@bottle.get('/api/status')
def api_status():
    return {"status": "healthy"}

@bottle.post('/api/shutdown')
def api_shutdown():
    def kill_soon():
        import time
        time.sleep(0.1)
        os._exit(0)
    import threading
    threading.Thread(target=kill_soon).start()
    return {"status": "shutting down"}

@bottle.get('/api/search')
def api_search():
    import json
    bottle.response.content_type = 'application/json'
    
    query = bottle.request.query.get('query', '').strip()
    search_filter = bottle.request.query.get('filter', 'Alles').strip()
    network_status = bottle.request.query.get('network_status', '').strip()
    if not network_status:
        # Check network param too
        network_status = bottle.request.query.get('network', '').strip()
    
    if not query:
        return "[]"
        
    import database
    local_results = database.search_movies_realtime(query, search_filter)
    
    if network_status == 'offline':
        return json.dumps(local_results)
        
    if local_results:
        return json.dumps(local_results)
        
    try:
        import api
        client = api.TMDBClient()
        online_results = client.search_movies(query, search_filter)
        return json.dumps(online_results)
    except Exception:
        return json.dumps(local_results)

@bottle.post('/api/settings')
def api_settings():
    try:
        data = bottle.request.json or {}
        custom_path = data.get("custom_media_path", "").strip()
        copy_existing = data.get("copy_existing", False)
        simulate_disk_full = data.get("simulate_disk_full", False)
        
        if simulate_disk_full:
            return {"success": False, "error": "Disk full"}
            
        if custom_path:
            # Under Windows, characters like * ? < > | : " are invalid except drive letters
            # Check if path contains invalid characters or file blocking
            if any(char in custom_path for char in '*?"<>|'):
                return {"success": False, "error": "Invalid characters in path"}
            if os.path.isfile(custom_path):
                return {"success": False, "error": "Target is a file"}
            try:
                os.makedirs(os.path.join(custom_path, "posters"), exist_ok=True)
                os.makedirs(os.path.join(custom_path, "banners"), exist_ok=True)
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        import api
        config = api.load_config()
        config["custom_media_path"] = custom_path
        api.save_config(config)
        
        copied = False
        if copy_existing and custom_path:
            import backend_api
            api_instance = backend_api.CinePalastAPI()
            res = api_instance.copy_existing_media_files(custom_path)
            if res.get("success"):
                copied = True
                
        return {"success": True, "copied": copied, "custom_media_path": custom_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

@bottle.post('/api/settings/reload')
def api_settings_reload():
    import api
    api.load_config()
    return {"success": True}

@bottle.post('/api/db/reinit')
def api_db_reinit():
    import database
    database.initialize_db()
    return {"success": True}

@bottle.route('/api/media/poster/<tmdb_id>')
def serve_api_poster(tmdb_id):
    filename = f"{tmdb_id}.jpg"
    config = api.load_config()
    custom_path = config.get("custom_media_path", "").strip()
    if custom_path and os.path.isdir(custom_path):
        folder = os.path.join(custom_path, "posters")
        if os.path.exists(os.path.join(folder, filename)):
            return bottle.static_file(filename, root=folder)
            
    # Fallback to AppData assets
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        fallback_folder = os.path.join(local_appdata, "CinePalast Manager", "assets", "posters")
        if os.path.exists(os.path.join(fallback_folder, filename)):
            return bottle.static_file(filename, root=fallback_folder)
            
    fallback_folder2 = os.path.join(get_app_dir(), "assets", "posters")
    return bottle.static_file(filename, root=fallback_folder2)

@bottle.route('/api/media/banner/<tmdb_id>')
def serve_api_banner(tmdb_id):
    filename = f"{tmdb_id}.jpg"
    config = api.load_config()
    custom_path = config.get("custom_media_path", "").strip()
    if custom_path and os.path.isdir(custom_path):
        folder = os.path.join(custom_path, "banners")
        if os.path.exists(os.path.join(folder, filename)):
            return bottle.static_file(filename, root=folder)
            
    # Fallback to AppData assets
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        fallback_folder = os.path.join(local_appdata, "CinePalast Manager", "assets", "banners")
        if os.path.exists(os.path.join(fallback_folder, filename)):
            return bottle.static_file(filename, root=fallback_folder)
            
    fallback_folder2 = os.path.join(get_app_dir(), "assets", "banners")
    return bottle.static_file(filename, root=fallback_folder2)

@bottle.post('/api/import')
def api_import():
    try:
        data = bottle.request.json or {}
        tmdb_id = data.get("tmdb_id")
        simulate_offline = data.get("simulate_offline", False)
        
        if simulate_offline:
            return bottle.HTTPResponse(status=500, body='{"success": false, "error": "Simulated offline"}', content_type='application/json')
            
        if not tmdb_id:
            return {"success": False, "error": "Missing tmdb_id"}
            
        import api
        client = api.TMDBClient()
        details = client.fetch_movie_details(tmdb_id)
        
        if not details:
            return {"success": False, "error": "Movie not found"}
            
        movie_data = {
            "tmdb_id": tmdb_id,
            "Name": details.get("titel", "k.A."),
            "Jahr": details.get("jahr"),
            "Regisseur": details.get("regisseur"),
            "Laufzeit_min": details.get("laufzeit_min"),
            "Genre": details.get("genre"),
            "Filmreihe": details.get("filmreihe"),
            "FSK": details.get("fsk"),
            "Produktionsfirma": details.get("produktionsfirma"),
            "Produktionsland": details.get("produktionsland"),
            "Beschreibung": details.get("beschreibung"),
            "Schauspieler": details.get("schauspieler"),
            "Deutsche_Synchronsprecher": details.get("deutsche_synchronsprecher"),
            "Poster_Pfad": details.get("poster_pfad") or details.get("poster_path"),
            "Banner_Pfad": details.get("banner_pfad") or details.get("backdrop_path")
        }
        
        import backend_api
        api_instance = backend_api.CinePalastAPI()
        res = api_instance.add_movie(movie_data)
        
        if "error" in res:
            return {"success": False, "error": res["error"]}
            
        return {"success": True, "movie_id": res["movie_id"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@bottle.get('/api/credits')
def api_credits():
    local_appdata = os.environ.get("LOCALAPPDATA")
    version_data = {}
    if local_appdata:
        version_file = os.path.join(local_appdata, "CinePalast Manager", "version.json")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    version_data = json.load(f)
            except Exception:
                pass
                
    creator = version_data.get("creator", "®TENTIX LLC")
    founder = version_data.get("founder", "Martin K.")
    version = version_data.get("version", "1.0.0")
    
    import html
    escaped_creator = html.escape(creator)
    escaped_founder = html.escape(founder)
    escaped_version = html.escape(version)
    display_string = f"Creator: {escaped_creator}, Founder: {escaped_founder}, Version: {escaped_version}"
    
    return {
        "creator": creator,
        "founder": founder,
        "version": version,
        "display_string": display_string
    }

@bottle.get('/api/settings/view')
def api_settings_view():
    import api
    config = api.load_config()
    credits_info = api_credits()
    return {
        "custom_media_path": config.get("custom_media_path", ""),
        "credits": credits_info
    }

@bottle.post('/api/first_run')
def api_first_run():
    import database
    import api
    database.initialize_db()
    api.load_config()
    return {"success": True}

@bottle.get('/api/media/details/<tmdb_id>')
def api_media_details(tmdb_id):
    import sqlite3
    import database
    import api
    
    conn = sqlite3.connect(database.DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM media 
        WHERE Poster_Pfad LIKE ? 
           OR Banner_Pfad LIKE ?;
    """, (f"%{tmdb_id}.%", f"%{tmdb_id}.%"))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {}
        
    res = dict(row)
    
    config = api.load_config()
    custom_path = config.get("custom_media_path", "").strip()
    
    poster_filename = os.path.basename(res.get("Poster_Pfad") or "")
    banner_filename = os.path.basename(res.get("Banner_Pfad") or "")
    
    if custom_path and os.path.isdir(custom_path):
        poster_abs = os.path.join(custom_path, "posters", poster_filename)
        banner_abs = os.path.join(custom_path, "banners", banner_filename)
    else:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            poster_abs = os.path.join(local_appdata, "CinePalast Manager", "assets", "posters", poster_filename)
            banner_abs = os.path.join(local_appdata, "CinePalast Manager", "assets", "banners", banner_filename)
        else:
            poster_abs = os.path.join(get_app_dir(), "assets", "posters", poster_filename)
            banner_abs = os.path.join(get_app_dir(), "assets", "banners", banner_filename)
            
    res["Poster_Pfad"] = poster_abs
    res["Banner_Pfad"] = banner_abs
    
    compat_res = {}
    for k, v in res.items():
        compat_res[k] = v
        compat_res[k.lower()] = v
        
    return compat_res


@bottle.route('/<path:path>')
def serve_static(path):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    if not os.path.isdir(frontend_dir):
        # PyInstaller temp directory fallback
        if hasattr(sys, '_MEIPASS'):
            frontend_dir = os.path.join(sys._MEIPASS, "frontend")
            
    return bottle.static_file(path, root=frontend_dir)

@bottle.route('/')
def serve_index():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    if not os.path.isdir(frontend_dir):
        if hasattr(sys, '_MEIPASS'):
            frontend_dir = os.path.join(sys._MEIPASS, "frontend")
            
    return bottle.static_file("index.html", root=frontend_dir)
