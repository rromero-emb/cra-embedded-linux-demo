# Demo CRA para Linux embebido – Plan técnico

**Objetivo:** un repositorio público que demuestre, de forma reproducible y en 3 minutos de vídeo, cómo se prepara un dispositivo con Linux embebido para el **Cyber Resilience Act** (Reglamento UE 2024/2847).
**Calendario:** 8 sesiones (~2 meses, hasta mediados de diciembre de 2026).

> Aviso que debe figurar en el README: *esta demo ilustra técnicas para cumplir requisitos del Anexo I; no hace "conforme al CRA" a ningún producto. La conformidad es por producto e incluye evaluación de riesgos, documentación técnica y procesos del fabricante. Las normas armonizadas (serie EN 40000) siguen en elaboración en 2026.*

---

## 1. Qué se va a ver en el vídeo (criterio de éxito)

| # | Escena | Requisito CRA que ilustra |
|---|---|---|
| 1 | El equipo arranca; `cra-status` muestra versión, clave de firma, slot A/B activo, estado del firewall | Seguro por defecto, transparencia |
| 2 | Modifico 1 byte del kernel → **U-Boot se niega a arrancarlo** | Integridad, protección frente a manipulación |
| 3 | Instalo una actualización **firmada** → cambia de slot A→B. Intento instalar una **sin firmar o con otra clave** → rechazada | Actualizaciones de seguridad seguras |
| 4 | Actualización que no arranca → **vuelta atrás automática** al slot bueno | Disponibilidad, resiliencia |
| 5 | CI genera el **SBOM** y el informe de CVE; un paquete antiguo aparece con CVE → lo actualizo → informe limpio + **VEX** publicado | Parte II: SBOM, gestión y divulgación de vulnerabilidades |
| 6 | Sin contraseñas por defecto, SSH solo con clave, puertos cerrados salvo los necesarios | Seguro por defecto, superficie de ataque mínima |
| 7 | `docs/` con la matriz del Anexo I, política de divulgación coordinada (CVD), periodo de soporte y procedimiento de notificación 24 h / 72 h / 14 días | Obligaciones de proceso del fabricante |

---

## 2. Decisiones de diseño

| Tema | Elección | Por qué |
|---|---|---|
| Sistema de construcción | **Buildroot 2025.02.x (LTS, soporte hasta marzo 2028)** como `BR2_EXTERNAL` | Lo dominas; el LTS permite hablar de **periodo de soporte**, otro requisito del CRA. Plan B si faltan utilidades SBOM recientes: 2026.05/2026.08 |
| Plataforma | **QEMU aarch64 `virt`** (fase 1) | Cualquiera puede reproducirlo sin hardware; permite pruebas automáticas en CI |
| Hardware real (fase 2, opcional) | STM32MP135F-DK o Raspberry Pi 4/CM4 | Para la versión "de verdad" con raíz de confianza en hardware |
| Arranque verificado | **U-Boot + FIT firmado** (RSA-4096/SHA-256) con la clave pública en el DTB de control de U-Boot (`required = "conf"`) | Estándar, bien documentado, demostrable en QEMU |
| Rootfs | **SquashFS de solo lectura** + partición de datos aparte; **dm-verity** como objetivo ampliado | Integridad del sistema; datos separados para las actualizaciones |
| Actualizaciones | **RAUC** con bundles firmados (CMS/X.509) + esquema **A/B** + `bootchooser` de U-Boot con contador de intentos | Usa **X.509**, que ya dominas; rollback automático |
| SBOM | `utils/generate-cyclonedx` de Buildroot → CycloneDX JSON; enriquecido con `support/scripts/cve-check` (≥2025.11) o con **Grype** | Formato estándar; importable en Dependency-Track |
| Seguimiento de vulnerabilidades | **Dependency-Track** (contenedor Docker local) + VEX en CycloneDX | Muestra el proceso continuo, no solo un informe puntual |
| CI | **GitHub Actions**: build con caché, SBOM, CVE, prueba de arranque en QEMU, pruebas de manipulación, publicación de artefactos | Evidencia automática y reproducible |
| Claves | Claves de **desarrollo** generadas por script y **nunca** en el repo (`.gitignore`); en CI desde *secrets* | Buena práctica; en el README explicar que en producción iría en HSM/PKI |

**Limitación honesta (decirla en el README y en las llamadas):** en QEMU la cadena de confianza empieza en U-Boot. En hardware real empieza en la ROM del SoC con la clave grabada en OTP/fusibles (paso **irreversible**: se hace en placas de desarrollo, nunca a la ligera).

---

