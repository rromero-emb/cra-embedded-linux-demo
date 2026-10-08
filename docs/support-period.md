# Periodo de soporte

Modelo de declaración del periodo de soporte para un producto basado en esta demo (CRA, art. 13, apartados 8, 9 y 19). Las fechas de los componentes son las publicadas por sus proyectos en octubre de 2026.

## Lo que pide el CRA

| Artículo | Obligación |
|---|---|
| 13(8) | Periodo de soporte acorde al tiempo que se espera usar el producto; **al menos 5 años** salvo que se espere usarlo menos tiempo |
| 13(9) | Cada actualización de seguridad sigue disponible **al menos 10 años** desde su publicación, o el resto del periodo de soporte si es más largo |
| 13(19) | La **fecha de fin de soporte** (al menos mes y año) se muestra de forma clara en el momento de la compra y, si es técnicamente posible, se avisa al usuario cuando llega |

## Componentes base y su fin de soporte

| Componente | Versión | Soporte del proyecto | Fin previsto |
|---|---|---|---|
| Buildroot | 2025.02.x LTS | mantenimiento de la rama LTS | marzo de 2028 |
| Linux | 6.12.x LTS | kernel.org (fecha "no fija", ampliable) | diciembre de 2028 |
| U-Boot | 2026.07 | sin ramas LTS: se actualiza a versiones nuevas | — |
| glibc, toolchain | Bootlin aarch64 glibc *stable* (glibc 2.39, gcc 13.3) | sigue a Buildroot | con Buildroot |

**Ningún componente base cubre por sí solo 5 años.** El soporte del producto lo da el fabricante, no la versión de la que parte.

## Plan para cubrir el periodo

1. **Actualizaciones de mantenimiento dentro de la LTS**: subir Buildroot, kernel y U-Boot dentro de su rama en cuanto haya correcciones de seguridad. La CI semanal (`make cve`) avisa de las CVE nuevas aunque no cambie el código.
2. **Migración a la siguiente LTS** antes de que acabe la actual: Buildroot 2026.02 LTS (o la que corresponda) y el siguiente kernel LTS, planificada con 6 meses de margen. El sistema de actualizaciones A/B y las pruebas (`make test`) son los que hacen posible migrar sin riesgo en equipos ya instalados.
3. **Alternativa para soportes largos (10 años o más)**: kernel SLTS del proyecto Civil Infrastructure Platform (CIP) o un acuerdo de soporte comercial.
4. **Formato de cada actualización**: paquete RAUC firmado completo, con su SBOM y su VEX.

## Disponibilidad de las actualizaciones (13(9))

- Cada paquete publicado (`update.raucb`), con su SBOM y VEX, se archiva **10 años** desde su publicación en un almacenamiento propio del fabricante.
- No basta con los artefactos de la CI de GitHub: caducan a los 90 días como máximo.

## Fecha de fin de soporte (13(19))

| Dónde | Cómo |
|---|---|
| Punto de venta y ficha del producto | "Actualizaciones de seguridad hasta: MM/AAAA" |
| Información al usuario | [`docs/user-information.md`](user-information.md) |
| En el propio equipo | Propuesta: campo `SUPPORT_END=AAAA-MM` en `/usr/lib/os-release` (lo admite la especificación de os-release) y aviso en `cra-status` al pasar la fecha. **No implementado aún en la demo** |

## Ejemplo de declaración

> *Producto X, versión 1.0. Periodo de soporte: desde la puesta en el mercado hasta **diciembre de 2031**. Durante este periodo el fabricante publicará gratuitamente las actualizaciones de seguridad necesarias. Cada actualización seguirá disponible para su descarga durante al menos 10 años desde su publicación.*
