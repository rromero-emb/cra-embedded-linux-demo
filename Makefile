# Envoltorio de Buildroot para la demo CRA.
#   make            -> descarga Buildroot (si falta), configura y compila
#   make run        -> arranca la imagen en QEMU
#   make test       -> pruebas automáticas (arranque, endurecimiento, arranque verificado y actualizaciones A/B)
#   make ssh        -> entra en el equipo arrancado con `make run` (usuario admin)
#   make sbom       -> SBOM CycloneDX del producto y de compilación (output/sbom/)
#   make cve        -> vulnerabilidades (NVD) + VEX + informe; falla si hay críticas sin analizar
#   make br-<orden> -> orden directa de Buildroot (p. ej. br-uboot-dirclean)
#   make hooks      -> activa el hook que impide subir claves privadas

BR_VERSION   ?= 2025.02.18
BR_REPO      ?= https://gitlab.com/buildroot.org/buildroot.git
DEFCONFIG    ?= qemu_aarch64_cra_defconfig
TOP          := $(CURDIR)
BR_DIR       := $(TOP)/buildroot
O            := $(TOP)/output
export BR2_DL_DIR ?= $(TOP)/dl
VERSION      := $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
BR_MAKE      := $(MAKE) -C $(BR_DIR) O=$(O) BR2_EXTERNAL=$(TOP)/br2-external

.PHONY: all keys buildroot config build menuconfig savedefconfig run test ssh sbom cve hooks clean distclean

all: build

buildroot:
	@if [ ! -d $(BR_DIR) ]; then \
		git clone --depth 1 --branch $(BR_VERSION) $(BR_REPO) $(BR_DIR); \
	fi
	@test "$$(git -C $(BR_DIR) describe --tags)" = "$(BR_VERSION)" || \
		{ echo "Buildroot en $(BR_DIR) no es $(BR_VERSION)"; exit 1; }

$(O)/.config: br2-external/configs/$(DEFCONFIG) | buildroot
	$(BR_MAKE) $(DEFCONFIG)

config: $(O)/.config

keys:
	scripts/gen-dev-keys.sh

build: config keys
	$(BR_MAKE)

menuconfig: config
	$(BR_MAKE) menuconfig

savedefconfig: config
	$(BR_MAKE) savedefconfig BR2_DEFCONFIG=$(TOP)/br2-external/configs/$(DEFCONFIG)

run:
	scripts/run-qemu.sh $(O)/images

test:
	python3 scripts/tests/test_boot.py $(O)/images
	python3 scripts/tests/test_hardening.py $(O)
	python3 scripts/tests/test_verified_boot.py $(O)
	python3 scripts/tests/test_update.py $(O)

ssh:
	ssh -i keys/dev_ssh -p $${SSH_PORT:-2222} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@localhost

SBOM_DIR     := $(O)/sbom
CDX          := $(BR_DIR)/utils/generate-cyclonedx --project-name cra-demo --project-version $(VERSION)
NVD_DIR      ?= $(TOP)/nvd
FAIL_ON      ?= critical
KVULNS_DIR   ?= $(TOP)/kernel-vulns

# SBOM del producto (lo que va en el equipo) y SBOM de compilación (herramientas de host)
sbom: config
	mkdir -p $(SBOM_DIR)
	$(BR_MAKE) --no-print-directory -s show-info > $(SBOM_DIR)/show-info.json
	scripts/sbom/product-show-info.py $(O) < $(SBOM_DIR)/show-info.json | $(CDX) > $(SBOM_DIR)/sbom.cdx.json
	scripts/sbom/add-runtime-components.py $(SBOM_DIR)/sbom.cdx.json $(O)/target $(O)/host
	$(CDX) < $(SBOM_DIR)/show-info.json > $(SBOM_DIR)/sbom-build.cdx.json
	@python3 -c "import json;f=lambda p:len(json.load(open(p))['components']);print('SBOM producto:',f('$(SBOM_DIR)/sbom.cdx.json'),'componentes | SBOM compilación:',f('$(SBOM_DIR)/sbom-build.cdx.json'))"

# Vulnerabilidades: NVD (cve-check de Buildroot) + análisis VEX propio (security/vex/triage.json)
cve: sbom
	@test -d $(KVULNS_DIR)/cve || git clone -q --depth 1 https://git.kernel.org/pub/scm/linux/security/vulns.git $(KVULNS_DIR)
	$(BR_DIR)/support/scripts/cve-check --nvd-path $(NVD_DIR) \
		-i $(SBOM_DIR)/sbom.cdx.json -o $(SBOM_DIR)/sbom-vuln.cdx.json
	scripts/sbom/kernel-vex.py $(SBOM_DIR)/sbom-vuln.cdx.json $(KVULNS_DIR) \
		$$(ls -d $(O)/build/linux-[0-9]* | tail -1) -o $(SBOM_DIR)/kernel-triage.json
	scripts/sbom/vuln-report.py $(SBOM_DIR)/sbom-vuln.cdx.json --fail-on $(FAIL_ON) \
		--triage security/vex/triage.json --triage $(SBOM_DIR)/kernel-triage.json \
		--vex-out $(SBOM_DIR)/vex.cdx.json --report-out $(SBOM_DIR)/vulnerabilidades.md

hooks:
	git config core.hooksPath .githooks
	@echo "Hook pre-commit activado"

clean:
	$(BR_MAKE) clean

# Pasa cualquier orden a Buildroot: make br-linux-menuconfig, make br-uboot-dirclean...
br-%: config
	$(BR_MAKE) $*

distclean:
	rm -rf $(O)
