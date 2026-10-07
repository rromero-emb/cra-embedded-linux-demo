#!/bin/sh
# Genera las claves de DESARROLLO de la demo en ./keys (ignorado por git).
# En producción irían en un HSM/PKI y nunca en el equipo de compilación.
set -eu
KEYS="$(dirname "$0")/../keys"
mkdir -p "$KEYS" && chmod 700 "$KEYS"

# Acceso SSH de desarrollo (usuario admin)
if [ ! -f "$KEYS/dev_ssh" ]; then
	ssh-keygen -q -t ed25519 -N "" -C "cra-demo-dev-access" -f "$KEYS/dev_ssh"
	echo "Clave SSH de acceso de desarrollo: $KEYS/dev_ssh"
fi

# Firma del arranque (FIT): RSA-4096. mkimage busca <nombre>.key y <nombre>.crt en el directorio
mkdir -p "$KEYS/fit"
if [ ! -f "$KEYS/fit/cra-dev.key" ]; then
	openssl genrsa -out "$KEYS/fit/cra-dev.key" 4096 2>/dev/null
	openssl req -batch -new -x509 -days 3650 -subj "/CN=CRA demo boot signing (DEV)" \
		-key "$KEYS/fit/cra-dev.key" -out "$KEYS/fit/cra-dev.crt"
	chmod 600 "$KEYS/fit/cra-dev.key"
	echo "Clave de firma de arranque: $KEYS/fit/cra-dev.key"
fi
