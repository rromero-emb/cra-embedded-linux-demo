#!/usr/bin/env python3
"""Prueba de arranque: QEMU debe llegar a 'CRA-DEMO: BOOT OK' sin pánico de kernel."""
import os, subprocess, sys, time

IMAGES = sys.argv[1] if len(sys.argv) > 1 else "output/images"
TIMEOUT = int(os.environ.get("BOOT_TIMEOUT", "240"))
OK, FAIL = "CRA-DEMO: BOOT OK", ("Kernel panic", "Bad Linux ARM64 Image", "Wrong Image")

cmd = [os.path.join(os.path.dirname(__file__), "..", "run-qemu.sh"), IMAGES]
p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
os.set_blocking(p.stdout.fileno(), False)
log, start, result = b"", time.time(), None
try:
    while time.time() - start < TIMEOUT and result is None:
        chunk = p.stdout.read() or b""
        if chunk:
            sys.stdout.write(chunk.decode(errors="replace")); sys.stdout.flush()
            log += chunk
            text = log.decode(errors="replace")
            if OK in text:
                result = True
            elif any(f in text for f in FAIL):
                result = False
        elif p.poll() is not None:
            result = False
        else:
            time.sleep(0.2)
finally:
    p.kill(); p.wait()

if result:
    print(f"\n[PASS] arranque correcto en {time.time() - start:.0f} s")
    sys.exit(0)
print(f"\n[FAIL] {'timeout' if result is None else 'error de arranque'}")
sys.exit(1)
