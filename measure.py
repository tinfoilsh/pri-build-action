import base64
import json
import subprocess
import yaml
from pathlib import Path

from measure_amd import measure_amd
from measure_intel import measure_intel

from util import sha256sum, fetch


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
    artifact_name = Path(file_path).name
    print(f"Attestation verified for {artifact_name} from {repo}")
    return file_path


def fetch_verified_json_artifact(url: str, repo: str) -> dict:
    artifact_file = fetch_verified_artifact(url, repo)
    return json.loads(open(artifact_file, "r").read())


config = yaml.safe_load(open("/config.yml", "r"))

CVM_VERSION = config["cvm-version"]
CPUS = config["cpus"]
MEMORY = config["memory"]

CVMIMAGE_REPO = "tinfoilsh/cvmimage"

manifest_url = f"https://github.com/{CVMIMAGE_REPO}/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
manifest = fetch_verified_json_artifact(manifest_url, CVMIMAGE_REPO)

kernel_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", CACHE_DIR)
initrd_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", CACHE_DIR)

kernel_hash = sha256sum(kernel_file)
initrd_hash = sha256sum(initrd_file)

if kernel_hash != manifest["kernel"]:
    raise ValueError(f"Kernel hash mismatch: expected {manifest['kernel']}, got {kernel_hash}")
if initrd_hash != manifest["initrd"]:
    raise ValueError(f"Initrd hash mismatch: expected {manifest['initrd']}, got {initrd_hash}")

EDK2_REPO = "tinfoilsh/edk2"
EDK2_VERSION = "v0.0.3"

amd_ovmf = fetch_verified_artifact(f"https://github.com/{EDK2_REPO}/releases/download/{EDK2_VERSION}/OVMF.fd", EDK2_REPO)

cmdline = f"readonly=on pci=realloc,nocrs modprobe.blacklist=nouveau nouveau.modeset=0 root=/dev/mapper/root roothash={manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')}"

print("Measuring...")

snp_measurement = measure_amd(CPUS, amd_ovmf, kernel_file, initrd_file, cmdline)
tdx_measurement = measure_intel(CPUS, MEMORY, kernel_file, initrd_file, cmdline)

deployment_cfg = {
    "snp_measurement": snp_measurement,
    "tdx_measurement": tdx_measurement,
    "cmdline": cmdline,
    "hashes": manifest,
    "config": base64.b64encode(open("/config.yml", "rb").read()).decode("utf-8"),
}

print(deployment_cfg)

md = f"""SEV-SNP Measurement: `{deployment_cfg['snp_measurement']}`
TDX Measurement: `{deployment_cfg['tdx_measurement']}`
Inference Image Version: [`{CVM_VERSION}`](https://github.com/tinfoilsh/cvmimage/releases/tag/v{CVM_VERSION})
"""

with open("/output/release.md", "w") as f:
    f.write(md)

with open("/output/tinfoil-deployment.json", "w") as f:
    f.write(json.dumps(deployment_cfg, indent=4))
