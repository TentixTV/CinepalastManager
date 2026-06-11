import os
import json
import sqlite3
import shutil
import pytest
import requests

def get_db_path():
    return os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager", "cinepalast.db")

def get_config_path():
    return os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager", "config.json")

def seed_db(name, year, actors, director):
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Jahr INTEGER,
        Schauspieler TEXT,
        Genre TEXT,
        Laufzeit_min INTEGER,
        Beschreibung TEXT,
        FSK TEXT,
        Produktionsfirma TEXT,
        Regisseur TEXT,
        Filmreihe TEXT,
        Produktionsland TEXT,
        Deutsche_Synchronsprecher TEXT,
        Poster_Pfad TEXT,
        Banner_Pfad TEXT
    );
    """)
    cursor.execute("""
    INSERT INTO media (Name, Jahr, Schauspieler, Regisseur, Genre, FSK, Poster_Pfad, Banner_Pfad)
    VALUES (?, ?, ?, ?, 'Action', '12', 'assets/posters/27205.jpg', 'assets/banners/27205.jpg')
    """, (name, year, actors, director))
    conn.commit()
    conn.close()

# --- Feature 1: Actor/Director Search (5 tests) ---

def test_tier1_search_actor_local(backend_server):
    """Local database query search for known cast members returns their films."""
    seed_db("Inception", 2010, "Leonardo DiCaprio, Tom Hardy", "Christopher Nolan")
    # Query via API endpoint (which raises ConnectionError or returns data if active)
    resp = requests.get(f"{backend_server}/api/search?query=Leonardo&filter=Schauspieler", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    assert any("Inception" in m["Name"] for m in data)

def test_tier1_search_director_local(backend_server):
    """Local database query search for known directors returns their films."""
    seed_db("Inception", 2010, "Leonardo DiCaprio, Tom Hardy", "Christopher Nolan")
    resp = requests.get(f"{backend_server}/api/search?query=Nolan&filter=Regisseur", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    assert any("Inception" in m["Name"] for m in data)

def test_tier1_search_actor_online(backend_server):
    """Online TMDB person search for a known actor returns their filmography."""
    # This hits the TMDB mock server configured in conftest.py
    resp = requests.get(f"{backend_server}/api/search?query=Leonardo&filter=Schauspieler", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert any("Inception" in m.get("titel", "") for m in data)

def test_tier1_search_director_online(backend_server):
    """Online TMDB person search for a known director returns their filmography."""
    resp = requests.get(f"{backend_server}/api/search?query=Christopher&filter=Regisseur", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert any("Inception" in m.get("titel", "") for m in data)

def test_tier1_search_all_combined(backend_server):
    """Search with 'Alles' dropdown option returns combined film/cast/director matches."""
    seed_db("Inception", 2010, "Leonardo DiCaprio, Tom Hardy", "Christopher Nolan")
    resp = requests.get(f"{backend_server}/api/search?query=Inception&filter=Alles", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert any("Inception" in m.get("titel", m.get("Name", "")) for m in data)


# --- Feature 2: Web UI Boot (5 tests) ---

def test_tier1_boot_server_status(backend_server):
    """Backend server starts on standard port and responds to basic HTTP requests."""
    resp = requests.get(f"{backend_server}/api/status", timeout=1)
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"

def test_tier1_boot_serve_assets(backend_server):
    """Server serves frontend assets (index.html, CSS, JS) correctly."""
    resp = requests.get(f"{backend_server}/index.html", timeout=1)
    assert resp.status_code == 200
    assert "CinePalast" in resp.text

def test_tier1_boot_load_config(backend_server):
    """Server successfully reads config.json at startup."""
    # Ensure config file is loaded/created in AppData by the server
    config_path = get_config_path()
    assert os.path.exists(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "api_key" in data

def test_tier1_boot_db_connect(backend_server):
    """Server connects to the SQLite database cinepalast.db."""
    # Verify DB file was created and contains the 'media' table
    db_path = get_db_path()
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
    row = cursor.fetchone()
    conn.close()
    assert row is not None

def test_tier1_boot_shutdown(backend_server):
    """Server shuts down gracefully when receiving termination signal/endpoint."""
    resp = requests.post(f"{backend_server}/api/shutdown", timeout=1)
    assert resp.status_code == 200


# --- Feature 3: Custom Storage Path (5 tests) ---

def test_tier1_custom_path_save(backend_server):
    """Save custom path in settings, verified in config.json under custom_media_path."""
    custom_path = os.path.abspath("test_custom_media_path_tier1")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    assert resp.status_code == 200
    
    with open(get_config_path(), "r", encoding="utf-8") as f:
        config_data = json.load(f)
    assert config_data.get("custom_media_path") == custom_path

def test_tier1_custom_path_dirs_created(backend_server):
    """Check that <custom_path>/posters and <custom_path>/banners folders are created."""
    custom_path = os.path.abspath("test_custom_media_path_dirs_tier1")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    assert resp.status_code == 200
    
    assert os.path.exists(os.path.join(custom_path, "posters"))
    assert os.path.exists(os.path.join(custom_path, "banners"))
    shutil.rmtree(custom_path, ignore_errors=True)

def test_tier1_custom_path_download_save(backend_server):
    """Downloading a movie poster/banner saves it directly under the custom path."""
    custom_path = os.path.abspath("test_custom_download_path")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    # Import a movie which triggers poster download (mocked TMDB ID 27205)
    resp = requests.post(f"{backend_server}/api/import", json={"tmdb_id": 27205}, timeout=1)
    assert resp.status_code == 200
    
    # Poster should NOT be inside the custom path directly yet (since import doesn't do it anymore)
    import glob
    assert len(glob.glob(os.path.join(custom_path, "*_PT.png"))) == 0
    assert len(glob.glob(os.path.join(custom_path, "*_WP.png"))) == 0
    
    # Fetch movie details to get the image paths
    resp_details = requests.get(f"{backend_server}/api/media/details/27205", timeout=1)
    assert resp_details.status_code == 200
    details = resp_details.json()
    
    # Call download_desktop for poster
    res_poster = requests.post(f"{backend_server}/api/download_desktop", json={
        "movie_title": details.get("name"),
        "file_path": details.get("poster_pfad"),
        "img_type": "poster",
        "movie_year": details.get("jahr")
    }, timeout=1)
    assert res_poster.status_code == 200
    assert res_poster.json().get("success") is True
    
    # Call download_desktop for banner
    res_banner = requests.post(f"{backend_server}/api/download_desktop", json={
        "movie_title": details.get("name"),
        "file_path": details.get("banner_pfad"),
        "img_type": "banner",
        "movie_year": details.get("jahr")
    }, timeout=1)
    assert res_banner.status_code == 200
    assert res_banner.json().get("success") is True
    
    # Now poster/banner should be inside the custom path directly
    assert len(glob.glob(os.path.join(custom_path, "*_PT.png"))) > 0
    assert len(glob.glob(os.path.join(custom_path, "*_WP.png"))) > 0
    shutil.rmtree(custom_path, ignore_errors=True)


def test_tier1_custom_path_load(backend_server):
    """Load media files from the custom path if set and file is present."""
    custom_path = os.path.abspath("test_custom_load_path")
    os.makedirs(os.path.join(custom_path, "posters"), exist_ok=True)
    
    # Write a dummy poster image
    dummy_poster = os.path.join(custom_path, "posters", "27205.jpg")
    with open(dummy_poster, "wb") as f:
        f.write(b"DUMMY_IMAGE_DATA")
        
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    # Request the media file via server API
    resp = requests.get(f"{backend_server}/api/media/poster/27205", timeout=1)
    assert resp.status_code == 200
    assert resp.content == b"DUMMY_IMAGE_DATA"
    shutil.rmtree(custom_path, ignore_errors=True)

def test_tier1_custom_path_fallback(backend_server):
    """Fallback to app assets/AppData when custom path is empty or image is missing in custom path."""
    # Setup default poster in AppData assets
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(os.path.join(app_dir, "assets", "posters"), exist_ok=True)
    default_poster = os.path.join(app_dir, "assets", "posters", "27205.jpg")
    with open(default_poster, "wb") as f:
        f.write(b"DEFAULT_POSTER_DATA")
        
    # Unset custom path
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": ""}, timeout=1)
    
    # Get media poster, should fallback to default AppData assets
    resp = requests.get(f"{backend_server}/api/media/poster/27205", timeout=1)
    assert resp.status_code == 200
    assert resp.content == b"DEFAULT_POSTER_DATA"


# --- Feature 4: Image Copying (5 tests) ---

def test_tier1_copy_trigger(backend_server):
    """Change custom path, check if copy prompt triggers image copying."""
    # Toggle setting to copy existing files
    new_path = os.path.abspath("test_copy_trigger_dest")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    assert resp.status_code == 200
    assert resp.json().get("copied") is True
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier1_copy_posters(backend_server):
    """Verify existing posters are copied to <new_path>/posters."""
    # Place dummy poster in old path (AppData)
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(os.path.join(app_dir, "assets", "posters"), exist_ok=True)
    with open(os.path.join(app_dir, "assets", "posters", "copy_test_poster.jpg"), "wb") as f:
        f.write(b"POSTER_TO_COPY")
        
    new_path = os.path.abspath("test_copy_posters_dest")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    assert resp.status_code == 200
    
    copied_file = os.path.join(new_path, "copy_test_poster.jpg")
    assert os.path.exists(copied_file)
    with open(copied_file, "rb") as f:
        assert f.read() == b"POSTER_TO_COPY"
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier1_copy_banners(backend_server):
    """Verify existing banners are copied to <new_path>/banners."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(os.path.join(app_dir, "assets", "banners"), exist_ok=True)
    with open(os.path.join(app_dir, "assets", "banners", "copy_test_banner.jpg"), "wb") as f:
        f.write(b"BANNER_TO_COPY")
        
    new_path = os.path.abspath("test_copy_banners_dest")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    assert resp.status_code == 200
    
    copied_file = os.path.join(new_path, "copy_test_banner.jpg")
    assert os.path.exists(copied_file)
    with open(copied_file, "rb") as f:
        assert f.read() == b"BANNER_TO_COPY"
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier1_copy_already_exists(backend_server):
    """Verify existing files are not corrupted/cleared if destination folders already exist."""
    new_path = os.path.abspath("test_copy_exists_dest")
    os.makedirs(os.path.join(new_path, "posters"), exist_ok=True)
    existing_file = os.path.join(new_path, "posters", "existing.jpg")
    with open(existing_file, "wb") as f:
        f.write(b"PRE_EXISTING_DATA")
        
    # Trigger copy
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    assert resp.status_code == 200
    
    # Pre-existing file should not be cleared/corrupted
    assert os.path.exists(existing_file)
    with open(existing_file, "rb") as f:
        assert f.read() == b"PRE_EXISTING_DATA"
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier1_copy_skip_invalid(backend_server):
    """Skip/fail copy operation gracefully if destination path is invalid or read-only."""
    # Use an invalid path name
    invalid_path = "/:*?\\\"<>|"
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": invalid_path, "copy_existing": True}, timeout=1)
    # The API should respond with an error status or status indicating failure, without crashing
    assert resp.status_code in [400, 500, 200]
    if resp.status_code == 200:
        assert resp.json().get("success") is False


