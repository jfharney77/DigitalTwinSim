from __future__ import annotations

from compose.resample import downsample, hold, mean_pool, steady_window, to_events


def test_mean_pool_conserves_the_integral():
    raw = [float((i * 37) % 11) + 0.25 * i for i in range(240)]
    for n in (1, 6, 24, 60):
        pooled = mean_pool(raw, n)
        assert abs(sum(pooled) * n - sum(raw[:len(pooled) * n])) < 1e-9


def test_hold_is_the_inverse_of_pooling_a_held_series():
    slow = [3.0, 7.5, 1.0]
    assert mean_pool(hold(slow, 24), 24) == slow
    assert len(hold(slow, 24)) == 72


def test_steady_window_reads_the_operating_point():
    trace = [{"x": 0.0}] * 80 + [{"x": 10.0}] * 20
    assert steady_window(trace, "x") == 10.0


def test_to_events_respects_the_deadband_and_the_cap():
    flat = [5.0] * 100
    assert to_events(flat, 0.5, first=False)[0] == []
    ramp = [float(i) for i in range(1000)]
    pairs, band = to_events(ramp, 0.5, max_events=240, first=False)
    assert len(pairs) <= 240 and band > 0.5, "the deadband widens until the series fits"
    # Reconstructing from the events never strays further than the band used.
    value, k, worst = ramp[0], 0, 0.0
    for i, v in enumerate(ramp):
        while k < len(pairs) and pairs[k][0] <= i:
            value = pairs[k][1]
            k += 1
        worst = max(worst, abs(v - value))
    assert worst <= band + 1e-9


def test_downsample_is_bounded_and_keeps_the_ends():
    values = [float(i) for i in range(900)]
    out = downsample(values, 120)
    assert len(out) == 120 and out[0] == 0.0 and out[-1] == 899.0
