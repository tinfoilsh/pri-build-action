import json
import math
import os
import shutil
import urllib.request

from sevsnpmeasure import guest
from sevsnpmeasure.vcpu_types import CPU_SIGS
from sevsnpmeasure.vmm_types import VMMType

INFERENCE_IMAGE_VERSION = os.getenv("INFERENCE_IMAGE_VERSION")
OVMF_VERSION = os.getenv("OVMF_VERSION")
CPUS = int(os.getenv("CPUS"))
DOMAIN = os.getenv("DOMAIN")
MODEL = os.getenv("MODEL")


def model_size(model: str, tag: str) -> int:
    url = f"https://registry.ollama.ai/v2/library/{model}/manifests/{tag}"
    req = urllib.request.urlopen(url)
    body = json.loads(req.read().decode('utf-8'))
    total = body["config"]["size"]
    for layer in body["layers"]:
        total += layer["size"]

    return math.ceil(total / 1000 / 1000 / 1000)


def fetch(url, file):
    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response, open(file, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)


fetch(f"https://github.com/tinfoilanalytics/edk2/releases/download/v{OVMF_VERSION}/OVMF.fd", "OVMF.fd")

url = f"https://github.com/tinfoilanalytics/cvmimage/releases/download/v{INFERENCE_IMAGE_VERSION}/tinfoil-inference-v{INFERENCE_IMAGE_VERSION}-manifest.json"
manifest = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))

fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{INFERENCE_IMAGE_VERSION}.vmlinuz", "kernel")
fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{INFERENCE_IMAGE_VERSION}.initrd", "initrd")

cmdline = f"readonly=on console=ttyS0 earlyprintk=serial root=/dev/mapper/root roothash={manifest['root']} tinfoil-model={MODEL} tinfoil-domain={DOMAIN}"

print("Measuring...")
ld = guest.snp_calc_launch_digest(
    CPUS, CPU_SIGS["EPYC-v4"], "OVMF.fd", "kernel", "initrd", cmdline,
    0x1, "", VMMType.QEMU, dump_vmsa=False,
)

model_parts = MODEL.split(":")
mem_size = model_size(model_parts[0], model_parts[1]) + 18
mem_size += (mem_size % 2)

deployment_cfg = {
    "config": {
        "model": MODEL,
        "domain": DOMAIN,
    },
    "measurement": ld.hex(),
    "deployment": {
        "cmdline": cmdline,
        "cpus": CPUS,
        "memory": mem_size,
        "inference_image": INFERENCE_IMAGE_VERSION,
        "ovmf": OVMF_VERSION,
    },
    "hashes": manifest,
}

print(deployment_cfg)

md = f"""Model: `{MODEL}`
Domain: [{DOMAIN}](https://{DOMAIN}/.well-known/tinfoil-attestation)
SEV-SNP Measurement: `{deployment_cfg['measurement']}`
Inference Image Version: [`{INFERENCE_IMAGE_VERSION}`](https://github.com/tinfoilanalytics/cvmimage/releases/tag/v{INFERENCE_IMAGE_VERSION})
OVMF Version: [`{OVMF_VERSION}`](https://github.com/tinfoilanalytics/edk2/releases/tag/v{OVMF_VERSION})
Resources: {deployment_cfg['deployment']['cpus']} vCPUs / {deployment_cfg['deployment']['memory']}GB RAM
"""

with open("/output/release.md", "w") as f:
    f.write(md)

with open("/output/tinfoil-deployment.json", "w") as f:
    f.write(json.dumps(deployment_cfg, indent=4))
