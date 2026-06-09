import subprocess
import sys
import os
import urllib.request
import json
import time

env = os.environ.copy()
env['CINEPALAST_WEB'] = '1'
env['CINEPALAST_PORT'] = '8080'
# Clear LOCALAPPDATA db first so it performs online search
local_appdata = os.environ.get("LOCALAPPDATA")
db_path = os.path.join(local_appdata, "CinePalast Manager", "cinepalast.db")
if os.path.exists(db_path):
    os.remove(db_path)

p = subprocess.Popen([sys.executable, 'main.py', '--web', '--port', '8080'], env=env)
time.sleep(1.5)
try:
    res = urllib.request.urlopen('http://127.0.0.1:8080/api/search?query=Leonardo&filter=Schauspieler').read()
    print("RESPONSE:", json.loads(res.decode('utf-8')))
finally:
    p.terminate()
