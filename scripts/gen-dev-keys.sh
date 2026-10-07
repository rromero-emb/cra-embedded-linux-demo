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

# PKI de actualizaciones (RAUC): CA de desarrollo + certificado de firma emitido por ella.
# El equipo solo confía en la CA (keyring); los paquetes se firman con el certificado.
R="$KEYS/rauc"
mkdir -p "$R"
if [ ! -f "$R/ca.key" ]; then
	openssl req -batch -x509 -newkey rsa:4096 -nodes -days 3650 -sha256 \
		-subj "/CN=CRA demo update CA (DEV)" -keyout "$R/ca.key" -out "$R/ca.crt" \
		-addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
	openssl req -batch -newkey rsa:4096 -nodes -sha256 -subj "/CN=CRA demo update signing (DEV)" \
		-keyout "$R/signing.key" -out "$R/signing.csr" 2>/dev/null
	printf 'basicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=codeSigning\n' > "$R/ext.cnf"
	openssl x509 -req -in "$R/signing.csr" -CA "$R/ca.crt" -CAkey "$R/ca.key" -CAcreateserial \
		-days 1825 -sha256 -extfile "$R/ext.cnf" -out "$R/signing.crt" 2>/dev/null
	rm -f "$R/signing.csr" "$R/ext.cnf"
	chmod 600 "$R"/*.key
	echo "PKI de actualizaciones: $R (ca.crt va al equipo como keyring)"
fi
