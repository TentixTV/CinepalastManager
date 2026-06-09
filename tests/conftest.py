import os
import sys
import shutil
import tempfile
import socket
import time
import subprocess
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import pytest
from unittest.mock import patch, MagicMock

# 1. Environment Isolation (Redirect LOCALAPPDATA and USERPROFILE)
# Generate temp dirs at session start to ensure absolute isolation
temp_localappdata = tempfile.mkdtemp(prefix="cinepalast_test_appdata_")
temp_userprofile = tempfile.mkdtemp(prefix="cinepalast_test_userprofile_")

os.environ["LOCALAPPDATA"] = temp_localappdata
os.environ["USERPROFILE"] = temp_userprofile
os.environ["CINEPALAST_TEST_MODE"] = "1"

# Create a temporary directory for sitecustomize.py to intercept requests in subprocesses
temp_pythonpath = tempfile.mkdtemp(prefix="cinepalast_test_pythonpath_")
sitecustomize_path = os.path.join(temp_pythonpath, "sitecustomize.py")

# Write sitecustomize.py
with open(sitecustomize_path, "w", encoding="utf-8") as f:
    f.write("""
import os
import requests

mock_server_url = os.environ.get("CINEPALAST_MOCK_SERVER_URL")
if mock_server_url:
    original_request = requests.Session.request
    def mocked_request(self, method, url, *args, **kwargs):
        rewritten_url = url
        if "api.themoviedb.org" in url:
            path = url.split("api.themoviedb.org")[1]
            rewritten_url = f"{mock_server_url}/tmdb_api{path}"
        elif "image.tmdb.org" in url:
            path = url.split("image.tmdb.org")[1]
            rewritten_url = f"{mock_server_url}/tmdb_image{path}"
        elif "www.themoviedb.org" in url:
            path = url.split("www.themoviedb.org")[1]
            rewritten_url = f"{mock_server_url}/tmdb_web{path}"
        elif "synchronkartei.de" in url:
            path = url.split("synchronkartei.de")[1]
            rewritten_url = f"{mock_server_url}/synchronkartei{path}"
        elif "api.github.com" in url:
            path = url.split("api.github.com")[1]
            rewritten_url = f"{mock_server_url}/github{path}"
        elif "upload.wikimedia.org" in url:
            path = url.split("upload.wikimedia.org")[1]
            rewritten_url = f"{mock_server_url}/wikimedia{path}"
        return original_request(self, method, rewritten_url, *args, **kwargs)
    requests.Session.request = mocked_request
""")

# Prepend temp_pythonpath to PYTHONPATH for subprocesses
old_pythonpath = os.environ.get("PYTHONPATH", "")
if old_pythonpath:
    os.environ["PYTHONPATH"] = f"{temp_pythonpath}{os.pathsep}{old_pythonpath}"
else:
    os.environ["PYTHONPATH"] = temp_pythonpath

