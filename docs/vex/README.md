# VEX: qué CVE afectan al producto y por qué

Un documento **VEX** (*Vulnerability Exploitability eXchange*) acompaña al SBOM y dice, para cada CVE que aparece en sus componentes, si afecta al producto. Sin él, un SBOM del kernel muestra cientos de CVE que en su mayoría están en código que no se compila.

## Cómo se genera

`make cve` produce `output/sbom/vex.cdx.json` (CycloneDX 1.6) a partir de tres fuentes, de menor a mayor prioridad:

| Fuente | Qué decide |
|---|---|
| NVD (`cve-check` de Buildroot) | lista de CVE candidatas por CPE y versión |
| Análisis automático del kernel (`scripts/sbom/kernel-vex.py`) | con los datos del CNA del kernel ([vulns.git](https://git.kernel.org/pub/scm/linux/security/vulns.git)): si la versión ya está corregida y si los ficheros afectados se compilan en este kernel |
| Análisis manual (`security/vex/triage.json`) | justificación revisada por una persona, con evidencia comprobable |

## Estados

| Estado | Significado |
|---|---|
| `not_affected` | no afecta; siempre con una justificación (`code_not_present`, `code_not_reachable`, `requires_configuration`…) y el detalle |
| `resolved` | corregida en la versión del componente |
| `false_positive` | la CVE no corresponde a este componente (p. ej. fue rechazada por el CNA del kernel) |
| `exploitable` | afecta y hay que actuar |
| `in_triage` | sin analizar todavía (estado por defecto) |

## Reglas para el análisis manual

1. Cada entrada dice **qué se ha comprobado y cómo** (fichero de configuración, objeto compilado, `strings`, sysctl…), para que otra persona pueda repetirlo.
2. `requires_configuration` solo vale si el producto **fija** esa configuración (p. ej. `ioam6_enabled=0` en `/etc/sysctl.d/90-cra-hardening.conf`).
3. Fecha y analista en cada entrada; se revisa en cada versión.
4. Si hay duda, no es `not_affected`.

## Puerta de calidad

`vuln-report.py --fail-on critical`: la CI falla si queda alguna CVE crítica en estado `exploitable` o `in_triage`. El informe legible es `output/sbom/vulnerabilidades.md` y se publica en el resumen de cada ejecución de CI.

## Publicación

El VEX de cada versión se publica junto a su paquete de actualización (Anexo I, Parte II, punto 4): permite a los usuarios y a las autoridades ver no solo qué se ha corregido, sino por qué el resto no les afecta.
