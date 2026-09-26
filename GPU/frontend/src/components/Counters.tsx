import { useEffect, useState } from "react";
import { fetchMeasurements } from "../api";
import type {
  DType,
  Execution,
  GpuProfile,
  Measurements,
  SimState,
  Summary,
} from "../types";
import { InfoDot } from "./InfoDot";
import { Leveled } from "./Leveled";

export function Counters({
  state,
  tiling,
  summary,
  losses,
  profile,
  llm,
  execution,
  dtype,
  trace,
  cursor,
}: {
  state: SimState | null;
  tiling?: { hbmLoads: number; tilesDone: number; tilesTotal: number } | null;
  summary?: Summary | null;
  // Losses computed so far (spec_06); null for plain matmul workloads.
  losses?: number[] | null;
  // spec_24: the die's residency limits, for the occupancy prose.
  profile?: GpuProfile | null;
  // spec_26: the live decode read-outs — KV length grows, intensity falls,
  // and the per-token regime flips across the ridge.
  llm?: {
    kvLen: number;
    token: number;
    tokens: number;
    intensity: number;
    intensities: number[];
    regime: "memory" | "compute";
    prefill: boolean;
  } | null;
  // spec_23: tensor-core mode read-outs (ranks/step + effective MACs/cycle).
  execution?: Execution;
  dtype?: DType;
  // spec_25: the trace + cursor, for the replay-to-cursor joules counter
  // (the same walk MatrixPanels does for accumulation depth).
  trace?: SimState[] | null;
  cursor?: number;
}) {
  const macs = state?.macDone ?? 0;
  // spec_23: the tensor path's effective throughput next to the scalar figure.
  const tensorSpec = profile?.tensor ?? null;
  const tensorMult =
    execution === "tensor" && tensorSpec && dtype
      ? tensorSpec.multipliers[dtype] ?? null
      : null;
  const scalarMacsPerCycle = profile?.bandwidth?.macsPerCycle ?? 4;
  const total = state?.macTotal ?? 0;
  const active = state?.activeCores ?? 0;
  const util = state ? Math.round(state.utilization * 100) : 0;

  // spec_15: calibration from lesson 06 — real hardware annotating the model.
  const [measured, setMeasured] = useState<Measurements>({});
  useEffect(() => {
    fetchMeasurements()
      .then(setMeasured)
      .catch(() => setMeasured({}));
  }, []);
  const stream = measured["stream_gbps"];
  // spec_25: watts + joules. Envelope derives from the profile's power
  // block, same arithmetic as the backend's envelope_watts().
  const peakPower = measured["peak_power_w"];
  const power = profile?.power ?? null;
  const totalCores = profile
    ? profile.sm.rows *
      profile.sm.cols *
      profile.coresPerSM.rows *
      profile.coresPerSM.cols
    : 0;
  const envelope = power
    ? power.idleW +
      power.laneW * totalCores +
      power.byteW * (profile?.bandwidth?.bytesPerCycle ?? 8)
    : null;
  const joulesSoFar = (trace ?? [])
    .slice(0, (cursor ?? 0) + 1)
    .reduce((j, s) => j + (s.powerWatts ?? 0) * s.cycleCost, 0);

  return (
    <div className="an-panel">
      <h2>Counters</h2>
      <div className="stat">
        <span>
          MACs (multiply-accumulates) done{" "}
          <InfoDot title="MACs">
            <Leveled
              novice={
                <p>
                  A MAC is one multiply-accumulate: multiply two numbers and
                  add the product to a running total. Some texts call the same
                  thing a multiply-add. Every cell of the result matrix is a
                  chain of N of them, so a whole N×N matmul is N×N×N MACs. This
                  counter is the simulator's measure of arithmetic done.
                </p>
              }
              standard={
                <p>
                  MAC = multiply-accumulate (a multiply-add): one term of one
                  output cell's dot product. An N×N matmul is N³ of them; this
                  is the page's unit of arithmetic.
                </p>
              }
              expert={<p>MAC = multiply-accumulate; N³ per N×N matmul.</p>}
            />
          </InfoDot>
        </span>
        <span>{macs}</span>
      </div>
      <div className="stat">
        <span>of total</span>
        <span>{total}</span>
      </div>
      <div className="stat">
        <span>active cores</span>
        <span>{active}</span>
      </div>
      <div className="stat">
        <span>utilization</span>
        <span>{util}%</span>
      </div>
      {state && power && envelope != null && (
        <>
          <div className="stat">
            <span>
              power (illustrative){" "}
              <InfoDot title="Modeled watts">
                <p>
                  idle floor + watts per computing lane + watts per byte of
                  foreground memory traffic — derived from this state's own
                  fields. A stalled load reads idle + memory watts while
                  macDone stands still: the memory-bound regime as a number.
                </p>
                <p>
                  The absolute watts are teaching estimates; across the die
                  menu the <em>ratios</em> are honest (each envelope tracks
                  the real part's TDP/TGP).
                </p>
              </InfoDot>
            </span>
            <span>
              {state.powerWatts.toFixed(1)} W of {envelope.toFixed(0)} W
            </span>
          </div>
          {peakPower && (
            <div className="mini">
              last recorded peak: {peakPower.value.toFixed(0)} W, sampled
              during a live session on {peakPower.measuredAt}
              {peakPower.device ? ` (${peakPower.device})` : ""} — it belongs
              to the GPU that ran that session, not to this profile; the
              model's watts are illustrative.
            </div>
          )}
          <div className="stat">
            <span>energy so far</span>
            <span>
              {joulesSoFar >= 100
                ? Math.round(joulesSoFar).toLocaleString()
                : joulesSoFar.toFixed(1)}{" "}
              J
            </span>
          </div>
        </>
      )}
      {tensorMult != null && (
        <>
          <div className="stat">
            <span>
              ranks/step{" "}
              <InfoDot title="Ranks per MMA step">
                <p>
                  How many k-ranks of the dot product one MMA instruction
                  consumes at once — up to mmaK ({tensorSpec?.mmaK ?? 16}), with
                  a partial final chunk when the depth doesn't divide evenly.
                  The scalar path always consumes exactly 1.
                </p>
              </InfoDot>
            </span>
            <span>{state?.mma ? state?.ranksPerStep ?? "—" : "—"}</span>
          </div>
          <div className="stat">
            <span>effective MACs/cycle</span>
            <span>
              {scalarMacsPerCycle * tensorMult} (scalar: {scalarMacsPerCycle})
            </span>
          </div>
        </>
      )}
      {summary?.occupancy && (() => {
        const occ = summary.occupancy;
        const warpSize = profile?.warpSize ?? 32;
        const maxWarps = Math.floor((profile?.maxThreadsPerSm ?? 1536) / warpSize);
        const slotsUsed = occ.blocksResident * occ.warpsPerBlock;
        const limiterProse =
          occ.limiter === "blocks"
            ? `block-limited: ${occ.blocksResident} blocks × ${
                occ.warpsPerBlock * warpSize
              } threads = ${slotsUsed * warpSize} of ${maxWarps * warpSize} slots`
            : occ.limiter === "threads"
              ? `thread-limited: ${occ.blocksResident} × ${
                  occ.warpsPerBlock * warpSize
                }-thread block${occ.blocksResident > 1 ? "s" : ""} = ${
                  slotsUsed * warpSize
                } of ${maxWarps * warpSize} slots`
              : `full: every one of the SM's ${maxWarps * warpSize} thread slots claimed`;
        return (
          <>
            <div className="stat">
              <span>
                occupancy{" "}
                <InfoDot title="Occupancy vs utilization">
                  <p>
                    <strong>Utilization</strong> answers "how many lanes are computing{" "}
                    <em>right now</em>?" — it changes every state as the animation plays.
                  </p>
                  <p>
                    <strong>Occupancy</strong> answers "how much of the SM's{" "}
                    <em>resident-thread budget</em> did this launch claim?" — it is fixed
                    the moment the kernel launches. Block size runs against two ceilings,
                    max threads per SM <em>and</em> max blocks per SM, and whichever runs
                    out first wins. (Registers and shared memory are the other two real
                    budgets; this model leaves them out on purpose.)
                  </p>
                  <p>
                    Same arithmetic the Live tab shows as theoretical occupancy for real
                    kernels — lesson 03 measures it on your hardware.
                  </p>
                </InfoDot>
              </span>
              <span>{occ.occupancyPct.toFixed(occ.occupancyPct % 1 ? 1 : 0)}%</span>
            </div>
            <div className="mini">{limiterProse}</div>
          </>
        );
      })()}
      {losses != null && (
        <>
          <div className="stat">
            <span>loss</span>
            <span>{losses.length ? losses[losses.length - 1].toFixed(3) : "—"}</span>
          </div>
          {losses.length > 1 && (
            <div className="mini">
              per step: {losses.map((l) => l.toFixed(2)).join(" · ")}{" "}
              <svg width={90} height={20} aria-label="Loss per training step">
                <title>loss per step — falling means the network is learning</title>
                <polyline
                  fill="none"
                  stroke="#4f7cff"
                  strokeWidth={1.5}
                  points={losses
                    .map(
                      (l, i) =>
                        `${(i / (losses.length - 1)) * 86 + 2},${
                          18 - (l / Math.max(...losses)) * 15
                        }`,
                    )
                    .join(" ")}
                />
              </svg>
            </div>
          )}
        </>
      )}
      {llm && (
        <>
          <div className="stat">
            <span>
              KV length (incl. this token){" "}
              <InfoDot title="KV cache length (live)">
                <p>
                  The cache the current token must re-read in full — it grows by
                  one row per decoded token, so every token costs a little more
                  than the last.
                </p>
                <p>
                  It reads one higher than the slider on the first token, and
                  that is not an off-by-one: the token being decoded appends its
                  own key and value before attending, so it re-reads the slider's
                  starting length plus itself.
                </p>
              </InfoDot>
            </span>
            <span>{llm.kvLen}</span>
          </div>
          <div className="stat">
            <span>
              token intensity{" "}
              <InfoDot title="Per-token arithmetic intensity">
                <p>
                  MACs per byte for <em>this</em> token: (6N + 2S) / (b·(12 +
                  2S)). As the cache length S grows, the bytes grow and the
                  useful arithmetic barely does, so this number falls — and when
                  it crosses the ridge point the token is memory-bound.
                </p>
                <p>
                  ⓘ The drawn attention matmuls share their cache block across
                  the N streams, which under-charges KV traffic — real streams
                  do not share caches. The trace is the drawing; this accounting
                  is the honest books.
                </p>
              </InfoDot>
            </span>
            <span>{llm.intensity.toFixed(3)}</span>
          </div>
          <div className="stat">
            <span>
              regime (this token){" "}
              <InfoDot title="Two regimes, two scopes">
                <p>
                  This line grades the token being decoded now. The Roofline
                  panel below grades the whole trace — prefill blocks included,
                  which move far more arithmetic per byte. The two can disagree,
                  and when they do it is the scopes differing, not the model.
                </p>
              </InfoDot>
            </span>
            <span>
              {llm.regime === "memory" ? "memory-bound" : "compute-bound"}
              {summary &&
              Math.abs(llm.intensity - summary.ridgePoint) < 0.005
                ? " — sitting on the ridge"
                : ""}
            </span>
          </div>
          {!llm.prefill && llm.intensities.length > 1 && (
            <div className="mini">
              per token:{" "}
              {llm.intensities.map((v) => v.toFixed(2)).join(" · ")}{" "}
              <svg width={90} height={20} aria-label="Intensity per token">
                <title>
                  arithmetic intensity per token — falling means the roofline
                  dot is sliding left
                </title>
                <polyline
                  fill="none"
                  stroke="#4f7cff"
                  strokeWidth={1.5}
                  points={llm.intensities
                    .map(
                      (v, i) =>
                        `${(i / (llm.intensities.length - 1)) * 86 + 2},${
                          18 - (v / Math.max(...llm.intensities)) * 15
                        }`,
                    )
                    .join(" ")}
                />
              </svg>
            </div>
          )}
          {llm.prefill && (
            <div className="mini">
              prefill: whole prompt blocks, full operand reuse — intensity holds
              steady
            </div>
          )}
        </>
      )}
      {tiling && (
        <>
          <div className="stat">
            <span>HBM tile-loads</span>
            <span>{tiling.hbmLoads}</span>
          </div>
          <div className="stat">
            <span>tiles done</span>
            <span>
              {tiling.tilesDone} / {tiling.tilesTotal}
            </span>
          </div>
        </>
      )}

      {summary && (
        <>
          <h2 style={{ marginTop: 16 }}>
            Roofline (illustrative){" "}
            <InfoDot title="The roofline model">
              <Leveled
                novice={
                  <>
                    <p>
                      A chip can be held back by one of two things: how fast it
                      does arithmetic, or how fast memory can hand it numbers.
                      The roofline model is a way to tell which. Picture a
                      graph whose line rises like a sloped roof and then goes
                      flat. On the slope, memory is the limit (memory-bound).
                      On the flat part, arithmetic is the limit (compute-bound).
                    </p>
                    <p>
                      This page does not draw the graph. It gives you the two
                      numbers that place a workload on it — intensity and the
                      ridge point, each explained by its own dot below — and
                      the verdict on the regime line.
                    </p>
                  </>
                }
                standard={
                  <p>
                    The roofline model bounds throughput by min(compute rate,
                    memory bandwidth × arithmetic intensity): a sloped memory
                    roof that meets a flat compute roof at the ridge point. The
                    page does not plot it; it reports the two numbers that place
                    this workload on it, and the regime they imply.
                  </p>
                }
                expert={
                  <p>
                    Throughput ≤ min(compute rate, bandwidth × intensity). Not
                    plotted; intensity, ridge and regime are reported.
                  </p>
                }
              />
            </InfoDot>
          </h2>
          <div className="stat">
            <span>regime{llm ? " (whole trace)" : ""}</span>
            <span>{summary.regime === "memory" ? "memory-bound" : "compute-bound"}</span>
          </div>
          {llm && (
            <div className="mini">
              this panel measures the whole trace, prefill included; the
              per-token figures above measure one decoded token, so the two
              regimes can differ
            </div>
          )}
          {tensorMult != null && (
            <div className="mini">
              tensor mode: faster math, same memory — feed it or starve it. The
              ridge point moved right ×{tensorMult}; only tiling moves the dot.
            </div>
          )}
          {summary.joulesPerMac > 0 && (
            <div className="stat">
              <span>
                joules/MAC{" "}
                <InfoDot title="Energy per MAC">
                  <p>
                    Whole-run energy ÷ macTotal — this sim's tokens-per-joule.
                    Shrink the tile and watch it climb even though macTotal is
                    identical: same math, more energy, because the die idled
                    hot through more dwelling loads.
                  </p>
                  <p>
                    Compare it with itself, never with a datasheet. The sim
                    runs tens of MACs over illustrative cycles, so the absolute
                    value lands around a joule per MAC — real silicon is some
                    thirteen orders of magnitude below that. The direction the
                    number moves is the lesson; its size is an artefact of the
                    toy scale.
                  </p>
                </InfoDot>
              </span>
              <span>
                {summary.joulesPerMac < 0.01
                  ? summary.joulesPerMac.toExponential(2)
                  : summary.joulesPerMac.toFixed(3)}
              </span>
            </div>
          )}
          <div className="stat">
            <span>
              intensity (MAC/byte){" "}
              <InfoDot title="Arithmetic intensity">
                <Leveled
                  novice={
                    <p>
                      Arithmetic intensity is how much arithmetic the workload
                      gets out of each byte it fetches: total MACs
                      (multiply-accumulates) divided by total bytes moved, both
                      shown in this panel. A high figure means each fetched
                      number is reused many times. A low one means the chip
                      keeps going back to memory. Shrinking the tile or choosing
                      a wider number format lowers it, because more bytes move
                      for the same arithmetic.
                    </p>
                  }
                  standard={
                    <p>
                      Arithmetic intensity = MACs total ÷ bytes moved, for the
                      whole workload. It is a property of the workload and its
                      tiling and dtype, not of the die. Below the ridge point
                      the run is memory-bound; at or above it, compute-bound.
                    </p>
                  }
                  expert={
                    <p>
                      macTotal ÷ bytesMoved. Workload-side; compare with the
                      ridge.
                    </p>
                  }
                />
              </InfoDot>
            </span>
            <span>{summary.arithmeticIntensity.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span>
              ridge point{" "}
              <InfoDot title="Ridge point">
                <Leveled
                  novice={
                    <>
                      <p>
                        The ridge point belongs to the die, not the workload.
                        Each cycle the selected die can do a fixed number of
                        MACs (multiply-accumulates) and fetch a fixed number of
                        bytes. The ridge point is the first divided by the
                        second
                        {profile?.bandwidth
                          ? `: ${profile.bandwidth.macsPerCycle} MACs per cycle ÷ ${profile.bandwidth.bytesPerCycle} bytes per cycle on ${profile.name}`
                          : ""}
                        . It is the intensity at which arithmetic and memory
                        finish in the same time.
                      </p>
                      <p>
                        Those two per-cycle figures are roofline constants
                        chosen to order the profiles against one another. They
                        are not a count of the lanes drawn on the die, and the
                        cycle here is illustrative, not a hardware clock — so
                        4 MACs per cycle and 128 drawn lanes are two different
                        pictures of the same die, not a contradiction.
                      </p>
                      <p>
                        A workload whose intensity is below the ridge spends
                        more cycles loading than computing: memory-bound. At or
                        above it, compute-bound. Exactly at the ridge, the load
                        cycles and compute cycles below come out equal (give or
                        take rounding up to whole cycles).
                      </p>
                    </>
                  }
                  standard={
                    <p>
                      Ridge = the die's MACs per cycle ÷ bytes per cycle
                      {profile?.bandwidth
                        ? ` (${profile.bandwidth.macsPerCycle} ÷ ${profile.bandwidth.bytesPerCycle} on ${profile.name}; tensor mode multiplies the numerator)`
                        : ""}
                      : the intensity at which load cycles equal compute cycles,
                      up to rounding. Intensity below it is memory-bound, at or
                      above it compute-bound. It moves with the die profile and
                      execution mode, never with the workload. The two
                      per-cycle figures are illustrative roofline constants
                      that order the profiles — not a per-cycle count of the
                      lanes drawn above, and not a hardware clock.
                    </p>
                  }
                  expert={
                    <p>
                      macsPerCycle ÷ bytesPerCycle (tensor mode scales the
                      numerator). intensity &lt; ridge ⇒ memory-bound; at the
                      ridge, load cycles = compute cycles. Both figures are
                      illustrative profile constants, unrelated to the drawn
                      lane count.
                    </p>
                  }
                />
              </InfoDot>
            </span>
            <span>{summary.ridgePoint.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span>load cycles</span>
            <span>{summary.loadCyclesTotal}</span>
          </div>
          <div className="stat">
            <span>compute cycles</span>
            <span>{summary.computeCyclesTotal}</span>
          </div>
          <div className="stat">
            <span>bytes moved</span>
            <span>{summary.bytesMoved}</span>
          </div>
          {stream && (
            <>
              <div className="stat">
                <span>last bandwidth measurement</span>
                <span>{stream.value.toFixed(0)} GB/s</span>
              </div>
              <div className="mini">
                Posted to this backend on {stream.measuredAt} by the CUDA
                bandwidth lesson's {stream.kernel ?? "copy"} kernel
                {stream.device
                  ? `, running on ${stream.device}`
                  : "; the record does not name the GPU or say whether the run was live"}
                . It describes the GPU that ran that lesson, not the{" "}
                {profile?.name ?? "selected"} profile, and it changes no other
                number in this panel, whose units are illustrative. For
                scale: the RTX 4060 Laptop's memory is rated 256 GB/s, and a
                copy kernel lands a little under its part's rating.
              </div>
            </>
          )}
          <div className="stat">
            <span>serial cycles</span>
            <span>{summary.serialCycles}</span>
          </div>
          <div className="stat">
            <span>double-buffered</span>
            <span>
              {summary.pipelinedCycles}
              {summary.pipelinedCycles < summary.serialCycles
                ? ` (${(summary.serialCycles / summary.pipelinedCycles).toFixed(2)}×)`
                : ""}
            </span>
          </div>
          {summary.exchangeCycles > 0 && (
            <>
              <div className="stat">
                <span>
                  exchange cycles{" "}
                  <InfoDot title="NVLink exchange">
                    <p>
                      The all-gather's cost: each die pulls the other's half of
                      C over the link — ceil(bytes(C) ÷ link rate). It grows as
                      N², while compute grows as N³: that mismatch is the whole
                      scaling story.
                    </p>
                  </InfoDot>
                </span>
                <span>{summary.exchangeCycles}</span>
              </div>
              <div className="stat">
                <span>
                  scale-up speedup{" "}
                  <InfoDot title="Scale-up speedup">
                    <p>
                      serial 1-GPU cycles ÷ (max(die 0, die 1) + exchange). The
                      dies run concurrently in this cost model even though the
                      trace draws them one after the other. Always below 2× —
                      compute halves, but communication is added, not hidden.
                    </p>
                  </InfoDot>
                </span>
                <span>
                  ×{summary.scaleupSpeedup.toFixed(2)} of 2 GPUs
                </span>
              </div>
              {summary.scaleupSpeedup < 1 && (
                <div className="mini">
                  slower than one GPU — the exchange dominates at this size;
                  this is why people say "don't shard tiny kernels"
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
