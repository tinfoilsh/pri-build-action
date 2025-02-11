import json
import urllib.request

import yaml
from sevsnpmeasure import guest
from sevsnpmeasure.vcpu_types import CPU_SIGS
from sevsnpmeasure.vmm_types import VMMType

from util import sha256sum, fetch

config = yaml.safe_load(open("/config.yml", "r"))

CVM_VERSION = config["cvm-version"]
OVMF_VERSION = config["ovmf-version"]
CPUS = config["cpus"]
MEMORY = config["memory"]

fetch(f"https://github.com/tinfoilsh/edk2/releases/download/v{OVMF_VERSION}/OVMF.fd", "OVMF.fd")

url = f"https://github.com/tinfoilsh/cvmimage/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
manifest = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))

fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", "kernel")
fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", "initrd")

cmdline = f"readonly=on console=ttyS0 earlyprintk=serial root=/dev/mapper/root roothash={manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')}"

print("Measuring...")
ld = guest.snp_calc_launch_digest(
    CPUS, CPU_SIGS["EPYC-v4"], "OVMF.fd", "kernel", "initrd", cmdline,
    0x1, "", VMMType.QEMU, dump_vmsa=False,
)

deployment_cfg = {
    "measurement": ld.hex(),
    "cmdline": cmdline,
    "hashes": manifest,
    "config": config,
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