# 2. Local HTTP Mock Server for Offline Mode
class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging to stdout/stderr to keep test output clean
        pass

    def do_GET(self):
        path = self.path
        
        # TMDB API
        if path.startswith("/tmdb_api/"):
            subpath = path[len("/tmdb_api/"):]
            
            # /configuration
            if subpath.startswith("3/configuration"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"images": {"base_url": "http://localhost/", "secure_base_url": "http://localhost/"}}')
                return
                
            # /search/person
            elif subpath.startswith("3/search/person"):
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(path).query).get("query", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if "Leonardo" in query:
                    self.wfile.write(b'{"results": [{"id": 6193, "name": "Leonardo DiCaprio", "popularity": 50.0}]}')
                elif "Christopher" in query:
                    self.wfile.write(b'{"results": [{"id": 525, "name": "Christopher Nolan", "popularity": 60.0}]}')
                elif "Developer" in query or "TENTIX" in query:
                    self.wfile.write(b'{"results": [{"id": 9999, "name": "Martin K.", "popularity": 10.0}]}')
                else:
                    self.wfile.write(b'{"results": []}')
                return
                
            # /person/{id}/movie_credits
            elif "movie_credits" in subpath:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if "6193" in subpath: # DiCaprio
                    self.wfile.write(b'{"cast": [{"id": 27205, "title": "Inception", "release_date": "2010-07-16", "poster_path": "/inception.jpg", "media_type": "movie"}]}')
                elif "525" in subpath: # Nolan
                    self.wfile.write(b'{"crew": [{"id": 27205, "title": "Inception", "job": "Director", "release_date": "2010-07-16", "poster_path": "/inception.jpg", "media_type": "movie"}]}')
                else:
                    self.wfile.write(b'{"cast": [], "crew": []}')
                return
                
            # /search/movie
            elif subpath.startswith("3/search/movie"):
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(path).query).get("query", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if "Inception" in query:
                    self.wfile.write(b'{"results": [{"id": 27205, "title": "Inception", "release_date": "2010-07-16", "poster_path": "/inception.jpg"}]}')
                else:
                    self.wfile.write(b'{"results": []}')
                return
                
            # /movie/{id}
            elif "3/movie/" in subpath:
                movie_id = subpath.split("/")[-1].split("?")[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if movie_id == "27205":
                    self.wfile.write(b"""{
                        "id": 27205,
                        "title": "Inception",
                        "release_date": "2010-07-16",
                        "genres": [{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}],
                        "runtime": 148,
                        "overview": "Dom Cobb ist ein begnadeter Dieb...",
                        "production_companies": [{"name": "Warner Bros. Pictures"}],
                        "production_countries": [{"name": "USA"}],
                        "poster_path": "/inception.jpg",
                        "backdrop_path": "/inception_banner.jpg",
                        "credits": {
                            "cast": [{"name": "Leonardo DiCaprio"}, {"name": "Joseph Gordon-Levitt"}],
                            "crew": [{"name": "Christopher Nolan", "job": "Director"}]
                        },
                        "release_dates": {
                            "results": [
                                {
                                    "iso_3166_1": "DE",
                                    "release_dates": [{"certification": "12"}]
                                }
                            ]
                        }
                    }""")
                else:
                    self.wfile.write(b'{"id": 0, "title": "Unknown"}')
                return
                
        # TMDB Web (for scraper fallback)
        elif path.startswith("/tmdb_web/"):
            subpath = path[len("/tmdb_web/"):]
            
            # search/person?query=...
            if subpath.startswith("search/person"):
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(path).query).get("query", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if "Leonardo" in query:
                    self.wfile.write(b'<html><body><a href="/person/6193">Leonardo DiCaprio</a></body></html>')
                elif "Christopher" in query:
                    self.wfile.write(b'<html><body><a href="/person/525">Christopher Nolan</a></body></html>')
                else:
                    self.wfile.write(b'<html><body>No Results</body></html>')
                return
                
            # person/{person_id}
            elif subpath.startswith("person/"):
                person_id = subpath.split("/")[1].split("?")[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if person_id == "6193": # DiCaprio
                    self.wfile.write(b"""<html><body>
                        <h3>Darsteller</h3>
                        <table>
                        <table class="credit_group">
                            <tr class="credit_group">
                                <td class="year">2010</td>
                                <td class="role"><a href="/movie/27205">Inception</a></td>
                            </tr>
                        </table>
                        </table>
                    </body></html>""")
                elif person_id == "525": # Nolan
                    self.wfile.write(b"""<html><body>
                        <h3>Regie</h3>
                        <table>
                        <table class="credit_group">
                            <tr class="credit_group">
                                <td class="year">2010</td>
                                <td class="role"><a href="/movie/27205">Inception</a></td>
                            </tr>
                        </table>
                        </table>
                    </body></html>""")
                else:
                    self.wfile.write(b'<html><body>No details</body></html>')
                return
                
            # search?query=... (general movie search)
            elif subpath.startswith("search"):
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(path).query).get("query", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if "Inception" in query:
                    self.wfile.write(b"""<html><body>
                        <div class="comp:media-card">
                            <a href="/movie/27205">Inception</a>
                            <h2>Inception</h2>
                            <span class="release_date">2010</span>
                            <img src="/t/p/w500/inception.jpg"/>
                        </div>
                    </body></html>""")
                else:
                    self.wfile.write(b'<html><body>No Results</body></html>')
                return
                
            # movie/{movie_id}
            elif subpath.startswith("movie/"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""<html><body>
                    <h2>Inception <span class="release_date">(2010)</span></h2>
                    <div class="overview">Dom Cobb...</div>
                    <span class="genres"><a href="/genre/action">Action</a></span>
                    <span class="runtime">148m</span>
                    <li class="profile"><p class="character">Director</p><a href="/person/525">Christopher Nolan</a></li>
                    <ol class="people"><li class="card"><p>Leonardo DiCaprio</p></li></ol>
                    <span class="certification">FSK 12</span>
                    <meta property="og:image" content="https://image.tmdb.org/t/p/w500/inception.jpg"/>
                    <meta property="og:title" content="Inception - The Movie Database (TMDB)"/>
                </body></html>""")
                return
                
        # Synchronkartei
        elif path.startswith("/synchronkartei/"):
            subpath = path[len("/synchronkartei/"):]
            if subpath.startswith("suche"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'<html><body><a href="/film/12345">Inception (2010)</a></body></html>')
                return
            elif subpath.startswith("film/"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""<html><body>
                    <table class="table">
                        <tr><td>Leonardo DiCaprio</td><td>Gerrit Schmidt-Fo\xc3\x9f</td><td>Dom Cobb</td></tr>
                    </table>
                </body></html>""")
                return
                
        # GitHub
        elif path.startswith("/github/"):
            subpath = path[len("/github/"):]
            if "version.json" in subpath:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"version": "1.2.0"}')
                return
            elif "CinePalastSetup.exe" in subpath:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(b"DUMMY_EXE_BYTES_12345")
                return
                
        # Wikimedia
        elif path.startswith("/wikimedia/"):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            # 1x1 PNG dummy image
            self.wfile.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
            return
            
        # TMDB Image
        elif path.startswith("/tmdb_image/"):
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            # Send dummy 1x1 jpeg
            self.wfile.write(b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\xff\xd9')
            return
            
        self.send_response(404)
        self.end_headers()

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture(scope="session", autouse=True)
def mock_http_server():
    port = get_free_port()
    server = ThreadingHTTPServer(('127.0.0.1', port), MockHandler)
    server_url = f"http://127.0.0.1:{port}"
    
    # Expose this url to test and sitecustomize
    os.environ["CINEPALAST_MOCK_SERVER_URL"] = server_url
    
    # Run server in background thread
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    yield server_url
    
    # Shut down server
    server.shutdown()
    server.server_close()
    
    # Clean up temp directories
    shutil.rmtree(temp_localappdata, ignore_errors=True)
    shutil.rmtree(temp_userprofile, ignore_errors=True)
    shutil.rmtree(temp_pythonpath, ignore_errors=True)

# 3. Intercept requests in the parent test runner process too
import requests
original_request = requests.Session.request
def mocked_request(self, method, url, *args, **kwargs):
    mock_server_url = os.environ.get("CINEPALAST_MOCK_SERVER_URL")
    if mock_server_url:
        rewritten_url = url
        if "api.themoviedb.org" in url:
            path = url.split("api.themoviedb.org")[1]
            rewritten_url = f"{mock_server_url}/tmdb_api{path}"
        elif "image.tmdb.org" in url:
            path = url.split("image.tmdb.org")[1]
            rewritten_url = f"{mock_server_url}/tmdb_image{path}"
        elif "www.themoviedb.org" in url:
            path = url.split("www.themoviedb.org")[1]
            rewritten_url = f"{mock_server_url}/tmdb_web{path}"
        elif "synchronkartei.de" in url:
            path = url.split("synchronkartei.de")[1]
            rewritten_url = f"{mock_server_url}/synchronkartei{path}"
        elif "api.github.com" in url:
            path = url.split("api.github.com")[1]
            rewritten_url = f"{mock_server_url}/github{path}"
        elif "upload.wikimedia.org" in url:
            path = url.split("upload.wikimedia.org")[1]
            rewritten_url = f"{mock_server_url}/wikimedia{path}"
        return original_request(self, method, rewritten_url, *args, **kwargs)
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = mocked_request

# 4. Mock Tkinter messageboxes globally to prevent hangs
@pytest.fixture(autouse=True)
def mock_tkinter():
    with patch("tkinter.messagebox.askyesno", return_value=True) as m1, \
         patch("tkinter.messagebox.showinfo", return_value=True) as m2, \
         patch("tkinter.messagebox.showerror", return_value=True) as m3, \
         patch("tkinter.messagebox.showwarning", return_value=True) as m4, \
         patch("tkinter.messagebox.askokcancel", return_value=True) as m5:
        yield {
            "askyesno": m1,
            "showinfo": m2,
            "showerror": m3,
            "showwarning": m4,
            "askokcancel": m5
        }

@pytest.fixture(autouse=True)
def clean_db():
    local_appdata = os.environ.get("LOCALAPPDATA")
    db_path = os.path.join(local_appdata, "CinePalast Manager", "cinepalast.db") if local_appdata else "cinepalast.db"
    import sqlite3
    def do_clean():
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
                if cursor.fetchone():
                    cursor.execute("DELETE FROM media;")
                conn.commit()
                conn.close()
            except Exception:
                pass
    do_clean()
    yield
    do_clean()

@pytest.fixture(autouse=True)
def cleanup_appdata():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        version_file = os.path.join(local_appdata, "CinePalast Manager", "version.json")
        config_file = os.path.join(local_appdata, "CinePalast Manager", "config.json")
        import json
        def do_cleanup():
            if os.path.exists(version_file):
                try:
                    os.remove(version_file)
                except Exception:
                    pass
            if os.path.exists(config_file):
                try:
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump({"api_key": "dummy_key", "custom_media_path": ""}, f)
                except Exception:
                    pass
        do_cleanup()
        yield
        do_cleanup()
    else:
        yield

@pytest.fixture(autouse=True)
def cleanup_local_dirs():
    yield
    cwd = os.getcwd()
    for item in os.listdir(cwd):
        if item.startswith("test_") and os.path.isdir(os.path.join(cwd, item)):
            if item == "tests":
                continue
            shutil.rmtree(os.path.join(cwd, item), ignore_errors=True)

# 5. Backend Server Fixture (starts process running main.py and checks if it binds to 8080)
@pytest.fixture(scope="function")
def backend_server():
    port = 8080
    env = os.environ.copy()
    env["CINEPALAST_WEB"] = "1"
    env["CINEPALAST_PORT"] = str(port)
    
    # Path to main.py
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    
    # Run main.py with --web --port 8080
    log_file = open("server_test.log", "a", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, main_py, "--web", "--port", str(port)],
        env=env,
        stdout=log_file,
        stderr=log_file,
        text=True
    )
    
    # Poll to see if port 8080 binds
    bound = False
    start_time = time.time()
    while time.time() - start_time < 10.0: # Check for 10 seconds
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                bound = True
                break
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(0.1)
            
    # Yield the server url (tests will hit this, and get ConnectionError if it hasn't bound, which is correct)
    yield f"http://127.0.0.1:{port}"
    
    # Terminate process cleanly
    process.terminate()
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        process.kill()
    log_file.close()
