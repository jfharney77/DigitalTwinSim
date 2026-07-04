import { useCallback, useEffect, useRef, useState } from "react";
import { fetchProfiles, simulate } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { DieView } from "./components/DieView";
import { MatrixPanels } from "./components/MatrixPanels";
import { Controls } from "./components/Controls";
import { Counters } from "./components/Counters";
import { Legend } from "./components/Legend";
import type { DType, GpuProfile, SimState, Summary } from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow load (pacing only)

function phaseLabel(s: SimState | null): string {
  if (!s) return "idle — press Run";
  switch (s.phase) {
    case "idle":
      return "idle — press Run";
    case "load": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol}) k-tile ${s.kTile}` : "";
      return `loading A,B tiles from HBM → shared mem${tile}`;
    }
    case "compute": {
      const n = Math.round(Math.cbrt(s.macTotal));
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      const pf = s.prefetching ? " · prefetching next tile" : "";
      return `MAC accumulate · k=${s.k}/${n}${tile}${pf}`;
    }
    case "writeback": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      return `results flushing to C${tile}`;
    }
    case "done":
      return "results written to C · done";
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
    simulate(profile, { kind: "matmul", N: n, dtype, seed: 0, tileSize, doubleBuffer })
      .then((res) => {
        setTrace(res.trace);
        setOperands({ a: res.a, b: res.b });
        setEffTileSize(res.tileSize);
        setSummary(res.summary);
      })
      .catch((e) => setError(String(e)));
  }, [profile, n, tileSize, dtype, doubleBuffer, stop]);

  const state = trace[cursor] ?? null;
  const done = state?.phase === "done";

  // Tiling counters (derived from the trace up to the cursor).
  const tilingActive = effTileSize > 0 && effTileSize < n;
  const tiling = tilingActive
    ? {
        hbmLoads: trace
          .slice(0, cursor + 1)
          .filter((s) => s.phase === "load").length,
        tilesDone: trace
          .slice(0, cursor + 1)
          .filter((s) => s.phase === "writeback").length,
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
        <MatrixPanels
          a={operands.a}
          b={operands.b}
          trace={trace}
          cursor={cursor}
          tileSize={effTileSize}
        />
        </div>
      </div>

      <aside className="controls">
        <Controls
          profiles={profiles}
          profileName={profile?.name ?? ""}
          onProfile={onProfile}
          n={n}
          tileSize={tileSize}
          dtype={dtype}
          doubleBuffer={doubleBuffer}
          speed={speed}
          running={running}
          done={done}
          phaseLabel={phaseLabel(state)}
          onN={setN}
          onTileSize={setTileSize}
          onDtype={setDtype}
          onDoubleBuffer={setDoubleBuffer}
          onSpeed={setSpeed}
          onRun={run}
          onStep={step}
          onReset={reset}
        />
        <Counters state={state} tiling={tiling} summary={summary} />
        <Legend />
      </aside>
        </>
      )}
    </div>
  );
}
