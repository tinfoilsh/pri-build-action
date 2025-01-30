#!/bin/bash
set -ex

GPU=01:00.0
MEMORY=$(jq -r .deployment.memory tinfoil-deployment.json)000M
CPUS=$(jq -r .deployment.cpus tinfoil-deployment.json)
CMDLINE=$(jq -r .deployment.cmdline tinfoil-deployment.json)
INFERENCE_IMAGE=$(jq -r .deployment.inference_image tinfoil-deployment.json)
OVMF_VERSION=$(jq -r .deployment.ovmf tinfoil-deployment.json)

sudo python3 /shared/nvtrust/host_tools/python/gpu-admin-tools/nvidia_gpu_tools.py --gpu-bdf $GPU --set-cc-mode=on --reset-after-cc-mode-switch
sudo python3 /shared/nvtrust/host_tools/python/gpu-admin-tools/nvidia_gpu_tools.py --gpu-bdf $GPU --query-cc-mode
stty intr ^]
sudo ~/qemu/build/qemu-system-x86_64 \
  -enable-kvm \
  -cpu EPYC-v4 \
  -machine q35 -smp $CPUS,maxcpus=$CPUS \
  -m $MEMORY \
  -no-reboot \
  -bios images/ovmf-v$OVMF_VERSION.fd \
  -drive file=images/tinfoil-inference-v$INFERENCE_IMAGE.raw,if=none,id=disk0,format=raw \
  -device virtio-scsi-pci,id=scsi0,disable-legacy=on,iommu_platform=true \
  -device scsi-hd,drive=disk0 -machine memory-encryption=sev0,vmport=off \
  -object memory-backend-memfd,id=ram1,size=$MEMORY,share=true,prealloc=false \
  -machine memory-backend=ram1 -object sev-snp-guest,id=sev0,policy=0x30000,cbitpos=51,reduced-phys-bits=5,kernel-hashes=on \
  -kernel images/tinfoil-inference-v$INFERENCE_IMAGE.vmlinuz \
  -initrd images/tinfoil-inference-v$INFERENCE_IMAGE.initrd \
  -append "$CMDLINE" \
  -net nic,model=e1000 -net user,hostfwd=tcp::8443-:443 \
  -nographic -monitor pty -monitor unix:monitor,server,nowait \
  -device pcie-root-port,id=pci.1,bus=pcie.0 \
  -device vfio-pci,host=$GPU,bus=pci.1 \
  -fw_cfg name=opt/ovmf/X-PciMmio64Mb,string=262144
stty intr ^c
