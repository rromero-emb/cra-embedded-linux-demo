#!/bin/sh
# Arranca la imagen de la demo en QEMU (salir: Ctrl-a x)
set -eu
IMAGES="${1:-output/images}"
exec qemu-system-aarch64 \
	-M virt -cpu cortex-a53 -smp 2 -m 512 -nographic \
	-bios "${IMAGES}/u-boot.bin" \
	-drive file="${IMAGES}/disk.img",if=none,format=raw,id=hd0,snapshot=on \
	-device virtio-blk-device,drive=hd0 \
	-netdev user,id=net0 -device virtio-net-device,netdev=net0
