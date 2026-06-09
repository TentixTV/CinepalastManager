import os
import json
import sqlite3
import shutil
import pytest
import requests
import sys
import time
import socket
import subprocess

def get_db_path():
    return os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager", "cinepalast.db")

def get_config_path():
    return os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager", "config.json")

# --- Feature 1: Actor/Director Search Boundary Cases (5 tests) ---

def test_tier2_search_empty_query(backend_server):
    """Search with empty query string returns empty list safely."""
    resp = requests.get(f"{backend_server}/api/search?query=&filter=Alles", timeout=1)
    assert resp.status_code == 200
    assert resp.json() == []

def test_tier2_search_sql_injection(backend_server):
    """Search with SQL injection payloads (e.g. ' OR '1'='1) is handled safely."""
    # Ensure tables are created first
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        ID INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL, Jahr INTEGER, Schauspieler TEXT, Regisseur TEXT
    );
    """)
    conn.commit()
    conn.close()

    resp = requests.get(f"{backend_server}/api/search?query=%27%20OR%20%271%27%3D%271&filter=Alles", timeout=1)
    assert resp.status_code == 200
    # SQL injection should not leak all items or crash the system (it should return no results)
    assert resp.json() == []

def test_tier2_search_non_existent(backend_server):
    """Search for a non-existent name returns empty results list."""
    resp = requests.get(f"{backend_server}/api/search?query=NonExistentActorNameXYZ&filter=Schauspieler", timeout=1)
    assert resp.status_code == 200
    assert resp.json() == []

def test_tier2_search_network_offline(backend_server):
    """Offline/scraper timeout returns only local db matches without crashing."""
    # Seed a local film first
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS media (ID INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL, Jahr INTEGER, Schauspieler TEXT, Regisseur TEXT);")
    cursor.execute("INSERT INTO media (Name, Jahr, Schauspieler) VALUES ('Local Movie', 2020, 'Offline Actor')")
    conn.commit()
    conn.close()
    
    # We simulate offline mode or mock server 500
    # Setting header or query parameter to mock network failure in mock server
    resp = requests.get(f"{backend_server}/api/search?query=Offline&filter=Schauspieler&network_status=offline", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    # Should fall back to local database search successfully
    assert any("Local Movie" in m["Name"] for m in data)

def test_tier2_search_unicode_long(backend_server):
    """Search with extremely long query or special unicode characters (e.g. Cyrillic/emojis)."""
    unicode_query = "Кириллица 🎬 Emoji!" * 10
    resp = requests.get(f"{backend_server}/api/search?query={unicode_query}&filter=Alles", timeout=1)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# --- Feature 2: Web UI Boot Boundary Cases (5 tests) ---

def test_tier2_boot_port_in_use():
    """Boot when port is occupied (binds alternative port or terminates gracefully)."""
    # Bind port 8080 manually
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 8080))
    s.listen(1)
    
    # Start server as subprocess
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    env = os.environ.copy()
    env["CINEPALAST_PORT"] = "8080"
    process = subprocess.Popen([sys.executable, main_py, "--web"], env=env)
    
    # Let it run for a brief moment and check it doesn't crash completely,
    # or terminates cleanly, or binds to another port.
    time.sleep(1)
    poll = process.poll()
    if poll is not None:
        # If it terminated, it should terminate with code 0 or 1, not crash
        assert poll in [0, 1]
    else:
        process.terminate()
        process.wait()
    s.close()

def test_tier2_boot_missing_config(backend_server):
    """Boot when config.json is missing/corrupted (recreates with defaults)."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        os.remove(config_path)
        
    # Trigger config reload/load via server
    resp = requests.post(f"{backend_server}/api/settings/reload", timeout=1)
    assert resp.status_code == 200
    
    # Config file should be recreated
    assert os.path.exists(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "api_key" in data

def test_tier2_boot_missing_db(backend_server):
    """Boot when SQLite db is missing (recreates db and schema)."""
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
        
    # Trigger database check/re-initialization via server
    resp = requests.post(f"{backend_server}/api/db/reinit", timeout=1)
    assert resp.status_code == 200
    
    # DB should be recreated
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
    row = cursor.fetchone()
    conn.close()
    assert row is not None

def test_tier2_boot_concurrent_connections(backend_server):
    """Handle multiple concurrent client connections."""
    import threading
    results = []
    
    def worker():
        try:
            resp = requests.get(f"{backend_server}/api/status", timeout=2)
            results.append(resp.status_code)
        except Exception as e:
            results.append(type(e))
            
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    # All threads should have succeeded without timing out or breaking
    assert all(r == 200 for r in results)

def test_tier2_boot_headless_mode(backend_server):
    """Boot without display server (headless mode check)."""
    # Start subprocess with no DISPLAY/graphics env
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    env = os.environ.copy()
    if "DISPLAY" in env:
        del env["DISPLAY"]
    env["CINEPALAST_WEB"] = "1"
    
    process = subprocess.Popen([sys.executable, main_py, "--web", "--headless"], env=env)
    time.sleep(1)
    poll = process.poll()
    # It should either be running in background (headless) or have exited with 0 (not crashed)
    if poll is not None:
        assert poll == 0
    else:
        process.terminate()
        process.wait()


# --- Feature 3: Custom Storage Path Boundary Cases (5 tests) ---

def test_tier2_custom_path_nonexistent_dir(backend_server):
    """Set path to non-existent directory (creates directory recursively)."""
    nested_path = os.path.abspath("non_existent_yet/subfolder/media_path")
    shutil.rmtree(os.path.dirname(os.path.dirname(nested_path)), ignore_errors=True)
    
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": nested_path}, timeout=1)
    assert resp.status_code == 200
    assert os.path.exists(nested_path)
    assert os.path.exists(os.path.join(nested_path, "posters"))
    shutil.rmtree(os.path.dirname(os.path.dirname(nested_path)), ignore_errors=True)

def test_tier2_custom_path_invalid_dir(backend_server):
    """Set path to invalid/unwritable directory (falls back to AppData, error handled)."""
    # Make a read-only directory or file that prevents directory creation
    unwritable_file = os.path.abspath("unwritable_target_file")
    with open(unwritable_file, "w") as f:
        f.write("blocking")
        
    # Setting path to file will fail to create folder structure recursively
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": unwritable_file}, timeout=1)
    # Backend should handle error and report failure or fallback
    assert resp.status_code in [200, 400, 500]
    if resp.status_code == 200:
        assert resp.json().get("success") is False
    os.remove(unwritable_file)

def test_tier2_custom_path_spaces_unicode(backend_server):
    """Set path containing spaces, brackets, or unicode characters."""
    special_path = os.path.abspath("test [path] mit ÖÄÜß & Spaces")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": special_path}, timeout=1)
    assert resp.status_code == 200
    assert os.path.exists(special_path)
    assert os.path.exists(os.path.join(special_path, "posters"))
    shutil.rmtree(special_path, ignore_errors=True)

def test_tier2_custom_path_offline_download(backend_server):
    """Download movie when TMDB is offline/timeout (no corrupted media saved)."""
    custom_path = os.path.abspath("test_offline_download")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    # Fetch details while TMDB API is "offline"
    resp = requests.post(f"{backend_server}/api/import", json={"tmdb_id": 99999, "simulate_offline": True}, timeout=1)
    assert resp.status_code in [400, 500, 200]
    if resp.status_code == 200:
        assert resp.json().get("success") is False
        
    # Check that no corrupted or empty posters were saved
    posters_dir = os.path.join(custom_path, "posters")
    if os.path.exists(posters_dir):
        files = os.listdir(posters_dir)
        # Any file written must have size > 0
        for f in files:
            assert os.path.getsize(os.path.join(posters_dir, f)) > 0
    shutil.rmtree(custom_path, ignore_errors=True)

def test_tier2_custom_path_clear_reset(backend_server):
    """Unset custom path (config updated, default directories active)."""
    # Set it first
    custom_path = os.path.abspath("temp_custom_path_clear")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    # Clear/reset it
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": ""}, timeout=1)
    assert resp.status_code == 200
    
    with open(get_config_path(), "r", encoding="utf-8") as f:
        config = json.load(f)
    assert config.get("custom_media_path") == ""
    shutil.rmtree(custom_path, ignore_errors=True)


# --- Feature 4: Image Copying Boundary Cases (5 tests) ---

def test_tier2_copy_empty_source(backend_server):
    """Trigger copy when there are no images in source (succeeds, no crash)."""
    # Empty out AppData posters/banners folders
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    shutil.rmtree(os.path.join(app_dir, "assets", "posters"), ignore_errors=True)
    shutil.rmtree(os.path.join(app_dir, "assets", "banners"), ignore_errors=True)
    os.makedirs(os.path.join(app_dir, "assets", "posters"), exist_ok=True)
    os.makedirs(os.path.join(app_dir, "assets", "banners"), exist_ok=True)
    
    new_path = os.path.abspath("test_empty_source_dest")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    assert resp.status_code == 200
    assert resp.json().get("copied") is True
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier2_copy_locked_file(backend_server):
    """Trigger copy when file is locked/open in another process (handles gracefully)."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(os.path.join(app_dir, "assets", "posters"), exist_ok=True)
    locked_file = os.path.join(app_dir, "assets", "posters", "locked.jpg")
    with open(locked_file, "wb") as f:
        f.write(b"LOCKED_DATA")
        
    # Lock the file by keeping it open in Python
    with open(locked_file, "a") as f_lock:
        new_path = os.path.abspath("test_locked_copy_dest")
        resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
        assert resp.status_code == 200
        
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier2_copy_invalid_destination(backend_server):
    """Copy to invalid/read-only path (handles error gracefully)."""
    invalid_path = "/:*?\\\"<>|"
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": invalid_path, "copy_existing": True}, timeout=1)
    assert resp.status_code in [200, 400, 500]

def test_tier2_copy_insufficient_space(backend_server):
    """Handle copy failures due to lack of disk space simulated."""
    new_path = os.path.abspath("test_low_space_dest")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True, "simulate_disk_full": True}, timeout=1)
    assert resp.status_code in [200, 400, 500]
    if resp.status_code == 200:
        assert resp.json().get("success") is False
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier2_copy_cancel(backend_server):
    """Simulated user cancels the copy prompt (verify files are not copied)."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(os.path.join(app_dir, "assets", "posters"), exist_ok=True)
    with open(os.path.join(app_dir, "assets", "posters", "not_copied.jpg"), "wb") as f:
        f.write(b"DO_NOT_COPY")
        
    new_path = os.path.abspath("test_copy_cancel_dest")
    # Send copy_existing=False (simulating cancel or declining prompt)
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": False}, timeout=1)
    assert resp.status_code == 200
    
    assert not os.path.exists(os.path.join(new_path, "posters", "not_copied.jpg"))
    shutil.rmtree(new_path, ignore_errors=True)


# --- Feature 5: Developer Name Credits Boundary Cases (5 tests) ---

def test_tier2_credits_missing_file(backend_server):
    """Missing credits metadata file (falls back to hardcoded default credits)."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    version_file = os.path.join(app_dir, "version.json")
    if os.path.exists(version_file):
        os.remove(version_file)
        
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    assert "®TENTIX LLC" in resp.json().get("creator", "")

def test_tier2_credits_corrupted_json(backend_server):
    """Corrupted JSON credits metadata file (restores default credits)."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(app_dir, exist_ok=True)
    version_file = os.path.join(app_dir, "version.json")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write("INVALID_JSON_DATA{{")
        
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    assert "®TENTIX LLC" in resp.json().get("creator", "")

def test_tier2_credits_html_escaping(backend_server):
    """Credits string containing HTML characters is properly escaped."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(app_dir, exist_ok=True)
    version_file = os.path.join(app_dir, "version.json")
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump({"creator": "<b>Bold Team</b>", "founder": "Martin K."}, f)
        
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    display_str = resp.json().get("display_string", "")
    # Tag should be escaped
    assert "<b>" not in display_str
    assert "&lt;b&gt;" in display_str or "Bold Team" in display_str

def test_tier2_credits_long_string(backend_server):
    """Extremely long name/string in credits doesn't break API or layout."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(app_dir, exist_ok=True)
    version_file = os.path.join(app_dir, "version.json")
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump({"creator": "LongCreator" * 100, "founder": "Martin K."}, f)
        
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    assert "LongCreator" in resp.json().get("creator", "")

def test_tier2_credits_offline_load(backend_server):
    """Credits are loaded entirely offline."""
    # Test credits endpoint runs completely without TMDB mock server online
    # Query with a simulate_offline header/param
    resp = requests.get(f"{backend_server}/api/credits?network=offline", timeout=1)
    assert resp.status_code == 200
    assert "®TENTIX LLC" in resp.json().get("creator", "")
