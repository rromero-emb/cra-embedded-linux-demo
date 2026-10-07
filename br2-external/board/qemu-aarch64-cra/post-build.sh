#!/bin/sh
# Post-build: se ejecuta con el rootfs ($1 = TARGET_DIR) ya montado en output/target.
set -eu
TARGET_DIR="$1"
BOARD_DIR="$(dirname "$0")"
KEYS_DIR="${BR2_EXTERNAL_CRA_DEMO_PATH}/../keys"

# --- Sesión 4/6: arranque verificado ---
# El FIT firmado ya no va dentro del sistema de ficheros: se construye en post-image junto al
# árbol de hashes dm-verity (scripts/mk-slot-image.sh) y se coloca en un offset fijo del slot.
[ -f "${KEYS_DIR}/fit/cra-dev.key" ] || { echo "ERROR: falta ${KEYS_DIR}/fit/cra-dev.key (make keys)" >&2; exit 1; }
rm -rf "${TARGET_DIR}/boot/fitImage" "${TARGET_DIR}/boot/boot.scr" "${TARGET_DIR}/boot/Image"

# Versión de la imagen (trazabilidad: qué software exacto lleva cada equipo)
VERSION="$(git -C "${BR2_EXTERNAL_CRA_DEMO_PATH}" describe --tags --always --dirty 2>/dev/null || echo dev)"
# IMAGE_BUILD: número de versión monótono (commits en la rama). Lo usa el anti-rollback de RAUC.
BUILD="$(git -C "${BR2_EXTERNAL_CRA_DEMO_PATH}" rev-list --count HEAD 2>/dev/null || echo 0)"
sed -i '/^IMAGE_VERSION=/d; /^IMAGE_BUILD=/d' "${TARGET_DIR}/usr/lib/os-release"
echo "IMAGE_VERSION=${VERSION}" >> "${TARGET_DIR}/usr/lib/os-release"
echo "IMAGE_BUILD=${BUILD}" >> "${TARGET_DIR}/usr/lib/os-release"

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
# ...y se guardan en /data para que no cambien con cada actualización (sesión 5)
rm -rf "${TARGET_DIR}/etc/dropbear"
ln -s /data/dropbear "${TARGET_DIR}/etc/dropbear"

# --- Sesión 5: actualizaciones ---
# El equipo solo confía en la CA de actualizaciones
[ -f "${KEYS_DIR}/rauc/ca.crt" ] || { echo "ERROR: falta ${KEYS_DIR}/rauc/ca.crt (make keys)" >&2; exit 1; }
install -D -m 0644 "${KEYS_DIR}/rauc/ca.crt" "${TARGET_DIR}/etc/rauc/keyring.pem"

# Servicios innecesarios fuera (superficie de ataque mínima)
rm -f "${TARGET_DIR}/etc/init.d/S50crond"

# Herramientas que RAUC arrastra como dependencias pero que este producto no usa:
#  - fw_printenv/fw_setenv (uboot-tools): el backend A/B es propio (bootstate.txt)
#  - herramientas de squashfs: solo se aceptan paquetes verity, que monta el kernel
#  - utilidades de GLib (gdbus, gio...): RAUC solo usa la biblioteca
# Al quitarlas desaparecen del SBOM del producto (se calcula a partir de los ficheros reales).
rm -f "${TARGET_DIR}"/usr/sbin/fw_printenv "${TARGET_DIR}"/usr/sbin/fw_setenv \
	"${TARGET_DIR}"/usr/bin/mksquashfs "${TARGET_DIR}"/usr/bin/unsquashfs \
	"${TARGET_DIR}"/usr/bin/sqfscat "${TARGET_DIR}"/usr/bin/sqfstar \
	"${TARGET_DIR}"/usr/bin/gdbus "${TARGET_DIR}"/usr/bin/gio "${TARGET_DIR}"/usr/bin/gsettings \
	"${TARGET_DIR}"/usr/bin/gapplication "${TARGET_DIR}"/usr/bin/gresource \
	"${TARGET_DIR}"/usr/bin/gi-compile-repository "${TARGET_DIR}"/etc/fw_env.config
