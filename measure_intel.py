import os
import json

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
            "path_boot_xxxx": ""
        },
        "direct": {
            "kernel": kernel_file,
            "initrd": initrd_file,
            "cmdline": cmdline,
        }
    }
    with open("metadata.json", "w") as f:
        json.dump(tdx_metadata, f)

    tdx_measure_cmd = f"/app/tdx-measure metadata.json --runtime-only --cpu {num_cpus} --memory {mem_m}G --direct-boot=true --json-file measurement.json"
    print(tdx_measure_cmd)
    os.system(tdx_measure_cmd)
    with open("measurement.json", "r") as f:
        return json.load(f)
