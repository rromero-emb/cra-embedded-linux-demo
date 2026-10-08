#!/usr/bin/env python3
"""Pruebas de endurecimiento (sesión 2).

Estáticas, sobre output/target: cuentas, claves, servicios, permisos y flags de compilación.
Dinámicas, con el equipo arrancado en QEMU: cortafuegos, puertos, SSH solo con clave, sysctl.
Uso: test_hardening.py [output_dir]
"""
import glob, os, re, stat, subprocess, sys
from qemu import Qemu

OUT = sys.argv[1] if len(sys.argv) > 1 else "output"
TARGET, IMAGES = os.path.join(OUT, "target"), os.path.join(OUT, "images")
KEY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "keys", "dev_ssh")
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not ok else ""))


def readelf(path, *args):
    return subprocess.run(["readelf", "-W", *args, path], capture_output=True, text=True).stdout


def is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


# ---------------- Estáticas ----------------
print("== Comprobaciones estáticas (output/target) ==")
shadow = dict(l.split(":")[:2] for l in open(os.path.join(TARGET, "etc/shadow")) if ":" in l)
check("root sin contraseña utilizable", shadow.get("root", "") in ("*", "!", "!!") or shadow.get("root", "").startswith("!"),
      shadow.get("root"))
check("ninguna cuenta con contraseña vacía", all(v != "" for v in shadow.values()),
      [u for u, v in shadow.items() if v == ""])
check("clave SSH autorizada para admin",
      os.path.isfile(os.path.join(TARGET, "home/admin/.ssh/authorized_keys")))
check("sin claves de host SSH dentro de la imagen",
      not glob.glob(os.path.join(TARGET, "etc/dropbear/dropbear_*_host_key")))
check("dropbear: sin contraseñas ni root",
      all(f in open(os.path.join(TARGET, "etc/default/dropbear")).read() for f in ("-s", "-w", "-g")))
check("crond deshabilitado", not os.path.exists(os.path.join(TARGET, "etc/init.d/S50crond")))

# Permisos: se leen de la IMAGEN FINAL (rootfs.ext2) con debugfs, porque los modos definitivos
# (setuid, sticky...) los aplica fakeroot al generarla y no aparecen en output/target.
DEBUGFS = [os.path.join(OUT, "host/sbin/debugfs"), "-f", "-", os.path.join(IMAGES, "rootfs.ext2")]


def image_entries():
    """Recorre la imagen y devuelve (ruta, modo) de cada entrada, sin extraerla."""
    pending, seen = ["/"], []
    while pending:
        batch, pending = pending, []
        out = subprocess.run(DEBUGFS, input="".join(f"ls -p {d}\n" for d in batch),
                             capture_output=True, text=True).stdout
        cur = None
        for line in out.splitlines():
            if line.startswith("debugfs: ls -p "):
                cur = line[len("debugfs: ls -p "):].rstrip("/") or ""
                continue
            f = line.split("/")
            if cur is None or len(f) < 7 or f[5] in (".", ".."):
                continue
            path, mode = f"{cur}/{f[5]}", int(f[2], 8)
            seen.append((path, mode))
            if stat.S_ISDIR(mode):
                pending.append(path)
    return seen


world_writable, setuid = [], []
entries = image_entries()
for path, mode in entries:
    if stat.S_ISLNK(mode):
        continue
    if mode & stat.S_IWOTH and not (stat.S_ISDIR(mode) and mode & stat.S_ISVTX):
        world_writable.append(path)
    if mode & (stat.S_ISUID | stat.S_ISGID) and stat.S_ISREG(mode):
        setuid.append(path)
check(f"imagen final leída ({len(entries)} entradas)", len(entries) > 100, len(entries))
check("imagen final: sin ficheros escribibles por cualquiera", not world_writable, world_writable[:10])
check("imagen final: sin binarios setuid/setgid", not setuid, setuid)

bad_pie, bad_relro, no_ssp, total = [], [], [], 0
for d in ("bin", "sbin", "usr/bin", "usr/sbin", "usr/libexec"):
    for p in glob.glob(os.path.join(TARGET, d, "*")):
        if os.path.islink(p) or not is_elf(p):
            continue
        total += 1
        rel = "/" + os.path.relpath(p, TARGET)
        hdr, prog, dyn = readelf(p, "-h"), readelf(p, "-l"), readelf(p, "-d")
        syms = readelf(p, "--dyn-syms")
        if "DYN (" not in hdr:
            bad_pie.append(rel)
        if "GNU_RELRO" not in prog or not re.search(r"BIND_NOW|FLAGS_1.*NOW", dyn):
            bad_relro.append(rel)
        if "__stack_chk_fail" not in syms:
            no_ssp.append(rel)
