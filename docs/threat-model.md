# Modelo de amenazas (STRIDE)

Base de la evaluación de riesgos del Anexo I, Parte I, punto 1. En un producto real se completa con el uso previsto, el entorno de instalación, los datos que trata y la probabilidad e impacto de cada amenaza.

## Sistema y límites de confianza

```
            ┌────────────── equipo ──────────────────────────────────────────┐
 red ──SSH──┤ dropbear ─► admin ─► /data/updates/incoming ─► cra-updater/RAUC│
 (no        │                                                                │
  confiable)│ firmware de confianza: u-boot.bin + DT de control (clave FIT)  │
            │ disco (no confiable):  slot A │ slot B │ bootstate │ /data      │
            └────────────────────────────────────────────────────────────────┘
 fabricante: claves FIT y RAUC (fuera del equipo), CI, SBOM/VEX, avisos de seguridad
```

| Límite | Lado confiable | Lado no confiable |
|---|---|---|
| Red → equipo | servicios del equipo | cualquier host de la red |
| Firmware → disco | U-Boot y su clave pública | todo el contenido del disco |
| Instalador → paquete | RAUC y el llavero de la CA | quien deposite el paquete |
| Fabricante → equipo | claves privadas de firma | canal de distribución |

## Activos

| Activo | Propiedad que se protege |
|---|---|
| Kernel, device tree y sistema de ficheros raíz | integridad, autenticidad |
| Claves privadas de firma (FIT, RAUC) | confidencialidad (fuera del equipo) |
| Claves de host SSH y datos de `/data` | confidencialidad, integridad |
| Estado A/B | integridad (no debe permitir saltarse la verificación) |
| Funcionamiento del equipo | disponibilidad |

## Amenazas y medidas

| ID | STRIDE | Amenaza | Medida | Prueba / estado |
|---|---|---|---|---|
| T1 | Suplantación | Acceso por SSH con contraseña o como root | Solo clave pública; root bloqueado y rechazado | `scripts/tests/test_hardening.py` |
| T2 | Suplantación | Clonar un equipo y suplantarlo con sus claves de host | Claves de host generadas en cada equipo, nunca en la imagen | `scripts/tests/test_hardening.py` |
| T3 | Manipulación | Sustituir el kernel o el device tree en el disco | FIT con configuración firmada RSA-4096; U-Boot rechaza y se apaga | `scripts/tests/test_verified_boot.py` |
| T4 | Manipulación | Modificar un fichero de la raíz con acceso al disco | dm-verity con root hash dentro del FIT firmado; reinicio y cambio de slot | `scripts/tests/test_verity.py` |
| T5 | Manipulación | Usar el entorno o un script de U-Boot del disco para cambiar los argumentos del kernel | Entorno compilado; del disco solo se importan 3 variables con lista blanca; sin `boot.scr` | `scripts/tests/test_verified_boot.py` |
| T6 | Manipulación | Instalar un paquete de actualización ajeno | Firma CMS de la CA propia con uso *Code Signing*; formato verity | `scripts/tests/test_update.py` |
| T7 | Manipulación | Instalar una versión antigua firmada pero vulnerable | Anti-rollback en la instalación | `scripts/tests/test_update.py` |
| T8 | Manipulación | Elegir con acceso al disco el slot más antiguo | **Abierto**: requiere contador anti-rollback en almacenamiento seguro (RPMB/OTP) | — |
| T9 | Manipulación | Sustituir el propio firmware (U-Boot) | **Fuera de la demo**: en hardware, la ROM del SoC verifica el firmware con una clave en OTP | — |
| T10 | Repudio | Negar que se instaló una actualización o se borró el equipo | syslog local de actualizaciones y restablecimientos | 🟡 registro solo en memoria (Anexo I 2(l)) |
| T11 | Revelación | Leer `/data` extrayendo el disco | **Abierto**: `/data` sin cifrar | 🟡 Anexo I 2(e) |
| T12 | Revelación | Filtrar direcciones del kernel para facilitar exploits | `kptr_restrict=2`, `dmesg_restrict=1`, KASLR | `scripts/tests/test_hardening.py` |
| T13 | Revelación | Datos que quedan al vender o retirar el equipo | Restablecimiento de fábrica | `scripts/tests/test_factory_reset.py` (🟡 en flash ver 2(m)) |
| T14 | Denegación de servicio | Inundar SSH o ICMP | Límites de tasa en nftables; tiempos de espera de dropbear | configuración, sin prueba de carga |
| T15 | Denegación de servicio | Actualización rota que deja el equipo sin arrancar | A/B con 3 intentos y vuelta atrás automática | `scripts/tests/test_update.py` |
| T16 | Elevación de privilegios | Explotar un binario para ganar root | PIE, RELRO, SSP, FORTIFY; sin setuid; Yama | `scripts/tests/test_hardening.py` |
| T17 | Elevación de privilegios | Ejecutar código desde la partición de datos | `/data` con `noexec,nosuid,nodev`; raíz de solo lectura | `br2-external/board/qemu-aarch64-cra/rootfs-overlay/etc/fstab`, `scripts/tests/test_hardening.py` (raíz) |
| T18 | Elevación de privilegios | Vulnerabilidad conocida en un componente | SBOM + NVD + VEX, puerta de calidad y análisis semanal | `make cve` |
| T19 | Cadena de suministro | Código fuente alterado en la descarga | Hashes de todos los paquetes en Buildroot; firma GPG de U-Boot verificada | `br2-external/patches/uboot/2026.07/uboot.hash` |
| T20 | Cadena de suministro | Robo de las claves de firma | Claves fuera de git (hook que lo impide). En producción: HSM y firma en un entorno aislado | `.githooks/pre-commit` |

## Riesgos aceptados en la demo

- T8, T9, T11: requieren hardware (OTP, RPMB, elemento seguro o TPM) que QEMU no aporta.
- Las claves son de desarrollo y se generan en local con `make keys`.
- El acceso físico con depurador (JTAG) queda fuera del alcance.

Revisión: en cada versión y siempre que cambie una interfaz externa.
