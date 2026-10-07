# CRA demo · Linux embebido

Demostración reproducible de técnicas para cumplir requisitos técnicos del **Cyber Resilience Act** (Reglamento UE 2024/2847) en un dispositivo con Linux embebido: arranque verificado, actualizaciones firmadas A/B, SBOM, gestión de vulnerabilidades y endurecimiento.

> **Aviso:** esta demo ilustra técnicas para requisitos del Anexo I. No hace "conforme al CRA" a ningún producto: la conformidad es por producto e incluye evaluación de riesgos, documentación técnica y procesos del fabricante. Las normas armonizadas (serie EN 40000) siguen en elaboración.

## Estado

| Sesión | Contenido | Estado |
|---|---|---|
| 1 | Imagen base en QEMU, CI, SBOM básico | ✅ |
| 2 | Endurecimiento (kernel, binarios, cortafuegos, SSH solo con clave, sysctl) | ✅ |
| 3 | SBOM del producto, CVE (NVD + kernel CNA), VEX y puerta de calidad | ✅ |
| 4 | Arranque verificado: FIT firmado (RSA-4096), U-Boot bloqueado, 4 ataques probados | ✅ |
| 5 | Actualizaciones A/B firmadas (RAUC, verity), anti-rollback y vuelta atrás automática | ✅ |
| 6 | Raíz de solo lectura verificada con dm-verity (root hash firmado en el FIT) | ✅ |
| 7 | Documentación de proceso (Anexo I, CVD, soporte) | ⏳ |

## Uso rápido

Requisitos (Debian/Ubuntu): `build-essential rsync bc cpio unzip file wget libssl-dev libgnutls28-dev python3 qemu-system-arm xxd`

```sh
make          # descarga Buildroot 2025.02.x (LTS) y compila
make run      # arranca en QEMU (salir con Ctrl-a x)
make ssh      # en otra terminal: entra como 'admin' con la clave de desarrollo
make test     # arranque + endurecimiento + ataques al arranque + dm-verity + actualizaciones A/B
make sbom     # SBOM CycloneDX del producto y de compilación en output/sbom/
make cve      # vulnerabilidades + VEX + informe (falla si hay críticas sin analizar)
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

## Vulnerabilidades y VEX (sesión 3)

`make cve` produce en `output/sbom/`:

| Fichero | Contenido |
|---|---|
| `sbom.cdx.json` | SBOM **del producto** (solo lo que va en el equipo, incluida glibc con su CPE) |
| `sbom-build.cdx.json` | SBOM de compilación (herramientas de host) |
| `sbom-vuln.cdx.json` | SBOM enriquecido con las CVE de NVD (`cve-check` de Buildroot) |
| `vex.cdx.json` | Documento VEX: cada CVE con su estado y justificación |
| `vulnerabilidades.md` | Informe legible y resultado de la puerta de calidad |

Cómo se reducen las CVE del kernel a las que importan:

| | Kernel 6.12.27 | Kernel 6.12.112 |
|---|---|---|
| CVE que reporta NVD | 3.201 | 360 |
| No afectan: código no compilado (datos del kernel CNA + `.o` del build) | 2.531 | 169 |
| Corregidas en la versión / introducidas después | 67 | 140 |
| **Abiertas tras el análisis** | **589** | **~50** |

- Análisis automático del kernel: [`scripts/sbom/kernel-vex.py`](scripts/sbom/kernel-vex.py) con [linux/security/vulns.git](https://git.kernel.org/pub/scm/linux/security/vulns.git).
- Análisis manual justificado: [`security/vex/triage.json`](security/vex/triage.json).
- U-Boot actualizado a 2026.07 (firma GPG del mantenedor verificada) antes de confiar en la firma FIT: CVE-2026-46728 permitía saltársela en versiones anteriores a 2026.04. Pila de red de U-Boot eliminada.
- CI semanal: vuelve a analizar aunque no cambie el código, porque aparecen CVE nuevas.

## Arranque verificado (sesión 4)

```
firmware de confianza                         disco (no confiable)
┌─────────────────────────────────┐          ┌──────────────────────────────┐
│ u-boot.bin                      │  carga   │ /boot/fitImage               │
│ + DT de control con la clave    │ ───────► │  kernel + device tree        │
│   pública (required = "conf")   │ verifica │  hashes SHA-256              │
│ orden de arranque y bootargs    │          │  configuración firmada       │
│ compilados; sin consola         │          │  (RSA-4096)                  │
└─────────────────────────────────┘          └──────────────────────────────┘
```

- La **configuración** del FIT está firmada (no cada imagen suelta): impide combinar piezas firmadas de versiones distintas.
- U-Boot solo admite FIT firmados: sin formato legacy, sin `booti`/`bootz`, sin `bootflow` (no ejecuta `boot.scr` del disco), entorno solo en memoria, `bootdelay=-2` y **se apaga** si la verificación falla (no queda consola).
- KASLR activo: U-Boot inyecta una `kaslr-seed` nueva en cada arranque desde `virtio-rng`.
- `make test` comprueba que se rechazan: 1 byte del kernel alterado · FIT firmado con otra clave del mismo nombre · FIT sin firma · kernel suelto.

**Límites (honestos):**
- Con A/B, un atacante con acceso al disco puede elegir entre los dos slots firmados (p. ej. el anterior). El anti-rollback de RAUC impide *instalar* versiones antiguas, pero no hay contador anti-rollback en el arranque (requiere almacenamiento seguro, p. ej. RPMB/OTP).
- En QEMU la raíz de confianza es el firmware (`u-boot.bin` + DT de control, que QEMU entrega con `-dtb`). En hardware real, la ROM del SoC o TF-A verifica ese firmware con una clave grabada en OTP (paso irreversible).
- Las claves son de desarrollo (`make keys`, nunca en git). En producción: HSM/PKI.
- QEMU con `-bios` y ACPI sustituye el GPIO PL061 por ACPI GED: se usa `acpi=off` para que la máquina coincida con el device tree.

## Actualizaciones A/B (sesión 5)

```
 disco:  p1 sistema A │ p2 sistema B │ p3 bootstate (FAT) │ p4 datos (ext4)
                                         BOOT_ORDER=A B
 U-Boot (entorno compilado) ──importa──► BOOT_A_LEFT=3     ◄── RAUC (backend propio)
                                         BOOT_B_LEFT=3
