# RHB Banking Group — Malaysia

Open `setup.html` in a browser for the drawing.

The publicly reported facts: RHB is a featured Dell customer story for PowerProtect Cyber
Recovery — securing data with an air-gapped, immutable vault and AI-driven analytics
(CyberSense) so recoveries start from a provably clean copy. PowerProtect Cyber Recovery is
the first solution endorsed under the Sheltered Harbor standard for financial-sector data
vaulting and counts 1,300+ customers.

This setup is the one deployment pattern two of the repo's twins were explicitly built to
model as a pair: `DellPowerProtect/` (does a copy survive?) and `DellCyberDetect/`
(which copy is clean?).

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| Backup + air gap + vault + clean room | `DellPowerProtect/` | 5183 |
| CyberSense-style content analytics | `DellCyberDetect/` | 5192 |
| Production storage (representative) | `DellPowerStore/` | 5175 |
| Core-banking storage (representative) | `DellPowerMax/` | 5178 |

Note: PowerMax and CyberDetect share the 8005/5178 vs 8019/5192 port plan from CLAUDE.md;
PowerMax collides with PowerSwitchE3200 — run one at a time.

Sources:
- https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/powerprotect-cyber-recovery
- https://www.delltechnologies.com/asset/en-us/products/data-protection/industry-market/h18661-dell-powerprotect-cyber-recovery-reference-architecture-wp.pdf
- https://indexengines.com/products/cybersense-for-dell-technologies/
