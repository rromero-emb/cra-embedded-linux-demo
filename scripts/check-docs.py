#!/usr/bin/env python3
"""Comprueba que la documentación de cumplimiento no se queda desfasada:
  - la matriz del Anexo I cubre todos los puntos (Parte I 1, 2(a)-(m); Parte II 1-8);
  - toda ruta citada entre comillas invertidas en docs/ y SECURITY.md existe en el repo;
  - toda prueba citada en la matriz se ejecuta en `make test`.
Uso: check-docs.py
"""
import glob, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
errors = []

matrix = open("docs/annex-i-matrix.md").read()
part1, part2 = matrix.split("## Parte II", 1)
for letter in "abcdefghijklm":
    if not re.search(rf"^### 2\({letter}\) ", part1, re.M):
        errors.append(f"matriz: falta Parte I 2({letter})")
if not re.search(r"^### \(1\) ", part1, re.M):
    errors.append("matriz: falta Parte I (1)")
for n in range(1, 9):
    if not re.search(rf"^\| \({n}\) \|", part2, re.M):
        errors.append(f"matriz: falta Parte II ({n})")

# Rutas del repo citadas (se ignoran las del equipo y las de output/, que se generan al compilar)
PREFIXES = ("docs/", "scripts/", "security/", "br2-external/", ".github/", ".githooks/", "SECURITY.md")
docs = glob.glob("docs/**/*.md", recursive=True) + ["SECURITY.md", "README.md"]
for doc in docs:
    for ref in re.findall(r"`([^`\s]+)`", open(doc).read()):
        if ref.startswith(PREFIXES) and not os.path.exists(ref):
            errors.append(f"{doc}: no existe `{ref}`")

makefile = open("Makefile").read()
for test in sorted(set(re.findall(r"scripts/tests/(test_\w+\.py)", matrix))):
    if f"scripts/tests/{test}" not in makefile:
        errors.append(f"matriz: {test} no se ejecuta en `make test`")

for e in errors:
    print(f"[FAIL] {e}")
print(f"documentación: {len(docs)} ficheros revisados, {len(errors)} errores")
sys.exit(1 if errors else 0)
