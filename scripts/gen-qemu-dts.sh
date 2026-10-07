#!/bin/sh
# Genera el device tree de la máquina QEMU (mismas opciones que run-qemu.sh) para usarlo
# como device tree INTEGRADO en U-Boot (donde va la clave pública de verificación) y dentro
# del FIT firmado para el kernel. Se eliminan las semillas aleatorias que QEMU genera en cada
# arranque: congeladas en un fichero serían idénticas en todos los arranques. U-Boot añade una
# kaslr-seed nueva en cada arranque desde virtio-rng (fdt_kaslrseed).
set -eu
OUT="${1:-br2-external/board/qemu-aarch64-cra/qemu-cra.dts}"
TMP="$(mktemp -d)"
qemu-system-aarch64 -M virt-7.2,acpi=off,dumpdtb="$TMP/virt.dtb" -cpu cortex-a53 -smp 2 -m 512 -nographic >/dev/null
dtc -q -I dtb -O dts "$TMP/virt.dtb" | grep -vE '^\s*(rng-seed|kaslr-seed) = ' > "$TMP/virt.dts"
{
	echo "// Generado por scripts/gen-qemu-dts.sh a partir de: qemu-system-aarch64 -M virt-7.2,acpi=off -cpu cortex-a53 -smp 2 -m 512 (sin ACPI: con -bios y ACPI, QEMU cambia el GPIO PL061 por ACPI GED)"
	echo "// QEMU $(qemu-system-aarch64 --version | head -1 | awk '{print $4}'). Sin rng-seed/kaslr-seed (los pone U-Boot en cada arranque)."
	cat "$TMP/virt.dts"
} > "$OUT"
rm -rf "$TMP"
echo "Device tree: $OUT"
