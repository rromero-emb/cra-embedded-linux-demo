#!/usr/bin/env python3
"""Prueba del restablecimiento de fábrica (CRA Anexo I, parte I, 2(m)).
Se crean datos del usuario, se pide el restablecimiento y se comprueba que tras el reinicio:
los datos ya no existen, las claves de host SSH son nuevas y el estado A/B es el de fábrica.
Uso: test_factory_reset.py [output_dir]
"""
import os, re, subprocess, sys, time
from qemu import Qemu

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "output")
KEY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "keys", "dev_ssh")
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not ok else ""), flush=True)


def ssh(vm, cmd):
    base = ["ssh", "-i", KEY, "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=no", "-o", "LogLevel=ERROR",
            "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10", "-p", str(vm.ssh_port), "admin@127.0.0.1"]
    for _ in range(10):
        r = subprocess.run(base + [cmd], capture_output=True, text=True, timeout=60)
        if r.returncode != 255:
            return r
        time.sleep(3)
    return r


def host_key(vm):
    r = subprocess.run(["ssh-keyscan", "-p", str(vm.ssh_port), "-t", "ed25519,ecdsa,rsa", "127.0.0.1"],
                       capture_output=True, text=True, timeout=30)
    return sorted(l.split()[-1] for l in r.stdout.splitlines() if l and not l.startswith("#"))


with Qemu(os.path.join(OUT, "images"), echo=False) as vm:
    check("arranque", vm.wait_for() is True)
    ssh(vm, "echo 'dato privado del usuario' > /data/updates/incoming/mis-datos.txt")
    before = host_key(vm)
    check("datos del usuario creados", ssh(vm, "cat /data/updates/incoming/mis-datos.txt").returncode == 0)
    since = vm.mark()
    ssh(vm, "touch /data/updates/incoming/factory-reset.request")
    rebooted = vm.wait_for(since=since, timeout=300)
    tail = vm.log[since:]
    check("restablecimiento ejecutado y reinicio", bool(rebooted) and "CRA: datos borrados" in tail)
    check("los datos del usuario ya no existen", ssh(vm, "test -e /data/updates/incoming/mis-datos.txt").returncode == 1)
    after = host_key(vm)
    check("claves de host SSH nuevas (las anteriores se destruyeron)", before and after and before != after)
    st = re.findall(r"estado A/B: (.*)", tail)
    check("estado A/B de fábrica", bool(st) and "BOOT_A_LEFT=3" in st[-1] and "BOOT_B_LEFT=3" in st[-1], st[-1:] )

print(f"\n{sum(results)}/{len(results)} comprobaciones superadas")
sys.exit(0 if all(results) else 1)
