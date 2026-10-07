#!/bin/sh
# Post-build: se ejecuta con el rootfs ($1 = TARGET_DIR) ya montado en output/target.
set -eu
TARGET_DIR="$1"
BOARD_DIR="$(dirname "$0")"

# Script de arranque de U-Boot dentro del rootfs (/boot/boot.scr)
mkdir -p "${TARGET_DIR}/boot"
"${HOST_DIR}/bin/mkimage" -A arm64 -O linux -T script -C none \
	-n "CRA demo boot" -d "${BOARD_DIR}/boot.cmd" "${TARGET_DIR}/boot/boot.scr"

# Versión de la imagen (trazabilidad: qué software exacto lleva cada equipo)
VERSION="$(git -C "${BR2_EXTERNAL_CRA_DEMO_PATH}" describe --tags --always --dirty 2>/dev/null || echo dev)"
sed -i '/^IMAGE_VERSION=/d' "${TARGET_DIR}/usr/lib/os-release"
echo "IMAGE_VERSION=${VERSION}" >> "${TARGET_DIR}/usr/lib/os-release"
