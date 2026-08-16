import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteLiveSession,
  fetchAtlas,
  fetchLiveSessions,
  fetchLiveTrace,
  fetchProfiles,
  fetchSessionSummary,
  importLiveSession,
  liveStreamUrl,
  sessionCsvUrl,
  sessionDownloadUrl,
  startLiveSession,
  stopLiveSession,
} from "../api";
import { downloadSvgFrom } from "../svgExport";
import type { Atlas, GpuProfile, LiveSessionInfo, LiveState } from "../types";
import { dieForDevice } from "../types";
import { ComparePane } from "./ComparePane";
import { GanttStrip } from "./GanttStrip";
import { LessonTour } from "./LessonTour";
import { dieGrid, fmt, frameKey, LiveCounters, LiveDieView } from "./LiveViz";

// Live CUDA co-browsing (spec_08 + specs 10/11/12/14/16/17/18). The page owns
// its clock (SSE frames are buffered and rendered; replay plays a recorded
// trace on a local interval) — the backend never paces anything, exactly like
// the simulator. Pins and timeline selection use frameKey(), not indices:
// the buffer trims at its cap and indices shift (spec_11).

const BUFFER_CAP = 2000;
const REPLAY_MS = 350;
const CHIP_CAP = 50; // spec_19 #14: don't render 1,000 timeline buttons

type Conn = "live" | "reconnecting" | "replaying";

// spec_19 #15: recent kernel times as a tiny trend line.
function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const w = 120;
  const h = 22;
  const max = Math.max(...values);
  const pts = values
    .map(
      (v, i) =>
        `${(i / (values.length - 1)) * (w - 4) + 2},${h - 2 - (v / max) * (h - 6)}`,
    )
    .join(" ");
  return (
    <svg
      width={w}
      height={h}
      aria-label="Recent kernel times"
      style={{ verticalAlign: "middle" }}
    >
      <title>last {values.length} kernel times (ms), newest right</title>
      <polyline points={pts} fill="none" stroke="#4f7cff" strokeWidth={1.5} />
    </svg>
  );
}

