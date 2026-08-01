# F1Soft — Kathmandu, Nepal

Open `setup.html` in a browser for the drawing.

The publicly reported facts: F1Soft, Nepal's leading fintech group (mobile banking and
digital payments for much of the country's banking sector), deployed Dell PowerFlex
software-defined storage in its data centers for performance, agility, scalability, and
reliability. CIO Akbar Khan, in Dell's customer story: "With PowerFlex, we've reduced the
time spent on routine tasks by around 40% — decreasing operational costs and allowing our
IT team to focus on strategic initiatives."

A payments platform is the canonical PowerFlex workload — the estate can never pause, and
the drawing centers on the failure/rebuild story: every surviving node repairs at once
while I/O keeps flowing.

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| PowerFlex pool | `DellPowerFlex/` | 5189 |
| What each node is (inferred) | `DellPowerEdgeR760/` | 5174 |
| IP fabric (representative) | `DellPowerSwitchSN6000/` | 5185 |
| Fleet observability (representative) | `DellCloudIQ/` | 5180 |

Sources:
- https://www.dell.com/en-us/lp/dt/customer-stories
- https://www.dell.com/en-us/dt/storage/powerflex.htm
- https://en.wikipedia.org/wiki/Dell_Technologies_PowerFlex
