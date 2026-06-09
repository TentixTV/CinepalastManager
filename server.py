import os
import sys
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

def run_server(port):
    bottle.run(host='127.0.0.1', port=port, quiet=True)
