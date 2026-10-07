# Envoltorio de Buildroot para la demo CRA.
#   make            -> descarga Buildroot (si falta), configura y compila
#   make run        -> arranca la imagen en QEMU
#   make test       -> prueba automática de arranque
#   make sbom       -> genera el SBOM CycloneDX (output/sbom/)
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

.PHONY: all buildroot config build menuconfig savedefconfig run test sbom hooks clean distclean

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

build: config
	$(BR_MAKE)

menuconfig: config
	$(BR_MAKE) menuconfig

savedefconfig: config
	$(BR_MAKE) savedefconfig BR2_DEFCONFIG=$(TOP)/br2-external/configs/$(DEFCONFIG)

run:
	scripts/run-qemu.sh $(O)/images

test:
	python3 scripts/tests/test_boot.py $(O)/images

sbom: config
	mkdir -p $(O)/sbom
	$(BR_MAKE) --no-print-directory show-info | $(BR_DIR)/utils/generate-cyclonedx \
		--project-name cra-demo --project-version $(VERSION) > $(O)/sbom/sbom.cdx.json
	@python3 -c "import json;d=json.load(open('$(O)/sbom/sbom.cdx.json'));print('SBOM:',len(d.get('components',[])),'componentes ->','$(O)/sbom/sbom.cdx.json')"

hooks:
	git config core.hooksPath .githooks
	@echo "Hook pre-commit activado"

clean:
	$(BR_MAKE) clean

distclean:
	rm -rf $(O)
