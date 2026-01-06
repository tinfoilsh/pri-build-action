import base64
import json
import os
import subprocess
import requests
import yaml
from pathlib import Path
from util import sha256sum, sha256sum_bytes, fetch

from measure_amd import measure_amd
from measure_intel import measure_intel

def get_latest_release(repo: str, suffix: str):
    releases_url = f"https://api.github.com/repos/{repo}/releases"
    releases_response = requests.get(releases_url)
    releases_response.raise_for_status()
    releases = releases_response.json()

    latest_release = None
    for release in releases:
        if release["tag_name"].startswith(suffix):
            latest_release = release
            break

    if not latest_release:
        raise ValueError(f"No {suffix} release found in {repo}")

    return latest_release["tag_name"]

def verify_attestation_gh(file_path: str, repo: str) -> None:
    """Verify attestation using GitHub CLI, ensuring it was built on GitHub-hosted runners."""
    result = subprocess.run(
        ["gh", "attestation", "verify", file_path, "-R", repo, "--deny-self-hosted-runners"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Attestation verification failed for {file_path}: {result.stderr}")

CACHE_DIR = "/cache"

def fetch_verified_artifact(url: str, repo: str) -> str:
    file_path = fetch(url, CACHE_DIR)
    verify_attestation_gh(file_path, repo)
    artifact_name = artifact_name = Path(file_path).name
    print(f"Attestation verified for {artifact_name} from {repo}")
    return file_path

def fetch_verified_json_artifact(url: str, repo: str) -> dict:
   artifact_file = fetch_verified_artifact(url, repo)
   return json.loads(open(artifact_file, "r").read()) 

config = yaml.safe_load(open("/config.yml", "r"))

# === Old release format used for TDX ===
OLD_REPO = "tinfoilsh/cvmimage"

CPUS = config["cpus"]
MEMORY = config["memory"]
CVM_VERSION = config["cvm-version"]

old_manifest_url = f"https://github.com/{OLD_REPO}/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
old_manifest = fetch_verified_json_artifact(old_manifest_url, OLD_REPO)

old_kernel_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", CACHE_DIR)
old_initrd_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", CACHE_DIR)

old_kernel_hash = sha256sum(old_kernel_file)
old_initrd_hash = sha256sum(old_initrd_file)

if old_kernel_hash != old_manifest["kernel"]:
    raise ValueError(f"Old kernel hash mismatch...")
if old_initrd_hash != old_manifest["initrd"]:
    raise ValueError(f"Old initrd hash mismatch...")

old_cmdline = f"readonly=on pci=realloc,nocrs modprobe.blacklist=nouveau nouveau.modeset=0 root=/dev/mapper/root roothash={old_manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')}"

tdx_measurement = measure_intel(CPUS, MEMORY, old_kernel_file, old_initrd_file, old_cmdline)

# === New release format used for AMD SNP ===
TF_CORE_REPO = "tinfoilsh/tf-core"
OAK_REPO = "tinfoilsh/oak"

PLATFORM = config["platform"]
STAGE0_VERSION = config["stage0-version"]
CVMIMAGE_VERSION = config["cvmimage-version"]

# Extract version numbers from tags (e.g., cvmimage-v0.0.5 -> v0.0.5)
CVMIMAGE_VER = CVMIMAGE_VERSION.replace("cvmimage-", "")
STAGE0_VER = STAGE0_VERSION.replace("stage0-", "")

new_manifest_url = f"https://github.com/{TF_CORE_REPO}/releases/download/{CVMIMAGE_VERSION}/manifest-{CVMIMAGE_VER}.json"
new_manifest = fetch_verified_json_artifact(new_manifest_url, TF_CORE_REPO)

# Download kernel/initrd/stage0 from R2
new_kernel_file = fetch_verified_artifact(f"https://images.tinfoil.sh/cvm/tinfoilcvm-{CVMIMAGE_VER}.vmlinuz", TF_CORE_REPO)
new_initrd_file = fetch_verified_artifact(f"https://images.tinfoil.sh/cvm/tinfoilcvm-{CVMIMAGE_VER}.initrd", TF_CORE_REPO)
new_stage0_file = fetch_verified_artifact(f"https://images.tinfoil.sh/fw/stage0-{STAGE0_VER}.fd", OAK_REPO)

new_kernel_hash = sha256sum(new_kernel_file)
new_initrd_hash = sha256sum(new_initrd_file)

if new_kernel_hash != new_manifest["kernel"]:
    raise ValueError(f"New kernel hash mismatch... {new_kernel_hash} != {new_manifest['kernel']}")
if new_initrd_hash != new_manifest["initrd"]:
    raise ValueError(f"New initrd hash mismatch... {new_initrd_hash} != {new_manifest['initrd']}")

plt_msr_release = get_latest_release(TF_CORE_REPO, "plt-msr-v")

# Download platform-measurements.json from the release
plt_msr_measurements_url = f"https://github.com/{TF_CORE_REPO}/releases/download/{plt_msr_release}/platform-measurements.json"
plt_msr_measurements = fetch_verified_json_artifact(plt_msr_measurements_url, TF_CORE_REPO)

if PLATFORM not in plt_msr_measurements:
    raise ValueError(f"Platform '{PLATFORM}' not found in platform-measurements.json. Available: {list(plt_msr_measurements.keys())}")

# Cmdline for AMD SNP (new cvmimage, with acpi_hash)
acpi_hash = plt_msr_measurements[PLATFORM]["acpi"]
new_cmdline = f"readonly=on pci=realloc,nocrs modprobe.blacklist=nouveau nouveau.modeset=0 root=/dev/mapper/root roothash={new_manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')} acpi_hash={acpi_hash}"

# AMD SNP measurement (stage0-based, new cvmimage from tf-core)
snp_measurement = measure_amd(CPUS, new_stage0_file, new_kernel_file, new_initrd_file, new_cmdline)

# === Finalize Release ===
deployment_cfg = {
    "snp_measurement": snp_measurement,
    "tdx_measurement": tdx_measurement,
    "cmdline": old_cmdline,
    "cmdline_stage0": new_cmdline,
    "hashes": old_manifest,
    "hashes_stage0": new_manifest,
    "config": base64.b64encode(open("/config.yml", "rb").read()).decode("utf-8"),
}

print(deployment_cfg)

md = f"""## Measurements

| Platform | Measurement |
|----------|-------------|
| AMD SEV-SNP | `{snp_measurement}` |
| Intel TDX | `{tdx_measurement}` |

## Build Artifacts

| Component | Version |
|-----------|---------|
| CVM Image | [`{CVMIMAGE_VERSION}`](https://github.com/tinfoilsh/tf-core/releases/tag/{CVMIMAGE_VERSION}) |
| Firmware (stage0) | [`{STAGE0_VERSION}`](https://github.com/tinfoilsh/oak/releases/tag/{STAGE0_VERSION}) |
| Platform Measurements | [`{plt_msr_release}`](https://github.com/tinfoilsh/tf-core/releases/tag/{plt_msr_release}) |
| Legacy CVM Image (TDX) | [`{CVM_VERSION}`](https://github.com/tinfoilsh/cvmimage/releases/tag/v{CVM_VERSION}) |

All artifacts verified via GitHub attestation.
"""

with open("/output/release.md", "w") as f:
    f.write(md)

with open("/output/tinfoil-deployment.json", "w") as f:
    f.write(json.dumps(deployment_cfg, indent=4))
