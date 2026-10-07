#!/usr/bin/env python3
"""Añade al SBOM las bibliotecas de la toolchain externa que viajan en el producto.

Buildroot declara la toolchain externa como un único componente sin CPE, así que
glibc (y sus CVE) quedaría fuera del análisis. Leemos la versión real de lo que hay
en output/target y la añadimos como componente con su CPE.
Uso: add-runtime-components.py <sbom.cdx.json> <target_dir> <host_dir>
"""
import glob, json, os, re, subprocess, sys

sbom_path, target, host = sys.argv[1:4]
sbom = json.load(open(sbom_path))
added = []

libc = os.path.join(target, "lib/libc.so.6")
if os.path.exists(libc):
    m = re.search(rb"GNU C Library[^\n]*?version (\d+\.\d+)", open(libc, "rb").read())
    if m:
        v = m.group(1).decode()
        added.append({"bom-ref": "glibc", "type": "library", "name": "glibc", "version": v,
                      "cpe": f"cpe:2.3:a:gnu:glibc:{v}:*:*:*:*:*:*:*",
                      "purl": f"pkg:generic/gnu/glibc@{v}",
                      "licenses": [{"license": {"id": "LGPL-2.1-or-later"}}],
                      "description": "Biblioteca C (de la toolchain externa Bootlin)"})

gcc = glob.glob(os.path.join(host, "bin/*-linux-gcc"))
if gcc and glob.glob(os.path.join(target, "lib/libgcc_s.so*")):
    v = subprocess.run([gcc[0], "-dumpfullversion"], capture_output=True, text=True).stdout.strip()
    # Sin CPE a propósito: las CVE de gcc son del compilador, no de libgcc/libatomic (evita falsos positivos)
    added.append({"bom-ref": "gcc-runtime", "type": "library", "name": "gcc-runtime", "version": v,
                  "purl": f"pkg:generic/gnu/gcc-runtime@{v}",
                  "licenses": [{"license": {"id": "GPL-3.0-with-GCC-exception"}}],
                  "description": "libgcc_s y libatomic (de la toolchain externa Bootlin)"})

names = {c["name"] for c in sbom["components"]}
sbom["components"] += [c for c in added if c["name"] not in names]
for d in sbom.get("dependencies", []):
    if d.get("ref") == "toolchain-external-bootlin":
        d.setdefault("dependsOn", []).extend(c["bom-ref"] for c in added if c["bom-ref"] not in d.get("dependsOn", []))
json.dump(sbom, open(sbom_path, "w"), indent=1)
print("Añadidos al SBOM:", ", ".join(f'{c["name"]} {c["version"]}' for c in added) or "nada")
