# CRA demo · Embedded Linux

**English** · [Español](README.es.md)

[![build-and-test](https://github.com/rromero-emb/cra-embedded-linux-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/rromero-emb/cra-embedded-linux-demo/actions/workflows/ci.yml)

Reproducible demonstration of techniques for meeting the technical requirements of the **Cyber Resilience Act** (EU Regulation 2024/2847) on an embedded Linux device: verified boot, signed A/B updates, SBOM, vulnerability management and hardening.

> **Disclaimer:** this demo illustrates techniques for Annex I requirements. It does not make any product "CRA compliant": conformity is assessed per product and includes risk assessment, technical documentation and manufacturer processes. The harmonised standards (EN 40000 series) are still being drafted.

## Status

| Session | Content | Status |
|---|---|---|
| 1 | Base image on QEMU, CI, basic SBOM | ✅ |
| 2 | Hardening (kernel, binaries, firewall, key-only SSH, sysctl) | ✅ |
| 3 | Product SBOM, CVEs (NVD + kernel CNA), VEX and quality gate | ✅ |
| 4 | Verified boot: signed FIT (RSA-4096), locked-down U-Boot, 4 attacks tested | ✅ |
| 5 | Signed A/B updates (RAUC, verity), anti-rollback and automatic fallback | ✅ |
| 6 | Read-only root verified with dm-verity (root hash signed in the FIT) | ✅ |
| 7 | Factory reset and compliance documentation (Annex I, threats, CVD, support, art. 14) | ✅ |

## Quick start

Requirements (Debian/Ubuntu): `build-essential rsync bc cpio unzip file wget libssl-dev libgnutls28-dev python3 qemu-system-arm xxd`

```sh
make          # downloads Buildroot 2025.02.x (LTS) and builds
make run      # boots in QEMU (exit with Ctrl-a x)
make ssh      # in another terminal: log in as 'admin' with the development key
make test     # boot + hardening + boot attacks + dm-verity + A/B updates + wipe
make sbom     # CycloneDX SBOM of the product and of the build in output/sbom/
make cve      # vulnerabilities + VEX + report (fails on unanalysed critical CVEs)
make docs-check  # compliance docs only cite files and tests that exist
make hooks    # blocks commits containing private keys
```

## Hardening (session 2)

| Area | Measures |
|---|---|
| Binaries | PIE, `-fstack-protector-strong`, full RELRO, `_FORTIFY_SOURCE=2` |
| Kernel | KASLR, `HARDENED_USERCOPY`, `INIT_ON_ALLOC`, restricted `dmesg`, Yama; no `/dev/mem`, kexec or SysRq |
| Network | nftables with `drop` policy on input and output; only SSH (rate-limited), DHCP, DNS, NTP and HTTPS |
| Accounts | root locked; `admin` user with SSH key only; host keys generated on each device's first boot |
| System | no setuid (busybox included), no `crond`, hardened sysctl |

`make test` checks this on the **final image** (permissions read with `debugfs`) and on the running device (ports, firewall, SSH).

## Vulnerabilities and VEX (session 3)

`make cve` produces in `output/sbom/`:

| File | Content |
|---|---|
| `sbom.cdx.json` | **Product** SBOM (only what ships on the device, including glibc with its CPE) |
| `sbom-build.cdx.json` | Build SBOM (host tools) |
| `sbom-vuln.cdx.json` | SBOM enriched with NVD CVEs (Buildroot `cve-check`) |
| `vex.cdx.json` | VEX document: every CVE with its status and justification |
| `vulnerabilidades.md` | Human-readable report and quality-gate result |

How kernel CVEs are narrowed down to the ones that matter:

| | Kernel 6.12.27 | Kernel 6.12.112 |
|---|---|---|
| CVEs reported by NVD | 3,201 | 360 |
| Not affected: code not built (kernel CNA data + build `.o` files) | 2,531 | 169 |
| Fixed in this version / introduced later | 67 | 140 |
| **Open after analysis** | **589** | **~50** |

- Automatic kernel analysis: [`scripts/sbom/kernel-vex.py`](scripts/sbom/kernel-vex.py) with [linux/security/vulns.git](https://git.kernel.org/pub/scm/linux/security/vulns.git).
- Justified manual triage: [`security/vex/triage.json`](security/vex/triage.json).
- U-Boot upgraded to 2026.07 (maintainer's GPG signature verified) before trusting FIT signatures: CVE-2026-46728 allowed bypassing them in versions before 2026.04. U-Boot network stack removed.
- Weekly CI: re-scans even when the code does not change, because new CVEs keep appearing.

## Verified boot (session 4)

```
trusted firmware                              disk (untrusted)
┌─────────────────────────────────┐          ┌──────────────────────────────┐
│ u-boot.bin                      │  loads   │ /boot/fitImage               │
│ + control DT with the public    │ ───────► │  kernel + device tree        │
│   key (required = "conf")       │ verifies │  SHA-256 hashes              │
│ built-in boot order and         │          │  signed configuration        │
│ bootargs; no console            │          │  (RSA-4096)                  │
└─────────────────────────────────┘          └──────────────────────────────┘
```

- The FIT **configuration** is signed (not each image separately): this prevents mixing signed pieces from different versions.
- U-Boot only accepts signed FITs: no legacy format, no `booti`/`bootz`, no `bootflow` (it never runs a `boot.scr` from disk), environment in memory only, `bootdelay=-2`, and it **powers off** if verification fails (no console left).
- KASLR enabled: U-Boot injects a fresh `kaslr-seed` from `virtio-rng` on every boot.
- `make test` checks that these are rejected: 1 altered kernel byte · FIT signed with another key of the same name · unsigned FIT · bare kernel.

**Limits (honest):**
- With A/B, an attacker with disk access can choose between the two signed slots (e.g. the older one). RAUC's anti-rollback prevents *installing* old versions, but there is no anti-rollback counter at boot (that needs secure storage, e.g. RPMB/OTP).
- In QEMU the root of trust is the firmware (`u-boot.bin` + control DT, passed by QEMU with `-dtb`). On real hardware the SoC ROM or TF-A verifies that firmware with a key fused into OTP (an irreversible step).
- Keys are development keys (`make keys`, never in git). In production: HSM/PKI.
- QEMU with `-bios` and ACPI replaces the PL061 GPIO with ACPI GED: `acpi=off` is used so the machine matches the device tree.

## A/B updates (session 5)

```
 disk:  p1 system A │ p2 system B │ p3 bootstate (FAT) │ p4 data (ext4)
                                        BOOT_ORDER=A B
 U-Boot (built-in env) ──imports──►     BOOT_A_LEFT=3     ◄── RAUC (custom backend)
                                        BOOT_B_LEFT=3
```

- **RAUC** with bundles in **verity** format (`plain` is rejected): CMS signature with a **custom CA** (the signing certificate must be *Code Signing*), and every block verified with dm-verity during installation.
- **Anti-rollback**: a handler rejects bundles with a lower version than the installed one (an old version may be signed and still vulnerable).
- **Automatic fallback**: U-Boot decrements one attempt per boot; the system is marked good at the end of boot; if a slot runs out of its 3 attempts or its FIT fails verification, U-Boot switches to the other one.
- **A/B state does not open a door into boot**: U-Boot loads no environment from disk; from `bootstate.txt` it only imports `BOOT_ORDER`, `BOOT_A_LEFT` and `BOOT_B_LEFT` (`env import` with an allow-list). Boot order and kernel parameters stay built in.
- Fixed `init=/sbin/init`: if it fails, the kernel panics and reboots (counted as a failed attempt) instead of dropping to `/bin/sh`.
- An agent (such as an OTA client) installs whatever is dropped into `/data/updates/incoming`: it does not matter who drops it, only signed bundles get installed.

`make test` checks: bundle from another CA → rejected · old bundle → rejected · new bundle → boots into B · signed but broken bundle → 3 attempts and automatic fallback.

## Root verified with dm-verity (session 6)

```
slot (A or B, 160 MiB):
0 ─── read-only ext4 (128 MiB) ─── 128 ─ hash tree ─ 136 ─── signed FIT ─── 160 MiB
                                                                │ kernel
                                                                │ device tree + /chosen/cra,verity
                                                                │   (root hash + salt, signed)
U-Boot: reads the raw FIT → verifies the signature → extracts the root hash → dm-mod.create=... root=/dev/dm-0
```

- The kernel verifies **every root block as it is read**. A single altered byte → `data block N is corrupted` → reboot (`restart_on_corruption`) → counted as a failed A/B attempt → boots the other slot.
- The root hash lives inside the FIT's **signed** device tree; the FIT sits outside the verified area to avoid a circular dependency.
- No initramfs: the kernel creates the verity device at boot (`CONFIG_DM_INIT`).
- Read-only root; whatever must persist (SSH host keys, random seed, RAUC state) goes to `/data`.
- RAUC installs the whole slot (ext4 + hashes + FIT) as a raw image, inside a bundle that is itself verity.

`make test` alters 1 byte of `/bin/busybox` in slot A (without touching the FIT): dm-verity detects it and the device falls back to slot B on its own.

## Factory reset and documentation (session 7)

- **Secure data wipe** (Annex I 2(m)): `touch /data/updates/incoming/factory-reset.request` → the device overwrites and reformats `/data` (SSH keys, RAUC state, data), restores the factory A/B state and reboots. `make test` checks that the data is gone and that the SSH host keys are new.

| Document | Purpose |
|---|---|
| [`docs/annex-i-matrix.md`](docs/annex-i-matrix.md) | Each Annex I requirement → implementation → automated test → status (partial ones included) |
| [`docs/threat-model.md`](docs/threat-model.md) | STRIDE threat model: 20 threats, the mitigation and test for each, accepted risks |
| [`SECURITY.md`](SECURITY.md) | Coordinated vulnerability disclosure policy and reporting channel |
| [`docs/support-period.md`](docs/support-period.md) | Support period (art. 13): end of support for each component and migration plan |
| [`docs/incident-runbook.md`](docs/incident-runbook.md) | Reporting of actively exploited vulnerabilities and incidents (art. 14: 24 h / 72 h / final report) |
| [`docs/user-information.md`](docs/user-information.md) | User information template (Annex II) |
| [`docs/vex/README.md`](docs/vex/README.md) | How we decide whether a CVE applies and what each status means |

`make docs-check` (also in CI) fails if the matrix leaves any item uncovered or cites a file or test that does not exist: the documentation cannot fall behind the code.

**What a real product would still need** (details in the matrix): encryption of `/data`, an OTA client with automatic download, persistent and remote logging, a boot-time anti-rollback counter, a proper secure erase for the flash memory, and the risk assessment of the specific product.

> The compliance documents in `docs/` are written in Spanish.

## Technical base

- Buildroot **2025.02.x LTS** (supported until March 2028) as `BR2_EXTERNAL`
- QEMU aarch64 `virt`, U-Boot 2026.07 as firmware, Linux kernel 6.12.112 (LTS)
- Bootlin external toolchain (glibc, stable)

Full plan: [`docs/PLAN.md`](docs/PLAN.md)

## License

MIT. Buildroot and the packages it downloads keep their own licenses (see `make legal-info`).
