#!/bin/sh
# Post-build: se ejecuta con el rootfs ($1 = TARGET_DIR) ya montado en output/target.
set -eu
TARGET_DIR="$1"
BOARD_DIR="$(dirname "$0")"
KEYS_DIR="${BR2_EXTERNAL_CRA_DEMO_PATH}/../keys"

# Script de arranque de U-Boot dentro del rootfs (/boot/boot.scr)
mkdir -p "${TARGET_DIR}/boot"
"${HOST_DIR}/bin/mkimage" -A arm64 -O linux -T script -C none \
	-n "CRA demo boot" -d "${BOARD_DIR}/boot.cmd" "${TARGET_DIR}/boot/boot.scr"

# Versión de la imagen (trazabilidad: qué software exacto lleva cada equipo)
VERSION="$(git -C "${BR2_EXTERNAL_CRA_DEMO_PATH}" describe --tags --always --dirty 2>/dev/null || echo dev)"
sed -i '/^IMAGE_VERSION=/d' "${TARGET_DIR}/usr/lib/os-release"
echo "IMAGE_VERSION=${VERSION}" >> "${TARGET_DIR}/usr/lib/os-release"

# --- Sesión 2: endurecimiento ---
# Acceso solo con clave SSH (sin contraseñas por defecto)
if [ ! -f "${KEYS_DIR}/dev_ssh.pub" ]; then
	echo "ERROR: falta ${KEYS_DIR}/dev_ssh.pub (ejecuta scripts/gen-dev-keys.sh)" >&2
	exit 1
fi
mkdir -p "${TARGET_DIR}/home/admin/.ssh"
cp "${KEYS_DIR}/dev_ssh.pub" "${TARGET_DIR}/home/admin/.ssh/authorized_keys"

# Las claves de host SSH NO van en la imagen: dropbear las genera en el primer arranque,
# así cada equipo tiene las suyas (nada de secretos compartidos entre unidades)
rm -f "${TARGET_DIR}"/etc/dropbear/dropbear_*_host_key

# Servicios innecesarios fuera (superficie de ataque mínima)
rm -f "${TARGET_DIR}/etc/init.d/S50crond"