```

- **RAUC** con paquetes en formato **verity** (se rechaza `plain`): firma CMS con una **CA propia** (el certificado de firma debe ser *Code Signing*) y cada bloque verificado con dm-verity al instalar.
- **Anti-rollback**: un handler rechaza paquetes con versión inferior a la instalada (una versión antigua puede estar firmada y ser vulnerable).
- **Vuelta atrás automática**: U-Boot descuenta un intento por arranque; el sistema se marca como bueno al final del arranque; si un slot agota sus 3 intentos o su FIT no verifica, U-Boot pasa al otro.
- **El estado A/B no abre la puerta al arranque**: U-Boot no carga ningún entorno del disco; del fichero `bootstate.txt` solo importa `BOOT_ORDER`, `BOOT_A_LEFT` y `BOOT_B_LEFT` (`env import` con lista blanca). Orden de arranque y parámetros del kernel siguen compilados.
- `init=/sbin/init` fijo: si falla, el kernel entra en pánico y reinicia (cuenta como intento fallido) en lugar de caer a `/bin/sh`.
- Un agente (como un cliente OTA) instala lo que se deja en `/data/updates/incoming`: no importa quién lo deje, solo se instala lo firmado.

`make test` comprueba: paquete de otra CA → rechazado · paquete antiguo → rechazado · paquete nuevo → arranca en B · paquete firmado pero roto → 3 intentos y vuelta atrás automática.

## Raíz verificada con dm-verity (sesión 6)

```
slot (A o B, 160 MiB):
0 ─── ext4 solo lectura (128 MiB) ─── 128 ─ árbol de hashes ─ 136 ─── FIT firmado ─── 160 MiB
                                                                  │ kernel
                                                                  │ device tree + /chosen/cra,verity
                                                                  │   (root hash + salt, firmados)
U-Boot: lee el FIT en bruto → verifica la firma → extrae el root hash → dm-mod.create=... root=/dev/dm-0
```

- El kernel verifica **cada bloque de la raíz al leerlo**. Un solo byte alterado → `data block N is corrupted` → reinicio (`restart_on_corruption`) → cuenta como intento fallido A/B → arranca el otro slot.
- El root hash va dentro del device tree **firmado** del FIT; el FIT está fuera de la zona verificada para evitar la dependencia circular.
- Sin initramfs: el kernel crea el dispositivo verity al arrancar (`CONFIG_DM_INIT`).
- Raíz de solo lectura; lo que debe persistir (claves de host SSH, semilla aleatoria, estado de RAUC) va en `/data`.
- RAUC instala el slot completo (ext4 + hashes + FIT) como imagen en bruto, dentro de un paquete también verity.

`make test` altera 1 byte de `/bin/busybox` en el slot A (sin tocar el FIT): dm-verity lo detecta y el equipo vuelve solo al slot B.

## Base técnica

- Buildroot **2025.02.x LTS** (soporte hasta marzo de 2028) como `BR2_EXTERNAL`
- QEMU aarch64 `virt`, U-Boot 2026.07 como firmware, kernel Linux 6.12.112 (LTS)
- Toolchain externa Bootlin (glibc, estable)

Plan completo: [`docs/PLAN.md`](docs/PLAN.md)

## Licencia

MIT. Buildroot y los paquetes que descarga mantienen sus propias licencias (ver `make legal-info`).
