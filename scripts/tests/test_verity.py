#!/usr/bin/env python3
"""Prueba de dm-verity (sesión 6): se altera UN byte de /bin/busybox en el disco del slot A.
El FIT del slot está intacto (su firma es válida): la única defensa es dm-verity.
Esperado: el kernel detecta el bloque corrupto al leerlo, reinicia (restart_on_corruption),
U-Boot descuenta intentos de A y, al agotarlos, arranca B (intacto).
Uso: test_verity.py [output_dir]
"""
import os, re, shutil, struct, subprocess, sys, tempfile
from qemu import Qemu

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "output")
IMAGES, HOST = os.path.join(OUT, "images"), os.path.join(OUT, "host")
work = tempfile.mkdtemp(prefix="cra-verity-")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not ok else ""), flush=True)


def partition(disk, n):
    with open(disk, "rb") as f:
        f.seek(0x1BE + 16 * (n - 1) + 8)
        lba, sectors = struct.unpack("<II", f.read(8))
    return lba * 512, sectors * 512


try:
    for f in ("u-boot.bin", "u-boot-control.dtb"):
        os.symlink(os.path.join(IMAGES, f), os.path.join(work, f))
    disk = os.path.join(work, "disk.img")
    shutil.copyfile(os.path.join(IMAGES, "disk.img"), disk)

    # Primer bloque de datos de /bin/busybox dentro del ext4 (bloques de 4 KiB)
    out = subprocess.run([os.path.join(HOST, "sbin", "debugfs"), "-R", "blocks /bin/busybox",
                          os.path.join(IMAGES, "rootfs.ext2")], capture_output=True, text=True).stdout
    block = int(out.split()[0])
    off_a, _ = partition(disk, 1)
    pos = off_a + block * 4096 + 1234
    with open(disk, "r+b") as f:
        f.seek(pos); b = f.read(1); f.seek(pos); f.write(bytes([b[0] ^ 0xFF]))
    print(f"         1 byte alterado en /bin/busybox (bloque {block} del ext4 del slot A)")

    with Qemu(work, echo=False) as vm:
        ok = vm.wait_for(timeout=600)
        log = vm.log
    corrupted = re.findall(r"verity: .*(?:corrupted|data block \d+)", log)
    attempts_a = len(re.findall(r"CRA: slot A", log))
    fit_ok_a = re.search(r"slot A[\s\S]*?rsa4096:cra-dev\+ OK", log) is not None
    slot = re.findall(r"Slot activo\s*: ([AB])", log)
    check("la firma del FIT del slot A sigue siendo válida (el ataque no toca el FIT)", fit_ok_a)
    check("dm-verity detecta el bloque alterado", bool(corrupted), "sin mensaje de verity")
    if corrupted:
        print("         kernel:", corrupted[0].strip()[:150])
    check(f"reinicio y {attempts_a} intentos en A; arranca el slot B intacto", ok and slot and slot[-1] == "B" and attempts_a >= 3,
          f"slot={slot[-1] if slot else None}, intentos A={attempts_a}")
finally:
    shutil.rmtree(work, ignore_errors=True)

print(f"\n{sum(results)}/{len(results)} comprobaciones superadas")
sys.exit(0 if all(results) else 1)