## 3. Arquitectura

```
QEMU aarch64 virt
 └─ U-Boot (DTB de control con clave pública, FIT_SIGNATURE, bootchooser A/B)
     ├─ FIT firmado slot A: kernel + DTB (+ cmdline con root hash de dm-verity, fase ampliada)
     └─ FIT firmado slot B
Disco (genimage):
  p1 boot/ESP | p2 rootfs A (squashfs) | p3 rootfs B (squashfs) | p4 datos (ext4, persistente)
Rootfs:
  BusyBox/systemd-lite, dropbear (solo clave), nftables (deny por defecto),
  rauc + system.conf (keyring con CA de actualizaciones), cra-status (script de estado)
```

---

## 4. Estructura del repositorio

```
cra-embedded-linux-demo/
├── README.md                     # Qué es, vídeo/GIF, cómo reproducirlo en 3 comandos, aviso legal
├── external.desc / external.mk / Config.in      # BR2_EXTERNAL
├── configs/qemu_aarch64_cra_defconfig
├── board/qemu-aarch64-cra/
│   ├── genimage.cfg              # particiones A/B + datos
│   ├── uboot.fragment            # FIT_SIGNATURE, bootchooser, sin consola interactiva en "release"
│   ├── linux.fragment            # endurecimiento del kernel
│   ├── fit-image.its             # descripción del FIT (kernel+dtb, hash, firma)
│   ├── boot.cmd                  # lógica A/B y contador de intentos
│   ├── post-build.sh             # quitar sobrantes, permisos, usuarios, banner
│   ├── post-image.sh             # firmar FIT, inyectar clave en DTB de U-Boot, genimage
│   └── rootfs-overlay/           # nftables.conf, rauc/system.conf, sshd sin contraseña, cra-status
├── scripts/
│   ├── gen-dev-keys.sh           # CA de actualizaciones + clave de arranque (desarrollo)
│   ├── run-qemu.sh
│   ├── make-bundle.sh            # bundle RAUC firmado
│   ├── sbom.sh                   # CycloneDX + CVE + VEX
│   └── tests/
│       ├── test_boot.py          # arranca y comprueba cra-status (pexpect)
│       ├── test_tamper_fit.py    # FIT alterado → no arranca
│       ├── test_update.py        # bundle firmado OK / sin firmar rechazado / rollback
│       └── test_hardening.py     # puertos, usuarios, ficheros con permisos peligrosos
├── docs/
│   ├── annex-i-matrix.md         # cada requisito → implementación → prueba → evidencia
│   ├── threat-model.md           # STRIDE ligero del dispositivo
│   ├── SECURITY.md               # política de divulgación coordinada (CVD) y contacto
│   ├── support-period.md         # periodo de soporte declarado y justificación (LTS)
│   ├── incident-runbook.md       # notificación ENISA: 24 h / 72 h / 14 días (simulacro)
│   └── vex/                      # declaraciones VEX publicadas
└── .github/workflows/ci.yml
```

---

## 5. Matriz del Anexo I (borrador para `docs/annex-i-matrix.md`)

| Requisito (resumen) | Implementación en la demo | Prueba automática |
|---|---|---|
| **Parte I** – Sin vulnerabilidades explotables conocidas al comercializar | SBOM + escaneo CVE como puerta de calidad en CI | CI falla si hay CVE críticas sin VEX |
| Seguro por defecto, restaurable | Sin credenciales por defecto, servicios mínimos, partición de datos borrable ("reset de fábrica") | `test_hardening.py` |
| Actualizaciones de seguridad | RAUC firmado, A/B, rollback | `test_update.py` |
| Protección frente a acceso no autorizado | SSH solo por clave, sin root remoto, firewall deny por defecto | `test_hardening.py` |
| Confidencialidad de datos | Actualizaciones y gestión sobre TLS/SSH; (ampliación: cifrado de la partición de datos) | Revisión |
| Integridad | FIT firmado; rootfs de solo lectura; (ampliación: dm-verity) | `test_tamper_fit.py` |
| Minimización de datos | Sin telemetría; registros locales con rotación | Revisión |
| Disponibilidad de funciones esenciales | Watchdog + rollback A/B | `test_update.py` (caso de fallo) |
| Minimizar impacto en otros | Firewall de salida restrictivo | `test_hardening.py` |
| Limitar superficie de ataque | Kernel y BusyBox recortados; sin compiladores ni herramientas de depuración en "release" | `test_hardening.py` |
| Mitigación de explotación | `BR2_SSP_STRONG`, `BR2_RELRO_FULL`, `BR2_FORTIFY_SOURCE_2`, PIE; kernel con `STRICT_KERNEL_RWX`, `RANDOMIZE_BASE`, etc. | Script `checksec` en CI |
| Registro de eventos de seguridad | Log de intentos SSH fallidos, actualizaciones y rechazos de firma | Revisión |
| Borrado seguro de datos | Script de reset de fábrica | Revisión |
| **Parte II** – Identificar componentes (SBOM) | `generate-cyclonedx` en cada build, publicado como artefacto | CI |
| Corregir sin demora | Flujo documentado: aviso → análisis → bundle → publicación | Simulacro documentado |
| Pruebas regulares | CI en cada commit + escaneo CVE semanal (cron) | CI |
| Divulgar vulnerabilidades corregidas | `docs/vex/` + notas de versión de seguridad | Revisión |
| Política de divulgación coordinada | `SECURITY.md` + `security.txt` | Revisión |
| Compartir información / contacto | Dirección de contacto en `SECURITY.md` | Revisión |
| Distribución segura de actualizaciones | Bundles firmados por CA propia | `test_update.py` |
| Actualizaciones gratuitas y separadas de las funcionales | Política en `support-period.md` | Revisión |

