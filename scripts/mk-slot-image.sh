#!/bin/sh
# Construye la imagen de un slot (lo que RAUC escribe en la partición A o B):
#
#   0 MiB ─ ext4 de solo lectura (128 MiB) ─ 128 MiB ─ árbol de hashes dm-verity ─ 136 MiB ─ FIT firmado (≤ 24 MiB) ─ 160 MiB
#
# El root hash de dm-verity va en el device tree del FIT (/chosen/cra,verity), que está firmado:
# U-Boot lo lee después de verificar la firma y se lo pasa al kernel (dm-mod.create).
# El FIT queda fuera de la zona protegida por dm-verity para evitar la dependencia circular.
#
# Uso: mk-slot-image.sh <rootfs.ext4> <Image> <machine.dtb> <fit.its> <dir-claves-fit> <salida-dir> [control.dtb]
#   Con control.dtb, mkimage inserta en él la clave pública (required=conf).
#   Necesita HOST_DIR (herramientas de Buildroot: veritysetup, mkimage, fdtput).
set -eu
ROOTFS="$1"; KIMAGE="$2"; MDTB="$3"; ITS="$4"; FITKEYS="$5"; OUT="$6"; CONTROL="${7:-}"
: "${HOST_DIR:?HOST_DIR no definido}"
SLOT_MIB=160; DATA_BYTES=134217728; FIT_OFF_MIB=136; FIT_MAX_BYTES=25165824

SIZE=$(stat -L -c %s "$ROOTFS")
[ "$SIZE" -eq "$DATA_BYTES" ] || { echo "ERROR: el rootfs debe medir 128 MiB ($SIZE)" >&2; exit 1; }
BLOCKS=$((SIZE / 4096))
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT

# 1) ext4 + árbol de hashes en la misma imagen (hashes a partir de los 128 MiB)
cp "$ROOTFS" "$OUT/slot.img"
truncate -s "${SLOT_MIB}M" "$OUT/slot.img"
"$HOST_DIR/sbin/veritysetup" format --no-superblock --data-blocks="$BLOCKS" --hash-offset="$SIZE" \
	"$OUT/slot.img" "$OUT/slot.img" > "$W/verity.txt"
ROOT_HASH=$(sed -n 's/^Root hash:[[:space:]]*//p' "$W/verity.txt")
SALT=$(sed -n 's/^Salt:[[:space:]]*//p' "$W/verity.txt")
[ -n "$ROOT_HASH" ] && [ -n "$SALT" ] || { cat "$W/verity.txt" >&2; exit 1; }

# 2) Device tree del kernel con los parámetros de verity (irá firmado dentro del FIT).
#    restart_on_corruption: un bloque alterado reinicia el equipo (cuenta como intento fallido A/B).
cp "$MDTB" "$W/qemu-cra.dtb"
"$HOST_DIR/bin/fdtput" -t s "$W/qemu-cra.dtb" /chosen cra,verity-sectors "$((SIZE / 512))"
"$HOST_DIR/bin/fdtput" -t s "$W/qemu-cra.dtb" /chosen cra,verity \
	"$BLOCKS $BLOCKS sha256 $ROOT_HASH $SALT 1 restart_on_corruption"

# 3) FIT firmado (kernel + device tree con el root hash)
ln -s "$(readlink -f "$KIMAGE")" "$W/Image"
cp "$ITS" "$W/fit-image.its"
if [ -n "$CONTROL" ]; then
	( cd "$W" && "$HOST_DIR/bin/mkimage" -f fit-image.its -k "$FITKEYS" -K "$(readlink -f "$CONTROL")" -r fitImage ) > /dev/null
else
	( cd "$W" && "$HOST_DIR/bin/mkimage" -f fit-image.its -k "$FITKEYS" fitImage ) > /dev/null
fi
FIT_SIZE=$(stat -c %s "$W/fitImage")
[ "$FIT_SIZE" -le "$FIT_MAX_BYTES" ] || { echo "ERROR: FIT demasiado grande ($FIT_SIZE)" >&2; exit 1; }

# 4) FIT en su offset fijo del slot
dd if="$W/fitImage" of="$OUT/slot.img" bs=1M seek="$FIT_OFF_MIB" conv=notrunc status=none
cp "$W/fitImage" "$OUT/fitImage"
echo "Slot: $OUT/slot.img · root hash $ROOT_HASH · FIT $FIT_SIZE bytes en ${FIT_OFF_MIB} MiB"
