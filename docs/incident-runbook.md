# Procedimiento de notificación (CRA, art. 14)

Qué hacer cuando un producto basado en esta demo tiene una **vulnerabilidad explotada activamente** o sufre un **incidente grave**. La obligación se aplica desde el **11 de septiembre de 2026**, también a productos puestos en el mercado antes.

## Dónde se notifica

- En la **plataforma única de notificación** de ENISA.
- Va dirigida al **CSIRT coordinador** del Estado miembro donde el fabricante tenga su establecimiento principal en la UE; ENISA la recibe al mismo tiempo.
- En España, comprobar la designación oficial vigente del CSIRT coordinador antes del primer caso y anotarla aquí: `____________`.

## Plazos

Los plazos cuentan **desde que el fabricante tiene conocimiento** del hecho.

| | Vulnerabilidad explotada activamente | Incidente grave que afecta a la seguridad del producto |
|---|---|---|
| **Alerta temprana** | 24 h | 24 h (indicando si se sospecha que es malicioso) |
| **Notificación** | 72 h: producto, naturaleza general del exploit y de la vulnerabilidad, medidas correctoras o mitigaciones, sensibilidad de la información | 72 h: naturaleza del incidente, evaluación inicial, medidas correctoras o mitigaciones |
| **Informe final** | como máximo **14 días** después de que haya una medida correctora o mitigación | como máximo **1 mes** después de la notificación |
| | descripción y severidad, información sobre el actor malicioso si se conoce, actualización publicada | descripción detallada, severidad e impacto, causa probable, medidas aplicadas |

Además, tras conocer el hecho, hay que **informar a los usuarios afectados** (y, si procede, al público) del problema y de las medidas que deben tomar.

## Pasos

| # | Cuándo | Qué | Quién / herramienta |
|---|---|---|---|
| 1 | t = 0 | Registrar la entrada (notificación CVD, CISA KEV, aviso del proveedor, telemetría) y la hora | responsable de seguridad |
| 2 | < 4 h | ¿Afecta? Buscar el componente y la versión en el SBOM del producto publicado | `output/sbom/sbom.cdx.json`, `make cve` |
| 3 | < 4 h | ¿Está explotada activamente? (evidencia fiable, no solo una PoC) ¿Es incidente grave? | responsable de seguridad |
| 4 | < 24 h | **Alerta temprana** en la plataforma única | responsable de seguridad |
| 5 | < 72 h | Analizar el impacto en el producto; mitigación inmediata si existe (p. ej. regla de cortafuegos o sysctl en una actualización) | ingeniería |
| 6 | < 72 h | **Notificación** con el análisis | responsable de seguridad |
| 7 | — | Corregir: actualizar el componente, `make`, `make test`, `make cve` | ingeniería, CI |
| 8 | — | Publicar el paquete RAUC firmado, el VEX actualizado y el aviso de seguridad; avisar a los usuarios | ingeniería, `SECURITY.md` |
| 9 | ≤ 14 días tras 8 (vulnerabilidad) o ≤ 1 mes tras 6 (incidente) | **Informe final** | responsable de seguridad |
| 10 | tras cerrar | Lecciones aprendidas: ¿hay que cambiar el modelo de amenazas o las pruebas? | `docs/threat-model.md` |

## Qué preparar antes del primer caso

- [ ] Alta del fabricante en la plataforma única de notificación y persona responsable con suplente (los plazos corren también en fines de semana).
- [ ] CSIRT coordinador identificado.
- [ ] SBOM y VEX de **cada versión publicada** archivados (ver [`support-period.md`](support-period.md)).
- [ ] Canal para avisar a los usuarios (lista de clientes, página de avisos, mensaje en el equipo).
- [ ] Plantillas de alerta, notificación e informe final con los campos de esta tabla.
- [ ] Simulacro una vez al año, con un CVE real del SBOM como ejemplo.
