# Matriz del Anexo I del CRA

Correspondencia entre los requisitos esenciales del **Anexo I del Reglamento (UE) 2024/2847** y lo que implementa esta demo, con la prueba automática que lo demuestra.

> **Alcance.** Esta matriz describe una demo, no un producto. En un producto real, cada requisito se aplica "sobre la base de la evaluación de riesgos" (Anexo I, Parte I, punto 2): esa evaluación decide qué requisitos aplican y con qué intensidad, y forma parte de la documentación técnica (Anexo VII). Los textos de los requisitos están resumidos; la referencia es el texto publicado en el DOUE.

Estados: ✅ implementado y probado · 🟡 parcial (se explica qué falta) · 📄 proceso documentado (no es técnico) · ➖ no aplica a la demo (se explica por qué)

`scripts/check-docs.py` comprueba en CI que todas las rutas citadas aquí existen y que la matriz cubre todos los puntos.

## Parte I · Requisitos de las propiedades del producto

### (1) Nivel de ciberseguridad adecuado a los riesgos

| Estado | Implementación | Evidencia |
|---|---|---|
| 📄 | Modelo de amenazas STRIDE con los activos, las amenazas y la medida que las cubre | `docs/threat-model.md` |

### 2(a) Sin vulnerabilidades explotables conocidas al comercializarse

| Estado | Implementación | Prueba / evidencia |
|---|---|---|
| ✅ | SBOM del producto, cruce con NVD, análisis automático del kernel (código no compilado, versión corregida) y VEX manual justificado | `make cve` → `output/sbom/vulnerabilidades.md`, `output/sbom/vex.cdx.json` |
| ✅ | Puerta de calidad: la CI falla si queda una CVE **crítica** sin analizar | `scripts/sbom/vuln-report.py` (`--fail-on critical`), `.github/workflows/ci.yml` |
| ✅ | Análisis semanal aunque no cambie el código | `.github/workflows/ci.yml` (`cron`) |
| 🟡 | Quedan CVE altas y medias abiertas (kernel, glibc, OpenSSL, GLib, PCRE2). La puerta solo bloquea críticas: en un producto, el umbral y el plazo de cada severidad deben salir de la evaluación de riesgos | `security/vex/triage.json` |

### 2(b) Configuración segura por defecto y posibilidad de volver al estado original

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | root bloqueado; usuario `admin` solo con clave SSH; sin contraseñas; sin root por SSH | `scripts/tests/test_hardening.py` |
| ✅ | Cortafuegos con política `drop` en entrada y salida; solo el puerto 22 escucha | `scripts/tests/test_hardening.py` |
| ✅ | Claves de host SSH generadas en cada equipo (no hay secretos compartidos en la imagen) | `scripts/tests/test_hardening.py` |
| ✅ | Restablecimiento de fábrica: borra `/data` (claves, estado, datos) y devuelve el estado A/B al original | `scripts/tests/test_factory_reset.py` |

### 2(c) Actualizaciones de seguridad (automáticas por defecto, con exclusión voluntaria, aviso y aplazamiento)

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Paquetes RAUC firmados (CA propia, uso *Code Signing*), formato verity; se rechazan los de otra CA | `scripts/tests/test_update.py` |
| ✅ | Anti-rollback: no se instalan versiones anteriores aunque estén firmadas | `scripts/tests/test_update.py` |
| ✅ | Instalación en el slot inactivo y vuelta atrás automática si la nueva versión no arranca | `scripts/tests/test_update.py` |
| 🟡 | La instalación es automática en cuanto llega el paquete, pero **la descarga no**: falta un cliente OTA (p. ej. hawkBit, Mender) con aviso al usuario, exclusión voluntaria y aplazamiento | `br2-external/board/qemu-aarch64-cra/rootfs-overlay/usr/sbin/cra-updater` |

