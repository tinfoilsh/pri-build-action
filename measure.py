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
OIDC_ISSUER = "https://token.actions.githubusercontent.com"

def verify_attestation(attestations: list, repo: str) -> None:
    """Find and verify an attestation matching the given repo and policy."""
    verifier = Verifier.production()
    policy = AllOf([
        OIDCIssuer(OIDC_ISSUER),
        GitHubWorkflowRepository(repo),
        GitHubHostedRunner(),
    ])

    errors = []
    for att in attestations:
        try:
            bundle = Bundle.from_json(json.dumps(att["bundle"]))
            verifier.verify_dsse(bundle, policy)
            return
        except Exception as e:
            errors.append(str(e))

    raise VerificationError(f"No valid attestation found for {repo}: {errors}")


class GitHubHostedRunner:
    """Verifies the certificate's runner environment is github-hosted."""

    def verify(self, cert: Certificate) -> None:
        try:
            ext = cert.extensions.get_extension_for_oid(RUNNER_ENVIRONMENT_OID).value
            if b"github-hosted" not in ext.value:
                raise VerificationError(
                    f"Certificate's runner environment is not github-hosted "
                    f"(got '{ext.value}')"
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
TF_CORE_REPO = "tinfoilsh/tf-core"

config = yaml.safe_load(open("/config.yml", "r"))

CPUS = config["cpus"]
MEMORY = config["memory"]
PLATFORM = config["platform"]
STAGE0_VERSION = config["stage0-version"]

# Old cvmimage (tinfoilsh/cvmimage) for TDX
CVM_VERSION = config["cvm-version"]
CVMIMAGE_REPO = "tinfoilsh/cvmimage"

# New cvmimage (tf-core) for AMD SNP
CVMIMAGE_VERSION = config["cvmimage-version"]

# === TDX: Old cvmimage from tinfoilsh/cvmimage ===
manifest_url = f"https://github.com/{CVMIMAGE_REPO}/releases/download/v{CVM_VERSION}/tinfoil-inference-v{CVM_VERSION}-manifest.json"
manifest_response = requests.get(manifest_url)
manifest_response.raise_for_status()
manifest_bytes = manifest_response.content
manifest = json.loads(manifest_bytes)

manifest_digest = sha256sum_bytes(manifest_bytes)
attestation_url = f"https://api.github.com/repos/{CVMIMAGE_REPO}/attestations/sha256:{manifest_digest}"
attestation_response = requests.get(attestation_url)
attestation_response.raise_for_status()

verify_attestation(attestation_response.json()["attestations"], CVMIMAGE_REPO)
print(f"Manifest attestation verified for {CVMIMAGE_REPO} (TDX)")

kernel_file_tdx = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.vmlinuz", CACHE_DIR)
initrd_file_tdx = fetch(f"https://images.tinfoil.sh/cvm/tinfoil-inference-v{CVM_VERSION}.initrd", CACHE_DIR)

kernel_hash_tdx = sha256sum(kernel_file_tdx)
initrd_hash_tdx = sha256sum(initrd_file_tdx)

if kernel_hash_tdx != manifest["kernel"]:
    raise ValueError(f"TDX kernel hash mismatch: expected {manifest['kernel']}, got {kernel_hash_tdx}")
if initrd_hash_tdx != manifest["initrd"]:
    raise ValueError(f"TDX initrd hash mismatch: expected {manifest['initrd']}, got {initrd_hash_tdx}")

# === AMD SNP: New cvmimage from tf-core ===
manifest_snp_url = f"https://github.com/{TF_CORE_REPO}/releases/download/{CVMIMAGE_VERSION}/manifest.json"
manifest_snp_response = requests.get(manifest_snp_url)
manifest_snp_response.raise_for_status()
manifest_snp_bytes = manifest_snp_response.content
manifest_snp = json.loads(manifest_snp_bytes)

manifest_snp_digest = sha256sum_bytes(manifest_snp_bytes)
attestation_snp_url = f"https://api.github.com/repos/{TF_CORE_REPO}/attestations/sha256:{manifest_snp_digest}"
attestation_snp_response = requests.get(attestation_snp_url)
attestation_snp_response.raise_for_status()

verify_attestation(attestation_snp_response.json()["attestations"], TF_CORE_REPO)
print(f"Manifest attestation verified for {TF_CORE_REPO} (AMD SNP)")

# Download kernel/initrd from R2 (uploaded by system-cvmimage workflow)
kernel_file_snp = fetch("https://images.tinfoil.sh/cvm/tinfoilcvm.vmlinuz", CACHE_DIR)
initrd_file_snp = fetch("https://images.tinfoil.sh/cvm/tinfoilcvm.initrd", CACHE_DIR)

kernel_hash_snp = sha256sum(kernel_file_snp)
initrd_hash_snp = sha256sum(initrd_file_snp)

if kernel_hash_snp != manifest_snp["vmlinuz_sha256"]:
    raise ValueError(f"SNP kernel hash mismatch: expected {manifest_snp['vmlinuz_sha256']}, got {kernel_hash_snp}")
if initrd_hash_snp != manifest_snp["initrd_sha256"]:
    raise ValueError(f"SNP initrd hash mismatch: expected {manifest_snp['initrd_sha256']}, got {initrd_hash_snp}")

# Download stage0 from tf-core (for AMD SNP)
stage0_file = fetch(f"https://github.com/{TF_CORE_REPO}/releases/download/{STAGE0_VERSION}/stage0_bin", CACHE_DIR)
stage0_digest = sha256sum(stage0_file)

stage0_attestation_url = f"https://api.github.com/repos/{TF_CORE_REPO}/attestations/sha256:{stage0_digest}"
stage0_attestation_response = requests.get(stage0_attestation_url)
stage0_attestation_response.raise_for_status()

verify_attestation(stage0_attestation_response.json()["attestations"], TF_CORE_REPO)
print(f"Stage0 attestation verified for {TF_CORE_REPO}")

# Get ACPI hash from platform-measurements release
# Find latest plt-msr-v* release
releases_url = f"https://api.github.com/repos/{TF_CORE_REPO}/releases"
releases_response = requests.get(releases_url)
releases_response.raise_for_status()
releases = releases_response.json()

plt_msr_release = None
for release in releases:
    if release["tag_name"].startswith("plt-msr-v"):
        plt_msr_release = release
        break

if not plt_msr_release:
    raise ValueError("No platform measurements release (plt-msr-v*) found in tf-core")

print(f"Using platform measurements release: {plt_msr_release['tag_name']}")

# Download platform-measurements.json from the release
measurements_url = f"https://github.com/{TF_CORE_REPO}/releases/download/{plt_msr_release['tag_name']}/platform-measurements.json"
measurements_response = requests.get(measurements_url)
measurements_response.raise_for_status()
measurements_bytes = measurements_response.content
platform_measurements = json.loads(measurements_bytes)

# Verify attestation for platform-measurements.json
measurements_digest = sha256sum_bytes(measurements_bytes)
measurements_attestation_url = f"https://api.github.com/repos/{TF_CORE_REPO}/attestations/sha256:{measurements_digest}"
measurements_attestation_response = requests.get(measurements_attestation_url)
measurements_attestation_response.raise_for_status()

verify_attestation(measurements_attestation_response.json()["attestations"], TF_CORE_REPO)
print(f"Platform measurements attestation verified for {TF_CORE_REPO}")

if PLATFORM not in platform_measurements:
    raise ValueError(f"Platform '{PLATFORM}' not found in platform-measurements.json. Available: {list(platform_measurements.keys())}")

acpi_hash = platform_measurements[PLATFORM]["acpi"]
print(f"ACPI hash for {PLATFORM}: {acpi_hash}")

# Cmdline for TDX (old cvmimage, without acpi_hash)
cmdline_tdx = f"readonly=on pci=realloc,nocrs modprobe.blacklist=nouveau nouveau.modeset=0 root=/dev/mapper/root roothash={manifest['root']} tinfoil-config-hash={sha256sum('/config.yml')}"

# Cmdline for AMD SNP (new cvmimage, with acpi_hash)
cmdline = f"readonly=on pci=realloc,nocrs modprobe.blacklist=nouveau nouveau.modeset=0 root=/dev/mapper/root roothash={manifest_snp['disk_sha256']} tinfoil-config-hash={sha256sum('/config.yml')} acpi_hash={acpi_hash}"

print("Measuring...")

# AMD SNP measurement (stage0-based, new cvmimage from tf-core)
snp_measurement = measure_amd(CPUS, stage0_file, kernel_file_snp, initrd_file_snp, cmdline)

# TDX measurement (old cvmimage from tinfoilsh/cvmimage)
tdx_measurement = measure_intel(CPUS, MEMORY, kernel_file_tdx, initrd_file_tdx, cmdline_tdx)

deployment_cfg = {
    "snp_measurement": snp_measurement,
    "tdx_measurement": tdx_measurement,
    "cmdline": cmdline_tdx,
    "cmdline_snp": cmdline,
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
