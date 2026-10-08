#!/usr/bin/env python3
"""Pruebas de actualizaciones A/B (sesión 5), todo en una sola sesión de QEMU (el disco
se conserva entre reinicios):

  1. Paquete firmado por otra CA                -> rechazado, sigue en A
  2. Paquete antiguo, firmado (anti-rollback)   -> rechazado, sigue en A
  3. Paquete nuevo y firmado                    -> se instala en B, reinicia y arranca B
  4. Paquete firmado pero ROTO (init no arranca) -> se instala en A, falla 3 veces y
                                                   U-Boot vuelve solo a B (vuelta atrás)
Uso: test_update.py [output_dir]
"""
import os, re, shutil, subprocess, sys, tempfile, time
from qemu import Qemu

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "output")
IMAGES, HOST = os.path.join(OUT, "images"), os.path.join(OUT, "host")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
KEYS, SSH_KEY = os.path.join(ROOT, "keys", "rauc"), os.path.join(ROOT, "keys", "dev_ssh")
RAUC = os.path.join(HOST, "bin", "rauc")
work = tempfile.mkdtemp(prefix="cra-update-")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not ok else ""), flush=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> código {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def current_build():
    with open(os.path.join(OUT, "target", "usr", "lib", "os-release")) as f:
        return int(re.search(r"^IMAGE_BUILD=(\d+)", f.read(), re.M).group(1))


def make_pki(d):
    """CA + certificado de firma Code Signing (para el 'atacante')."""
    os.makedirs(d)
    run(["openssl", "req", "-batch", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30", "-subj", "/CN=CA atacante",
         "-keyout", f"{d}/ca.key", "-out", f"{d}/ca.crt", "-addext", "basicConstraints=critical,CA:TRUE"])
    run(["openssl", "req", "-batch", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=firma atacante",
         "-keyout", f"{d}/signing.key", "-out", f"{d}/signing.csr"])
    open(f"{d}/ext.cnf", "w").write("basicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=codeSigning\n")
    run(["openssl", "x509", "-req", "-in", f"{d}/signing.csr", "-CA", f"{d}/ca.crt", "-CAkey", f"{d}/ca.key",
         "-CAcreateserial", "-days", "30", "-extfile", f"{d}/ext.cnf", "-out", f"{d}/signing.crt"])
    return d


def broken_rootfs():
    """rootfs con un /sbin/init que termina al instante: el kernel entra en pánico."""
    p = os.path.join(work, "rootfs-roto.ext4")
    shutil.copyfile(os.path.join(IMAGES, "rootfs.ext4"), p)
    init = os.path.join(work, "init")
    open(init, "w").write("#!/bin/sh\necho 'init roto (prueba de vuelta atras)'\nexit 1\n")
    dbg = os.path.join(HOST, "sbin", "debugfs")
    run([dbg, "-w", "-R", "rm /sbin/init", p])
    run([dbg, "-w", "-R", f"write {init} /sbin/init", p])
    run([dbg, "-w", "-R", "set_inode_field /sbin/init mode 0100755", p])
    return p


def bundle(name, version, keys=KEYS, rootfs=None):
    """Paquete RAUC con una imagen de slot completa (ext4 + dm-verity + FIT firmado)."""
    d = os.path.join(work, "b-" + name)
    os.makedirs(d)
    board = os.path.join(ROOT, "br2-external", "board", "qemu-aarch64-cra")
    run([os.path.join(ROOT, "scripts", "mk-slot-image.sh"), rootfs or os.path.join(IMAGES, "rootfs.ext4"),
         os.path.join(IMAGES, "Image"), os.path.join(IMAGES, "qemu-cra.dtb"), os.path.join(board, "fit-image.its"),
         os.path.join(ROOT, "keys", "fit"), d])
    os.remove(os.path.join(d, "fitImage"))
    open(os.path.join(d, "manifest.raucm"), "w").write(
        f"[update]\ncompatible=cra-demo-qemu-aarch64\nversion={version}\n\n"
        "[bundle]\nformat=verity\n\n[image.rootfs]\nfilename=slot.img\n")
    out = os.path.join(work, name + ".raucb")
    run([RAUC, "bundle", f"--cert={keys}/signing.crt", f"--key={keys}/signing.key", d, out])
    return out


class Device:
    def __init__(self, vm):
        self.vm = vm
        self.ssh = ["ssh", "-i", SSH_KEY, "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=10",
                    "-p", str(vm.ssh_port), "admin@127.0.0.1"]

    def sh(self, cmd, stdin=None, timeout=120):
        for _ in range(10):
            r = subprocess.run(self.ssh + [cmd], stdin=stdin, capture_output=True, text=True, timeout=timeout)
            if r.returncode != 255:  # 255 = fallo de conexión SSH: reintentar
                return r
            time.sleep(3)
        return r

    def push(self, path):
        name = os.path.basename(path)
        with open(path, "rb") as f:
            r = self.sh(f"cat > /data/updates/incoming/{name}.part && mv /data/updates/incoming/{name}.part "
                        f"/data/updates/incoming/{name}", stdin=f, timeout=300)
        return r.returncode == 0

    def wait_status(self, name, timeout=300):
        end = time.time() + timeout
        while time.time() < end:
            st = self.sh("cat /data/updates/status 2>/dev/null").stdout.strip()
            if st.endswith(name) and not st.startswith("INSTALANDO"):
                return st.split()[0], self.sh("cat /data/updates/last.log 2>/dev/null").stdout
            time.sleep(3)
        return "TIMEOUT", ""


def slot_after_boot(vm, since, timeout=300, fail=None):
    ok = vm.wait_for(timeout=timeout, since=since, **({} if fail is None else {"fail": fail}))
    m = re.findall(r"Slot activo\s*: ([AB])", vm.log[since:])
    return (m[-1] if (ok and m) else None)


try:
    build = current_build()
    evil = make_pki(os.path.join(work, "evil"))
    b_evil = bundle("ajeno", build + 1, keys=evil)
    b_old = bundle("antiguo", build - 1)
    b_good = bundle("nuevo", build + 1)
    b_bad = bundle("roto", build + 2, rootfs=broken_rootfs())

    with Qemu(IMAGES, echo=False) as vm:
        dev = Device(vm)
        check("arranque inicial en slot A", slot_after_boot(vm, 0) == "A")

        # 1) Otra CA
        dev.push(b_evil)
        st, log = dev.wait_status("ajeno.raucb")
        check("paquete firmado por otra CA -> rechazado", st == "RECHAZADO", st)
        print("         RAUC:", next((l.strip() for l in log.splitlines() if re.search(r"fail|error|unable|not ", l, re.I) and "system status" not in l), log.strip()[-150:]))

        # 2) Anti-rollback
        dev.push(b_old)
        st, log = dev.wait_status("antiguo.raucb")
        check("paquete antiguo (anti-rollback) -> rechazado", st == "RECHAZADO" and "anti-rollback" in log, st)
        print("         RAUC:", next((l.strip() for l in log.splitlines() if "RECHAZADO" in l), log.strip()[-150:]))

        # 3) Actualización buena -> B
        since = vm.mark()
        dev.push(b_good)
        st, _ = dev.wait_status("nuevo.raucb")
        check("paquete nuevo y firmado -> instalado", st == "INSTALADO", st)
        slot = slot_after_boot(vm, since)
        check("tras reiniciar arranca el slot B", slot == "B", slot)

        # 4) Actualización rota -> vuelta atrás automática a B
        since = vm.mark()
        dev.push(b_bad)
        st, _ = dev.wait_status("roto.raucb")
        check("paquete firmado pero roto -> instalado en A", st == "INSTALADO", st)
        # Aquí los pánicos del kernel son lo esperado (init roto): solo es fallo que U-Boot no encuentre slot
        slot = slot_after_boot(vm, since, timeout=600, fail=("CRA: ARRANQUE RECHAZADO",))
        tail = vm.log[since:]
        attempts = len(re.findall(r"CRA: slot A", tail))
        check(f"init roto: {attempts} intentos en A y vuelta atrás automática a B", slot == "B" and attempts >= 3,
              f"slot={slot}, intentos A={attempts}")
        st = re.findall(r"CRA: slot [AB] \(intentos restantes[^)]*\)", tail)
        print("         U-Boot:", " | ".join(st[-5:]))
finally:
    shutil.rmtree(work, ignore_errors=True)

print(f"\n{sum(results)}/{len(results)} comprobaciones superadas")
sys.exit(0 if all(results) else 1)
