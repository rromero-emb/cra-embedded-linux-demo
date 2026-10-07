#!/usr/bin/env python3
"""Prueba de arranque: QEMU debe llegar a 'CRA-DEMO: BOOT OK' sin pánico de kernel."""
import os, sys, time
from qemu import Qemu

IMAGES = sys.argv[1] if len(sys.argv) > 1 else "output/images"
start = time.time()
with Qemu(IMAGES) as vm:
    result = vm.wait_for(timeout=int(os.environ.get("BOOT_TIMEOUT", "240")))

if result:
    print(f"\n[PASS] arranque correcto en {time.time() - start:.0f} s")
    sys.exit(0)
print(f"\n[FAIL] {'timeout' if result is None else 'error de arranque'}")
sys.exit(1)
