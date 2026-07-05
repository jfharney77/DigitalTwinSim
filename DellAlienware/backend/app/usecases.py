"""Worked use cases: things people actually do to an Alienware's power path.

Each ``UseCase`` walks a technically expert reader — one who has never
owned an Alienware — through a real workflow from Dell's support KBs. Every
step lists the anatomy regions it touches (``region_ids`` resolve against
anatomy.py; enforced by tests/test_catalog.py).
"""

from __future__ import annotations

from .models import SourceLink, UseCase, UseCaseStep

SUSTAINED_GPU = UseCase(
    id="sustained-gpu",
    title="Set up an m18 R2 for a sustained GPU workload",
    summary=(
        "An engineer commissions a new m18 R2 for a multi-hour GPU compute "
        "run: verify the adapter handshake, pick a thermal mode, and know "
        "in advance why the battery will drain a little while plugged in."
    ),
    persona=(
        "Experienced engineer, first Alienware. m18 R2 with i9-14900HX, "
        "RTX 4090 Laptop (175 W TGP), 97 Wh battery, 360 W SFF adapter."
    ),
    steps=[
        UseCaseStep(
            title="Plug in and check the adapter's own LED",
            body=(
                "The 360 W brick outputs 19.5 V at 18.46 A into the rear "
                "barrel jack. Before touching the laptop, glance at the LED "
                "ring on the plug: lit means the adapter is producing DC; "
                "dark or flickering means the fault is in the brick or "
                "cord, not the machine."
            ),
            region_ids=["dc-in"],
        ),
        UseCaseStep(
            title="Verify the PSID handshake in BIOS",
            body=(
                "F2 at the Alienware logo, then read the 'AC Adapter' "
                "field. It should say 360 W — the embedded controller "
                "learned that by reading the PSID chip in the brick over "
                "the barrel's center pin. 'Unknown' means that 1-Wire read "
                "failed (bent pin, damaged cable, third-party brick): "
                "expect slow or no charging and capped CPU/GPU power until "
                "it is fixed. On this machine an unverified adapter is not "
                "cosmetic — a sub-spec supply will run the battery down "
                "under load until under-voltage protection kills power."
            ),
            region_ids=["dc-in", "ec"],
        ),
        UseCaseStep(
            title="First boot — expect the fan blip",
            body=(
                "Both fans audibly spin to full for a moment at power-on. "
                "Dell documents this as working-as-designed self-test "
                "behavior. The power LED should settle to solid white: on "
                "AC with more than 5% battery."
            ),
            region_ids=["fan-left", "fan-right", "ec"],
        ),
        UseCaseStep(
            title="Set the charge policy for a desk-bound machine",
            body=(
                "This laptop will live on the adapter, so set 'Primarily "
                "AC Use' in Dell Power Manager / MyDell: the pack holds "
                "below 100% and ages slower. Before travel, switch back — "
                "ExpressCharge reaches about 80% in an hour with the lid "
                "closed, and ExpressCharge Boost does 0→35% in roughly "
                "20 minutes."
            ),
            region_ids=["battery", "charger"],
        ),
        UseCaseStep(
            title="Pick a thermal mode in Alienware Command Center",
            body=(
                "On the AWCC performance page choose 'Performance' for a "
                "sustained run — aggressive fan curve, long turbo "
                "residency. 'Full Speed' pins the fans at 100% and buys a "
                "little more sustained clock at maximum noise; 'Balanced' "
                "and 'Quiet' trade clocks for acoustics. Optionally set a "
                "TCC offset (0–15 °C) so the CPU throttles at, say, 95 °C "
                "instead of 100 °C for a quieter equilibrium."
            ),
            region_ids=["cpu", "gpu", "fan-left", "fan-right", "heatpipes"],
        ),
        UseCaseStep(
            title="Understand the plugged-in battery drain",
            body=(
                "During an hours-long CPU+GPU burn, Windows may show the "
                "battery slowly discharging on AC. This is hybrid power, "
                "by design: peak demand above the adapter's budget is "
                "served from the battery — up to about 5% per hour — "
                "inside the 94–100% band where the charger deliberately "
                "does not top back up. It only becomes a problem if the "
                "pack approaches 20%, where hybrid power disables and "
                "clocks drop instead. For multi-day unattended runs, "
                "adapter headroom (360 W over 280 W) is the fix."
            ),
            region_ids=["battery", "charger", "cpu", "gpu"],
        ),
        UseCaseStep(
            title="Monitor, and know what normal looks like",
            body=(
                "AWCC shows per-component temperature and frequency live. "
                "A CPU touching 99–100 °C with brief few-hundred-MHz dips "
                "is expected thermal-control behavior on this class of "
                "machine, not a fault. If something genuinely looks wrong, "
                "F12 at boot runs the ePSA pre-boot diagnostics, which "
                "test the adapter, battery, and thermals below the OS."
            ),
            region_ids=["cpu", "gpu", "heatpipes"],
        ),
    ],
    outcome=(
        "The machine sustains its full 175 W GPU budget on wall power with "
        "a verified adapter, the battery ages slowly under the AC-use "
        "charge policy, and the small plugged-in drain during peaks is "
        "understood as designed behavior rather than a defect."
    ),
    sources=[
        SourceLink(
            label="Dell — m18 R2 power adapter specs",
            url="https://www.dell.com/support/manuals/en-us/alienware-m18-r2-laptop/alienware-m18-r2-owners-manual/power-adapter",
        ),
        SourceLink(
            label="Dell KB — hybrid power / battery drain on AC",
            url="https://www.dell.com/support/kbdoc/en-us/000143915/alienware-15-r3-15-r4-17-r4-17-r5-m15-m17-performance-issue-or-battery-drain-while-ac-adapter-is-connected",
        ),
        SourceLink(
            label="Dell KB — thermal modes and TCC offset",
            url="https://www.dell.com/support/kbdoc/en-us/000198980/alienware-x15-r2-and-x17-r2-guide-to-thermal-controls-in-operating-modes-in-alienware-command-center",
        ),
        SourceLink(
            label="Dell KB — battery charge modes (ExpressCharge, Primarily AC Use)",
            url="https://www.dell.com/support/kbdoc/en-us/000123069/how-to-troubleshoot-dell-laptop-battery-issues",
        ),
    ],
)

