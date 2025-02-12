import hashlib
import os
import shutil
import urllib.request


def sha256sum(filename: str) -> str:
    sha256_hash = hashlib.sha256()

    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def fetch(url: str, cache_dir: str) -> str:
    file_path = os.path.join(
        cache_dir,
        url.
        lstrip("https://").
        lstrip("http://")
    )

    if os.path.exists(file_path):
        print(f"Using cached file {file_path}")
        return file_path

    os.makedirs(
        os.path.dirname(file_path),
        exist_ok=True,
    )

    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response, open(file_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

    return file_path
