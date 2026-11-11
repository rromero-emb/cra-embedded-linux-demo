# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

The image version (`IMAGE_VERSION` in `/usr/lib/os-release`) and the SBOM `project-version` come from `git describe`, so a tagged release build reports exactly its tag.

## [Unreleased]

## [1.0.0] - 2026-11-11

First tagged release. Covers the seven build sessions of the demo.

### Security
- Linux kernel 6.12.112 → **6.12.117** to fix **CVE-2026-64024** (critical, network-reachable TCP ISN prediction). The scheduled CVE gate in CI caught it; see [`pilots/0001-cve-2026-64024/REPORT.md`](pilots/0001-cve-2026-64024/REPORT.md). Open kernel CVEs after triage dropped from 60 to 28.

### Changed
- CI: GitHub Actions bumped to `checkout@v7`, `cache@v6`, `upload-artifact@v7` (Node 24 runtime); Dependabot keeps them current.

### Added
- **Session 7** – factory reset (user data wiped, new SSH host keys, A/B state reset) and compliance documentation: Annex I matrix, threat model, coordinated vulnerability disclosure, support period, art. 14 incident runbook.
- **Session 6** – read-only root filesystem verified with dm-verity; root hash signed inside the FIT image.
- **Session 5** – signed A/B updates with RAUC (verity bundles), anti-rollback and automatic fallback to the previous slot.
- **Session 4** – verified boot: signed FIT image (RSA-4096), locked-down U-Boot, four boot attacks tested in CI.
- **Session 3** – product SBOM (CycloneDX), CVE matching against NVD and the kernel CNA, VEX triage and a CI quality gate that fails on unanalysed critical CVEs.
- **Session 2** – system hardening: hardened compiler flags, kernel options, nftables default-drop, key-only SSH, no setuid binaries, sysctl.
- **Session 1** – Buildroot 2025.02 LTS image on QEMU aarch64, CI pipeline, basic SBOM.
- English README (`README.md`); Spanish version in `README.es.md`.

[Unreleased]: https://github.com/rromero-emb/cra-embedded-linux-demo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/rromero-emb/cra-embedded-linux-demo/releases/tag/v1.0.0
