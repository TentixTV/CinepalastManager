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

def test_tier3_search_online_and_save_custom(backend_server):
    """Online actor search, download movie, verify poster saved to custom storage path."""
    custom_path = os.path.abspath("test_tier3_save_custom")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    # 1. Search actor online
    resp_search = requests.get(f"{backend_server}/api/search?query=Leonardo&filter=Schauspieler", timeout=1)
    assert resp_search.status_code == 200
    movies = resp_search.json()
    assert len(movies) > 0
    movie_id = movies[0]["tmdb_id"]
    
    # 2. Download/import movie
    resp_import = requests.post(f"{backend_server}/api/import", json={"tmdb_id": movie_id}, timeout=1)
    assert resp_import.status_code == 200
    
    # 3. Verify poster in custom path
    poster_file = os.path.join(custom_path, "posters", f"{movie_id}.jpg")
    assert os.path.exists(poster_file)
    shutil.rmtree(custom_path, ignore_errors=True)

def test_tier3_boot_with_custom_path(backend_server):
    """Boot app with preconfigured custom path in config.json, verify server loads images from that path on startup."""
    custom_path = os.path.abspath("test_tier3_preconfigured_path")
    os.makedirs(os.path.join(custom_path, "posters"), exist_ok=True)
    with open(os.path.join(custom_path, "posters", "27205.jpg"), "wb") as f:
        f.write(b"PRECONFIGURED_IMAGE_DATA")
        
    # Set path in config.json directly
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(app_dir, exist_ok=True)
    with open(os.path.join(app_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"custom_media_path": custom_path, "api_key": "dummy_key"}, f)
        
    # Hit server to load details and check it fetches from custom path
    resp = requests.get(f"{backend_server}/api/media/poster/27205", timeout=1)
    assert resp.status_code == 200
    assert resp.content == b"PRECONFIGURED_IMAGE_DATA"
    shutil.rmtree(custom_path, ignore_errors=True)

def test_tier3_copy_and_load_details(backend_server):
    """Change custom path, copy images, load movie details and verify images load from the new path."""
    app_dir = os.path.join(os.environ["LOCALAPPDATA"], "CinePalast Manager")
    os.makedirs(os.path.join(app_dir, "assets", "posters"), exist_ok=True)
    with open(os.path.join(app_dir, "assets", "posters", "27205.jpg"), "wb") as f:
        f.write(b"SOURCE_POSTER_IMAGE")
        
    new_path = os.path.abspath("test_tier3_copy_load_dest")
    # Change path and trigger copy
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    
    # Request media from new path via server API
    resp = requests.get(f"{backend_server}/api/media/poster/27205", timeout=1)
    assert resp.status_code == 200
    assert resp.content == b"SOURCE_POSTER_IMAGE"
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier3_search_add_and_relocate(backend_server):
    """Search actor/director, add movie (downloads images), change custom path, trigger copy, verify new images are copied."""
    # 1. Search actor
    resp_search = requests.get(f"{backend_server}/api/search?query=Leonardo&filter=Schauspieler", timeout=1)
    movie_id = resp_search.json()[0]["tmdb_id"]
    
    # 2. Add movie (downloads to default path first)
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": ""}, timeout=1)
    requests.post(f"{backend_server}/api/import", json={"tmdb_id": movie_id}, timeout=1)
    
    # 3. Change path and trigger copy
    new_path = os.path.abspath("test_tier3_relocate_dest")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    
    # 4. Verify copied to new path
    assert os.path.exists(os.path.join(new_path, "posters", f"{movie_id}.jpg"))
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier3_boot_serve_credits(backend_server):
    """Boot app, verify server reads credits config and serves it to client."""
    resp = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp.status_code == 200
    assert "®TENTIX LLC" in resp.json().get("creator", "")

def test_tier3_boot_run_api_search(backend_server):
    """Boot app, execute search query via API server, verify results."""
    resp = requests.get(f"{backend_server}/api/search?query=Inception&filter=Alles", timeout=1)
    assert resp.status_code == 200
    assert len(resp.json()) > 0

def test_tier3_settings_path_and_credits(backend_server):
    """Set custom path, query settings view, verify both custom path and credits are returned."""
    custom_path = os.path.abspath("test_tier3_settings_view")
    requests.post(f"{backend_server}/api/settings", json={"custom_media_path": custom_path}, timeout=1)
    
    resp = requests.get(f"{backend_server}/api/settings/view", timeout=1)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("custom_media_path") == custom_path
    assert "®TENTIX LLC" in data.get("credits", {}).get("creator", "")

def test_tier3_copy_while_reading_credits(backend_server):
    """Trigger copy and concurrent check of developer name credits API."""
    import threading
    new_path = os.path.abspath("test_tier3_concurrent_dest")
    
    results = []
    def read_credits():
        try:
            r = requests.get(f"{backend_server}/api/credits", timeout=2)
            results.append(r.status_code)
        except Exception:
            results.append(500)
            
    # Trigger copy
    t = threading.Thread(target=read_credits)
    t.start()
    
    resp_copy = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=2)
    t.join()
    
    assert resp_copy.status_code == 200
    assert 200 in results
    shutil.rmtree(new_path, ignore_errors=True)

def test_tier3_search_developer_as_actor(backend_server):
    """Search for a name matching developer, verify search and credits do not conflict."""
    # Search for developer name 'Martin K.'
    resp_search = requests.get(f"{backend_server}/api/search?query=Martin+K.&filter=Schauspieler", timeout=1)
    assert resp_search.status_code == 200
    
    resp_credits = requests.get(f"{backend_server}/api/credits", timeout=1)
    assert resp_credits.status_code == 200
    assert "Martin K." in resp_credits.json().get("founder", "")

def test_tier3_boot_change_path_copy(backend_server):
    """Boot app, change path, prompt and copy images, check success status."""
    new_path = os.path.abspath("test_tier3_boot_change_path")
    resp = requests.post(f"{backend_server}/api/settings", json={"custom_media_path": new_path, "copy_existing": True}, timeout=1)
    assert resp.status_code == 200
    assert resp.json().get("success") is True
    shutil.rmtree(new_path, ignore_errors=True)
