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

def test_tier4_scenario_first_run(backend_server):
    """First startup, default config initialization, check database and AppData assets."""
    # Simulate fresh boot: remove DB and config
    config_path = get_config_path()
    db_path = get_db_path()
    if os.path.exists(config_path):
        os.remove(config_path)
    if os.path.exists(db_path):
        os.remove(db_path)
        
    # Trigger first-run logic via endpoint
    resp = requests.post(f"{backend_server}/api/first_run", timeout=1)
    assert resp.status_code == 200
    
    # Assert default config is created
    assert os.path.exists(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    assert "api_key" in config_data
    
    # Assert database schema is created
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media';")
    assert cursor.fetchone() is not None
    conn.close()

def test_tier4_scenario_curation(backend_server):
    """Actor/director search, online query, add movie, custom path downloads."""
    custom_path = os.path.abspath("test_tier4_curation_dest")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    # 1. Online query for movie details
    resp_search = requests.get(f"{backend_server}/api/search?query=Inception&filter=Alles", timeout=1)
    movie = resp_search.json()[0]
    movie_id = movie["tmdb_id"]
    
    # 2. Add movie to database
    resp_import = requests.post(f"{backend_server}/api/import", json={"tmdb_id": movie_id}, timeout=1)
    assert resp_import.status_code == 200
    
    # 3. Check that custom path is empty first
    import glob
    assert len(glob.glob(os.path.join(custom_path, "*_PT.png"))) == 0
    assert len(glob.glob(os.path.join(custom_path, "*_WP.png"))) == 0
    
    # Fetch details
    resp_details = requests.get(f"{backend_server}/api/media/details/{movie_id}", timeout=1)
    assert resp_details.status_code == 200
    details = resp_details.json()
    
    # Save poster
    res_poster = requests.post(f"{backend_server}/api/download_desktop", json={
        "movie_title": details.get("name"),
        "file_path": details.get("poster_pfad"),
        "img_type": "poster",
        "movie_year": details.get("jahr")
    }, timeout=1)
    assert res_poster.status_code == 200
    
    # Save banner
    res_banner = requests.post(f"{backend_server}/api/download_desktop", json={
        "movie_title": details.get("name"),
        "file_path": details.get("banner_pfad"),
        "img_type": "banner",
        "movie_year": details.get("jahr")
    }, timeout=1)
    assert res_banner.status_code == 200
    
    # 4. Check downloaded assets in custom path (saved direct 1:1 as PNG)
    assert len(glob.glob(os.path.join(custom_path, "*_PT.png"))) > 0
    assert len(glob.glob(os.path.join(custom_path, "*_WP.png"))) > 0
    shutil.rmtree(custom_path, ignore_errors=True)


def test_tier4_scenario_relocation(backend_server):
    """Change path, copy images, reload movie details, verify new paths loaded."""
    # Reset path
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": ""}, timeout=1)
    
    # 1. Add movie to default path
    requests.post(f"{backend_server}/api/import", json={"tmdb_id": 27205}, timeout=1)
    
    # 2. Change path and trigger copy
    new_path = os.path.abspath("test_tier4_relocation_dest")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    
    # 3. Load movie details via API and assert they reference the relocated assets
    resp_details = requests.get(f"{backend_server}/api/media/details/27205", timeout=1)
    assert resp_details.status_code == 200
    details = resp_details.json()
    assert new_path in details.get("poster_pfad", "")
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier4_scenario_offline_mode(backend_server):
    """Start offline, query local search only, check settings and credits."""
    # Trigger offline boot
    resp_boot = requests.post(f"{backend_server}/api/first_run", json={"offline": True}, timeout=1)
    assert resp_boot.status_code == 200
    
    # Check that search runs entirely offline
    resp_search = requests.get(f"{backend_server}/api/search?query=Inception&filter=Alles&network=offline", timeout=1)
    assert resp_search.status_code == 200
    
    # Check settings and credits are still accessible
    resp_credits = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp_credits.status_code == 200
    assert "®TENTIX LLC" in resp_credits.json().get("creator", "")

def test_tier4_scenario_error_recovery(backend_server):
    """Set invalid path, check fallback/recovery, reset custom path."""
    # 1. Try to set invalid path (should fallback to AppData)
    invalid_path = "/:*?\\\"<>|"
    resp_set = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": invalid_path}, timeout=1)
    assert resp_set.status_code in [200, 400, 500]
    
    # 2. Check settings, it should have fallback/restored or kept default
    resp_view = requests.get(f"{backend_server}/api/settings/view", timeout=1)
    assert resp_view.status_code == 200
    assert resp_view.json().get("custom_media_path") != invalid_path
    
    # 3. Explicitly reset path to empty and confirm it works
    resp_reset = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": ""}, timeout=1)
    assert resp_reset.status_code == 200
    assert resp_reset.json().get("custom_media_path") == ""
