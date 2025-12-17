import hashlib
import os
import shutil
import requests


def sha256sum(filename: str) -> str:
    sha256_hash = hashlib.sha256()

    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def sha256sum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, cache_dir: str) -> str:
    file_path = os.path.join(
        cache_dir,
        url.split("/")[-1]
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
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    with open(file_path, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)

    return file_path
