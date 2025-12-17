import base64
import json
import requests
import yaml

from cryptography.x509.oid import ObjectIdentifier
from sigstore.verify import Verifier
from sigstore.verify.policy import AllOf, OIDCIssuer, GitHubWorkflowRepository, Certificate, ExtensionNotFound
from sigstore.models import Bundle
from sigstore.errors import VerificationError

RUNNER_ENVIRONMENT_OID = ObjectIdentifier("1.3.6.1.4.1.57264.1.11")


class GitHubHostedRunner:
    """Verifies the certificate's runner environment is github-hosted."""

    def verify(self, cert: Certificate) -> None:
        try:
            ext = cert.extensions.get_extension_for_oid(RUNNER_ENVIRONMENT_OID).value
            ext_value = ext.value.decode()
            if ext_value != "github-hosted":
                raise VerificationError(
                    f"Certificate's runner environment is not github-hosted "
                    f"(got '{ext_value}')"
                )
        except ExtensionNotFound:
            raise VerificationError(
                f"Certificate does not contain runner environment "
                f"({RUNNER_ENVIRONMENT_OID.dotted_string}) extension"
            )

from measure_amd import measure_amd
from measure_intel import measure_intel

from util import sha256sum, sha256sum_bytes, fetch

CACHE_DIR = "/cache"

config = yaml.safe_load(open("/config.yml", "r"))

CVM_VERSION = config["cvm-version"]
CPUS = config["cpus"]
MEMORY = config["memory"]

CVMIMAGE_REPO = "tinfoilsh/cvmimage"
OIDC_ISSUER = "https://token.actions.githubusercontent.com"

manifest_url = f"https://github.com/{CVMIMAGE_REPO}/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
manifest_response = requests.get(manifest_url)
manifest_response.raise_for_status()
manifest_bytes = manifest_response.content
manifest = json.loads(manifest_bytes)

manifest_digest = sha256sum_bytes(manifest_bytes)
attestation_url = f"https://api.github.com/repos/{CVMIMAGE_REPO}/attestations/sha256:{manifest_digest}"
attestation_response = requests.get(attestation_url)
attestation_response.raise_for_status()
attestation_bundle_json = json.dumps(attestation_response.json()["attestations"][0]["bundle"])

verifier = Verifier.production()
bundle = Bundle.from_json(attestation_bundle_json)
id_policy = AllOf([
    OIDCIssuer(OIDC_ISSUER),
    GitHubWorkflowRepository(CVMIMAGE_REPO),
    GitHubHostedRunner(),
])

verifier.verify_artifact(artifact=manifest_bytes, bundle=bundle, policy=id_policy)
print(f"Manifest attestation verified for {CVMIMAGE_REPO}")

kernel_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", CACHE_DIR)
initrd_file = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", CACHE_DIR)

kernel_hash = sha256sum(kernel_file)
initrd_hash = sha256sum(initrd_file)

if kernel_hash != manifest["kernel"]:
    raise ValueError(f"Kernel hash mismatch: expected {manifest['kernel']}, got {kernel_hash}")
if initrd_hash != manifest["initrd"]:
    raise ValueError(f"Initrd hash mismatch: expected {manifest['initrd']}, got {initrd_hash}")

EDK2_REPO = "tinfoilsh/edk2"
EDK2_VERSION = "v0.0.2"

amd_ovmf = fetch(f"https://github.com/{EDK2_REPO}/releases/download/{EDK2_VERSION}/OVMF.fd", CACHE_DIR)
ovmf_digest = sha256sum(amd_ovmf)

ovmf_attestation_url = f"https://api.github.com/repos/{EDK2_REPO}/attestations/sha256:{ovmf_digest}"
ovmf_attestation_response = requests.get(ovmf_attestation_url)
ovmf_attestation_response.raise_for_status()
ovmf_bundle_json = json.dumps(ovmf_attestation_response.json()["attestations"][0]["bundle"])

ovmf_bundle = Bundle.from_json(ovmf_bundle_json)
ovmf_policy = AllOf([
    OIDCIssuer(OIDC_ISSUER),
    GitHubWorkflowRepository(EDK2_REPO),
    GitHubHostedRunner(),
])

with open(amd_ovmf, "rb") as f:
    ovmf_bytes = f.read()

verifier.verify_artifact(artifact=ovmf_bytes, bundle=ovmf_bundle, policy=ovmf_policy)
print(f"OVMF attestation verified for {EDK2_REPO}")

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
