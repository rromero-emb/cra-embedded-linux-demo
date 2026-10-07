#!/usr/bin/env python3
"""Filtra la salida de `make show-info` para quedarse con lo que va DENTRO del producto.

El CRA pide el SBOM de los componentes del producto. Las herramientas de host (cmake,
autoconf...) solo se usan para compilar: se documentan aparte (SBOM de compilación).
Uso: make show-info | product-show-info.py > product-show-info.json
"""
import json, sys

info = json.load(sys.stdin)
keep = {k for k, v in info.items() if v.get("type") == "target"}
for k in keep:
    for field in ("dependencies", "reverse_dependencies"):
        if field in info[k]:
            info[k][field] = [d for d in info[k][field] if d in keep]
json.dump({k: info[k] for k in sorted(keep)}, sys.stdout, indent=1)