libs_no_relro, nlibs = [], 0
for p in glob.glob(os.path.join(TARGET, "lib", "*.so*")) + glob.glob(os.path.join(TARGET, "usr/lib", "*.so*")):
    if os.path.islink(p) or not is_elf(p):
        continue
    nlibs += 1
    if "GNU_RELRO" not in readelf(p, "-l"):
        libs_no_relro.append("/" + os.path.relpath(p, TARGET))
check(f"bibliotecas con RELRO ({nlibs} revisadas)", not libs_no_relro, libs_no_relro)
check(f"ejecutables PIE ({total} revisados)", not bad_pie, bad_pie)
check("ejecutables con RELRO completo (BIND_NOW)", not bad_relro, bad_relro)
print(f"[INFO] sin referencia a stack protector (normal si no usan buffers en pila): {len(no_ssp)} -> {no_ssp[:8]}")

kcfg = open(glob.glob(os.path.join(OUT, "build/linux-*/.config"))[0]).read()
need = ["CONFIG_RANDOMIZE_BASE=y", "CONFIG_HARDENED_USERCOPY=y", "CONFIG_STRICT_KERNEL_RWX=y",
        "CONFIG_STACKPROTECTOR_STRONG=y", "CONFIG_SECURITY_DMESG_RESTRICT=y", "CONFIG_INIT_ON_ALLOC_DEFAULT_ON=y",
        "# CONFIG_DEVMEM is not set", "# CONFIG_KEXEC is not set", "# CONFIG_PROC_KCORE is not set",
        "# CONFIG_MAGIC_SYSRQ is not set", "CONFIG_NF_TABLES=y", "CONFIG_SECURITY_YAMA=y"]
missing = [o for o in need if o not in kcfg]
check("opciones de endurecimiento del kernel", not missing, missing)

# ---------------- Dinámicas ----------------
print("\n== Comprobaciones con el equipo arrancado (QEMU) ==")
with Qemu(IMAGES, echo=False) as vm:
    booted = vm.wait_for()
    check("arranque", bool(booted), "timeout" if booted is None else "error")
    if booted:
        log = vm.log
        check("cortafuegos: entrada y salida en drop", "entrada=drop salida=drop" in log,
              re.findall(r"Cortafuegos.*", log))
        check("cuenta root bloqueada", re.search(r"Cuenta root\s*: bloqueada", log) is not None)
        check("raíz de solo lectura sobre dm-verity", re.search(r"Rootfs\s*: dm-verity, ro", log) is not None,
              re.findall(r"Rootfs.*", log))
        ports = re.search(r"Puertos TCP\s*: (.*)", log)
        check("solo el puerto 22 escuchando", ports is not None and ports.group(1).split() == ["22"],
              ports.group(1) if ports else "?")

        ssh = ["ssh", "-p", str(vm.ssh_port), "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
               "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
        r = None
        for _ in range(10):  # dropbear puede tardar un poco en generar sus claves de host
            r = subprocess.run(ssh + ["-i", KEY, "-o", "IdentitiesOnly=yes", "admin@127.0.0.1",
                                      "cat /proc/sys/kernel/kptr_restrict /proc/sys/kernel/dmesg_restrict; id -u"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                break
        check("SSH con clave como admin", r.returncode == 0, r.stderr.strip()[-200:])
        if r.returncode == 0:
            check("sysctl kptr_restrict=2 y dmesg_restrict=1", r.stdout.split()[:2] == ["2", "1"], r.stdout.split())
            check("admin no es root", r.stdout.split()[-1] != "0")
        r = subprocess.run(ssh + ["-i", KEY, "-o", "IdentitiesOnly=yes", "root@127.0.0.1", "true"],
                           capture_output=True, text=True, timeout=30)
        check("SSH como root rechazado", r.returncode != 0)
        r = subprocess.run(ssh + ["-v", "-o", "PubkeyAuthentication=no", "admin@127.0.0.1", "true"],
                           capture_output=True, text=True, timeout=30)
        methods = re.findall(r"Authentications that can continue: (\S+)", r.stderr)
        check("el servidor no ofrece autenticación por contraseña",
              r.returncode != 0 and all("password" not in m for m in methods), methods)

passed = sum(results)
print(f"\n{passed}/{len(results)} comprobaciones superadas")
sys.exit(0 if passed == len(results) else 1)