export function LivePage({ profile }: { profile: GpuProfile }) {
  const [buffer, setBuffer] = useState<LiveState[]>([]);
  const [conn, setConn] = useState<Conn>("reconnecting");
  const [skipped, setSkipped] = useState(0); // frames this tab lagged past
  const [pinnedKey, setPinnedKey] = useState<string | null>(null);
  const [compareKeys, setCompareKeys] = useState<{
    a: string | null;
    b: string | null;
  }>({ a: null, b: null });
  const [sessions, setSessions] = useState<LiveSessionInfo[]>([]);
  const [sessionName, setSessionName] = useState(
    () => localStorage.getItem("twin.sessionName") ?? "",
  );
  const [active, setActive] = useState<string | null>(null);
  const [replayCursor, setReplayCursor] = useState(0);
  const [replayTrace, setReplayTrace] = useState<LiveState[] | null>(null);
  // spec_28: fleet replay — which die the recording is viewed on (null =
  // the recorded device), the recorded trace kept for side-by-side, and
  // the fleet names for the picker.
  const [replaySession, setReplaySession] = useState<string | null>(null);
  const [viewProfile, setViewProfile] = useState<string | null>(null);
  const [baseTrace, setBaseTrace] = useState<LiveState[] | null>(null);
  const [compareRemap, setCompareRemap] = useState(false);
  const [profileNames, setProfileNames] = useState<string[]>([]);
  // spec_30: the atlas's deviceMatch substrings drive the die badge on the
  // device line — the local 4060 gets none until an AD107 anatomy lands.
  const [atlas, setAtlas] = useState<Atlas | null>(null);
  useEffect(() => {
    fetchProfiles()
      .then((ps) => setProfileNames(ps.map((p) => p.name)))
      .catch(() => setProfileNames([]));
    fetchAtlas().then(setAtlas).catch(() => setAtlas(null));
  }, []);
  const [replayPaused, setReplayPaused] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(1); // spec_20 #12
  const [showAllChips, setShowAllChips] = useState(false);
  const [summaryText, setSummaryText] = useState<Record<string, string>>({});
  // spec_20 #14: #live/tour deep-links straight into the guided lessons.
  const [touring, setTouring] = useState(
    () => window.location.hash === "#live/tour",
  );
  // spec_21 #9: "reconnecting" could mean a hiccup or a dead backend —
  // a health probe on mount tells the difference honestly.
  const [backendDown, setBackendDown] = useState(false);
  useEffect(() => {
    fetch("/api/health")
      .then((r) => setBackendDown(!r.ok))
      .catch(() => setBackendDown(true));
  }, [conn]);
  const replayTimer = useRef<number | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);

  const refreshSessions = useCallback(() => {
    fetchLiveSessions()
      .then((s) => {
        setSessions(s);
        setActive(s.find((x) => x.active)?.id ?? null);
      })
      .catch(() => setSessions([]));
  }, []);

  // SSE subscription — the live feed. EventSource reconnects on its own.
  useEffect(() => {
    if (replayTrace || touring) return; // replay/tour mode owns the screen
    const es = new EventSource(liveStreamUrl());
    es.onopen = () => setConn("live");
    es.onerror = () => setConn("reconnecting");
    es.onmessage = (m) => {
      const s = JSON.parse(m.data) as LiveState;
      setBuffer((b) => [...b.slice(-BUFFER_CAP + 1), s]);
      if (s.kind === "kernel") refreshSessions();
    };
    // The backend reports frames this consumer lagged past — show them, so a
    // stale view never silently passes as live.
    es.addEventListener("dropped", (m) => {
      setSkipped((n) => n + Number((m as MessageEvent).data));
    });
    return () => es.close();
  }, [replayTrace, touring, refreshSessions]);

  useEffect(refreshSessions, [refreshSessions]);

  // Keep the hash honest for the tour deep link (spec_20 #14).
  useEffect(() => {
    if (touring) window.location.hash = "live/tour";
    else if (window.location.hash === "#live/tour") window.location.hash = "live";
  }, [touring]);

  // Replay clock — lives here, never in the backend.
  useEffect(() => {
    if (!replayTrace || replayPaused) return;
    setConn("replaying");
    replayTimer.current = window.setInterval(() => {
      setReplayCursor((c) => Math.min(c + 1, replayTrace.length - 1));
    }, REPLAY_MS / replaySpeed);
    return () => {
      if (replayTimer.current !== null) window.clearInterval(replayTimer.current);
    };
  }, [replayTrace, replayPaused, replaySpeed]);

  // spec_19 #12: space pauses/resumes replay, arrows step the cursor.
  useEffect(() => {
    if (!replayTrace) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        setReplayPaused((p) => !p);
      } else if (e.code === "ArrowRight") {
        setReplayPaused(true);
        setReplayCursor((c) => Math.min(c + 1, replayTrace.length - 1));
      } else if (e.code === "ArrowLeft") {
        setReplayPaused(true);
        setReplayCursor((c) => Math.max(0, c - 1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [replayTrace]);

  const pool = replayTrace ?? buffer;
  const byKey = (key: string | null): LiveState | null =>
    key ? (pool.find((s) => frameKey(s) === key) ?? null) : null;

  const liveState = buffer.length ? buffer[buffer.length - 1] : null;
  const kernels = pool.filter((s) => s.kind === "kernel");
  const shown: LiveState | null = replayTrace
    ? (replayTrace[Math.min(replayCursor, replayTrace.length - 1)] ?? null)
    : (byKey(pinnedKey) ?? liveState);

  const compareA = byKey(compareKeys.a);
  const compareB = byKey(compareKeys.b);
  const smCount = shown ? dieGrid(shown, profile).count : 24;
  // spec_30: when the session/recording's device name matches an atlas
  // deviceMatch substring, badge it with that die's anatomy (the lesson-07
  // H100/B300 goldens are the payoff). Device info carries forward on every
  // folded frame, so the badge holds for the whole session.
  const badgeDie = dieForDevice(atlas, shown?.device?.name);

  // spec_28: the recorded frame matching the shown remapped frame — remap is
  // 1:1 on frames and keeps tMs/kernel/kind, so frameKey() resolves it.
  const remapBase =
    compareRemap && baseTrace && shown
      ? (baseTrace.find((s) => frameKey(s) === frameKey(shown)) ?? null)
      : null;

  // spec_20 #13: while pinned, count kernels that arrived after the pin.
  const pinnedFrame = byKey(pinnedKey);
  const movedOn =
    pinnedFrame && !replayTrace
      ? buffer.filter((s) => s.kind === "kernel" && s.tMs > pinnedFrame.tMs).length
      : 0;

  // spec_20 #18: delta vs the previous run of the same kernel.
  const deltaFor = (s: LiveState): string => {
    if (s.elapsedMs == null) return "";
    const prev = [...kernels]
      .filter((k) => k.kernel === s.kernel && k.tMs < s.tMs && k.elapsedMs != null)
      .pop();
    if (!prev || prev.elapsedMs == null) return "";
    const d = s.elapsedMs - prev.elapsedMs;
    if (Math.abs(d) < 0.005) return " ·=";
    return ` ${d < 0 ? "▼" : "▲"}${Math.abs(d).toFixed(2)}`;
  };

  const showSummary = (id: string) => {
    if (summaryText[id]) {
      setSummaryText((m) => ({ ...m, [id]: "" }));
      return;
    }
    fetchSessionSummary(id).then((s) => {
      const fastest = s.kernelStats
        .filter((k) => k.bestMs != null)
        .sort((x, y) => (x.bestMs ?? 0) - (y.bestMs ?? 0))[0];
      setSummaryText((m) => ({
        ...m,
        [id]:
          `${s.kernelLaunches} kernel run(s) · ${s.frames} frames · ` +
          `${(s.durationMs / 1000).toFixed(1)}s` +
          (fastest ? ` · fastest ${fastest.kernel} ${fastest.bestMs?.toFixed(2)}ms` : "") +
          (s.deviceName ? ` · ${s.deviceName}` : ""),
      }));
    });
  };

  const importFile = (file: File) => {
    file.text().then((jsonl) =>
      importLiveSession(file.name.replace(/\.jsonl$/, ""), jsonl)
        .then(refreshSessions)
        .catch((e) => alert(`import failed: ${e}`)),
    );
  };

  const startReplay = (id: string) => {
    fetchLiveTrace(id).then((t) => {
      setPinnedKey(null);
      setCompareKeys({ a: null, b: null });
      setReplaySession(id);
      setViewProfile(null);
      setBaseTrace(null);
      setCompareRemap(false);
      setReplayCursor(0);
      setReplayPaused(false);
      setReplayTrace(t);
    });
  };

  // spec_28: refetch the same recording remapped onto another die. The remap
  // is 1:1 on frames (frameKey still resolves), so the cursor is kept.
  const viewOn = (name: string | null) => {
    if (!replaySession) return;
    Promise.all([
      fetchLiveTrace(replaySession, name),
      name ? fetchLiveTrace(replaySession) : Promise.resolve(null),
    ]).then(([t, base]) => {
      setViewProfile(name);
      setBaseTrace(name ? base : null);
      if (!name) setCompareRemap(false);
      setReplayTrace(t);
      setReplayCursor((c) => Math.min(c, t.length - 1));
    });
  };

  // spec_19 #18 (shared helper since spec_21 #3).
  const downloadSvg = () =>
    downloadSvgFrom(stageRef.current, `${shown?.kernel ?? "die"}-live`);
  const backToLive = () => {
    setReplayTrace(null);
    setReplaySession(null);
    setViewProfile(null);
    setBaseTrace(null);
    setCompareRemap(false);
    setPinnedKey(null);
    setConn("reconnecting");
  };

  const pinChip = (s: LiveState, shift: boolean) => {
    const key = frameKey(s);
    if (shift) {
      // shift-click: build the comparison (first shift-click = A, next = B).
      setCompareKeys((c) => (c.a ? { ...c, b: key } : { a: key, b: null }));
    } else if (replayTrace) {
      const idx = replayTrace.findIndex((x) => frameKey(x) === key);
      if (idx >= 0) setReplayCursor(idx);
    } else {
      setPinnedKey(key);
    }
  };

  const badge =
    conn === "live"
      ? skipped > 0
        ? `Live · ${skipped} frames skipped`
        : "Live"
      : conn === "replaying"
        ? "Replaying"
        : "Reconnecting…";

  if (touring) {
    return (
      <>
        <div className="stage">
          <div className="an-card">
            <LessonTour profile={profile} onExit={() => setTouring(false)} />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="an-hero">
        <h2>Live CUDA</h2>
        <p>
          Run an instrumented CUDA program (see <code>GPU/cuda/</code>) and
          watch the die light the SMs the hardware scheduler actually chose.
          Start <code>twin-sampler</code> for utilization, VRAM, power, and
          temperature — or <code>twin-run any-cuda-app</code> for timing-only
          capture of uninstrumented programs. No fake data: an idle die stays
          dark. New to CUDA? <button onClick={() => setTouring(true)}>▶ Guided lessons</button>
        </p>
      </div>
      <div className="stage">
        <div className="an-card">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span
              className={`badge ${conn === "live" ? "badge-compute" : "badge-memory"}`}
              role="status"
              aria-live="polite"
              onClick={() => setSkipped(0)}
              style={skipped > 0 ? { cursor: "pointer" } : undefined}
              title={skipped > 0 ? "click to acknowledge skipped frames" : undefined}
            >
              {badge}
            </span>
            {backendDown && conn !== "live" && (
              <span className="mini an-error">
                backend unreachable — start it: ./GPU/scripts/start_backend.sh
              </span>
            )}
            {shown?.kernel && (
              <span className="mini">
                {shown.kernel}
                {shown.running && <strong> · running…</strong>} · grid{" "}
                {shown.grid?.join("×")} · block {shown.block?.join("×")}
                {shown.source === "cupti" && " · cupti (timing only)"}
                {shown.recordsDropped > 0 && (
                  <strong>
                    {" "}
                    · partial — {shown.recordsDropped} block records missing
                  </strong>
                )}
              </span>
            )}
            {badgeDie && (
              <a
                className="mini"
                href={`#anatomy/${badgeDie}`}
                title={`${shown?.device?.name ?? "this device"} in the anatomy tab`}
              >
                die anatomy →
              </a>
            )}
            {replayTrace && (
              <>
                <select
                  value={viewProfile ?? ""}
                  onChange={(e) => viewOn(e.target.value || null)}
                  title="fleet replay (spec_28): view this recording remapped onto another die"
                >
                  <option value="">View on: recorded device</option>
                  {profileNames.map((n) => (
                    <option key={n} value={n}>
                      View on: {n}
                    </option>
                  ))}
                </select>
                {baseTrace && (
                  <label className="mini" style={{ whiteSpace: "nowrap" }}>
                    <input
                      type="checkbox"
                      checked={compareRemap}
                      onChange={(e) => setCompareRemap(e.target.checked)}
                    />{" "}
                    vs recorded
                  </label>
                )}
                <input
                  type="range"
                  min={0}
                  max={replayTrace.length - 1}
                  value={replayCursor}
                  onChange={(e) => setReplayCursor(Number(e.target.value))}
                  style={{ flex: 1 }}
                />
                {[0.5, 1, 2, 4].map((s) => (
                  <button
                    key={s}
                    className={replaySpeed === s ? "active" : ""}
                    onClick={() => setReplaySpeed(s)}
                  >
                    {s}×
                  </button>
                ))}
                <button onClick={backToLive}>Back to live</button>
              </>
            )}
            {!replayTrace && pinnedKey && (
              <button onClick={() => setPinnedKey(null)}>
                {movedOn > 0 ? `live moved on (${movedOn} new) →` : "Back to live"}
              </button>
            )}
          </div>
          <div ref={stageRef}>
            <LiveDieView profile={profile} state={shown} />
          </div>
          {shown?.placement === "modeled" && (
            <p className="mini" style={{ color: "#c77700", marginTop: 4 }}>
              modeled placement (recorded on {shown.recordedOn ?? "another device"})
              — durations recorded on {shown.recordedOn ?? "the original die"}; a
              bigger die changes queueing, not the work.
            </p>
          )}
          {shown && (
            <button className="mini" onClick={downloadSvg}>
              Download die SVG
            </button>
          )}
          {!shown && (
            <div className="mini">
              <p>waiting for events — quick start:</p>
              <pre>
                {"./GPU/scripts/start_all.sh\n"}
                {"./GPU/cuda/twin-sampler &        # counters\n"}
                {"cd GPU/cuda && make run-01       # first die lighting"}
              </pre>
            </div>
          )}
          <LiveCounters state={shown} />
          <GanttStrip state={shown} smCount={smCount} />
          {remapBase && shown && (
            <ComparePane
              a={remapBase}
              b={shown}
              profile={profile}
              onClose={() => setCompareRemap(false)}
              onSwap={() => {}}
            />
          )}
          {compareA && compareB && (
            <ComparePane
              a={compareA}
              b={compareB}
              profile={profile}
              onClose={() => setCompareKeys({ a: null, b: null })}
              onSwap={() => setCompareKeys((c) => ({ a: c.b, b: c.a }))}
            />
          )}
          {kernels.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="mini" style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <span>
                  Kernel timeline (this {replayTrace ? "recording" : "session"})
                  — click to inspect, shift-click two to compare
                  {replayTrace ? " · space pauses, arrows step" : ""}
                </span>
                <Sparkline
                  values={kernels
                    .slice(-30)
                    .map((s) => s.elapsedMs ?? 0)
                    .filter((v) => v > 0)}
                />
              </div>
              {kernels.length > CHIP_CAP && !showAllChips && (
                <button className="mini" onClick={() => setShowAllChips(true)}>
                  show all {kernels.length} (rendering latest {CHIP_CAP})
                </button>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                {(showAllChips ? kernels : kernels.slice(-CHIP_CAP)).map((s) => {
                  const key = frameKey(s);
                  const isPinned = replayTrace
                    ? frameKey(replayTrace[replayCursor] ?? s) === key
                    : pinnedKey === key;
                  const mark =
                    compareKeys.a === key ? " [A]" : compareKeys.b === key ? " [B]" : "";
                  return (
                    <button
                      key={key}
                      className={isPinned ? "active" : ""}
                      onClick={(e) => pinChip(s, e.shiftKey)}
                      title={`t=${(s.tMs / 1000).toFixed(1)}s${s.source === "cupti" ? " · cupti" : ""}`}
                      aria-label={`kernel ${s.kernel}, ${fmt(s.elapsedMs, " milliseconds", 2)}, occupancy ${fmt(s.occupancyPct, " percent", 0)}${isPinned ? ", inspecting" : ""}`}
                    >
                      {s.kernel} · {fmt(s.elapsedMs, "ms", 2)}
                      {deltaFor(s)} · {fmt(s.occupancyPct, "%", 0)}
                      {mark}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
      <aside className="controls">
        <div className="an-card">
          <h3>Session</h3>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              placeholder="session name"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
            />
            <button
              onClick={() => {
                localStorage.setItem("twin.sessionName", sessionName);
                startLiveSession(sessionName || "session").then(() => {
                  setBuffer([]);
                  setPinnedKey(null);
                  setCompareKeys({ a: null, b: null });
                  setSkipped(0);
                  refreshSessions();
                });
              }}
            >
              Start
            </button>
            <button
              onClick={() => stopLiveSession().then(refreshSessions)}
              disabled={!active}
            >
              Stop
            </button>
          </div>
          <h3 style={{ marginTop: 14 }}>Recordings</h3>
          <label className="mini" style={{ display: "block", marginBottom: 6 }}>
            Import a downloaded .jsonl:{" "}
            <input
              type="file"
              accept=".jsonl"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) importFile(f);
                e.target.value = "";
              }}
            />
          </label>
          {sessions.length === 0 && <p className="mini">none yet</p>}
          <ul className="mini" style={{ listStyle: "none", padding: 0 }}>
            {sessions.map((s) => (
              <li
                key={s.id}
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  justifyContent: "space-between",
                  gap: 8,
                  padding: "3px 0",
                }}
              >
                <span>
                  {s.name} · {s.eventCount} events{s.active ? " · recording" : ""}
                </span>
                <span style={{ display: "flex", gap: 4 }}>
                  {s.eventCount > 0 && (
                    <>
                      <button title="session summary" onClick={() => showSummary(s.id)}>
                        ⓘ
                      </button>
                      <button onClick={() => startReplay(s.id)}>Replay</button>
                      <a href={sessionDownloadUrl(s.id)} download>
                        <button>Download</button>
                      </a>
                      <a href={sessionCsvUrl(s.id)} download>
                        <button title="kernel frames as CSV">CSV</button>
                      </a>
                    </>
                  )}
                  <button
                    disabled={s.active}
                    title={s.active ? "actively recording" : "delete recording"}
                    onClick={() => deleteLiveSession(s.id).then(refreshSessions)}
                  >
                    Delete
                  </button>
                </span>
                {summaryText[s.id] && (
                  <div style={{ flexBasis: "100%" }}>{summaryText[s.id]}</div>
                )}
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </>
  );
}
