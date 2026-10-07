# CRA demo · Linux embebido

Demostración reproducible de técnicas para cumplir requisitos técnicos del **Cyber Resilience Act** (Reglamento UE 2024/2847) en un dispositivo con Linux embebido: arranque verificado, actualizaciones firmadas A/B, SBOM, gestión de vulnerabilidades y endurecimiento.

> **Aviso:** esta demo ilustra técnicas para requisitos del Anexo I. No hace "conforme al CRA" a ningún producto: la conformidad es por producto e incluye evaluación de riesgos, documentación técnica y procesos del fabricante. Las normas armonizadas (serie EN 40000) siguen en elaboración.

## Estado

| Sesión | Contenido | Estado |
|---|---|---|
| 1 | Imagen base en QEMU, CI, SBOM básico | ✅ |
| 2 | Endurecimiento | ⏳ |
| 3 | SBOM + CVE + VEX | ⏳ |
| 4 | Arranque verificado (FIT firmado) | ⏳ |
| 5 | Actualizaciones A/B firmadas (RAUC) | ⏳ |
| 6 | dm-verity o cifrado de datos | ⏳ |
| 7 | Documentación de proceso (Anexo I, CVD, soporte) | ⏳ |

## Uso rápido

Requisitos (Debian/Ubuntu): `build-essential rsync bc cpio unzip file wget libssl-dev libgnutls28-dev python3 qemu-system-arm`

```sh
make          # descarga Buildroot 2025.02.x (LTS) y compila
make run      # arranca en QEMU (salir con Ctrl-a x)
make test     # prueba automática de arranque
make sbom     # SBOM CycloneDX en output/sbom/
make hooks    # impide hacer commit de claves privadas
```

## Base técnica

- Buildroot **2025.02.x LTS** (soporte hasta marzo de 2028) como `BR2_EXTERNAL`
- QEMU aarch64 `virt`, U-Boot como firmware, kernel Linux 6.12 LTS
- Toolchain externa Bootlin (glibc, estable)

Plan completo: [`docs/PLAN.md`](docs/PLAN.md)

## Licencia

MIT. Buildroot y los paquetes que descarga mantienen sus propias licencias (ver `make legal-info`).