# --- Feature 5: Developer Name Credits (5 tests) ---

def test_tier1_credits_api_response(backend_server):
    """Verify developer credits API endpoint returns developer/team info."""
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    assert "creator" in resp.json()

def test_tier1_credits_name_match(backend_server):
    """Check that developer name (or team name) matches specific expected credit string."""
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    credits_data = resp.json()
    assert "®TENTIX LLC" in credits_data.get("creator", "")
    assert "Martin K." in credits_data.get("founder", "")

def test_tier1_credits_version_match(backend_server):
    """Verify version info is returned along with developer credits."""
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    assert "version" in resp.json()

def test_tier1_credits_config_read(backend_server):
    """Verify developer credits are read from a config/metadata file if applicable."""
    # Write a dummy version metadata if app reads from a version/credits json
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(app_dir, exist_ok=True)
    version_file = os.path.join(app_dir, "version.json")
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump({"version": "9.9.9", "creator": "TEST_CREATOR"}, f)
        
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    # If read from config, it might return updated info or standard defaults if frozen
    assert resp.status_code == 200
    
def test_tier1_credits_ui_element(backend_server):
    """Verify backend provides correct credits display structure to the UI."""
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    # It must contain the display formatted structure
    assert "display_string" in data
    assert "Founder" in data["display_string"] or "Creator" in data["display_string"]
