#!/bin/sh
# Post-image: construye la imagen de slot (ext4 + dm-verity + FIT firmado) y el paquete
# de actualización RAUC firmado que la contiene.
# Formato verity: el equipo verifica cada bloque con dm-verity al instalar.
set -eu

# Estado A/B de fábrica (partición bootstate): arranca A, 3 intentos por slot
printf 'BOOT_ORDER=A B\nBOOT_A_LEFT=3\nBOOT_B_LEFT=3\n' > "${BINARIES_DIR}/bootstate.txt"

BOARD_DIR="$(dirname "$0")"
TOP="${BR2_EXTERNAL_CRA_DEMO_PATH}/.."

# --- Slot: ext4 + árbol dm-verity + FIT firmado (con el root hash) en offset fijo ---
# Device tree de control de U-Boot = device tree de la máquina + clave pública (required=conf)
"${HOST_DIR}/bin/dtc" -q -I dts -O dtb -o "${BINARIES_DIR}/qemu-cra.dtb" "${BOARD_DIR}/qemu-cra.dts"
cp "${BINARIES_DIR}/qemu-cra.dtb" "${BINARIES_DIR}/u-boot-control.dtb"
HOST_DIR="${HOST_DIR}" "${TOP}/scripts/mk-slot-image.sh" "${BINARIES_DIR}/rootfs.ext4" "${BINARIES_DIR}/Image" \
	"${BINARIES_DIR}/qemu-cra.dtb" "${BOARD_DIR}/fit-image.its" "${TOP}/keys/fit" "${BINARIES_DIR}" \
	"${BINARIES_DIR}/u-boot-control.dtb"
# Comprobación de la firma (fit_check_sign termina con error porque busca un ramdisk que no usamos)
CHECK="$("${HOST_DIR}/bin/fit_check_sign" -f "${BINARIES_DIR}/fitImage" -k "${BINARIES_DIR}/u-boot-control.dtb" 2>&1 || true)"
if ! echo "${CHECK}" | grep -q "node 'conf-1'... sha256,rsa4096:cra-dev+" || \
   echo "${CHECK}" | grep -qE "(rsa4096:[^ ]+|sha256)- *$|error!"; then
	echo "${CHECK}" >&2; echo "ERROR: la firma del FIT no se verifica" >&2; exit 1
fi
echo "FIT firmado y verificado con la clave cra-dev (RSA-4096)"

KEYS_DIR="${TOP}/keys/rauc"
BUILD="$(sed -n 's/^IMAGE_BUILD=//p' "${TARGET_DIR}/usr/lib/os-release")"
WORK="${BUILD_DIR}/rauc-bundle"
rm -rf "${WORK}" && mkdir -p "${WORK}"
cp "${BINARIES_DIR}/slot.img" "${WORK}/slot.img"
cat > "${WORK}/manifest.raucm" <<MANIFEST
[update]
compatible=cra-demo-qemu-aarch64
version=${BUILD}
description=CRA demo, build ${BUILD}

[bundle]
format=verity

[image.rootfs]
filename=slot.img
MANIFEST
rm -f "${BINARIES_DIR}/update.raucb"
"${HOST_DIR}/bin/rauc" bundle --cert="${KEYS_DIR}/signing.crt" --key="${KEYS_DIR}/signing.key" \
	"${WORK}" "${BINARIES_DIR}/update.raucb"
# Verificación con las mismas reglas que el equipo: keyring = CA y certificado Code Signing
cat > "${BUILD_DIR}/rauc-host.conf" <<CONF
[system]
compatible=cra-demo-qemu-aarch64
bootloader=noop

[keyring]
path=${KEYS_DIR}/ca.crt
check-purpose=codesign
CONF
"${HOST_DIR}/bin/rauc" info --conf="${BUILD_DIR}/rauc-host.conf" "${BINARIES_DIR}/update.raucb" > /dev/null
echo "Paquete de actualización: ${BINARIES_DIR}/update.raucb (versión ${BUILD})"
