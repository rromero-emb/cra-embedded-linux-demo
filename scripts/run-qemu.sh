#!/bin/sh
# Arranca la imagen de la demo en QEMU (salir: Ctrl-a x)
set -eu
IMAGES="${1:-output/images}"
exec qemu-system-aarch64 \
	-M virt-7.2,acpi=off -cpu cortex-a53 -smp 2 -m 512 -nographic \
	-bios "${IMAGES}/u-boot.bin" -dtb "${IMAGES}/u-boot-control.dtb" \
	-drive file="${IMAGES}/disk.img",if=none,format=raw,id=hd0,snapshot=on \
	-device virtio-blk-device,drive=hd0 \
	-device virtio-rng-device \
	-netdev user,id=net0,hostfwd=tcp:127.0.0.1:${SSH_PORT:-2222}-:22 -device virtio-net-device,netdev=net0
