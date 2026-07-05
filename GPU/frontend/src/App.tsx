import { useCallback, useEffect, useRef, useState } from "react";
import { fetchProfiles, simulate } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { DieView } from "./components/DieView";
import { MatrixPanels } from "./components/MatrixPanels";
import { Controls } from "./components/Controls";
import { Counters } from "./components/Counters";
import { Legend } from "./components/Legend";
import { OpPipeline } from "./components/OpPipeline";
import type {
  DType,
  GpuProfile,
  MlpInfo,
  SimState,
  Summary,
  WorkloadKind,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow load (pacing only)

function phaseLabel(s: SimState | null, n: number, mlp: MlpInfo | null): string {
  if (!s) return "idle — press Run";
  // MLP pointwise ops are one flash state; the op name is the whole story.
  if (mlp && s.opIndex !== null && mlp.ops[s.opIndex]?.kind === "pointwise") {
    return s.opName ?? "pointwise op";
  }
  const op = s.opName ? `${s.opName} · ` : "";
  switch (s.phase) {
    case "idle":
      return "idle — press Run";
    case "load": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol}) k-tile ${s.kTile}` : "";
      return `${op}loading tiles from HBM → shared mem${tile}`;
    }
    case "compute": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      const pf = s.prefetching ? " · prefetching next tile" : "";
      return `${op}MAC accumulate · k=${s.k}/${n}${tile}${pf}`;
    }
    case "writeback": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      return `${op}results flushing out${tile}`;
    }
    case "done":
      return mlp ? "training run complete" : "results written to C · done";
  }
}

type Page = "sim" | "anatomy";

export function App() {
  // Deep-linkable pages: /#anatomy (or /#anatomy/<dieId>) opens the
  // die-anatomy view directly.
  const [page, setPage] = useState<Page>(() =>
    window.location.hash.startsWith("#anatomy") ? "anatomy" : "sim",
  );
  useEffect(() => {
    if (page === "anatomy" && !window.location.hash.startsWith("#anatomy")) {
      window.location.hash = "anatomy";
    } else if (page === "sim") {
      window.location.hash = "";
    }
    // Both pages use the light Dell skin; keep the body backdrop matching so
    // the dark gradient never bleeds through below the app grid.
    document.body.classList.add("dell-body");
  }, [page]);
  const [profiles, setProfiles] = useState<GpuProfile[]>([]);
  const [profile, setProfile] = useState<GpuProfile | null>(null);
  const [n, setN] = useState(4);
  const [kind, setKind] = useState<WorkloadKind>("matmul");
  const [steps, setSteps] = useState(1);
  const [mlp, setMlp] = useState<MlpInfo | null>(null);
  const [tileSize, setTileSize] = useState(2);
  const [dtype, setDtype] = useState<DType>("fp32");
  const [doubleBuffer, setDoubleBuffer] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [trace, setTrace] = useState<SimState[]>([]);
  const [operands, setOperands] = useState<{ a: number[][]; b: number[][] }>({
    a: [],
    b: [],
  });
  const [effTileSize, setEffTileSize] = useState(0);
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
        setProfile((cur) => cur ?? ps[0] ?? null);
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
    stop();
    setCursor(0);
    simulate(profile, { kind, N: n, dtype, seed: 0, tileSize, doubleBuffer, steps })
      .then((res) => {
        setTrace(res.trace);
        setOperands({ a: res.a, b: res.b });
        setEffTileSize(res.tileSize);
        setSummary(res.summary);
        setMlp(res.mlp ?? null);
      })
      .catch((e) => setError(String(e)));
  }, [profile, n, kind, steps, tileSize, dtype, doubleBuffer, stop]);

  const state = trace[cursor] ?? null;
  const done = state?.phase === "done";

  // spec_06: the matmul op the panels (and tiling counters) describe — the
  // current op, or the nearest preceding matmul during pointwise ops / done.
  const displayOpIdx = (() => {
    if (!mlp) return null;
    let i = state?.opIndex ?? (done ? mlp.ops.length - 1 : 0);
    while (i > 0 && mlp.ops[i].kind !== "matmul") i--;
    return i;
  })();

  // What the matrix panels show. For plain matmul it's A×B=C over the whole
  // trace; for a training run it's the display op's operands over that op's
  // slice of the trace.
  const panel = (() => {
    if (!mlp) {
      return {
        a: operands.a, b: operands.b, trace, cursor,
        aLabel: "A", bLabel: "B", cLabel: "C",
      };
    }
    const opIdx = displayOpIdx ?? 0;
    const op = mlp.ops[opIdx];
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

  // Tiling counters (derived from the trace up to the cursor). For a training
  // run they describe the display op only — totals are per matmul, not per run.
  const tilingActive = effTileSize > 0 && effTileSize < n;
  const tilingScope = trace
    .slice(0, cursor + 1)
    .filter((s) => displayOpIdx === null || s.opIndex === displayOpIdx);
  const tiling = tilingActive
    ? {
        hbmLoads: tilingScope.filter((s) => s.phase === "load").length,
        tilesDone: tilingScope.filter((s) => s.phase === "writeback").length,
        tilesTotal: Math.ceil(n / effTileSize) ** 2,
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
      </header>

      {page === "anatomy" && <AnatomyPage />}

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
        <div className="an-card">
        {error && <div className="mini an-error">{error}</div>}
        {profile && <DieView profile={profile} state={state} />}
        {mlp && (
          <OpPipeline mlp={mlp} currentOp={state?.opIndex ?? null} done={done} />
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
          tileSize={tileSize}
          dtype={dtype}
          doubleBuffer={doubleBuffer}
          speed={speed}
          running={running}
          done={done}
          phaseLabel={phaseLabel(state, n, mlp)}
          onN={setN}
          onTileSize={setTileSize}
          onDtype={setDtype}
          onDoubleBuffer={setDoubleBuffer}
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
        />
        <Legend />
      </aside>
        </>
      )}
    </div>
  );
}
