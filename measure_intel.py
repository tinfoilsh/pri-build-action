import json
import os
import subprocess
import tempfile

def measure_intel(
    num_cpus: int,
    mem_m: int,
    kernel_file: str, initrd_file: str, cmdline: str,
):
    tdx_metadata = {
          "boot_info": {
            "bios": "", 
            "acpi_tables": "",
            "rsdp": "",
            "table_loader": "",
            "boot_order": "",
            "boot_0000": "",
            "boot_0001": "",
            "boot_0006": "",
            "boot_0007": ""
        },
        "direct": {
            "kernel": kernel_file,
            "initrd": initrd_file,
            "cmdline": cmdline,
        }
    }

    with tempfile.TemporaryDirectory() as workdir:
        metadata_path = os.path.join(workdir, "metadata.json")
        measurement_path = os.path.join(workdir, "measurement.json")

        with open(metadata_path, "w") as f:
            json.dump(tdx_metadata, f)

        tdx_measure_cmd = [
            "/app/tdx-measure",
            metadata_path,
            "--runtime-only",
            "--cpu", str(num_cpus),
            "--memory", f"{mem_m}G",
            "--direct-boot=true",
            "--json-file", measurement_path
        ]
        print(" ".join(tdx_measure_cmd))
        subprocess.run(tdx_measure_cmd, check=True)
        with open(measurement_path, "r") as f:
            return json.load(f)
