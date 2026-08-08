"""Mock Redfish shaping (spec 01 §5): render a live ``SimState`` as the
``GET /redfish/v1/Chassis/System.Embedded.1/Thermal`` payload an iDRAC
would serve. Pure function — the FastAPI edge calls it, the tests call
it directly. Schema shape: simplified from DMTF's Thermal resource
(verify against DMTF/Dell docs before treating field names as gospel).

The point of the panel this feeds: a real digital twin replaces the
simulator's synthetic state with these same calls against hardware.
"""

from __future__ import annotations

from .models import SimState


def to_redfish_thermal(state: SimState, product: str) -> dict:
    temps = []

    def sensor(name: str, celsius: float, upper: float) -> dict:
        return {
            "@odata.id": (
                f"/redfish/v1/Chassis/System.Embedded.1/Thermal#/Temperatures/{len(temps)}"
            ),
            "Name": name,
            "ReadingCelsius": celsius,
            "UpperThresholdCritical": upper,
            "Status": {
                "State": "Enabled",
                "Health": "OK" if celsius < upper - 5 else "Warning",
            },
        }

    temps.append(sensor("CPU1 Temp", state.cpu_temp_c, 95))
    temps.append(sensor("GPU Hottest Temp", state.gpu_temp_hot_c, 90))
    temps.append(sensor("GPU Coolest Temp", state.gpu_temp_cool_c, 90))
    if product == "xe9712":
        temps.append(sensor("Coolant Supply", state.coolant_supply_c, 45))
        temps.append(sensor("Coolant Return", state.coolant_return_c, 75))

    fans = [
        {
            "Name": "System Fan Wall",
            "Reading": state.fan_rpm_pct,
            "ReadingUnits": "Percent",
            "Status": {"State": "Enabled" if state.fan_rpm_pct > 0 else "Disabled",
                       "Health": "OK"},
        }
    ] if product != "xe9712" else [
        {
            "Name": "CDU Pump",
            "Reading": state.flow_lpm,
            "ReadingUnits": "LPM",
            "Status": {"State": "Enabled" if state.flow_lpm > 0 else "Disabled",
                       "Health": "OK"},
        }
    ]

    return {
        "@odata.type": "#Thermal.v1_7_0.Thermal",
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/Thermal",
        "Id": "Thermal",
        "Name": "Thermal",
        "Temperatures": temps,
        "Fans": fans,
        "Oem": {
            "Dell": {
                "Simulated": True,
                "Note": (
                    "Synthetic state from the PhysicsCompute simulator. A "
                    "real twin binds these same fields to iDRAC telemetry."
                ),
                "SimTimeS": state.t,
                "DcPowerW": state.dc_power_w,
            }
        },
    }
