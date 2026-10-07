# CRA demo · Linux embebido

Demostración reproducible de técnicas para cumplir requisitos técnicos del **Cyber Resilience Act** (Reglamento UE 2024/2847) en un dispositivo con Linux embebido: arranque verificado, actualizaciones firmadas A/B, SBOM, gestión de vulnerabilidades y endurecimiento.

> **Aviso:** esta demo ilustra técnicas para requisitos del Anexo I. No hace "conforme al CRA" a ningún producto: la conformidad es por producto e incluye evaluación de riesgos, documentación técnica y procesos del fabricante. Las normas armonizadas (serie EN 40000) siguen en elaboración.

## Estado

| Sesión | Contenido | Estado |
|---|---|---|
| 1 | Imagen base en QEMU, CI, SBOM básico | ✅ |
| 2 | Endurecimiento (kernel, binarios, cortafuegos, SSH solo con clave, sysctl) | ✅ |
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
make ssh      # en otra terminal: entra como 'admin' con la clave de desarrollo
make test     # pruebas automáticas: arranque + 22 comprobaciones de endurecimiento
make sbom     # SBOM CycloneDX en output/sbom/
make hooks    # impide hacer commit de claves privadas
```

## Endurecimiento (sesión 2)

| Área | Medidas |
|---|---|
| Binarios | PIE, `-fstack-protector-strong`, RELRO completo, `_FORTIFY_SOURCE=2` |
| Kernel | KASLR, `HARDENED_USERCOPY`, `INIT_ON_ALLOC`, `dmesg` restringido, Yama; sin `/dev/mem`, kexec ni SysRq |
| Red | nftables con política `drop` en entrada y salida; solo SSH (con límite), DHCP, DNS, NTP y HTTPS |
| Cuentas | root bloqueado; usuario `admin` solo con clave SSH; claves de host generadas en el primer arranque de cada equipo |
| Sistema | sin setuid (incluido busybox), sin `crond`, sysctl endurecidos |

`make test` lo verifica sobre la **imagen final** (permisos leídos con `debugfs`) y con el equipo arrancado (puertos, cortafuegos, SSH).

## Base técnica

- Buildroot **2025.02.x LTS** (soporte hasta marzo de 2028) como `BR2_EXTERNAL`
- QEMU aarch64 `virt`, U-Boot como firmware, kernel Linux 6.12 LTS
- Toolchain externa Bootlin (glibc, estable)

Plan completo: [`docs/PLAN.md`](docs/PLAN.md)

## Licencia

MIT. Buildroot y los paquetes que descarga mantienen sus propias licencias (ver `make legal-info`).
