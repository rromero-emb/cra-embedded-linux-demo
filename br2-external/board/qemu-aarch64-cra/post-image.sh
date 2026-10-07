#!/bin/sh
# Post-image: genera el paquete de actualización RAUC firmado a partir de rootfs.ext4.
# Formato verity: el equipo verifica cada bloque con dm-verity al instalar.
set -eu

# Estado A/B de fábrica (partición bootstate): arranca A, 3 intentos por slot
printf 'BOOT_ORDER=A B\nBOOT_A_LEFT=3\nBOOT_B_LEFT=3\n' > "${BINARIES_DIR}/bootstate.txt"

KEYS_DIR="${BR2_EXTERNAL_CRA_DEMO_PATH}/../keys/rauc"
BUILD="$(sed -n 's/^IMAGE_BUILD=//p' "${TARGET_DIR}/usr/lib/os-release")"
WORK="${BUILD_DIR}/rauc-bundle"
rm -rf "${WORK}" && mkdir -p "${WORK}"
cp "${BINARIES_DIR}/rootfs.ext4" "${WORK}/rootfs.ext4"
cat > "${WORK}/manifest.raucm" <<MANIFEST
[update]
compatible=cra-demo-qemu-aarch64
version=${BUILD}
description=CRA demo, build ${BUILD}

[bundle]
format=verity

[image.rootfs]
filename=rootfs.ext4
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
