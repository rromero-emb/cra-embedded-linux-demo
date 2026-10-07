#!/usr/bin/env python3
"""Aplica el análisis VEX al SBOM con vulnerabilidades y genera informe + documento VEX.

Entrada : SBOM CycloneDX enriquecido por cve-check y security/vex/triage.json
Salida  : vex.cdx.json (CycloneDX solo con vulnerabilidades y su análisis),
          report.md (resumen legible) y código de salida 1 si hay vulnerabilidades
          explotables sin analizar con severidad >= --fail-on (puerta de calidad en CI).
"""
import argparse, collections, datetime, json, sys

SEV_ORDER = ["none", "info", "low", "medium", "high", "critical", "unknown"]


def severity(v):
    """Mayor severidad de las puntuaciones CVSS que trae la vulnerabilidad."""
    sevs = [r.get("severity", "unknown").lower() for r in v.get("ratings", [])] or ["unknown"]
    known = [s for s in sevs if s != "unknown"]
    return max(known, key=SEV_ORDER.index) if known else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sbom")
    ap.add_argument("--triage", action="append", help="fichero(s) de análisis; el primero tiene prioridad")
    ap.add_argument("--vex-out", required=True)
    ap.add_argument("--report-out", required=True)
    ap.add_argument("--fail-on", default="critical", choices=SEV_ORDER[:6] + ["never"])
    a = ap.parse_args()

    sbom = json.load(open(a.sbom))
    triage = []
    for t in reversed(a.triage or ["security/vex/triage.json"]):  # el primero (manual) pisa a los siguientes
        triage += json.load(open(t)).get("statements", [])
    comps = {c["bom-ref"]: f'{c["name"]} {c.get("version", "")}'.strip() for c in sbom.get("components", [])}
    rules = {}
    for t in triage:
        rules[(t["id"], t.get("component", "*"))] = t

    vulns, rows = [], []
    for v in sbom.get("vulnerabilities", []):
        refs = [x["ref"] for x in v.get("affects", [])]
        state = v.get("analysis", {}).get("state", "in_triage")
        rule = next((rules[k] for k in [(v["id"], comps.get(r, r).split()[0]) for r in refs] + [(v["id"], "*")]
                     if k in rules), None)
        if rule:
            v["analysis"] = {k: rule[k] for k in ("state", "justification", "response", "detail") if k in rule}
            state = rule["state"]
        vulns.append(v)
        for r in refs:
            rows.append({"id": v["id"], "component": comps.get(r, r), "severity": severity(v),
                         "state": state, "triaged": bool(rule)})

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = sbom.get("metadata", {})
    vex = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
           "metadata": {"timestamp": now, "component": meta.get("component", {})},
           "components": sbom.get("components", []), "vulnerabilities": vulns}
    json.dump(vex, open(a.vex_out, "w"), indent=1)

    open_rows = [r for r in rows if r["state"] in ("exploitable", "in_triage")]
    by_comp = collections.defaultdict(collections.Counter)
    for r in open_rows:
        by_comp[r["component"]][r["severity"]] += 1
    states = collections.Counter(r["state"] for r in rows)
    fail_idx = SEV_ORDER.index(a.fail_on) if a.fail_on != "never" else 99
    blocking = [r for r in open_rows if not r["triaged"] and r["severity"] != "unknown"
                and SEV_ORDER.index(r["severity"]) >= fail_idx]

    with open(a.report_out, "w") as f:
        f.write(f"# Informe de vulnerabilidades – {meta.get('component', {}).get('name', '')} "
                f"{meta.get('component', {}).get('version', '')}\n\n")
        f.write(f"Generado: {now} · Fuente: NVD (vía cve-check de Buildroot) + análisis VEX propio\n\n")
        f.write("| Estado | Nº |\n|---|---|\n" + "".join(f"| {s} | {n} |\n" for s, n in states.most_common()))
        f.write("\n## Abiertas por componente (exploitable / in_triage)\n\n| Componente | Crítica | Alta | Media | Baja | Sin puntuar |\n|---|---|---|---|---|---|\n")
        for c, cnt in sorted(by_comp.items(), key=lambda kv: -sum(kv[1].values())):
            f.write(f"| {c} | {cnt['critical']} | {cnt['high']} | {cnt['medium']} | {cnt['low']} | {cnt['unknown']} |\n")
        f.write(f"\n## Puerta de calidad (severidad ≥ {a.fail_on}, sin analizar): {len(blocking)}\n\n")
        for r in sorted(blocking, key=lambda r: (-SEV_ORDER.index(r["severity"]), r["id"]))[:50]:
            f.write(f"- {r['id']} · {r['component']} · {r['severity']}\n")

    print(open(a.report_out).read())
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
