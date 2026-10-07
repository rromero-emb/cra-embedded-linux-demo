#!/usr/bin/env python3
"""Análisis automático (VEX) de las CVE del kernel con los datos oficiales del kernel CNA.

NVD asocia las CVE del kernel a rangos de versión muy amplios. Para cada CVE del kernel
presente en el SBOM, este script usa el repositorio oficial linux/security/vulns.git para:
  1. Ver si la CVE ya está corregida en nuestra versión de la rama (p. ej. 6.12.N)
     o si se introdujo después  -> state "resolved" / "not_affected".
  2. Ver si alguno de los ficheros afectados (programFiles) está COMPILADO en nuestro
     kernel (existe el .o en el directorio de compilación). Si no -> "not_affected",
     justificación "code_not_present".
El resto queda abierto ("in_triage") para análisis manual.

Uso: kernel-vex.py <sbom-vuln.cdx.json> <vulns_repo> <linux_build_dir> -o kernel-triage.json
"""
import argparse, collections, glob, json, os, re, sys


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) + (0,) * (3 - len(re.findall(r"\d+", v)[:3]))


def version_status(record, ver):
    """Devuelve 'fixed', 'not_introduced', 'affected' o 'unknown' para la versión `ver`."""
    V, branch = vtuple(ver), ".".join(ver.split(".")[:2])
    seen = False
    for aff in record["containers"]["cna"].get("affected", []):
        for e in aff.get("versions", []):
            if e.get("versionType") not in (None, "semver", "original_commit_for_fix"):
                continue
            seen = True
            if e.get("status") != "unaffected":
                continue
            lo, lt, le = e.get("version", ""), e.get("lessThan"), e.get("lessThanOrEqual")
            if lo == "0" and lt and V < vtuple(lt):
                return "not_introduced"
            if le and le.startswith(branch + ".") and V >= vtuple(lo):
                return "fixed"
            if le == "*" and V >= vtuple(lo):
                return "fixed"
    return "affected" if seen else "unknown"


def compiled(build_dir, path):
    """True/False si se puede saber si el fichero acaba en el kernel; None si no (conservador)."""
    if path.endswith((".c", ".S")):
        return os.path.exists(os.path.join(build_dir, path.rsplit(".", 1)[0] + ".o"))
    if path.endswith(".h"):
        # Cabeceras públicas (include/, arch/*/include/): pueden usarse desde cualquier parte.
        if path.startswith("include/") or "/include/" in path:
            return None
        # Cabecera privada de un subsistema: solo cuenta si se compiló algo en su carpeta.
        return bool(glob.glob(os.path.join(build_dir, os.path.dirname(path), "*.o")))
    return None  # Kconfig, Makefile, scripts...: no se puede descartar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sbom"); ap.add_argument("vulns"); ap.add_argument("build_dir")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    sbom = json.load(open(a.sbom))
    kernel = next(c for c in sbom["components"] if c["name"] == "linux")
    kver, kref = kernel["version"], kernel["bom-ref"]
    index = {os.path.basename(p)[:-5]: p for p in glob.glob(os.path.join(a.vulns, "cve/published/*/CVE-*.json"))}
    rejected = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(a.vulns, "cve/rejected/*/CVE-*.json"))}

    out, stats = [], collections.Counter()
    for v in sbom.get("vulnerabilities", []):
        if kref not in [x["ref"] for x in v.get("affects", [])]:
            continue
        cid = v["id"]
        if cid in rejected:
            stats["rejected"] += 1
            out.append({"id": cid, "component": "linux", "state": "false_positive",
                        "detail": "CVE rechazada por el kernel CNA (cve/rejected en vulns.git)."})
            continue
        if cid not in index:
            stats["sin datos del kernel CNA"] += 1
            continue
        rec = json.load(open(index[cid]))
        st = version_status(rec, kver)
        if st in ("fixed", "not_introduced"):
            stats[f"versión: {st}"] += 1
            out.append({"id": cid, "component": "linux", "state": "resolved" if st == "fixed" else "not_affected",
                        **({} if st == "fixed" else {"justification": "code_not_present"}),
                        "detail": f"Según el kernel CNA, la CVE {'está corregida' if st == 'fixed' else 'no existe'} en {kver}."})
            continue
        files = sorted({f for aff in rec["containers"]["cna"].get("affected", []) for f in aff.get("programFiles", [])})
        built = {f: compiled(a.build_dir, f) for f in files}
        if files and not any(built.values()) and all(b is False for b in built.values()):
            stats["código no compilado"] += 1
            out.append({"id": cid, "component": "linux", "state": "not_affected", "justification": "code_not_present",
                        "detail": "Ninguno de los ficheros afectados está compilado en este kernel: " + ", ".join(files[:6])})
        else:
            stats["abierta (compilado o sin poder descartar)"] += 1

    json.dump({"_doc": f"Generado automáticamente para linux {kver}. No editar a mano.", "statements": out},
              open(a.out, "w"), indent=1)
    total = sum(stats.values())
    print(f"Kernel {kver}: {total} CVE analizadas")
    for k, n in stats.most_common():
        print(f"  {n:5d}  {k}")


if __name__ == "__main__":
    main()
