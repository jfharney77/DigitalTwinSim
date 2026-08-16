import { useCallback, useEffect, useRef, useState } from "react";
import { fetchProfiles, simulate } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { LivePage } from "./components/LivePage";
import { downloadSvgFrom } from "./svgExport";
import { DieView } from "./components/DieView";
import { MatrixPanels } from "./components/MatrixPanels";
import { Controls } from "./components/Controls";
import { Counters } from "./components/Counters";
import { Legend } from "./components/Legend";
import { OpPipeline } from "./components/OpPipeline";
import { LevelControl } from "./components/LevelControl";
import type {
  DType,
  Execution,
  GpuProfile,
  LlmInfo,
  MlpInfo,
  MlpOp,
  SimState,
  Summary,
  WorkloadKind,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow load (pacing only)

function phaseLabel(
  s: SimState | null,
  kDepth: number,
  ops: MlpOp[] | null,
  doneLabel: string,
  linkLabel?: string | null,
): string {
  if (!s) return "idle — press Run";
  // MLP/LLM pointwise ops are one flash state; the op name is the whole story.
  if (ops && s.opIndex !== null && ops[s.opIndex]?.kind === "pointwise") {
    return s.opName ?? "pointwise op";
  }
  const op = s.opName ? `${s.opName} · ` : "";
  const die = s.gpu != null ? `GPU ${s.gpu} · ` : "";
  switch (s.phase) {
    case "idle":
      return "idle — press Run";
    case "load": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol}) k-tile ${s.kTile}` : "";
      return `${die}${op}loading tiles from HBM → shared mem${tile}`;
    }
    case "compute": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      const pf = s.prefetching ? " · prefetching next tile" : "";
      return `${die}${op}MAC accumulate · k=${s.k}/${kDepth}${tile}${pf}`;
    }
    case "writeback": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      return `${die}${op}results flushing out${tile}`;
    }
    case "exchange":
      // spec_27: the seam left visible — each die all-gathers the other's
      // half of C over the link.
      return `all-gather C over ${linkLabel ?? "the die-to-die link"} — both dies stalled`;
    case "done":
      return doneLabel;
  }
}

type Page = "sim" | "anatomy" | "live";

export function App() {
  // Deep-linkable pages: /#anatomy (or /#anatomy/<dieId>) opens the
  // die-anatomy view directly; /#live opens the live CUDA view (spec_08).
  const [page, setPage] = useState<Page>(() =>
    window.location.hash.startsWith("#anatomy")
      ? "anatomy"
      : window.location.hash.startsWith("#live")
        ? "live"
        : "sim",
  );
  useEffect(() => {
    if (page === "anatomy" && !window.location.hash.startsWith("#anatomy")) {
      window.location.hash = "anatomy";
    } else if (page === "live" && !window.location.hash.startsWith("#live")) {
      window.location.hash = "live";
    } else if (page === "sim") {
      window.location.hash = "";
    }
    // Both pages use the light Dell skin; keep the body backdrop matching so
    // the dark gradient never bleeds through below the app grid.
    document.body.classList.add("dell-body");
  }, [page]);
  // spec_30: cross-navigation links (Controls' "see this die's anatomy",
  // tour-step buttons) change the hash directly — follow them. The effect
  // above only writes the hash when the page state itself changed, so the
  // two stay stable together.
  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash;
      setPage(
        h.startsWith("#anatomy") ? "anatomy" : h.startsWith("#live") ? "live" : "sim",
      );
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  // Page titles follow the tab (spec_21 #10).
  useEffect(() => {
    const titles: Record<Page, string> = {
      sim: "GPU Die — Simulator",
      anatomy: "GPU Die — Anatomy",
      live: "GPU Die — Live CUDA",
    };
    document.title = titles[page];
  }, [page]);

  // Sim settings survive a reload (spec_21 #2).
  const saved = (() => {
    try {
      return JSON.parse(localStorage.getItem("twin.simSettings") ?? "{}");
    } catch {
      return {};
    }
  })();
  const [profiles, setProfiles] = useState<GpuProfile[]>([]);
  const [profile, setProfile] = useState<GpuProfile | null>(null);
  const [n, setN] = useState<number>(saved.n ?? 4);
  // spec_22: 0 = "= N" (square). Sent as M/K; the backend echoes resolved dims.
  const [mDim, setMDim] = useState<number>(saved.m ?? 0);
  const [kDim, setKDim] = useState<number>(saved.k ?? 0);
  const [kind, setKind] = useState<WorkloadKind>(saved.kind ?? "matmul");
  const [steps, setSteps] = useState<number>(saved.steps ?? 1);
  const [mlp, setMlp] = useState<MlpInfo | null>(null);
  // spec_26: LLM decode — starting KV-cache length and the prefill contrast.
  const [kvLen, setKvLen] = useState<number>(saved.kvLen ?? 8);
  const [prefill, setPrefill] = useState<boolean>(saved.prefill ?? false);
  const [llm, setLlm] = useState<LlmInfo | null>(null);
  const [tileSize, setTileSize] = useState<number>(saved.tileSize ?? 2);
  const [dtype, setDtype] = useState<DType>(saved.dtype ?? "fp32");
  // spec_23: execution path; "cuda" default keeps every old trace unchanged.
  const [execution, setExecution] = useState<Execution>(
    saved.execution ?? "cuda",
  );
  const [doubleBuffer, setDoubleBuffer] = useState<boolean>(
    saved.doubleBuffer ?? false,
  );
  // spec_24: threads per block; 0 = derived (one tile = one block).
  const [blockSize, setBlockSize] = useState<number>(saved.blockSize ?? 0);
  // spec_27: 1 or 2 GPUs; 2 splits C's rows across two dies over the link.
  const [gpus, setGpus] = useState<number>(saved.gpus ?? 1);
  const [speed, setSpeed] = useState<number>(saved.speed ?? 8);
  useEffect(() => {
    localStorage.setItem(
      "twin.simSettings",
      JSON.stringify({
        n, m: mDim, k: kDim, kind, steps, tileSize, dtype, doubleBuffer,
        blockSize, speed, kvLen, prefill, execution, gpus,
        // spec_30: the selected die survives too — and "simulate this die"
        // on the anatomy page writes this key before navigating here.
        profileName: profile?.name,
      }),
    );
  }, [n, mDim, kDim, kind, steps, tileSize, dtype, doubleBuffer, blockSize, speed, kvLen, prefill, execution, gpus, profile]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [trace, setTrace] = useState<SimState[]>([]);
  const [operands, setOperands] = useState<{ a: number[][]; b: number[][] }>({
    a: [],
    b: [],
  });
  const [effTileSize, setEffTileSize] = useState(0);
  // Resolved dims from the backend (spec_22): never re-derive the 0-sentinel.
  const [dims, setDims] = useState<{ m: number; k: number; n: number } | null>(
    null,
  );
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  }, []);

  // Load the available dies once; select the first as default.
  useEffect(() => {
    fetchProfiles()
      .then((ps) => {
        setProfiles(ps);
        // spec_30: honor a persisted profileName (falling back to the first
        // profile as before) — this is how "simulate this die" lands here.
        setProfile(
          (cur) =>
            cur ??
            ps.find((p) => p.name === saved.profileName) ??
            ps[0] ??
            null,
        );
      })
      .catch((e) => setError(String(e)));
  }, []);

  const onProfile = useCallback(
    (name: string) => {
      const next = profiles.find((p) => p.name === name);
      if (next) setProfile(next);
    },
    [profiles],
  );

  // (Re)fetch the trace whenever the die or N changes. Backend is the engine;
  // the whole deterministic trace arrives as data and we play it back here.
  useEffect(() => {
    if (!profile) return;
    // spec_23: keep the request valid before it leaves the browser — the 422
    // is a belt-and-suspenders contract, not a user experience. A die without
    // tensor units drops back to the scalar path; an unsupported dtype snaps
    // to the die's first declared one.
    if (execution === "tensor") {
      const mult = profile.tensor?.multipliers ?? null;
      if (!mult) {
        setExecution("cuda");
        return; // state change re-runs this effect
      }
      if (!(dtype in mult)) {
        setDtype(Object.keys(mult)[0] as DType);
        return;
      }
    }
    // spec_27: same belt-and-suspenders rule — a linkless die (or a chained
    // workload) cannot scale up, so snap back to 1 GPU before the request
    // leaves the browser. The backend's 422 stays the contract.
    if (gpus === 2 && (kind !== "matmul" || !profile.link)) {
      setGpus(1);
      return; // state change re-runs this effect
    }
    stop();
    setCursor(0);
    simulate(profile, {
      kind,
      N: n,
      // mlp_step is square-only (nonzero M/K would 422); matmul opts in.
      M: kind === "matmul" ? mDim : 0,
      K: kind === "matmul" ? kDim : 0,
      dtype,
      seed: 0,
      tileSize,
      doubleBuffer,
      steps,
      blockSize,
      // spec_26: only the LLM workload carries the cache knobs.
      kvLen: kind === "llm_decode" ? kvLen : undefined,
      prefill: kind === "llm_decode" ? prefill : undefined,
      execution, // spec_23
      gpus: kind === "matmul" ? gpus : 1, // spec_27
    })
      .then((res) => {
        setTrace(res.trace);
        setOperands({ a: res.a, b: res.b });
        setEffTileSize(res.tileSize);
        setDims({ m: res.m, k: res.k, n: res.n });
        setSummary(res.summary);
        setMlp(res.mlp ?? null);
        setLlm(res.llm ?? null);
      })
      .catch((e) => setError(String(e)));
  }, [profile, n, mDim, kDim, kind, steps, tileSize, dtype, doubleBuffer, blockSize, kvLen, prefill, execution, gpus, stop]);

  const state = trace[cursor] ?? null;
  const done = state?.phase === "done";

  // spec_27: a scale-up trace interleaves per-die states. Each die view paints
  // from the latest state carrying its own gpu index (last-known, dimmed while
  // the other die's states play); during exchange both dim and the link strip
  // pulses — the only moment it does.
  const scaleup = trace.some((s) => s.gpu != null);
  const exchanging = state?.phase === "exchange";
  const dieState = (d: number): SimState | null => {
    for (let i = Math.min(cursor, trace.length - 1); i >= 0; i--) {
      if (trace[i].gpu === d) return trace[i];
    }
    return null;
  };
  const dieDimmed = (d: number) =>
    exchanging || (state?.gpu != null && state.gpu !== d);

  // spec_06/spec_26: the op list driving the panels and pipeline — mlp and
  // llm ops share the MlpOp wire shape, so everything downstream is common.
  const opsList = mlp?.ops ?? llm?.ops ?? null;

  // The matmul op the panels (and tiling counters) describe — the current
  // op, or the nearest preceding matmul during pointwise ops / done.
  const displayOpIdx = (() => {
    if (!opsList) return null;
    let i = state?.opIndex ?? (done ? opsList.length - 1 : 0);
    while (i > 0 && opsList[i].kind !== "matmul") i--;
    return i;
  })();

  // What the matrix panels show. For plain matmul it's A×B=C over the whole
  // trace; for a training/decode run it's the display op's operands over
  // that op's slice of the trace.
  const panel = (() => {
    // spec_27: die 1's tile coordinates are die-local (each die re-tiles its
    // own row-slice), so the single-C replay would paint its writebacks into
    // the wrong rows. Honest over clever: skip the panels in 2-GPU mode.
    if (scaleup) return null;
    if (!opsList) {
      return {
        a: operands.a, b: operands.b, trace, cursor,
        aLabel: "A", bLabel: "B", cLabel: "C",
      };
    }
    const opIdx = displayOpIdx ?? 0;
    const op = opsList[opIdx];
    if (!op || op.kind !== "matmul" || !op.a || !op.b) return null;
    const start = trace.findIndex((s) => s.opIndex === opIdx);
    let end = start;
    while (end + 1 < trace.length && trace[end + 1].opIndex === opIdx) end++;
    const upto = Math.min(done ? end : cursor, end);
    const slice = start >= 0 && upto >= start ? trace.slice(start, upto + 1) : [];
    return {
      a: op.a, b: op.b, trace: slice, cursor: slice.length - 1,
      aLabel: op.aLabel ?? "A", bLabel: op.bLabel ?? "B", cLabel: op.cLabel ?? "C",
    };
  })();

  // Losses known at the cursor: step i's loss exists once its δ2 op has run
  // (position 3 in the 8-op pipeline).
  const lossesSoFar = mlp
    ? done
      ? mlp.loss
      : state?.opIndex != null
        ? mlp.loss.slice(
            0,
            Math.floor(state.opIndex / mlp.opsPerStep) +
              (state.opIndex % mlp.opsPerStep >= 3 ? 1 : 0),
          )
        : []
    : null;

  // spec_26: OpPipeline is reused as-is via a per-token MlpInfo view — ops
  // per token vary (6+2B matmuls), so the strip shows the current token.
  const llmPipeline = llm
    ? (() => {
        const starts: number[] = [];
        let acc = 0;
        for (const c of llm.opsPerToken) {
          starts.push(acc);
          acc += c;
        }
        const tok = Math.min(
          state?.stepIndex ?? (done ? llm.opsPerToken.length - 1 : 0),
          llm.opsPerToken.length - 1,
        );
        const s0 = starts[tok] ?? 0;
        const count = llm.opsPerToken[tok] ?? 0;
        const info: MlpInfo = {
          ops: llm.ops.slice(s0, s0 + count),
          opsPerStep: Math.max(count, 1),
          loss: [],
          eta: 0,
        };
        return {
          info,
          currentOp: state?.opIndex != null ? state.opIndex - s0 : null,
          token: tok,
        };
      })()
    : null;

  // spec_26: the live decode read-outs — KV length grows per token while the
  // per-token intensity falls; the regime flips when it crosses the ridge.
  const llmLive =
    llm && summary
      ? (() => {
          const tok = Math.min(
            state?.stepIndex ?? (done ? llm.kvLen.length - 1 : 0),
            llm.kvLen.length - 1,
          );
          const intensity = llm.intensity[tok];
          return {
            kvLen: llm.kvLen[tok],
            token: tok + 1,
            tokens: llm.kvLen.length,
            intensity,
            intensities: llm.intensity,
            regime:
              intensity < summary.ridgePoint
                ? ("memory" as const)
                : ("compute" as const),
            prefill: llm.prefill,
          };
        })()
      : null;

  // Tiling counters (derived from the trace up to the cursor). For a training
  // run they describe the display op only — totals are per matmul, not per run.
  const rm = dims?.m ?? n; // resolved dims; fall back to n pre-fetch
  const rk = dims?.k ?? n;
  const rn = dims?.n ?? n;
  const tilingActive =
    effTileSize > 0 && effTileSize < Math.max(rm, rk, rn);
  const tilingScope = trace
    .slice(0, cursor + 1)
    .filter((s) => displayOpIdx === null || s.opIndex === displayOpIdx);
  const tiling = tilingActive
    ? {
        hbmLoads: tilingScope.filter((s) => s.phase === "load").length,
        tilesDone: tilingScope.filter((s) => s.phase === "writeback").length,
        // The C-tile grid is M×N (spec_22). In 2-GPU mode each die re-tiles
        // its own row-slice, so the honest total is the trace's own count.
        tilesTotal: scaleup
          ? trace.filter((s) => s.phase === "writeback").length
          : Math.ceil(rm / effTileSize) * Math.ceil(rn / effTileSize),
      }
    : null;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (trace[c]?.phase === "done" ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on costly states (slow HBM loads) so stalls are visible.
      if (dwell.current > 1) {
        dwell.current -= 1;
        return;
      }
      setCursor((c) => {
        const next = c + 1;
        if (next >= trace.length - 1) {
          stop();
          return trace.length - 1;
        }
        dwell.current = Math.min(trace[next]?.cycleCost ?? 1, MAX_DWELL);
        return next;
      });
    };
    const ms = Math.max(40, 600 / speedRef.current);
    timer.current = window.setInterval(tick, ms);
  }, [trace, stop]);

  const step = useCallback(() => {
    stop();
    setCursor((c) => Math.min(c + 1, trace.length - 1));
  }, [trace, stop]);

  const reset = useCallback(() => {
    stop();
    setCursor(0);
  }, [stop]);

  // Retune the interval live when speed changes mid-run.
  useEffect(() => {
    if (timer.current === null) return;
    stop();
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  // Sim keyboard shortcuts (spec_21 #1): space run/pause, → step, R reset.
  useEffect(() => {
    if (page !== "sim") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement)
        return;
      if (e.code === "Space") {
        e.preventDefault();
        running ? stop() : run();
      } else if (e.code === "ArrowRight") {
        step();
      } else if (e.code === "KeyR") {
        reset();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [page, running, run, stop, step, reset]);

  return (
    <div className="app dell">
      <header>
        <h1>GPU&nbsp;Die</h1>
        <nav className="nav">
          <button
            className={page === "sim" ? "active" : ""}
            onClick={() => setPage("sim")}
          >
            Simulator
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Die anatomy
          </button>
          <button
            className={page === "live" ? "active" : ""}
            onClick={() => setPage("live")}
          >
            Live CUDA
          </button>
        </nav>
        {page === "sim" && (
          <>
            {summary && (
              <span className={`badge badge-${summary.regime}`}>
                {summary.regime === "memory" ? "Memory-bound" : "Compute-bound"}
              </span>
            )}
            <span className="sub">
              {state?.stalled ? "waiting on HBM · " : ""}cycle {state?.cycle ?? 0}
            </span>
          </>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && (
        <ErrorBoundary label="anatomy">
          <AnatomyPage
            // spec_30: "simulate this die" — set the mapped profile (the
            // persistence effect writes twin.simSettings) and switch tabs.
            // The reader's N / tile size / dtype survive; only the die moves.
            onSimulate={(name) => {
              const next = profiles.find((p) => p.name === name);
              if (next) {
                setProfile(next);
                setPage("sim");
              }
            }}
          />
        </ErrorBoundary>
      )}

      {page === "live" &&
        (() => {
          // The live view targets the machine's real die (spec_07); fall back
          // to the first profile so the page still renders before load.
          const liveProfile =
            profiles.find((p) => p.name === "RTX-4060-Laptop") ?? profiles[0];
          return liveProfile ? (
            <ErrorBoundary label="Live CUDA">
              <LivePage profile={liveProfile} />
            </ErrorBoundary>
          ) : null;
        })()}

      {page === "sim" && (
        <>
      <div className="an-hero">
        <h2>Matrix multiply simulator</h2>
        <p>
          Pick a die and a workload, then play the trace to watch each load,
          compute, and writeback phase move through the silicon.
        </p>
      </div>
      <div className="stage">
        <div className="an-card" id="sim-stage">
        {error && <div className="mini an-error">{error}</div>}
        {profile && !scaleup && <DieView profile={profile} state={state} />}
        {profile && scaleup && (
          <>
            <div className="scaleup-row">
              <DieView
                profile={profile}
                state={dieState(0)}
                label="GPU 0"
                dimmed={dieDimmed(0)}
              />
              <div className={`link-strip${exchanging ? " exchanging" : ""}`}>
                <span>{profile.link?.label ?? "LINK"}</span>
              </div>
              <DieView
                profile={profile}
                state={dieState(1)}
                label="GPU 1"
                dimmed={dieDimmed(1)}
              />
            </div>
            <div className="mini">
              one logical trace, two die views — real dies run concurrently;
              the scale-up speedup in Counters uses the max()-based cost
            </div>
          </>
        )}
        {profile && (
          <button
            className="mini"
            onClick={() =>
              downloadSvgFrom(
                document.getElementById("sim-stage"),
                `${profile.name}-die`,
              )
            }
          >
            Download die SVG
          </button>
        )}
        {mlp && (
          <OpPipeline mlp={mlp} currentOp={state?.opIndex ?? null} done={done} />
        )}
        {llmPipeline && (
          <>
            <div className="mini">
              {llm?.prefill
                ? `prompt block ${llmPipeline.token + 1}`
                : `token ${llmPipeline.token + 1}`}{" "}
              of {llm?.opsPerToken.length}
            </div>
            <OpPipeline
              mlp={llmPipeline.info}
              currentOp={llmPipeline.currentOp}
              done={done}
            />
          </>
        )}
        {scaleup && (
          <div className="mini">
            matrix panels are single-GPU views — die 1 writes die-local rows,
            so switch back to 1 GPU to watch C fill cell by cell
          </div>
        )}
        {panel && (
          <MatrixPanels
            a={panel.a}
            b={panel.b}
            trace={panel.trace}
            cursor={panel.cursor}
            tileSize={effTileSize}
            aLabel={panel.aLabel}
            bLabel={panel.bLabel}
            cLabel={panel.cLabel}
          />
        )}
        </div>
      </div>

      <aside className="controls">
        <Controls
          profiles={profiles}
          profileName={profile?.name ?? ""}
          onProfile={onProfile}
          kind={kind}
          steps={steps}
          onKind={setKind}
          onSteps={setSteps}
          n={n}
          m={mDim}
          kDim={kDim}
          kvLen={kvLen}
          prefill={prefill}
          onKvLen={setKvLen}
          onPrefill={setPrefill}
          tileSize={tileSize}
          dtype={dtype}
          execution={execution}
          onExecution={setExecution}
          gpus={gpus}
          onGpus={setGpus}
          doubleBuffer={doubleBuffer}
          blockSize={blockSize}
          speed={speed}
          running={running}
          done={done}
          phaseLabel={phaseLabel(
            state,
            opsList ? n : rk,
            opsList,
            mlp
              ? "training run complete"
              : llm
                ? llm.prefill
                  ? "prefill run complete"
                  : "decode run complete"
                : scaleup
                  ? "C assembled on both dies · done"
                  : "results written to C · done",
            profile?.link?.label ?? null,
          )}
          onN={setN}
          onM={setMDim}
          onKDim={setKDim}
          onTileSize={setTileSize}
          onDtype={setDtype}
          onDoubleBuffer={setDoubleBuffer}
          onBlockSize={setBlockSize}
          onSpeed={setSpeed}
          onRun={run}
          onStep={step}
          onReset={reset}
        />
        <Counters
          state={state}
          tiling={tiling}
          summary={summary}
          losses={lossesSoFar}
          profile={profile}
          llm={llmLive}
          execution={execution}
          dtype={dtype}
          trace={trace}
          cursor={cursor}
        />
        <Legend />
      </aside>
        </>
      )}
    </div>
  );
}
