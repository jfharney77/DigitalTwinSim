"""Pure AC power-path engine for the Alienware laptop digital twin.

``simulate()`` returns the deterministic trace of what happens inside the
laptop from the moment the AC adapter is plugged in: plug detect, the
1-Wire PSID handshake, the EC's power-budget decision, the Li-ion charge
ramp, boot, workload ramp, and — when demand exceeds the adapter — hybrid
power, where the battery supplements the wall. Same purity rule as the GPU
and R760 engines: no FastAPI, no IO, no timers — the frontend owns the
playback clock, and each ``PowerState`` is plain data the renderer
consumes. ``cycle_cost`` marks the long stages (the handshake, the
constant-current charge bulk) so the UI dwells on them.

Every emitted state satisfies the energy invariant exactly:

    acW + batteryW == systemW + chargeW

(``ac_w`` is derived from the other three, never set independently), and
``acW`` never exceeds the adapter's rated wattage. Wattages and charge
rates are illustrative but anchored to Dell's published figures (280/360 W
adapters, 97 Wh pack, ExpressCharge ~80% in an hour); per the project's
scope guardrails, favor a correct mental model over measured numbers.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    AdapterOption,
    ChargeStage,
    LaptopProfile,
    PowerState,
    Scenario,
    Summary,
)

# Fraction of the silicon's max power each AWCC thermal mode allows to be
# sustained (illustrative; the real knobs are fan curves + TCC offsets).
THERMAL_CAP: dict[str, float] = {
    "quiet": 0.45,
    "balanced": 0.65,
    "performance": 0.85,
    "fullSpeed": 1.0,
}

# Baseline fan duty per mode once the OS is up. "Full Speed" is literally
# fans pinned at 100% (Dell's own description of the mode).
FAN_BASE: dict[str, float] = {
    "quiet": 22.0,
    "balanced": 35.0,
    "performance": 60.0,
    "fullSpeed": 100.0,
}

# Workload → (fraction of CPU cap, fraction of GPU cap).
WORKLOAD_FRAC: dict[str, tuple[float, float]] = {
    "idle": (0.0, 0.0),
    "gaming": (0.6, 1.0),  # GPU-bound: GPU pegged, CPU partial
    "fullLoad": (1.0, 1.0),  # synthetic burn: both pegged
}

EC_STANDBY_W = 3.0  # the embedded controller's keep-alive draw
CPU_IDLE_FLOOR_W = 6.0  # a booted OS never truly reaches 0 W on the CPU
# Hard caps the EC applies when the adapter is "Unknown" — it will not
# budget power it cannot verify.
THROTTLED_CPU_W = 25.0
THROTTLED_GPU_W = 10.0
# ExpressCharge constant-current bulk rate [inferred from "~80% in 1 h" on
# a 97 Wh pack]; Standard-charge packs get a gentler rate.
CC_EXPRESS_W = 90.0
CC_STANDARD_W = 60.0
HOLD_BAND_PCT = 94.0  # above this, charging holds off (anti-cycling band)
HYBRID_FLOOR_PCT = 20.0  # below this, hybrid disables and the system throttles


def _cc_rate(profile: LaptopProfile, adapter: AdapterOption) -> float:
    """Constant-current charge power the charger IC will ask for."""
    target = CC_EXPRESS_W if profile.battery.express_charge else CC_STANDARD_W
    return max(0.0, min(target, adapter.watts - EC_STANDBY_W))


def simulate(
    profile: LaptopProfile, adapter: AdapterOption, scenario: Scenario
) -> list[PowerState]:
    """The laptop's journey from unplugged to steady state, as pure data."""
    states: list[PowerState] = []
    pct = float(scenario.start_battery_pct)
    mode = scenario.thermal_mode
    budget = float(adapter.watts)
    recognized = adapter.recognized
    cc_w = _cc_rate(profile, adapter)

    def emit(
        *,
        phase: str,
        stage_id: str,
        label: str,
        description: str,
        active: list[str],
        system_w: float = 0.0,
        charge_w: float = 0.0,
        battery_w: float = 0.0,
        charge_stage: ChargeStage = "idle",
        cpu_w: float = 0.0,
        gpu_w: float = 0.0,
        fan_pct: float = 0.0,
        hybrid: bool = False,
        stalled: bool = False,
        cycle_cost: int = 1,
    ) -> None:
        # Round the independent terms first, then derive acW, so the energy
        # invariant holds exactly on the wire, not just before rounding.
        system_w = round(system_w, 1)
        charge_w = round(charge_w, 1)
        battery_w = round(battery_w, 1)
        ac_w = round(system_w + charge_w - battery_w, 1)
        states.append(
            PowerState(
                cycle=len(states),
                phase=phase,
                stage_id=stage_id,
                label=label,
                description=description,
                active_regions=active,
                ac_w=ac_w,
                system_w=system_w,
                charge_w=charge_w,
                battery_w=battery_w,
                battery_pct=round(pct, 1),
                charge_stage=charge_stage,
                cpu_w=round(cpu_w, 1),
                gpu_w=round(gpu_w, 1),
                fan_pct=round(min(max(fan_pct, 0.0), 100.0), 1),
                hybrid=hybrid,
                stalled=stalled,
                cycle_cost=cycle_cost,
            )
        )

    def topup(system_w: float) -> tuple[float, ChargeStage]:
        """Background charging while the system runs, within the AC budget."""
        nonlocal pct
        if not recognized:
            return 0.0, "idle"
        if pct >= HOLD_BAND_PCT:
            return 0.0, "full"  # 94–100% anti-cycling hold band
        headroom = max(0.0, min(cc_w, budget - system_w))
        if headroom <= 0.0:
            return 0.0, "idle"
        pct = min(pct + headroom * 0.02, HOLD_BAND_PCT)
        return headroom, ("cc" if pct < 80.0 else "cv")

    # ---- off: S0 --------------------------------------------------------
    emit(
        phase="off",
        stage_id="s0-unplugged",
        label="Unplugged",
        description=L(
            novice=(
                "The laptop is switched off and running on its own battery. Inside "
                "it, one small chip never sleeps: the embedded controller, which "
                "looks after power, charging, the fans, and the keyboard. It draws "
                "a couple of watts from the battery pack through the circuitry "
                "that decides where power comes from. Everything else in the "
                "machine is dark."
            ),
            plain=(
                "The laptop is shut down and on its own battery. The embedded "
                "controller — the always-on microcontroller managing power, "
                "charging, fans, and the keyboard — sips a few watts from the pack "
                "through the power-path controller. Everything else is dark."
            ),
            standard=(
                "The laptop is shut down and on its own battery. The EC "
                "(embedded controller) — the always-on microcontroller that "
                "manages power, charging, fans, and the keyboard — sips a few "
                "watts from the pack through the power-path controller. "
                "Everything else is dark."
            ),
            technical=(
                "Shut down, on battery. The EC — always-on microcontroller owning "
                "power, charging, thermal, and keyboard — draws a few watts from "
                "the pack through the power-path controller. All other rails down."
            ),
            expert=(
                "Off, on battery. EC alive on pack power through the power-path "
                "controller; all other rails down."
            ),
        ),
        active=["ec", "battery"],
        system_w=EC_STANDBY_W,
        battery_w=EC_STANDBY_W,
    )

    # ---- detect: S1 + S2 ------------------------------------------------
    emit(
        phase="detect",
        stage_id="s1-ac-convert",
        label="Adapter converts AC to 19.5 V",
        description=L(
            novice=(
                f"The {adapter.name} converts the alternating current from the "
                f"wall into a steady {adapter.voltage:g} volts of direct current, "
                f"at up to {adapter.amps:g} amps. The ring of light on the plug "
                "comes on, confirming the brick is producing output before the "
                "laptop is involved at all. The embedded controller is still "
                "running off the battery."
            ),
            plain=(
                f"The {adapter.name} rectifies wall AC into a regulated "
                f"{adapter.voltage:g} V DC at up to {adapter.amps:g} A. The LED "
                "ring on the plug lights, confirming the brick produces output "
                "before the laptop is involved. The EC still runs from the battery."
            ),
            standard=(
                f"The {adapter.name} rectifies wall AC to a regulated "
                f"{adapter.voltage:g} V DC at up to {adapter.amps:g} A. The LED "
                "ring on the plug lights, confirming the brick is producing "
                "output before the laptop is even involved. The EC is still "
                "running from the battery."
            ),
            technical=(
                f"The {adapter.name} rectifies mains AC to a regulated "
                f"{adapter.voltage:g} V DC, {adapter.amps:g} A maximum. Plug LED "
                "confirms output independently of the host. EC remains on pack "
                "power."
            ),
            expert=(
                f"{adapter.name}: AC rectified to {adapter.voltage:g} V DC at "
                f"{adapter.amps:g} A max. Output confirmed host-independently; EC "
                "still on pack."
            ),
        ),
        active=["dc-in"],
        system_w=EC_STANDBY_W,
        battery_w=EC_STANDBY_W,
    )
    emit(
        phase="detect",
        stage_id="s2-plug-detect",
        label="DC-in detect",
        description=L(
            novice=(
                "The plug goes into the socket. The outer sleeve is the ground "
                "connection, the inner sleeve carries the positive voltage, and a "
                "third pin in the very centre carries a single data wire. The "
                "embedded controller senses voltage arriving and immediately "
                "switches its own small draw from the battery over to the "
                "adapter — the first current this laptop takes from the wall."
                if adapter.connector == "barrel"
                else "The USB-C plug goes into the Thunderbolt port. Unlike the "
                "round barrel socket there is no separate identification pin here, "
                "so working out what the charger can do will have to happen "
                "through the USB Power Delivery conversation instead. The "
                "controller senses voltage on the port and shifts its own draw "
                "across to it."
            ),
            plain=(
                "The plug seats in the DC-in jack: outer barrel is ground, inner "
                "barrel is +19.5 V, and a third centre pin carries a 1-Wire data "
                "line. The EC senses voltage on the DC-in rail and immediately "
                "shifts its own few-watt draw from battery to adapter — the first "
                "current the laptop takes from the wall."
                if adapter.connector == "barrel"
                else "The USB-C plug seats in the Thunderbolt port. Unlike the "
                "barrel jack there is no dedicated identification pin, so "
                "identification happens through the USB Power Delivery protocol "
                "itself. The EC senses bus voltage and shifts its own draw to the "
                "port."
            ),
            standard=(
                "The plug seats in the DC-in jack: outer barrel is ground, "
                "inner barrel is +19.5 V, and a third center pin carries a "
                "1-Wire data line. The EC senses voltage on the DC-in rail and "
                "immediately shifts its own few-watt draw from battery to "
                "adapter — the first current the laptop takes from the wall."
                if adapter.connector == "barrel"
                else "The USB-C plug seats in the Thunderbolt port. Unlike the "
                "barrel jack there is no dedicated ID pin; identification will "
                "happen through the USB Power Delivery protocol itself. The EC "
                "senses bus voltage and shifts its own draw to the port."
            ),
            technical=(
                "Plug seated: outer barrel ground, inner +19.5 V, centre pin a "
                "1-Wire data line. The EC detects DC-in and transfers its own draw "
                "from pack to adapter — first current drawn from the wall."
                if adapter.connector == "barrel"
                else "USB-C seated in the Thunderbolt port. No dedicated ID pin, "
                "so identification defers to USB PD negotiation. EC detects bus "
                "voltage and transfers its draw to the port."
            ),
            expert=(
                "DC-in seated; barrel ground/+19.5 V plus a 1-Wire centre pin. EC "
                "transfers its own draw from pack to adapter."
                if adapter.connector == "barrel"
                else "USB-C seated. No ID pin — identification deferred to PD "
                "negotiation. EC transfers draw to the port."
            ),
        ),
        active=["dc-in", "ec"],
        system_w=EC_STANDBY_W,
    )

    # ---- handshake: S3 --------------------------------------------------
    emit(
        phase="handshake",
        stage_id="s3-psid-handshake",
        label="PSID handshake"
        if adapter.connector == "barrel"
        else "USB-PD contract",
        description=L(
            novice=(
                "Through that centre pin, the controller reads the adapter's "
                "identity — a tiny memory chip inside the brick, powered by the "
                "data line itself, holding the adapter's family, wattage, voltage "
                "and current, with a checksum to catch corruption. Reading it is "
                "slow by the standards of silicon, which is why the BIOS screen "
                "takes a moment before its 'AC Adapter' line fills in."
                if adapter.connector == "barrel"
                else "The laptop and the charger negotiate a contract using USB "
                "Power Delivery: the charger advertises the voltage and current "
                "combinations it supports, and the controller picks the highest on "
                "offer — here 20 volts at 5 amps, so 100 watts. This digital "
                "conversation replaces the identification pin on the round "
                "socket — but it also caps the budget at whatever that standard "
                "can carry."
            ),
            plain=(
                "Over the centre pin the EC reads the adapter's PSID — a tiny "
                "1-Wire memory inside the brick, powered by the data line itself, "
                "encoding adapter family, wattage, voltage and current, protected "
                "by a checksum. The read is slow by silicon standards, which is "
                "why BIOS takes a moment to fill in its 'AC Adapter' field."
                if adapter.connector == "barrel"
                else "The laptop and charger negotiate a USB Power Delivery "
                "contract: the charger advertises its supported voltage and "
                "current pairs, and the EC selects the highest — here 20 V at 5 A "
                "for 100 W. This negotiation replaces the barrel jack's ID pin, "
                "and also caps the budget at what PD can carry."
            ),
            standard=(
                "Over the center pin, the EC reads the adapter's PSID (power "
                "supply ID) — a tiny 1-Wire EEPROM inside the brick, parasite-"
                "powered by the data line itself, encoding adapter family, "
                "wattage, voltage, and current, protected by a CRC. This read "
                "is slow by silicon standards, which is why BIOS takes a "
                "moment before its 'AC Adapter' field fills in."
                if adapter.connector == "barrel"
                else "The laptop and charger negotiate a USB Power Delivery "
                "contract: the charger advertises its supported voltage/current "
                "pairs and the EC picks the highest, here 20 V at 5 A for "
                "100 W. This digital negotiation replaces the barrel jack's "
                "PSID pin — but it also caps the budget at what PD can carry."
            ),
            technical=(
                "EC reads the PSID over the 1-Wire centre pin — a parasite-powered "
                "EEPROM in the brick encoding family, wattage, voltage and "
                "current, CRC-protected. The read is slow enough to be visible as "
                "the delay before BIOS populates its 'AC Adapter' field."
                if adapter.connector == "barrel"
                else "USB PD contract negotiated: the source advertises its PDOs "
                "and the EC selects the highest, 20 V at 5 A for 100 W. Replaces "
                "the barrel ID pin and bounds the budget at what PD can carry."
            ),
            expert=(
                "PSID read over 1-Wire: parasite-powered EEPROM, family/wattage/"
                "voltage/current, CRC-protected. Read latency is the BIOS 'AC "
                "Adapter' field delay."
                if adapter.connector == "barrel"
                else "PD contract negotiated — highest advertised PDO, 20 V/5 A, "
                "100 W. Replaces the ID pin; bounds the budget at PD's ceiling."
            ),
        ),
        active=["dc-in", "ec"],
        system_w=EC_STANDBY_W,
        stalled=True,
        cycle_cost=4,
    )

    # ---- budget: S4 + S5 ------------------------------------------------
    if recognized:
        budget_desc = (
            f"The CRC checks out: the EC now knows it has a genuine "
            f"{adapter.watts:g} W supply and sets the platform's power "
            "budget accordingly — full charge rate and full CPU/GPU limits "
            "are on the table. BIOS Setup would show this adapter by name "
            "under 'AC Adapter'."
        )
        if budget < profile.cpu_max_w + profile.gpu_tgp_w + profile.idle_w:
            budget_desc += (
                " The budget is real but modest for this silicon: if CPU "
                "and GPU both hit their limits at once, demand will exceed "
                "the adapter and the battery will have to supplement."
            )
    else:
        budget_desc = (
            "The ID read fails — a damaged center pin or a brick with no "
            "PSID chip. BIOS reports the adapter as 'Unknown'. The EC will "
            "take current from the rail but refuses to trust its rating: "
            "battery charging is disabled and CPU/GPU power limits are "
            f"capped near {THROTTLED_CPU_W + THROTTLED_GPU_W:g} W. Wattage "
            "the platform can't verify is wattage it won't budget for."
        )
    emit(
        phase="budget",
        stage_id="s4-power-budget",
        label="EC sets the power budget",
        description=budget_desc,
        active=["ec", "charger"],
        system_w=EC_STANDBY_W,
    )
    emit(
        phase="budget",
        stage_id="s5-power-path",
        label="Power path switches to AC",
        description=L(
            novice=(
                "The charging chip — the component sitting between the incoming "
                "power, the battery, and the rest of the machine — switches the "
                "laptop's load fully onto the adapter, and if the budget allows, "
                "turns on the stage that pushes power toward the battery. From "
                "this point the battery only discharges when the controller "
                "specifically asks it to."
            ),
            plain=(
                "The charger IC — the power-path controller between the DC-in "
                "rail, the battery, and the system — switches the system load "
                "fully onto the adapter rail and, if the budget allows, enables "
                "its converter stage toward the battery. From here the battery "
                "only discharges when the EC asks it to."
            ),
            standard=(
                "The charger IC — the power-path controller between the DC-in "
                "rail, the battery, and the system — switches the system load "
                "fully onto the adapter rail and, if the budget allows, enables "
                "its buck converter stage toward the battery. From here on the "
                "battery only discharges when the EC asks it to."
            ),
            technical=(
                "The charger IC transfers system load fully to the adapter rail "
                "and, budget permitting, enables the buck stage toward the pack. "
                "Pack discharge becomes EC-directed rather than incidental."
            ),
            expert=(
                "Charger IC moves system load to the adapter rail; buck stage to "
                "the pack enabled if budget allows. Discharge becomes EC-directed."
            ),
        ),
        active=["ec", "charger", "battery"],
        system_w=EC_STANDBY_W,
    )

    # ---- charge: S6 (+S7) -----------------------------------------------
    # The machine charges lid-closed before boot in this trace; the EC and
    # charger are the only consumers, so nearly the whole budget can go to
    # the pack.
    if not recognized:
        emit(
            phase="charge",
            stage_id="s6-charge-disabled",
            label="Charging disabled — unknown adapter",
            description=L(
                novice=(
                    "Because the adapter could not be identified, the controller keeps "
                    "the charging stage switched off altogether. Pushing 90 watts into "
                    "a lithium battery from a supply whose real capability is unknown "
                    "is a fire risk, and the firmware will not take it. Windows will "
                    "later report 'plugged in, not charging'. The battery simply holds "
                    f"where it is, at {pct:.0f}%."
                ),
                plain=(
                    "With the adapter unidentified, the EC keeps the charging stage "
                    "off entirely: pushing 90 W into a lithium pack from a supply of "
                    "unverified capability is a fire risk it will not take. Windows "
                    "will later show 'plugged in, not charging'. The battery holds at "
                    f"{pct:.0f}%."
                ),
                standard=(
                    "With the adapter unidentified, the EC keeps the charging "
                    "stage off entirely: pushing 90 W into a lithium pack from "
                    "a supply of unverified capability is a fire risk it will "
                    "not take. Windows will later show 'plugged in, not "
                    "charging'. The battery simply holds at "
                    f"{pct:.0f}%."
                ),
                technical=(
                    "Adapter unidentified, so the charging stage stays disabled — "
                    "delivering 90 W into a lithium pack from a supply of unverified "
                    "capability is not a risk the firmware accepts. Presents as "
                    f"'plugged in, not charging'. Pack holds at {pct:.0f}%."
                ),
                expert=(
                    "Unidentified adapter: charging stage disabled. 90 W into lithium "
                    "from an unverified source is refused by firmware. Presents as "
                    f"'plugged in, not charging'; pack holds at {pct:.0f}%."
                ),
            ),
            active=["charger", "battery", "ec"],
            system_w=EC_STANDBY_W,
        )
    elif pct >= HOLD_BAND_PCT:
        emit(
            phase="charge",
            stage_id="s7-full-hold",
            label="Full — hold band",
            description=L(
                novice=(
                    "The battery is already in the 94-to-100% holding band, so the "
                    "charger stays off. Dell's firmware will not start charging again "
                    "until the level falls below about 94%, which avoids the shallow "
                    "repeated top-ups that wear lithium cells out early. The status "
                    "light is dark — on mains power with a full battery, that is the "
                    "normal indication rather than a fault."
                ),
                plain=(
                    "The battery is already sitting in the 94-to-100% holding band, so "
                    "the charger stays off. Dell's firmware will not restart charging "
                    "until the level drops below about 94%, which avoids the shallow "
                    "repeated top-ups that wear lithium cells out early. The status "
                    "LED being dark is the normal indication on mains power with a "
                    "full battery, not a fault."
                ),
                standard=(
                    "The pack is already in the 94–100% hold band, so the "
                    "charger stays off: Dell's firmware will not resume "
                    "charging until the battery falls below ~94%, avoiding the "
                    "shallow micro-cycles that age lithium cells. The status "
                    "LED is dark — on AC with a full battery, that is the "
                    "normal indication."
                ),
                technical=(
                    "Pack within the 94–100% hold band, so the charger remains off "
                    "until it falls below ~94%. The hysteresis exists to avoid "
                    "shallow micro-cycling, which is disproportionately hard on "
                    "lithium cells. Dark status LED is nominal here, not a fault."
                ),
                expert=(
                    "In the 94–100% hold band; charger off until <94%. Hysteresis "
                    "avoids micro-cycling. Dark LED is nominal."
                ),
            ),
            active=["charger", "battery"],
            system_w=EC_STANDBY_W,
            charge_stage="full",
        )
    else:
        if pct < 10.0:
            pct = min(pct + 2.0, 100.0)
            emit(
                phase="charge",
                stage_id="s6-precharge",
                label="Precharge",
                description=L(
                    novice=(
                        "The battery is very low, so the charger begins gently: a trickle "
                        "of a few watts brings the cell voltage up to the point where "
                        "full-rate charging becomes safe. A lithium cell below its minimum "
                        "voltage cannot take a large current without being damaged, so "
                        "this stage is the battery management system being careful rather "
                        "than being slow."
                    ),
                    plain=(
                        "The pack is deeply discharged, so the charger starts gently: a "
                        "trickle of a few watts brings cell voltage up to the point where "
                        "full-rate charging is safe. Li-ion cells below their minimum "
                        "voltage cannot take bulk current without damage — this stage is "
                        "the battery management system being careful."
                    ),
                    standard=(
                        "The pack is deeply discharged, so the charger starts "
                        "gently: a trickle of a few watts brings the cell "
                        "voltage up to the point where full-rate charging is "
                        "safe. Li-ion cells below their minimum voltage cannot "
                        "take bulk current without damage — this stage is the "
                        "battery management system being careful."
                    ),
                    technical=(
                        "Deeply discharged pack, so the charger enters precharge: a "
                        "few-watt trickle raises cell voltage to the bulk-charge "
                        "threshold. Below minimum cell voltage, bulk current is damaging, "
                        "so the BMS gates it."
                    ),
                    expert=(
                        "Precharge: few-watt trickle to the bulk threshold. Bulk current "
                        "below minimum cell voltage is damaging; BMS gates it."
                    ),
                ),
                active=["charger", "battery"],
                system_w=EC_STANDBY_W,
                charge_w=8.0,
                charge_stage="precharge",
                cycle_cost=2,
            )
        for i in (1, 2):
            pct = min(pct + cc_w * 0.2, HOLD_BAND_PCT)
            emit(
                phase="charge",
                stage_id=f"s6-charge-cc-{i}",
                label=f"Constant current · bulk charge ({i}/2)",
                description=L(
                    novice=(
                        f"The main part of the charge: the charger holds a steady "
                        f"{cc_w:.0f} watts into the battery while the cell voltage climbs. "
                        "This is the fast-charge regime — roughly 80% in an hour with the "
                        "lid closed, and 0 to 35% in about twenty minutes — and it is the "
                        "part where you actually see the battery percentage moving."
                        if profile.battery.express_charge
                        else f"The main part of the charge, at a steady {cc_w:.0f} watts "
                        "of constant current while the cell voltage climbs."
                    ),
                    plain=(
                        f"The main part of the charge: a constant ~{cc_w:.0f} W flows into "
                        "the pack while cell voltage rises. This is the ExpressCharge "
                        "regime — around 80% in an hour with the lid closed, and 0 to 35% "
                        "in roughly twenty minutes — and it is the stretch where the "
                        "battery percentage visibly moves."
                        if profile.battery.express_charge
                        else f"The main part of the charge: a steady ~{cc_w:.0f} W of "
                        "constant current while cell voltage rises."
                    ),
                    standard=(
                        f"The bulk of the charge: the charger holds a constant "
                        f"~{cc_w:.0f} W into the pack while cell voltage rises. "
                        "This is the ExpressCharge regime — roughly 80% in an "
                        "hour with the lid closed, 0→35% in about 20 minutes — "
                        "and it is where the battery percentage visibly climbs."
                        if profile.battery.express_charge
                        else f"The bulk of the charge at a steady ~{cc_w:.0f} W "
                        "constant current while cell voltage rises."
                    ),
                    technical=(
                        f"Constant-current bulk phase at ~{cc_w:.0f} W while cell voltage "
                        "rises. ExpressCharge regime — ~80% in an hour lid-closed, 0→35% "
                        "in ~20 minutes — and the segment where indicated percentage moves "
                        "fastest."
                        if profile.battery.express_charge
                        else f"Constant-current bulk phase at ~{cc_w:.0f} W while cell "
                        "voltage rises."
                    ),
                    expert=(
                        f"CC bulk at ~{cc_w:.0f} W. ExpressCharge: ~80% in 1 h lid-closed, "
                        "0→35% in ~20 min."
                        if profile.battery.express_charge
                        else f"CC bulk at ~{cc_w:.0f} W."
                    ),
                ),
                active=["charger", "battery"],
                system_w=EC_STANDBY_W,
                charge_w=cc_w,
                charge_stage="cc",
                stalled=True,
                cycle_cost=4,
            )
        pct = min(pct + 3.0, 99.0)
        emit(
            phase="charge",
            stage_id="s6-charge-cv",
            label="Constant voltage · taper",
            description=L(
                novice=(
                    "Near the top of the charge the charger changes strategy: instead "
                    "of holding the power steady it holds the voltage steady, and lets "
                    "the current fall away naturally as the battery fills. This is why "
                    "the last twenty percent always seems to take disproportionately "
                    "long — the current is deliberately tapering off."
                ),
                plain=(
                    "Near the top of the charge the charger changes approach: it holds "
                    "the pack at its maximum cell voltage and allows the current to "
                    "fall away on its own. The final 20% always takes "
                    "disproportionately long, and this taper is the reason."
                ),
                standard=(
                    "Near the top of the charge the charger switches to "
                    "constant voltage: it holds the pack at its maximum cell "
                    "voltage and lets the current taper off naturally. The "
                    "last 20% always takes disproportionately long — this "
                    "taper is why."
                ),
                technical=(
                    "Transition to constant-voltage: the charger clamps at maximum "
                    "cell voltage and current tapers asymptotically. The "
                    "disproportionate duration of the final 20% is this taper, not a "
                    "fault or a throttle."
                ),
                expert=(
                    "CV phase: clamped at max cell voltage, current tapers "
                    "asymptotically. Accounts for the long final 20%."
                ),
            ),
            active=["charger", "battery"],
            system_w=EC_STANDBY_W,
            charge_w=cc_w * 0.35,
            charge_stage="cv",
            cycle_cost=2,
        )

    # ---- boot -----------------------------------------------------------
    rails_w = 40.0
    c_w, c_stage = topup(rails_w)
    emit(
        phase="boot",
        stage_id="boot-rails",
        label="Power button — rails sequence, fans blip",
        description=L(
            novice=(
                "The power button — the alien head — is simply an input to the "
                "embedded controller. It brings the main power rails up in a "
                "strict order: memory first, then the chipset, then the processor "
                "regulators. Both fans blip briefly to full speed. That is a "
                "documented self-test on start-up, working as designed, not a "
                "fault."
            ),
            plain=(
                "The power button (the alien head) is just an input to the EC. "
                "The EC sequences the main rails up in strict order — memory, "
                "chipset, CPU voltage regulators — and both fans blip briefly to "
                "full speed, a documented working-as-designed spin-up self-test, "
                "not a fault."
            ),
            standard=(
                "The power button (the alien head) is just an input to the EC. "
                "The EC sequences the main rails up in strict order — memory, "
                "chipset, CPU voltage regulators — and both fans blip briefly "
                "to full speed, a documented working-as-designed self-test "
                "spin-up, not a fault."
            ),
            technical=(
                "The power button is an EC input like any other. The EC sequences "
                "the main rails in order — memory, chipset, CPU VRs — and both "
                "fans blip to full as a documented spin-up self-test rather than a "
                "fault indication."
            ),
            expert=(
                "Power button is an EC input. Rails sequenced memory → chipset → "
                "CPU VRs; fan blip is a documented spin-up self-test."
            ),
        ),
        active=["ec", "cpu", "fan-left", "fan-right"],
        system_w=rails_w,
        charge_w=c_w,
        charge_stage=c_stage,
        cpu_w=8.0,
        fan_pct=100.0,
    )
    post_w = 48.0
    c_w, c_stage = topup(post_w)
    bios_adapter_field = (
        f"{adapter.watts:g} W" if recognized else "'Unknown'"
    )
    emit(
        phase="boot",
        stage_id="boot-post",
        label="POST",
        description=L(
            novice=(
                "The BIOS runs its start-up self-test on the memory, the display "
                "path, and the storage. If any of it fails, the power light "
                "flashes a red-and-blue code — 2 then 3 means no memory, 3 then 5 "
                "means a power-rail failure — instead of booting. On success the "
                "Alienware logo appears with the prompt to press F2 for setup, "
                f"where the 'AC Adapter' field now reads {bios_adapter_field}."
            ),
            plain=(
                "BIOS runs its power-on self-test across memory, the display path, "
                "and storage. A failure here blinks a red and blue code on the "
                "power LED rather than booting — 2,3 means no memory, 3,5 means a "
                "power-rail failure. On success the Alienware logo appears with "
                "the F2 Setup prompt, and the 'AC Adapter' field there now reads "
                f"{bios_adapter_field}."
            ),
            standard=(
                "BIOS runs its power-on self-test: memory, display path, "
                "storage. If anything fails here, the power LED blinks a "
                "red/blue code (2,3 = no memory; 3,5 = power-rail failure) "
                "instead of booting. On success the Alienware logo appears "
                "with the F2 Setup prompt — where the 'AC Adapter' field now "
                f"reads {bios_adapter_field}."
            ),
            technical=(
                "POST: memory, display path, storage. Failure emits a red/blue "
                "blink code rather than booting — 2,3 for absent memory, 3,5 for a "
                "power-rail fault. On success the logo and F2 prompt appear, with "
                f"the 'AC Adapter' field reading {bios_adapter_field}."
            ),
            expert=(
                "POST over memory, display, storage; failure emits a blink code "
                f"(2,3 no memory; 3,5 rail fault). 'AC Adapter' reads "
                f"{bios_adapter_field}."
            ),
        ),
        active=["cpu", "dimm", "gpu", "ssd", "ec"],
        system_w=post_w,
        charge_w=c_w,
        charge_stage=c_stage,
        cpu_w=12.0,
        fan_pct=40.0,
        cycle_cost=2,
    )
    os_w = 55.0
    c_w, c_stage = topup(os_w)
    emit(
        phase="boot",
        stage_id="boot-os",
        label="OS loads · AWCC restores profile",
        description=L(
            novice=(
                "The operating system loads from the solid-state drive, and the "
                "Alienware Command Center service restores the thermal mode that "
                f"was active ('{mode}'), the lighting, and any overclock settings. "
                "The fans settle onto that mode's curve. The machine is now "
                "running inside the power budget the embedded controller decided "
                "on back at the handshake — which is where this whole story "
                "started."
            ),
            plain=(
                "The operating system loads from the M.2 SSD, and the Alienware "
                "Command Center service restores the active thermal mode "
                f"('{mode}'), the lighting, and any overclock profile. The fans "
                "settle onto that mode's curve. What governs the machine from here "
                "is the power budget the EC fixed back at the handshake."
            ),
            standard=(
                "The OS loads from the M.2 SSD and the Alienware Command "
                "Center service restores the active thermal mode "
                f"('{mode}'), lighting, and any overclock profile. Fans settle "
                "onto that mode's curve. The machine is now governed by the "
                "power budget the EC set back at the handshake."
            ),
            technical=(
                "OS loads from the M.2 SSD; AWCC restores the active thermal mode "
                f"('{mode}'), lighting, and overclock profile, and fans settle "
                "onto that curve. Operation is bounded by the budget the EC fixed "
                "at the handshake."
            ),
            expert=(
                f"OS up from M.2; AWCC restores thermal mode ('{mode}'), lighting, "
                "overclock. Fans to that curve. Bounded by the EC's handshake "
                "budget."
            ),
        ),
        active=["cpu", "dimm", "ssd", "wlan"],
        system_w=os_w,
        charge_w=c_w,
        charge_stage=c_stage,
        cpu_w=15.0,
        fan_pct=FAN_BASE[mode] if mode == "fullSpeed" else 30.0,
    )

    # ---- load + steady ---------------------------------------------------
    cap_cpu = profile.cpu_max_w * THERMAL_CAP[mode]
    cap_gpu = profile.gpu_tgp_w * THERMAL_CAP[mode]
    if not recognized:
        cap_cpu = min(cap_cpu, THROTTLED_CPU_W)
        cap_gpu = min(cap_gpu, THROTTLED_GPU_W)
    frac_cpu, frac_gpu = WORKLOAD_FRAC[scenario.workload]
    cpu_full = max(CPU_IDLE_FLOOR_W, cap_cpu * frac_cpu)
    gpu_full = cap_gpu * frac_gpu
    rest_w = profile.idle_w  # display, RAM, SSD, WLAN, lighting

    def run_state(cpu_w: float, gpu_w: float) -> dict:
        """Balance one running state against the AC budget.

        Within budget → leftover headroom keeps charging the pack.
        Over budget with charge in the pack → hybrid power: the battery
        supplements the adapter (batteryW > 0, pct falls).
        Over budget below the hybrid floor → the EC throttles CPU/GPU to
        fit the adapter instead, protecting the pack.
        """
        nonlocal pct
        system = rest_w + cpu_w + gpu_w
        battery_w = 0.0
        hybrid = False
        if system > budget:
            if pct > HYBRID_FLOOR_PCT:
                battery_w = system - budget
                hybrid = True
                pct = max(pct - battery_w * 0.03, 0.0)
                charge_w, c_stage = 0.0, "idle"
            else:
                scale = max(0.0, (budget - rest_w)) / (cpu_w + gpu_w)
                cpu_w *= scale
                gpu_w *= scale
                system = rest_w + cpu_w + gpu_w
                charge_w, c_stage = 0.0, "idle"
        else:
            charge_w, c_stage = topup(system)
        full_scale = profile.cpu_max_w + profile.gpu_tgp_w + rest_w
        fan = (
            100.0
            if mode == "fullSpeed"
            else FAN_BASE[mode] + 55.0 * system / full_scale
        )
        return dict(
            system_w=system,
            cpu_w=cpu_w,
            gpu_w=gpu_w,
            battery_w=battery_w,
            charge_w=charge_w,
            charge_stage=c_stage,
            hybrid=hybrid,
            fan_pct=fan,
        )

    load_regions = ["cpu", "gpu", "vram", "heatpipes", "fan-left", "fan-right"]
    if scenario.workload == "idle":
        ramp_desc = (
            "Desktop idle: single-digit CPU watts, GPU parked. Nearly all "
            "of the adapter's budget is free, so any remaining charge "
            "deficit is being made up in the background."
        )
    else:
        ramp_desc = (
            "The workload starts and clocks ramp. CPU and GPU climb toward "
            f"the limits the '{mode}' thermal mode allows"
            + (
                " — which the 'Unknown' adapter has pinned to a fraction "
                "of the silicon's capability."
                if not recognized
                else "; the fans follow the heat up their curve."
            )
        )
    ramp = run_state(cpu_full * 0.5, gpu_full * 0.5)
    emit(
        phase="load",
        stage_id="s8-load-ramp",
        label="Workload ramps",
        description=ramp_desc,
        active=load_regions,
        **ramp,
    )

    peak = run_state(cpu_full, gpu_full)
    if peak["hybrid"]:
        peak_stage, peak_label = "s9-hybrid", "Hybrid power — battery supplements"
        peak_desc = (
            f"Combined demand ({peak['system_w']:.0f} W) exceeds the "
            f"{budget:.0f} W adapter, so instead of throttling, the "
            "battery discharges in parallel with the wall — by design. "
            "Windows shows the battery slowly draining while plugged in, "
            "up to ~5% per hour under sustained load. Below ~20% charge, "
            "hybrid power disables and the system throttles to protect "
            "the pack."
        )
        peak_active = load_regions + ["battery", "charger"]
    else:
        peak_stage, peak_label = "s8-load-peak", "Peak load, within budget"
        peak_desc = (
            "Full demand for this thermal mode and workload — "
            f"{peak['cpu_w']:.0f} W CPU + {peak['gpu_w']:.0f} W GPU + "
            f"{rest_w:.0f} W platform — fits inside the adapter's "
            f"{budget:.0f} W budget"
            + (
                ", so the battery never has to help and keeps charging "
                "with the leftover headroom."
                if peak["charge_w"] > 0
                else ". The battery sits untouched."
            )
            if recognized
            else "The 'Unknown' adapter caps hold CPU and GPU far below "
            "their silicon limits — the machine runs, but at a fraction "
            "of its performance, exactly as the KBs describe for an "
            "unidentified supply."
        )
        peak_active = load_regions
    emit(
        phase="load",
        stage_id=peak_stage,
        label=peak_label,
        description=peak_desc,
        active=peak_active,
        cycle_cost=3,
        **peak,
    )

    steady = run_state(cpu_full, gpu_full)
    if steady["hybrid"]:
        steady_desc = (
            "Thermal and electrical equilibrium — with the battery still "
            "making up the difference between demand and the adapter. The "
            "drain plateaus inside the 94–100% no-recharge band on long "
            "runs; for a multi-day job, the fix is adapter headroom (the "
            "360 W brick), not settings."
        )
    elif not recognized:
        steady_desc = (
            "Steady state under the 'Unknown'-adapter caps: cool, quiet, "
            "and slow, with charging still disabled. The cure is a brick "
            "the EC can identify — swap the adapter or cable and the PSID "
            "handshake restores the full budget on the next plug-in."
        )
    else:
        steady_desc = (
            "Thermal and electrical equilibrium: fans hold the "
            f"'{mode}' curve, silicon holds its power limits, and the "
            "adapter covers everything with margin. CPU package "
            "temperatures near 100 °C under load are expected on this "
            "class of machine — the thermal control circuit trims a few "
            "hundred MHz at the limit, by design."
        )
    emit(
        phase="steady",
        stage_id="s10-steady",
        label="Steady state",
        description=steady_desc,
        active=load_regions + (["battery"] if steady["hybrid"] else []),
        cycle_cost=2,
        **steady,
    )

    return states


