"""spec_27 — NVLink scale-up: two GPUs, one matmul, one explicit exchange.

Contracts pinned here:
- regression: gpus=1 (default and explicit) is byte-for-byte the pre-spec_27
  trace — checked against a golden fixture dumped before the change (the
  additive SimState.gpu field is None on every state and is the only new key);
- validation: gpus=2 on a linkless die (RTX-5090, RTX-4060-Laptop, MI300X,
  both Generics) is a teaching 422; H100/B300 accept; the B300:H100 link
  ratio is exactly 2 (NVLink5 = 2x NVLink4); chained workloads refuse gpus=2;
- conservation: the row split is a partition — per-die contributions are
  exactly ceil(M/2)·K·N and floor(M/2)·K·N, mac_done stays globally monotonic
  and lands on M·K·N;
- phase order: monotonic within each die's subsequence; exactly one exchange,
  after every writeback, before done, stalled, costing
  ceil(M·N·dtype_bits/8 / link.bytes_per_cycle);
- the scaling lesson: speedup(N=8) < speedup(N=64) < 2.0 on both linked dies,
  and B300 >= H100 at equal N (the faster link can only help);
- composition: tensor mode and rectangular shapes ride through unchanged;
- power: the exchange burns idle + byte_w x link-bytes/cycle (lanes parked,
  link billed at spec_25's per-byte constant) and the energy ledger stays an
  exact sum;
- wire: camelCase keys match types.ts by hand.
"""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine import analyze, attach_energy, exchange_cycles, simulate
from app.main import app
from app.models import DTYPE_BITS, Workload
from app.profiles import PROFILES

client = TestClient(app)

LINKED = ["H100-SXM", "B300-Blackwell-Ultra"]
LINKLESS = [name for name in PROFILES if name not in LINKED]

FIXTURE = Path(__file__).parent / "fixtures" / "pre_spec27_traces.json.gz"


# --- regression: gpus=1 is byte-for-byte the pre-spec_27 trace ----------------


def test_gpus_defaults_to_one():
    assert Workload(N=4).gpus == 1  # type: ignore[arg-type]


def test_gpus_1_matches_the_golden_pre_spec27_dump():
    """The fixture was dumped from the engine BEFORE spec_27 landed. Every
    trace must match byte-for-byte, modulo the one additive field: the new
    'gpu' key must exist and be null on every state (lean wire, no other
    drift)."""
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as f:
        cases = json.load(f)
    assert len(cases) == 8
    for case in cases:
        p = PROFILES[case["profile"]]
        w = Workload(**case["workload"])  # type: ignore[arg-type]
        trace = [
            json.loads(s.model_dump_json(by_alias=True)) for s in simulate(p, w)
        ]
        assert len(trace) == len(case["trace"])
        for got, want in zip(trace, case["trace"]):
            assert got.pop("gpu") is None
            assert got == want
        summary = json.loads(analyze(p, w).model_dump_json(by_alias=True))
        assert summary.pop("exchangeCycles") == 0
        assert summary.pop("scaleupSpeedup") == 1.0
        assert summary == case["summary"]


def test_explicit_gpus_1_equals_omitted():
    p = PROFILES["H100-SXM"]
    omitted = Workload(N=6, tile_size=3)  # type: ignore[arg-type]
    explicit = Workload(N=6, tile_size=3, gpus=1)  # type: ignore[arg-type]
    assert [s.model_dump_json(by_alias=True) for s in simulate(p, omitted)] == [
        s.model_dump_json(by_alias=True) for s in simulate(p, explicit)
    ]
    assert analyze(p, omitted) == analyze(p, explicit)


def test_single_gpu_traces_carry_no_exchange_and_no_gpu_values():
    for name in ("Generic-128", "H100-SXM"):
        trace = simulate(PROFILES[name], Workload(N=6, tile_size=2))  # type: ignore[arg-type]
        assert all(s.phase != "exchange" for s in trace)
        assert all(s.gpu is None for s in trace)