### 2(d) Protección frente a accesos no autorizados (autenticación, gestión de identidades) e informar de posibles accesos no autorizados

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Solo autenticación por clave pública; el servidor no ofrece contraseña; root rechazado | `scripts/tests/test_hardening.py` |
| ✅ | Arranque verificado: solo arranca un FIT firmado (RSA-4096, configuración firmada); 4 ataques rechazados | `scripts/tests/test_verified_boot.py` |
| ✅ | U-Boot sin consola, sin red, sin entorno del disco; se apaga si la verificación falla | `br2-external/board/qemu-aarch64-cra/uboot.fragment` |
| 🟡 | Los intentos rechazados (SSH, cortafuegos) quedan en el registro local, pero no se notifican fuera del equipo | ver 2(l) |

### 2(e) Confidencialidad de los datos almacenados, transmitidos o tratados

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | En tránsito: la única interfaz de gestión es SSH | `scripts/tests/test_hardening.py` |
| 🟡 | **En reposo: `/data` no está cifrado.** En hardware real: dm-crypt/fscrypt con la clave sellada en el elemento seguro o TPM, ligada al arranque verificado | — |

### 2(f) Integridad de datos, órdenes, programas y configuración, e informar de corrupciones

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Kernel y device tree: firma del FIT verificada por U-Boot en cada arranque | `scripts/tests/test_verified_boot.py` |
| ✅ | Sistema de ficheros raíz y configuración: dm-verity (root hash dentro del FIT firmado), solo lectura; un byte alterado se detecta y el equipo arranca el otro slot | `scripts/tests/test_verity.py` |
| ✅ | Actualizaciones: firma CMS y dm-verity del paquete | `scripts/tests/test_update.py` |
| ✅ | Corrupción notificada: `data block N is corrupted` en el registro del kernel y rechazo del FIT en la consola de U-Boot | `scripts/tests/test_verity.py` |
| 🟡 | `/data` (escribible) no tiene protección de integridad; en un producto, dm-integrity o cifrado autenticado | — |

### 2(g) Minimización de datos

| Estado | Implementación | Evidencia |
|---|---|---|
| ➖ | La demo no recoge ni trata datos personales. En un producto, este punto depende de su función y de su análisis de protección de datos | — |

### 2(h) Disponibilidad de las funciones esenciales, también tras un incidente; resiliencia frente a denegación de servicio

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Dos slots A/B: un fallo de arranque, una corrupción o una actualización rota vuelven al slot bueno sin intervención | `scripts/tests/test_update.py`, `scripts/tests/test_verity.py` |
| ✅ | Límite de conexiones nuevas a SSH y de ICMP en el cortafuegos; dropbear con tiempos de espera | `br2-external/board/qemu-aarch64-cra/rootfs-overlay/etc/nftables.conf` |
| 🟡 | Sin vigilante (watchdog) hardware; en QEMU no hay | — |

### 2(i) Minimizar el impacto en otros dispositivos o redes

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Salida también con política `drop`: solo DNS, DHCP, NTP y HTTPS; sin reenvío de paquetes | `scripts/tests/test_hardening.py` |

### 2(j) Superficie de ataque limitada, incluidas las interfaces externas

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Solo el puerto 22 escucha; sin `crond`; sin herramientas de U-Boot, squashfs ni GLib en la imagen | `scripts/tests/test_hardening.py` |
| ✅ | Kernel sin `/dev/mem`, kexec, `/proc/kcore` ni SysRq | `scripts/tests/test_hardening.py` |
| ✅ | U-Boot sin red, sin consola interactiva, sin formatos de imagen sin firma | `scripts/tests/test_verified_boot.py` |
| ✅ | SBOM calculado a partir de los ficheros que realmente van en la imagen | `scripts/sbom/product-show-info.py` |

### 2(k) Reducir el impacto de un incidente con mecanismos de mitigación de explotación

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | Binarios PIE, RELRO completo, protector de pila, `_FORTIFY_SOURCE=2` | `scripts/tests/test_hardening.py` |
| ✅ | KASLR (semilla nueva en cada arranque), `HARDENED_USERCOPY`, `INIT_ON_ALLOC`, Yama, `kptr_restrict`, `dmesg_restrict` | `scripts/tests/test_hardening.py` |
| ✅ | Sin binarios setuid/setgid; ningún fichero escribible por cualquiera | `scripts/tests/test_hardening.py` |
| ✅ | `/data` montado con `nosuid,nodev,noexec` | `br2-external/board/qemu-aarch64-cra/rootfs-overlay/etc/fstab` |

