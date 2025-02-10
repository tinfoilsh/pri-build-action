import hashlib
import os
import shutil
import urllib.request


def sha256sum(filename):
    sha256_hash = hashlib.sha256()

    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def fetch(url, file):
    if os.path.exists(file):
        return

    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response, open(file, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
