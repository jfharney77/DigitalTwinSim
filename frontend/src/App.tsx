import { useCallback, useEffect, useRef, useState } from "react";
import { fetchProfiles, simulate } from "./api";
import { DieView } from "./components/DieView";
import { MatrixPanels } from "./components/MatrixPanels";
import { Controls } from "./components/Controls";
import { Counters } from "./components/Counters";
import { Legend } from "./components/Legend";
import type { GpuProfile, SimState } from "./types";

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
      return `MAC accumulate · k=${s.k}/${n}${tile}`;
    }
    case "writeback": {
      const tile = s.tileRow != null ? ` · C-tile (${s.tileRow},${s.tileCol})` : "";
      return `results flushing to C${tile}`;
    }
    case "done":
      return "results written to C · done";
  }
}

export function App() {
  const [profiles, setProfiles] = useState<GpuProfile[]>([]);
  const [profile, setProfile] = useState<GpuProfile | null>(null);
  const [n, setN] = useState(4);
  const [tileSize, setTileSize] = useState(2);
  const [speed, setSpeed] = useState(8);
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
    simulate(profile, { kind: "matmul", N: n, dtype: "fp32", seed: 0, tileSize })
      .then((res) => {
        setTrace(res.trace);
        setOperands({ a: res.a, b: res.b });
        setEffTileSize(res.tileSize);
      })
      .catch((e) => setError(String(e)));
  }, [profile, n, tileSize, stop]);

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
    const tick = () => {
      setCursor((c) => {
        const next = c + 1;
        if (next >= trace.length - 1) {
          stop();
          return trace.length - 1;
        }
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
    <div className="app">
      <header>
        <h1>GPU&nbsp;Die</h1>
        <span className="tag">◢ matmul trace</span>
        <span className="sub">cycle {state?.cycle ?? 0}</span>
      </header>

      <div className="stage">
        {error && <div className="mini" style={{ color: "#ff7a3c" }}>{error}</div>}
        {profile && <DieView profile={profile} state={state} />}
        <MatrixPanels
          a={operands.a}
          b={operands.b}
          trace={trace}
          cursor={cursor}
          tileSize={effTileSize}
        />
      </div>

      <aside className="controls">
        <Controls
          profiles={profiles}
          profileName={profile?.name ?? ""}
          onProfile={onProfile}
          n={n}
          tileSize={tileSize}
          speed={speed}
          running={running}
          done={done}
          phaseLabel={phaseLabel(state)}
          onN={setN}
          onTileSize={setTileSize}
          onSpeed={setSpeed}
          onRun={run}
          onStep={step}
          onReset={reset}
        />
        <Counters state={state} tiling={tiling} />
        <Legend />
      </aside>
    </div>
  );
}
