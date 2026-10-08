# Información para el usuario (modelo según el Anexo II)

Modelo de la información e instrucciones que debe acompañar a un producto basado en esta demo. Los campos entre `<>` los rellena el fabricante.

## 1. Fabricante y contacto

- Fabricante: `<nombre, marca, dirección postal, correo y web>`
- Punto de contacto para notificar vulnerabilidades: `<dirección>`. Política de divulgación coordinada: [`SECURITY.md`](../SECURITY.md).

## 2. Identificación del producto

- Producto, tipo y versión: `<nombre>`. En el equipo, la versión instalada se consulta con `cra-status` (campos "Imagen" y "Build") o en `/usr/lib/os-release`.

## 3. Uso previsto

`<función del producto y entorno de uso para el que se ha evaluado su seguridad>`

## 4. Circunstancias que pueden suponer riesgos de ciberseguridad

- Conectar el equipo a una red no protegida sin cambiar la clave de administración de fábrica por una propia.
- Dar acceso físico al equipo a personas no autorizadas: quien extrae el disco puede leer los datos de `/data` (no están cifrados en esta versión).
- Dejar el equipo sin actualizar después de una actualización de seguridad publicada.
- Usar el equipo después de la fecha de fin de soporte.

## 5. Declaración UE de conformidad

`<dirección web de la declaración>`

## 6. Soporte técnico de seguridad

- Fin del periodo de soporte: **`<MM/AAAA>`**. Hasta esa fecha se publican actualizaciones de seguridad gratuitas. Detalles: [`support-period.md`](support-period.md).

## 7. Instrucciones

### Puesta en marcha segura
1. El equipo genera sus propias claves de host SSH en el primer arranque. Comprueba su huella la primera vez que te conectes.
2. Sustituye la clave de administración (`/home/admin/.ssh/authorized_keys` en la imagen) por la tuya antes de desplegar.
3. El equipo solo acepta conexiones SSH con clave y como `admin`; root está bloqueado. No hay otros servicios de red.
4. El cortafuegos solo permite la salida a DNS, DHCP, NTP y HTTPS. Si tu red necesita más, la regla se cambia en una nueva versión firmada de la imagen.

### Actualizaciones de seguridad
- Deja el paquete `.raucb` en `/data/updates/incoming/`. El equipo lo verifica (firma, compatibilidad, versión) y, si es válido, lo instala en la otra partición y reinicia.
- Estado de la última actualización: `/data/updates/status` y `/data/updates/last.log`.
- Si la versión nueva no arranca, el equipo vuelve solo a la anterior tras 3 intentos.
- No se pueden instalar versiones anteriores a la instalada.

### Comprobar el estado de seguridad
`cra-status` muestra la versión, si la raíz está verificada (dm-verity), el cortafuegos, los puertos abiertos, el arranque verificado y la partición activa.

### Retirada, venta o reciclaje: borrar todos los datos
```sh
ssh admin@<equipo> 'touch /data/updates/incoming/factory-reset.request'
```
El equipo borra la partición de datos (claves SSH, estado y datos del usuario), restablece el estado de arranque de fábrica y reinicia. La versión del sistema instalada se conserva.

### Información sobre componentes (SBOM)
- `<indicar si se publica el SBOM y dónde, o cómo se facilita a las autoridades de vigilancia del mercado>`.
- Cada versión incluye un SBOM CycloneDX y un documento VEX: [`vex/README.md`](vex/README.md).
