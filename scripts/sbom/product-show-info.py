#!/usr/bin/env python3
"""Filtra la salida de `make show-info` para quedarse con lo que va DENTRO del producto.

El CRA pide el SBOM de los componentes del producto:
  - Se excluyen las herramientas de host (solo sirven para compilar: SBOM de compilación aparte).
  - Se excluyen los paquetes de target cuyos ficheros ya no están en la imagen (por ejemplo,
    herramientas eliminadas en post-build), usando build/packages-file-list.txt de Buildroot.
  - El kernel y el bootloader se mantienen siempre: van en el FIT y en el firmware, no en el rootfs.
Uso: make show-info | product-show-info.py <output_dir> > product-show-info.json
"""
import collections, json, os, sys

out = sys.argv[1] if len(sys.argv) > 1 else "output"
target = os.path.join(out, "target")
ALWAYS = {"linux", "uboot"}

files = collections.defaultdict(list)
with open(os.path.join(out, "build", "packages-file-list.txt")) as f:
    for line in f:
        pkg, _, path = line.rstrip("\n").partition(",")
        files[pkg].append(path)

info = json.load(sys.stdin)
keep, dropped = set(), []
for k, v in info.items():
    if v.get("type") != "target":
        continue
    if k in ALWAYS or not files.get(k) or any(os.path.lexists(os.path.join(target, p)) for p in files[k]):
        keep.add(k)
    else:
        dropped.append(k)
for k in keep:
    for field in ("dependencies", "reverse_dependencies"):
        if field in info[k]:
            info[k][field] = [d for d in info[k][field] if d in keep]
if dropped:
    print("Fuera del SBOM del producto (sus ficheros no están en la imagen):", ", ".join(sorted(dropped)), file=sys.stderr)
json.dump({k: info[k] for k in sorted(keep)}, sys.stdout, indent=1)
