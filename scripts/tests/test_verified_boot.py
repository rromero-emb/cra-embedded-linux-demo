#!/usr/bin/env python3
"""Pruebas de arranque verificado (sesión 4): U-Boot debe RECHAZAR todo lo que no esté
firmado con la clave de arranque. Para cada ataque se crea una copia del disco con
/boot/fitImage sustituido y se comprueba que el kernel nunca llega a ejecutarse.

Ataques: 1 byte del kernel alterado · FIT firmado con otra clave (mismo nombre de clave) ·
FIT sin firma · kernel Image suelto en lugar del FIT.
Uso: test_verified_boot.py [output_dir]
"""
import os, re, shutil, struct, subprocess, sys, tempfile
from qemu import Qemu

OUT = sys.argv[1] if len(sys.argv) > 1 else "output"
OUT = os.path.abspath(OUT)
IMAGES, HOST = os.path.join(OUT, "images"), os.path.join(OUT, "host")
BOARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "br2-external", "board", "qemu-aarch64-cra")
REJECTED, BOOTED = "CRA: ARRANQUE RECHAZADO", ("Starting kernel", "CRA-DEMO: BOOT OK")
work = tempfile.mkdtemp(prefix="cra-vboot-")
results = []


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def partition1(disk):
    """(offset, tamaño) en bytes de la partición 1 de la tabla MBR."""
    with open(disk, "rb") as f:
        f.seek(0x1BE + 8)
        lba, sectors = struct.unpack("<II", f.read(8))
    return lba * 512, sectors * 512


def disk_with_fit(name, fit_path):
    """Copia del disco con /boot/fitImage sustituido por `fit_path`."""
    d = os.path.join(work, name)
    os.makedirs(d)
    for f in ("u-boot.bin", "u-boot-control.dtb"):
        os.symlink(os.path.abspath(os.path.join(IMAGES, f)), os.path.join(d, f))
    disk = os.path.join(d, "disk.img")
    shutil.copyfile(os.path.join(IMAGES, "disk.img"), disk)
    off, size = partition1(disk)
    part = os.path.join(work, name + ".ext4")
    with open(disk, "rb") as src, open(part, "wb") as dst:
        src.seek(off); dst.write(src.read(size))
    run([os.path.join(HOST, "sbin/debugfs"), "-w", "-R", "rm /boot/fitImage", part])
    run([os.path.join(HOST, "sbin/debugfs"), "-w", "-R", f"write {fit_path} /boot/fitImage", part])
    with open(part, "rb") as src, open(disk, "r+b") as dst:
        dst.seek(off); dst.write(src.read())
    return d


def mkfit(name, keydir=None, unsigned=False):
    """Crea un FIT con el mismo contenido que el bueno: firmado con `keydir` o sin firma."""
    d = os.path.join(work, "fit-" + name)
    os.makedirs(d)
    for f in ("Image", "qemu-cra.dtb"):
        os.symlink(os.path.abspath(os.path.join(IMAGES, f)), os.path.join(d, f))
    its = open(os.path.join(BOARD, "fit-image.its")).read()
    if unsigned:
        its = re.sub(r"signature-1 \{.*?\};\n", "", its, flags=re.S)
    open(os.path.join(d, "fit.its"), "w").write(its)
    cmd = [os.path.join(HOST, "bin/mkimage"), "-f", "fit.its"] + (["-k", keydir] if keydir else []) + ["fitImage"]
    run(cmd, cwd=d)
    return os.path.join(d, "fitImage")


def expect_rejected(title, images_dir):
    with Qemu(images_dir, echo=False) as vm:
        r = vm.wait_for(ok=REJECTED, fail=BOOTED, timeout=120)
    why = [l.strip() for l in vm.log.splitlines() if re.search(r"error|Bad|Failed|Wrong|Unknown|Verif|rsa4096", l, re.I)]
    ok = r is True
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {title}")
    for l in why[:4]:
        print(f"         U-Boot: {l}")


try:
    # 1) Un byte del kernel cambiado dentro del FIT bueno
    fit = open(os.path.join(IMAGES, "fitImage"), "rb").read()
    data = bytearray(fit)
    data[len(data) // 2] ^= 0xFF
    p = os.path.join(work, "fit-tampered"); open(p, "wb").write(data)
    expect_rejected("1 byte del kernel alterado -> rechazado", disk_with_fit("tampered", p))

    # 2) Atacante con su propia clave RSA-4096 llamada igual (cra-dev)
    evil = os.path.join(work, "evil-keys"); os.makedirs(evil)
    run(["openssl", "genrsa", "-out", os.path.join(evil, "cra-dev.key"), "4096"])
    run(["openssl", "req", "-batch", "-new", "-x509", "-subj", "/CN=atacante",
         "-key", os.path.join(evil, "cra-dev.key"), "-out", os.path.join(evil, "cra-dev.crt")])
    expect_rejected("FIT firmado con otra clave (mismo nombre) -> rechazado",
                    disk_with_fit("evil", mkfit("evil", keydir=evil)))

    # 3) FIT sin firma
    expect_rejected("FIT sin firma -> rechazado", disk_with_fit("unsigned", mkfit("unsigned", unsigned=True)))

    # 4) Kernel suelto (sin FIT)
    expect_rejected("kernel Image suelto (sin FIT) -> rechazado",
                    disk_with_fit("raw", os.path.join(IMAGES, "Image")))
finally:
    shutil.rmtree(work, ignore_errors=True)

print(f"\n{sum(results)}/{len(results)} ataques rechazados")
sys.exit(0 if all(results) else 1)
