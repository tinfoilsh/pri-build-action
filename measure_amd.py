from sevsnpmeasure import guest
from sevsnpmeasure.vcpu_types import CPU_SIGS
from sevsnpmeasure.vmm_types import VMMType

def measure_amd(num_cpus, firmware_file, kernel_file, initrd_file, cmdline):
    """Compute AMD SEV-SNP launch digest. firmware_file can be OVMF or stage0."""
    ld = guest.snp_calc_launch_digest(
        num_cpus, CPU_SIGS["EPYC-v4"],
        firmware_file, kernel_file, initrd_file, cmdline,
        0x1, "", VMMType.QEMU, dump_vmsa=False,
    )
    return ld.hex()
