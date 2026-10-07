#!/bin/sh
# Genera las claves de DESARROLLO de la demo en ./keys (ignorado por git).
# En producción las claves irían en un HSM/PKI y nunca en el equipo de compilación.
set -eu
KEYS="$(dirname "$0")/../keys"
mkdir -p "$KEYS" && chmod 700 "$KEYS"
if [ ! -f "$KEYS/dev_ssh" ]; then
	ssh-keygen -q -t ed25519 -N "" -C "cra-demo-dev-access" -f "$KEYS/dev_ssh"
	echo "Clave SSH de acceso de desarrollo: $KEYS/dev_ssh"
fi
