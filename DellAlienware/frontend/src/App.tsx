import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCatalog, fetchDefaultProfile, simulate } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { UseCasePage } from "./components/UseCasePage";
import { PowerPathView } from "./components/PowerPathView";
import { PowerControls } from "./components/PowerControls";
import { PowerCounters } from "./components/PowerCounters";
import { Legend } from "./components/Legend";
import type {
  LaptopProfile,
  PowerPhase,
  PowerState,
  Summary,
  ThermalMode,
  WorkloadKind,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "sim" | "anatomy" | "usecases";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#usecases")) return "usecases";
  return "sim";
}

const PAGE_HASH: Record<Page, string> = {
  sim: "",
  anatomy: "anatomy",
  usecases: "usecases",
};

const PHASE_LABEL: Record<PowerPhase, string> = {
  off: "unplugged",
  detect: "plug detect",
  handshake: "PSID handshake",
  budget: "power budget",
  charge: "charging",
  boot: "boot",
  load: "under load",
  steady: "steady state",
};

export function App() {
  // Deep-linkable pages: /#anatomy/<id>, /#usecases/<id>.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<anatomyId>).
    if (!window.location.hash.startsWith(`#${PAGE_HASH[page]}`)) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);
  // Follow back/forward navigation and in-page hash links.
  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // --- Scenario controls ---
  const [profiles, setProfiles] = useState<LaptopProfile[]>([]);
  const [profileId, setProfileId] = useState<string>("");
  const [adapterId, setAdapterId] = useState<string>("");
  const [startBatteryPct, setStartBatteryPct] = useState(30);
  const [thermalMode, setThermalMode] = useState<ThermalMode>("balanced");
  const [workload, setWorkload] = useState<WorkloadKind>("gaming");

  // --- Trace playback ---
  const [trace, setTrace] = useState<PowerState[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
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

  // Load the catalog once; start on the backend's default profile.
  useEffect(() => {
    Promise.all([fetchCatalog(), fetchDefaultProfile()])
      .then(([list, def]) => {
        setProfiles(list);
        setProfileId(def.id);
        setAdapterId(def.defaultAdapterId);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // Refetch the trace whenever the scenario changes; reset the cursor. The
  // trace is pure data from the backend engine — the clock lives here.
  useEffect(() => {
    if (!profileId || !adapterId) return;
    let cancelled = false;
    simulate({ profileId, adapterId, startBatteryPct, thermalMode, workload })
      .then((resp) => {
        if (cancelled) return;
        setTrace(resp.trace);
        setSummary(resp.summary);
        setError(null);
        stop();
        setCursor(0);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [profileId, adapterId, startBatteryPct, thermalMode, workload, stop]);

  const state = trace[cursor] ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (charging, boot) so their real-world cost is
      // visible.
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

  const profile = profiles.find((p) => p.id === profileId) ?? null;
  const adapters = profile?.adapters ?? [];

  // Switching machines also switches to that machine's default adapter, so a
  // stale adapter id never rides along into the next simulate call.
  const onProfile = useCallback(
    (id: string) => {
      setProfileId(id);
      const p = profiles.find((x) => x.id === id);
      if (p) setAdapterId(p.defaultAdapterId);
    },
    [profiles],
  );

  return (
    <div className="app dell">
      <header>
        <h1>Alienware m18 — inside the power path</h1>
        <nav className="nav">
          <button
            className={page === "sim" ? "active" : ""}
            onClick={() => setPage("sim")}
          >
            Power path
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the m18
          </button>
          <button
            className={page === "usecases" ? "active" : ""}
            onClick={() => setPage("usecases")}
          >
            Use cases
          </button>
        </nav>
        {page === "sim" && state && (
          <span className="badge">{PHASE_LABEL[state.phase]}</span>
        )}
        {page === "sim" && (
          <span className="sub">
            {state
              ? `${state.label} · step ${cursor + 1}/${trace.length}`
              : "—"}
          </span>
        )}
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "sim" && (
        <>
          <div className="an-hero">
            <h2>What happens when you plug it in</h2>
            <p>
              A 280 W gaming laptop never just "takes power". The adapter must
              first prove what it is over a 1-Wire ID pin, the EC (embedded
              controller) sets a power budget from that answer, the charger IC
              routes watts between adapter, battery and silicon — and under a
              heavy enough load the battery quietly pitches in even while
              plugged in. Play the trace and watch the flows.
            </p>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              <PowerPathView state={state} />
              <div className="mini an-hint">
                Highlighted blocks are the parts doing work at this step; lit
                lines carry power, labelled with live wattage. The full tour of
                the real hardware lives under Inside the m18.
              </div>
            </div>
          </div>

          <aside className="controls">
            <PowerControls
              profiles={profiles}
              profileId={profileId}
              onProfile={onProfile}
              adapters={adapters}
              adapterId={adapterId}
              onAdapter={setAdapterId}
              startBatteryPct={startBatteryPct}
              onStartBatteryPct={setStartBatteryPct}
              thermalMode={thermalMode}
              onThermalMode={setThermalMode}
              workload={workload}
              onWorkload={setWorkload}
              speed={speed}
              onSpeed={setSpeed}
              running={running}
              done={done}
              phaseLabel={state?.label ?? "—"}
              onRun={run}
              onPause={stop}
              onStep={step}
              onReset={reset}
            />
            <PowerCounters
              state={state}
              summary={summary}
              stepIndex={cursor}
              stepCount={trace.length}
            />
            <Legend />
          </aside>
        </>
      )}
    </div>
  );
}
