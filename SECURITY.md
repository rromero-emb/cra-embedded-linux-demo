# Política de seguridad

Este repositorio es una demo, pero aplica la política de divulgación coordinada (CVD) que pide el CRA (Anexo I, Parte II, puntos 5 y 6) para servir de modelo.

## Cómo notificar una vulnerabilidad

Usa la **notificación privada de vulnerabilidades** de GitHub: pestaña *Security* → *Report a vulnerability* ([enlace directo](https://github.com/rromero-emb/cra-embedded-linux-demo/security/advisories/new)).

No abras una *issue* pública para vulnerabilidades.

Incluye, si puedes:
- versión o commit afectado (`IMAGE_VERSION` e `IMAGE_BUILD` de `/usr/lib/os-release`, o la salida de `cra-status`);
- descripción y componente afectado;
- pasos para reproducirla o prueba de concepto;
- impacto que estimas.

## Qué puedes esperar

| Paso | Plazo objetivo |
|---|---|
| Acuse de recibo | 5 días laborables |
| Primera evaluación (¿afecta?, severidad) | 10 días laborables |
| Corrección o mitigación | según severidad; las críticas, lo antes posible |
| Publicación coordinada | cuando haya corrección, como máximo 90 días tras la notificación salvo acuerdo |

Te mantendremos informado del avance y, si quieres, te citaremos en el aviso.

## Qué publicamos

Al corregir una vulnerabilidad (Anexo I, Parte II, punto 4):
- un **aviso de seguridad** en GitHub con la descripción, versiones afectadas y corregidas, impacto, severidad y cómo actualizar;
- el **documento VEX** actualizado (`vex.cdx.json` en los artefactos de CI), que también dice qué CVE **no** afectan y por qué ([`docs/vex/README.md`](docs/vex/README.md)).

En un producto, las vulnerabilidades explotadas activamente se notifican además a las autoridades en los plazos del art. 14 del CRA: ver [`docs/incident-runbook.md`](docs/incident-runbook.md).

## Versiones con soporte

| Versión | Soporte |
|---|---|
| `main` (última) | ✅ |
| anteriores | ❌ actualiza a la última |

Periodo de soporte de un producto basado en esta demo: [`docs/support-period.md`](docs/support-period.md).

## Fuera de alcance

- Las claves de desarrollo generadas con `make keys` (no protegen nada en producción).
- Ataques que requieren sustituir el firmware de QEMU (`u-boot.bin`): en hardware real lo protege la ROM del SoC.
- Los límites que ya están documentados en [`docs/annex-i-matrix.md`](docs/annex-i-matrix.md).