def analyze(
    profile: LaptopProfile,
    adapter: AdapterOption,
    scenario: Scenario,
    trace: list[PowerState],
) -> Summary:
    """Summary read-out computed from the trace, not recomputed physics."""
    peak_system_w = max(s.system_w for s in trace)
    peak_hybrid_w = max((s.battery_w for s in trace if s.hybrid), default=0.0)
    hybrid_used = any(s.hybrid for s in trace)
    if not adapter.recognized:
        regime = "throttled"
    elif hybrid_used:
        regime = "adapter-limited"
    else:
        regime = "within-budget"

    minutes_to_80 = None
    start = scenario.start_battery_pct
    if adapter.recognized and start < 80.0 and any(s.charge_w > 0 for s in trace):
        cc_w = _cc_rate(profile, adapter)
        if cc_w > 0:
            pct_per_min = cc_w / profile.battery.wh * 100.0 / 60.0
            minutes_to_80 = round((80.0 - start) / pct_per_min, 1)

    notes: list[str] = []
    if adapter.recognized:
        notes.append(
            f"Adapter identified over "
            f"{'the PSID center pin' if adapter.connector == 'barrel' else 'USB-PD negotiation'}"
            f" as a {adapter.watts:g} W supply."
        )
    else:
        notes.append(
            "Adapter reported as 'Unknown' (PSID unreadable): charging "
            "disabled, CPU/GPU power limits capped."
        )
    if hybrid_used:
        notes.append(
            f"Hybrid power engaged: battery supplemented up to "
            f"{peak_hybrid_w:.0f} W beyond the adapter — expect the pack "
            "to drain slowly while plugged in."
        )
    elif adapter.recognized and peak_system_w < adapter.watts:
        notes.append(
            f"Peak system draw {peak_system_w:.0f} W stayed inside the "
            f"{adapter.watts:g} W budget with "
            f"{adapter.watts - peak_system_w:.0f} W of headroom."
        )
    if minutes_to_80 is not None and profile.battery.express_charge:
        notes.append(
            f"ExpressCharge estimate: ~{minutes_to_80:.0f} min from "
            f"{start:g}% to 80% (illustrative)."
        )

    return Summary(
        adapter_w=adapter.watts,
        peak_system_w=peak_system_w,
        peak_hybrid_w=peak_hybrid_w,
        hybrid_used=hybrid_used,
        end_battery_pct=trace[-1].battery_pct,
        regime=regime,
        minutes_to_80_pct=minutes_to_80,
        notes=notes,
    )