### 2(l) Registro y supervisión de la actividad interna relevante, con exclusión voluntaria

| Estado | Implementación | Prueba |
|---|---|---|
| 🟡 | syslog local: paquetes descartados por el cortafuegos, accesos SSH, actualizaciones instaladas o rechazadas, restablecimiento de fábrica | — |
| 🟡 | **Falta:** el registro está en memoria (se pierde al reiniciar), no se envía a un servidor y no hay opción para desactivarlo | — |

### 2(m) Eliminar de forma segura y sencilla todos los datos y ajustes

| Estado | Implementación | Prueba |
|---|---|---|
| ✅ | `cra-factory-reset`: sobrescribe y reformatea `/data` y restablece el estado A/B | `scripts/tests/test_factory_reset.py` |
| 🟡 | Sobrescribir no garantiza el borrado en memoria flash (nivelación de desgaste). En hardware real: borrado seguro del controlador (eMMC *secure erase*/`BLKSECDISCARD`) o cifrado de `/data` y destrucción de la clave | — |

## Parte II · Requisitos de gestión de vulnerabilidades (fabricante)

| Punto | Requisito (resumen) | Estado | Implementación / evidencia |
|---|---|---|---|
| (1) | Identificar componentes y vulnerabilidades; SBOM legible por máquina | ✅ | CycloneDX del producto (`make sbom`), con glibc y su CPE: `scripts/sbom/add-runtime-components.py` |
| (2) | Corregir sin demora; actualizaciones de seguridad separadas de las funcionales cuando sea posible | 🟡 | Mecanismo de actualización listo (`scripts/tests/test_update.py`). Plazos y proceso: `docs/support-period.md`. La separación de actualizaciones depende del flujo de versiones del fabricante |
| (3) | Pruebas y revisiones de seguridad eficaces y periódicas | ✅ | `make test` en cada cambio y cada semana: `.github/workflows/ci.yml` |
| (4) | Publicar información de las vulnerabilidades corregidas | 📄 | Avisos de seguridad de GitHub y VEX publicado: `SECURITY.md`, `docs/vex/README.md` |
| (5) | Política de divulgación coordinada (CVD) | 📄 | `SECURITY.md` |
| (6) | Facilitar la notificación; dirección de contacto | 📄 | `SECURITY.md` (notificación privada de vulnerabilidades de GitHub) |
| (7) | Distribución segura de actualizaciones, automática cuando aplique | 🟡 | Paquetes firmados y verificados: `scripts/tests/test_update.py`. Falta el servidor/cliente OTA, ver 2(c) |
| (8) | Difundir las actualizaciones sin demora, gratis y con avisos para el usuario | 📄 | `docs/support-period.md`, `docs/user-information.md` |

## Otras obligaciones relacionadas

| Artículo | Obligación | Documento |
|---|---|---|
| Art. 13(8), 13(9), 13(19) | Periodo de soporte, disponibilidad de actualizaciones, fecha de fin de soporte | `docs/support-period.md` |
| Art. 14 | Notificación de vulnerabilidades explotadas e incidentes graves (24 h / 72 h / informe final) | `docs/incident-runbook.md` |
| Anexo II | Información e instrucciones para el usuario | `docs/user-information.md` |

## Resumen de lo que falta (para un producto real)

1. Cifrado e integridad de `/data`, con la clave sellada en hardware.
2. Cliente OTA con descarga automática, aviso, aplazamiento y exclusión voluntaria.
3. Registro persistente y envío a un servidor, con opción de desactivarlo.
4. Contador anti-rollback en el arranque (RPMB/OTP) y raíz de confianza en la ROM del SoC.
5. Borrado seguro propio de la memoria flash.
6. Evaluación de riesgos y documentación técnica completas (Anexo VII); normas armonizadas EN 40000 cuando se publiquen.
