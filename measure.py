import base64
import json
import requests
import yaml

from measure_amd import measure_amd
from measure_intel import measure_intel

from util import sha256sum, fetch

CACHE_DIR = "/cache"

config = yaml.safe_load(open("/config.yml", "r"))

CVM_VERSION = config["cvm-version"]
CPUS = config["cpus"]
MEMORY = config["memory"]

url = f"https://github.com/tinfoilsh/cvmimage/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
manifest = requests.get(url).json()

kernel_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", CACHE_DIR)
initrd_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", CACHE_DIR)

amd_ovmf = fetch(f"https://github.com/tinfoilsh/edk2/releases/download/v0.0.2/OVMF.fd", CACHE_DIR)

cmdline = f"readonly=on console=ttyS0 earlyprintk=serial root=/dev/mapper/root roothash={manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')}"

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
