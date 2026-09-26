import { useEffect, useMemo, useRef, useState } from "react";
import { TwinLayout } from "@twinsim/twin-ui";
import { fetchChains, fetchConstants, fetchCouplings, runChain } from "./api";
import { ChainStrip } from "./components/ChainStrip";
import { CouplingList } from "./components/CouplingList";
import { InjectedPanel } from "./components/InjectedPanel";
import { IterationPanel } from "./components/IterationPanel";
import { LevelControl } from "./components/LevelControl";
import { SeamCharts } from "./components/SeamCharts";
import { useLevel } from "./level";
import type { ChainInfo, Constant, CoupledTrace, CouplingInfo } from "./types";

// The chains are computed by the pure composition layer, which calls the pure
// engines in-process. This component owns only the playback clock — the same
// division every twin in this repo keeps.

type Tab = "chains" | "seams";

const SPEEDS = [1, 4, 16]; // timeline ticks advanced per playback frame

function tabFromHash(): Tab {
  return window.location.hash.startsWith("#seams") ? "seams" : "chains";
}

function chainFromHash(): string | null {
  const m = window.location.hash.match(/#chain=([a-z0-9-]+)/i);
  return m ? m[1] : null;
}

function writeHash(hash: string) {
  window.history.replaceState(null, "", window.location.pathname + window.location.search + hash);
}

export function App() {
  const level = useLevel();
  const [tab, setTab] = useState<Tab>(() => tabFromHash());
  const [chains, setChains] = useState<ChainInfo[]>([]);
  const [couplings, setCouplings] = useState<CouplingInfo[]>([]);
  const [constants, setConstants] = useState<Record<string, Constant>>({});
  const [chainId, setChainId] = useState<string>(() => chainFromHash() ?? "heat-to-cdu");
  const [trace, setTrace] = useState<CoupledTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(4);
  const [iteration, setIteration] = useState(0);

  // Prose-bearing content refetches on a reading-level change; the cursor is
  // deliberately left alone — every number is identical at every level.
  useEffect(() => {
    Promise.all([fetchChains(), fetchCouplings(), fetchConstants()])
      .then(([c, k, consts]) => {
        setChains(c);
        setCouplings(k);
        setConstants(consts.constants);
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    runChain(chainId)
      .then((t) => {
        if (!live) return;
        setTrace(t);
        setCursor(0);
        setIteration(Math.max(0, t.iterationLog.length - 1));
        setLoading(false);
      })
      .catch((e) => {
        if (!live) return;
        setError(String(e));
        setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [chainId]);

  // The playback clock. One interval, here, never in the composition layer.
  const lastRef = useRef(0);
  useEffect(() => {
    if (!running || !trace || trace.timeline.length === 0) return;
    lastRef.current = 0;
    const id = window.setInterval(() => {
      setCursor((c) => {
        const next = c + speed;
        return next >= trace.timeline.length ? trace.timeline.length - 1 : next;
      });
    }, 80);
    return () => window.clearInterval(id);
  }, [running, speed, trace]);

  useEffect(() => {
    writeHash(tab === "seams" ? "#seams" : `#chain=${chainId}`);
  }, [tab, chainId]);

  const info = useMemo(
    () => chains.find((c) => c.id === chainId) ?? null,
    [chains, chainId],
  );
  const lastTick = trace ? Math.max(trace.timeline.length - 1, 0) : 0;

  return (
    <TwinLayout
      title="Composition — the twins, coupled"
      subtitle="One engine's trace becomes another engine's scenario, and an identity is asserted across the seam."
      tabs={[
        { id: "chains" as Tab, label: "Chains" },
        { id: "seams" as Tab, label: "The seams" },
      ]}
      active={tab}
      onTab={setTab}
      aside={<LevelControl />}
    >
      {tab === "seams" ? (
        <main className="compose-main">
          <CouplingList couplings={couplings} constants={constants} />
        </main>
      ) : (
        <>
          <main className="compose-main">
            {error && <div className="an-panel mini an-error">Could not run the chain: {error}</div>}
            {loading && !trace && <div className="an-panel mini">Running the engines…</div>}
            {trace && (
              <>
                <ChainStrip trace={trace} info={info} cursor={cursor} />
                <SeamCharts
                  charts={trace.charts}
                  timeline={trace.timeline}
                  cursor={cursor}
                  timeUnit={trace.timeUnit}
                />
              </>
            )}
          </main>
          <aside className="compose-aside">
            <div className="controls chain-picker">
              <h2>Chains</h2>
              <div className="scenario-list">
                {chains.map((c) => (
                  <button
                    key={c.id}
                    className={c.id === chainId ? "active" : ""}
                    onClick={() => setChainId(c.id)}
                  >
                    {c.title}
                    <span className="mini">
                      {c.couplings.join(" · ").toUpperCase()}
                      {c.closed && " · closed loop"}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            {trace && (
              <div className="controls playback">
                <h2>Playback</h2>
                <div className="playback-row">
                  <button className="primary" onClick={() => setRunning((r) => !r)}>
                    {running ? "Pause" : "Play"}
                  </button>
                  <button onClick={() => setCursor(0)}>Reset</button>
                  {SPEEDS.map((s) => (
                    <button
                      key={s}
                      className={s === speed ? "active" : ""}
                      onClick={() => setSpeed(s)}
                    >
                      ×{s}
                    </button>
                  ))}
                </div>
                <label className="field scrub-field">
                  <span>
                    tick {cursor} / {lastTick}
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={lastTick}
                    value={Math.min(cursor, lastTick)}
                    onChange={(e) => {
                      setRunning(false);
                      setCursor(Number(e.target.value));
                    }}
                  />
                </label>
              </div>
            )}
            {trace && (
              <IterationPanel trace={trace} iteration={iteration} onIteration={setIteration} />
            )}
            {trace && <InjectedPanel trace={trace} />}
          </aside>
        </>
      )}
    </TwinLayout>
  );
}