# --- validation: the link is a feature of the die -----------------------------


def _simulate_status(profile_name: str, workload: dict):
    body = {
        "profile": PROFILES[profile_name].model_dump(by_alias=True),
        "workload": workload,
    }
    return client.post("/api/simulate", json=body)


@pytest.mark.parametrize("profile_name", LINKLESS)
def test_gpus_2_on_a_linkless_die_is_a_teaching_422(profile_name):
    r = _simulate_status(profile_name, {"N": 4, "gpus": 2})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert profile_name in detail
    assert "PCIe" in detail  # the refusal teaches, it doesn't just refuse


@pytest.mark.parametrize("profile_name", LINKED)
def test_gpus_2_on_a_linked_die_succeeds_end_to_end(profile_name):
    r = _simulate_status(profile_name, {"N": 8, "gpus": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["workload"]["gpus"] == 2
    assert any(s["phase"] == "exchange" for s in body["trace"])
    assert {s["gpu"] for s in body["trace"]} == {None, 0, 1}
    assert body["summary"]["exchangeCycles"] > 0
    assert 0 < body["summary"]["scaleupSpeedup"] < 2.0


def test_link_ratio_is_pinned_nvlink5_is_twice_nvlink4():
    h100 = PROFILES["H100-SXM"].link
    b300 = PROFILES["B300-Blackwell-Ultra"].link
    assert h100 is not None and b300 is not None
    assert h100.label == "NVLink4"
    assert b300.label == "NVLink5"
    assert b300.bytes_per_cycle == 2 * h100.bytes_per_cycle


def test_only_the_two_nvlink_dies_carry_a_link():
    assert [n for n, p in PROFILES.items() if p.link is not None] == LINKED


def test_link_rate_sits_far_below_hbm_rate():
    # HBM is on package, the link crosses the board — that gap IS the model.
    for name in LINKED:
        p = PROFILES[name]
        assert p.link.bytes_per_cycle < p.bandwidth.bytes_per_cycle


@pytest.mark.parametrize("kind", ["mlp_step", "llm_decode"])
def test_chained_workloads_refuse_gpus_2(kind):
    with pytest.raises(ValueError, match="single-GPU only"):
        Workload(kind=kind, N=4, gpus=2)  # type: ignore[arg-type]
    r = _simulate_status("H100-SXM", {"kind": kind, "N": 4, "gpus": 2})
    assert r.status_code == 422


def test_engine_never_raises_on_a_linkless_pair():
    # Defense in depth, tensor-style: called directly with a pair main.py
    # would have 422'd, the pure engine falls back to the single-die trace.
    p = PROFILES["Generic-128"]
    bad = Workload(N=4, gpus=2)  # type: ignore[arg-type]
    good = Workload(N=4)  # type: ignore[arg-type]
    assert [s.model_dump_json(by_alias=True) for s in simulate(p, bad)] == [
        s.model_dump_json(by_alias=True) for s in simulate(p, good)
    ]


# --- conservation: the split is a partition, not an approximation -------------

SCALEUP_CASES = [
    dict(N=8),
    dict(N=8, tile_size=3),
    dict(N=8, tile_size=3, double_buffer=True),
    dict(N=7, tile_size=2, dtype="fp16"),
    dict(N=8, M=5, K=3, tile_size=2),
    dict(N=6, M=3, K=5, dtype="bf16"),
    dict(N=16, tile_size=4, dtype="fp16", execution="tensor"),
]


def _dims(w: Workload) -> tuple[int, int, int]:
    return (w.m or w.n, w.k_dim or w.n, w.n)


@pytest.mark.parametrize("profile_name", LINKED)
@pytest.mark.parametrize("wl", SCALEUP_CASES)
def test_mac_conservation_across_dies(profile_name, wl):
    p = PROFILES[profile_name]
    w = Workload(**wl, gpus=2)  # type: ignore[arg-type]
    m_dim, k_dim, n = _dims(w)
    trace = simulate(p, w)

    prev = 0
    for s in trace:
        assert s.mac_done >= prev, "macDone must stay globally monotonic"
        assert s.mac_done <= s.mac_total == m_dim * k_dim * n
        prev = s.mac_done
    assert trace[-1].phase == "done"
    assert trace[-1].mac_done == m_dim * k_dim * n

    # Per-die contribution: exactly that die's rows x K x N — no MAC done
    # twice, none dropped.
    rows0 = math.ceil(m_dim / 2)
    contrib = {}
    for gpu in (0, 1):
        sub = [s for s in trace if s.gpu == gpu]
        assert sub, "both dies must appear in the trace"
        contrib[gpu] = max(s.mac_done for s in sub) - min(s.mac_done for s in sub)
        # k restarts per die; mac_done never regresses inside the subsequence.
        assert [s.mac_done for s in sub] == sorted(s.mac_done for s in sub)
    assert contrib[0] == rows0 * k_dim * n
    assert contrib[1] == (m_dim - rows0) * k_dim * n
    assert contrib[0] + contrib[1] == m_dim * k_dim * n


@pytest.mark.parametrize("profile_name", LINKED)
@pytest.mark.parametrize("wl", SCALEUP_CASES)
def test_phase_order_extends_per_die(profile_name, wl):
    p = PROFILES[profile_name]
    w = Workload(**wl, gpus=2)  # type: ignore[arg-type]
    m_dim, _k_dim, n = _dims(w)
    trace = simulate(p, w)

    # Bookends are shared (gpu=None): idle first, exchange then done last.
    assert trace[0].phase == "idle" and trace[0].gpu is None
    assert trace[-1].phase == "done" and trace[-1].gpu is None
    exchanges = [s for s in trace if s.phase == "exchange"]
    assert len(exchanges) == 1, "exactly one exchange, ever"
    x = exchanges[0]
    assert x.gpu is None and x.stalled and not x.mem_active
    xi = trace.index(x)
    assert all(s.phase != "writeback" for s in trace[xi:]), (
        "the exchange comes after every writeback"
    )
    assert trace[xi + 1].phase == "done"

    # Cost: ceil(bytes(C) / link rate), bytes(C) = ceil(M*N*bits/8).
    c_bytes = math.ceil(m_dim * n * DTYPE_BITS[w.dtype] / 8)
    assert x.cycle_cost == math.ceil(c_bytes / p.link.bytes_per_cycle)
    assert x.cycle_cost == exchange_cycles(p, w)

    # Within each die's subsequence the spec_01 order holds: load ->
    # compute -> writeback cycles, never regressing past a writeback into
    # the same tile.
    order = {"load": 0, "compute": 1, "writeback": 2}
    for gpu in (0, 1):
        sub = [s for s in trace if s.gpu == gpu]
        assert {s.phase for s in sub} <= {"load", "compute", "writeback"}
        # Die 1 starts only after die 0 has finished (trace order; the
        # concurrent cost lives in Summary, the caption owns the honesty).
        seen_tiles: list[tuple] = []
        for a, b in zip(sub, sub[1:]):
            same_tile = (a.tile_row, a.tile_col) == (b.tile_row, b.tile_col)
            if same_tile and a.phase in order and b.phase in order:
                if not w.double_buffer:
                    assert order[b.phase] >= order[a.phase] or b.k_tile != a.k_tile
        del seen_tiles
    i0 = max(i for i, s in enumerate(trace) if s.gpu == 0)
    i1 = min(i for i, s in enumerate(trace) if s.gpu == 1)
    assert i0 < i1, "one logical trace: die 0's states precede die 1's"

    # Cycles renumber contiguously across the whole logical trace.
    assert [s.cycle for s in trace] == list(range(len(trace)))


def test_a_tile_never_straddles_a_die():
    # Each die re-tiles its own row-slice, so its cell rows never exceed its
    # share of M — the split is by rows and the tiling is die-local.
    p = PROFILES["H100-SXM"]
    w = Workload(N=8, M=7, tile_size=3, gpus=2)  # type: ignore[arg-type]
    trace = simulate(p, w)
    rows = {0: math.ceil(7 / 2), 1: 7 - math.ceil(7 / 2)}
    for gpu in (0, 1):
        sub = [s for s in trace if s.gpu == gpu]
        max_tile_row = max(s.tile_row for s in sub if s.tile_row is not None)
        assert max_tile_row < math.ceil(rows[gpu] / 3)


# --- the scaling lesson, pinned -----------------------------------------------


def _speedup(profile_name: str, n: int) -> float:
    return analyze(
        PROFILES[profile_name], Workload(N=n, gpus=2)  # type: ignore[arg-type]
    ).scaleup_speedup


@pytest.mark.parametrize("profile_name", LINKED)
def test_small_n_scales_badly_large_n_scales_well_nothing_reaches_2x(profile_name):
    s8, s64 = _speedup(profile_name, 8), _speedup(profile_name, 64)
    assert s8 < s64 < 2.0


@pytest.mark.parametrize("n", [8, 16, 32, 64])
def test_the_faster_link_can_only_help(n):
    assert _speedup("B300-Blackwell-Ultra", n) >= _speedup("H100-SXM", n)


def test_speedup_is_1_when_gpus_is_1():
    s = analyze(PROFILES["H100-SXM"], Workload(N=8))  # type: ignore[arg-type]
    assert s.scaleup_speedup == 1.0
    assert s.exchange_cycles == 0


# --- composition: tensor mode and power ride through --------------------------


def test_tensor_mode_composes_per_die():
    p = PROFILES["H100-SXM"]
    w = Workload(N=16, tile_size=4, dtype="fp16", execution="tensor",
                 gpus=2)  # type: ignore[arg-type]
    trace = simulate(p, w)
    for gpu in (0, 1):
        assert any(s.mma for s in trace if s.gpu == gpu), (
            "both dies run the unchanged per-die engine — MMA included"
        )
    assert trace[-1].mac_done == 16**3


def test_exchange_power_is_idle_plus_link_bytes():
    # The lanes are parked (stalled) and the LINK, not HBM, moves the bytes:
    # idle floor + byte_w x link.bytes_per_cycle, spec_25's per-byte constant
    # billed at the link's own rate.
    for name in LINKED:
        p = PROFILES[name]
        trace = simulate(p, Workload(N=8, gpus=2))  # type: ignore[arg-type]
        x = next(s for s in trace if s.phase == "exchange")
        expected = p.power.idle_w + p.power.byte_w * p.link.bytes_per_cycle
        assert x.power_watts == pytest.approx(expected)
        assert x.power_watts <= p.envelope_watts()


def test_energy_ledger_stays_an_exact_sum_over_the_scaleup_trace():
    p = PROFILES["B300-Blackwell-Ultra"]
    w = Workload(N=8, tile_size=4, gpus=2)  # type: ignore[arg-type]
    trace = simulate(p, w)
    summary = attach_energy(analyze(p, w), trace)
    assert summary.energy_joules == sum(
        s.power_watts * s.cycle_cost for s in trace
    )
    assert summary.exchange_cycles > 0  # attach_energy preserves the read-out


# --- wire shape ---------------------------------------------------------------


def test_camelcase_wire_keys_match_types_ts():
    p = PROFILES["H100-SXM"]
    dump = p.model_dump(by_alias=True)
    assert set(dump["link"]) == {"label", "bytesPerCycle"}
    w = Workload(N=8, gpus=2)  # type: ignore[arg-type]
    assert w.model_dump(by_alias=True)["gpus"] == 2
    s = simulate(p, w)[2].model_dump(by_alias=True)
    assert "gpu" in s
    summary = analyze(p, w).model_dump(by_alias=True)
    assert "exchangeCycles" in summary and "scaleupSpeedup" in summary
