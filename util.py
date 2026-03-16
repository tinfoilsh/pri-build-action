import hashlib
import os
import subprocess


def sha256sum(filename: str) -> str:
    sha256_hash = hashlib.sha256()

    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


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
    subprocess.run(
        ["curl", "-fSL", "--retry", "3", "-o", file_path, url],
        check=True,
    )

    return file_path
