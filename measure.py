import base64
import json
import requests
import yaml
from sevsnpmeasure import guest
from sevsnpmeasure.vcpu_types import CPU_SIGS
from sevsnpmeasure.vmm_types import VMMType

from util import sha256sum, fetch

CACHE_DIR = "/cache"

config = yaml.safe_load(open("/config.yml", "r"))
external_config = yaml.safe_load(open("/external-config.yml", "r"))

CVM_VERSION = config["cvm-version"]
OVMF_VERSION = config["ovmf-version"]
CPUS = config["cpus"]
MEMORY = config["memory"]

url = f"https://github.com/tinfoilsh/cvmimage/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
manifest = requests.get(url).json()

ovmf_file = fetch(f"https://github.com/tinfoilsh/edk2/releases/download/v{OVMF_VERSION}/OVMF.fd", CACHE_DIR)
kernel_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", CACHE_DIR)
initrd_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", CACHE_DIR)

cmdline = f"readonly=on console=ttyS0 earlyprintk=serial root=/dev/mapper/root roothash={manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')}"

print("Measuring...")
ld = guest.snp_calc_launch_digest(
    CPUS, CPU_SIGS["EPYC-v4"],
    ovmf_file, kernel_file, initrd_file, cmdline,
    0x1, "", VMMType.QEMU, dump_vmsa=False,
)

deployment_cfg = {
    "measurement": ld.hex(),
    "cmdline": cmdline,
    "hashes": manifest,
    "config": base64.b64encode(open("/config.yml", "rb").read()).decode("utf-8"),
    "external_config": external_config
}

print(deployment_cfg)

md = f"""SEV-SNP Measurement: `{deployment_cfg['measurement']}`
Inference Image Version: [`{CVM_VERSION}`](https://github.com/tinfoilsh/cvmimage/releases/tag/v{CVM_VERSION})
OVMF Version: [`{OVMF_VERSION}`](https://github.com/tinfoilsh/edk2/releases/tag/v{OVMF_VERSION})
"""

with open("/output/release.md", "w") as f:
    f.write(md)

with open("/output/tinfoil-deployment.json", "w") as f:
    f.write(json.dumps(deployment_cfg, indent=4))