NOT_CHARGING = UseCase(
    id="not-charging",
    title="Diagnose 'plugged in, not charging'",
    summary=(
        "Windows says the m18 is on AC but the battery percentage will not "
        "move. Working outward from the wall — adapter LED, port LED, BIOS "
        "adapter field, charge settings, then pre-boot diagnostics — finds "
        "the culprit without guesswork."
    ),
    persona=(
        "Support-minded owner or IT tech with an m18 that runs fine on AC "
        "but refuses to charge."
    ),
    steps=[
        UseCaseStep(
            title="Start at the brick: the plug LED",
            body=(
                "The LED ring on the barrel plug is the adapter's own "
                "health indicator, independent of the laptop. Off or "
                "flickering means the adapter or cord is the problem — "
                "check for frayed cable or bent pins and stop here. Lit "
                "means 19.5 V is reaching the plug and the fault is "
                "further in."
            ),
            region_ids=["dc-in"],
        ),
        UseCaseStep(
            title="Read the charging-port LED",
            body=(
                "The status LED tells you what the charger thinks it is "
                "doing: solid white means charging normally; amber means "
                "charging but the pack's health is degraded; blinking "
                "amber signals a battery or charging error; off on AC "
                "means either a full battery — or no power reaching the "
                "charge circuit at all."
            ),
            region_ids=["charger", "battery"],
        ),
        UseCaseStep(
            title="Check the BIOS 'AC Adapter' field",
            body=(
                "F2 into Setup. If the field reads 'Unknown', the EC could "
                "not read the PSID chip over the center pin — the single "
                "most common cause of charging being disabled while the "
                "machine still runs. The adapter delivers volts, but the "
                "platform will not charge a lithium pack from a supply "
                "whose rating it cannot verify. Try reseating the plug, "
                "then a known-good Dell adapter."
            ),
            region_ids=["dc-in", "ec"],
        ),
        UseCaseStep(
            title="Rule out settings that mimic the fault",
            body=(
                "Two look-alikes before suspecting hardware: the "
                "'Primarily AC Use' charge mode intentionally holds the "
                "battery below 100%, which reads as 'not charging' at the "
                "top of the range; and some models have an Fn+F2 hotkey "
                "that disables charging outright. Also confirm the battery "
                "is within its 0–50 °C charging window and the Intel MEI "
                "driver is current — both are documented causes."
            ),
            region_ids=["battery", "ec"],
        ),
        UseCaseStep(
            title="Run the pre-boot diagnostics",
            body=(
                "F12 at the Alienware logo → Diagnostics runs ePSA, which "
                "exercises the adapter, the battery (M-BIST, the battery's "
                "built-in self test), and the board below the OS — so a "
                "clean pass points the finger at software, and a failure "
                "gives Dell support the exact error to dispatch parts "
                "against. If the machine took a deep discharge on a weak "
                "adapter and now will not power on at all, that is "
                "under-voltage protection: 30+ minutes on a correct "
                "adapter, then hold power 30–35 seconds for an RTC reset "
                "(the LED flashes three times) before the next boot."
            ),
            region_ids=["ec", "battery", "dc-in"],
        ),
    ],
    outcome=(
        "The fault is localized to one of: the adapter/cord (plug LED), "
        "the PSID handshake (BIOS 'Unknown'), a deliberate charge-policy "
        "setting, or a battery the diagnostics can name — each with its "
        "documented fix, none requiring trial-and-error part swaps."
    ),
    sources=[
        SourceLink(
            label="Dell KB — AC adapter troubleshooting and LED states",
            url="https://www.dell.com/support/kbdoc/en-us/000125125/how-to-troubleshoot-ac-adapter-issues",
        ),
        SourceLink(
            label="Dell KB — laptop battery issues and charge modes",
            url="https://www.dell.com/support/kbdoc/en-us/000123069/how-to-troubleshoot-dell-laptop-battery-issues",
        ),
        SourceLink(
            label="Dell KB — UVP shutdown after the wrong adapter, RTC reset",
            url="https://www.dell.com/support/kbdoc/en-us/000218837/no-power-after-shut-down-using-the-incorrect-ac-adapter-on-alienware-gaming-laptops",
        ),
        SourceLink(
            label="Dell KB — Alienware does not power on (diagnostics flow)",
            url="https://www.dell.com/support/kbdoc/en-us/000179529/alienware-computer-does-not-turn-on-or-go-into-windows",
        ),
    ],
)

USE_CASES: list[UseCase] = [SUSTAINED_GPU, NOT_CHARGING]