*(Redacta la versión final contra el texto oficial del Anexo I del Reglamento 2024/2847, no contra este resumen.)*

---

## 6. Calendario por sesiones (sábados, ~4 h)

| Sesión | Fecha orientativa | Entregable | Tareas |
|---|---|---|---|
| **S1** | 17 oct | Imagen base arrancando en QEMU + CI compilando | `BR2_EXTERNAL`, defconfig aarch64 virt, U-Boot + kernel, `run-qemu.sh`, workflow de GitHub con caché de `dl/` y ccache. **Comprobar** si 2025.02.x incluye `utils/generate-cyclonedx`; si no, decidir el plan B |
| **S2** | 24 oct | Endurecimiento | Fragmentos del kernel, opciones de compilación seguras, dropbear solo clave, nftables, usuario sin privilegios, `cra-status`, `test_boot.py` + `test_hardening.py` |
| **S3** | 31 oct | SBOM y CVE | `sbom.sh` → CycloneDX; CVE (cve-check o Grype); Dependency-Track en Docker local; artefactos en CI; meter a propósito un paquete con CVE conocida para la escena 5 |
| **S4** | 7 nov | Arranque verificado | `gen-dev-keys.sh`, `fit-image.its`, firma con `mkimage -k -K`, clave en DTB de U-Boot, `required=conf`, `test_tamper_fit.py` |
| **S5** | 14 nov | Actualizaciones A/B firmadas | Particiones A/B en genimage, RAUC + `system.conf` + keyring X.509, `boot.cmd` con bootchooser y contador, `make-bundle.sh`, `test_update.py` (OK / rechazo / rollback) |
| **S6** | 21 nov | Ampliación | dm-verity en el rootfs (root hash dentro del FIT firmado) **o** cifrado de la partición de datos. Elige uno; el otro queda como "siguiente paso" |
| **S7** | 28 nov | Documentación de proceso | `annex-i-matrix.md`, `threat-model.md`, `SECURITY.md`, `support-period.md`, `incident-runbook.md`, primera declaración VEX |
| **S8** | 5–12 dic | Publicación | README con GIF/vídeo de 3 min, etiqueta `v1.0`, post de LinkedIn (técnico) + post de "lecciones aprendidas" |

**Después (enero 2027):**
- Fase 2: portar a placa real (STM32MP135F-DK o RPi 4) con raíz de confianza en hardware.
- Fase 3: añadir un módulo de **IA en el borde** sobre la misma imagen (detección de anomalías), que demuestra CRA + AI Act en un solo dispositivo.

---

## 7. Riesgos y cómo evitarlos

| Riesgo | Mitigación |
|---|---|
| Tiempos de compilación largos en CI (Buildroot desde cero ≈ 1 h o más) | Caché de `dl/` y ccache; job de build manual + job de pruebas que reutiliza artefactos |
| Integración RAUC + U-Boot complicada | Empezar con el ejemplo oficial de RAUC/U-Boot; si se atasca más de una sesión, cambiar a SWUpdate (también con firma) |
| Utilidades SBOM no disponibles en el LTS | Plan B: Buildroot estable más reciente, o `show-info` → CycloneDX propio + Grype |
| Subir claves privadas por error | `.gitignore` desde S1 + hook pre-commit que busque `PRIVATE KEY` |
| Prometer de más ("cumple el CRA") | Aviso en README; hablar siempre de "requisitos técnicos ilustrados" |

