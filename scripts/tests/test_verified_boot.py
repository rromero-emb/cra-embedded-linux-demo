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
# Con A/B: rechaza el FIT de A, lo marca como malo, reinicia, rechaza el de B y se apaga.
work = tempfile.mkdtemp(prefix="cra-vboot-")
results = []


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> código {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def partition(disk, n):
    """(offset, tamaño) en bytes de la partición `n` (1-4) de la tabla MBR."""
    with open(disk, "rb") as f:
        f.seek(0x1BE + 16 * (n - 1) + 8)
        lba, sectors = struct.unpack("<II", f.read(8))
    return lba * 512, sectors * 512


FIT_OFFSET = 136 * 1024 * 1024  # offset fijo del FIT dentro de cada slot (scripts/mk-slot-image.sh)


def disk_with_fit(name, fit_path):
    """Copia del disco con el FIT sustituido por `fit_path` en los DOS slots (A y B):
    si solo se alterase uno, U-Boot lo marcaría como malo y arrancaría el otro (correcto,
    pero entonces no se probaría el rechazo)."""
    d = os.path.join(work, name)
    os.makedirs(d)
    for f in ("u-boot.bin", "u-boot-control.dtb"):
        os.symlink(os.path.abspath(os.path.join(IMAGES, f)), os.path.join(d, f))
    disk = os.path.join(d, "disk.img")
    shutil.copyfile(os.path.join(IMAGES, "disk.img"), disk)
    data = open(fit_path, "rb").read()
    with open(disk, "r+b") as dst:
        for n in (1, 2):
            off, _ = partition(disk, n)
            dst.seek(off + FIT_OFFSET)
            dst.write(data + b"\0" * 4096)  # borra la cabecera del FIT anterior si el nuevo es más corto
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
        r = vm.wait_for(ok=REJECTED, fail=BOOTED, timeout=240)
    why = [l.strip() for l in vm.log.splitlines() if re.search(r"error|Bad|Failed|Wrong|Unknown|Verif|rsa4096", l, re.I)]
    ok = r is True
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {title}")
    slots = re.findall(r"CRA: FIT del slot ([AB]) rechazado", vm.log)
    if slots:
        print(f"         slots rechazados: {', '.join(slots)}")
    for l in why[:4]:
        print(f"         U-Boot: {l}")


try:
    # 1) Un byte del kernel cambiado dentro del FIT bueno
    fit = open(os.path.join(IMAGES, "fitImage"), "rb").read()  # FIT bueno (el mismo que va en el slot)
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
