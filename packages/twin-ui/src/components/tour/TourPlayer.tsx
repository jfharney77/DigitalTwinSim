import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { makeRegionLook, useCameraTween, useReducedMotion } from "./motion";
import { silence, speak, speechSupported } from "./narration";
import type { CameraBox, Tour, TourRegion, TourStage } from "./types";
import "./tour.css";

// TourPlayer — the second clock owner (ACTIVE_TWIN_SPEC.md section 5).
//
// One requestAnimationFrame timeline advances through the tour's steps. The
// player never draws the product itself: the host twin passes its own diagram
// through `renderStage`, receiving the tweened camera, the lit regions and a
// per-region layer look. When a step pins a trace index the player reports it
// through `onTraceCursor`, and the host moves its existing playback cursor —
// the engine and the trace stay untouched.
//
// Nothing here imports from the host twin; it lives in packages/twin-ui and
// every twin imports it from @twinsim/twin-ui.

export interface TourPlayerProps {
  /** The tour, already resolved at the reader's level (GET /api/tour → tour). */
  tour: Tour;
  /** Region id → layer (GET /api/tour → layers). */
  layers: Record<string, number>;
  /** Map bounds the camera boxes live in (GET /api/tour → mapWidth/mapHeight). */
  bounds: { width: number; height: number };
  /** The map's regions, for the explode direction of peeled layers. */
  regions: TourRegion[];
  /** The twin's own diagram, drawn from the stage the player computes. */
  renderStage: (stage: TourStage) => ReactNode;
  /** A step pinned a trace index: move the host's playback cursor there. */
  onTraceCursor?: (index: number) => void;
  /** Step to open on (from a #tour/<stepId> deep link). Unknown ids open the first step. */
  initialStepId?: string | null;
  /** The current step changed; the host typically rewrites its #tour/<id> hash. */
  onStepChange?: (stepId: string) => void;
  /** Extra content for the side column — e.g. the pinned trace step's label. */
  aside?: ReactNode;
  /**
   * Width ÷ height of the stage's diagram box. Fixed so the stage does not
   * change height while the camera tweens. Defaults to the map's own bounds;
   * pass the renderer's ratio when it draws a margin around the map.
   */
  stageAspect?: number;
}

const SPEEDS = [0.75, 1, 1.25, 1.5, 2] as const;
const CAMERA_MS = 1100;

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return (
    tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || tag === "BUTTON" ||
    el.isContentEditable
  );
}

export function TourPlayer({
  tour,
  layers,
  bounds,
  regions,
  renderStage,
  onTraceCursor,
  initialStepId,
  onStepChange,
  aside,
  stageAspect,
}: TourPlayerProps) {
  const steps = tour.steps;
  const reduced = useReducedMotion();

  const [index, setIndex] = useState(() => {
    const i = steps.findIndex((s) => s.id === initialStepId);
    return i >= 0 ? i : 0;
  });
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const [muted, setMuted] = useState(true); // autoplay policy: sound waits for the viewer
  const [takenOver, setTakenOver] = useState(false);
  const [freeView, setFreeView] = useState(false);
  const [showPhoto, setShowPhoto] = useState(false);
  const [captionOver, setCaptionOver] = useState(false);

  // The rAF loop reads these without re-subscribing every frame.
  const pos = useRef({ index, elapsed });
  const speaking = useRef(false);
  const hold = useRef(0); // ms spent past the step's duration, waiting on speech
  const playingRef = useRef(playing);
  playingRef.current = playing;
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const stepsRef = useRef(steps);
  stepsRef.current = steps;

  const step = steps[Math.min(index, steps.length - 1)];
  const offsets = useMemo(() => {
    const out: number[] = [];
    let t = 0;
    for (const s of steps) {
      out.push(t);
      t += s.durationMs;
    }
    return { starts: out, total: t };
  }, [steps]);

  const goTo = useCallback((i: number, at = 0) => {
    const n = stepsRef.current.length;
    const next = Math.max(0, Math.min(n - 1, i));
    pos.current = { index: next, elapsed: at };
    hold.current = 0;
    setIndex(next);
    setElapsed(at);
  }, []);

  // --- the clock -----------------------------------------------------------
  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = now - last;
      last = now;
      const p = pos.current;
      const all = stepsRef.current;
      const cur = all[p.index];
      let e = p.elapsed + dt * speedRef.current;
      if (e >= cur.durationMs) {
        hold.current += dt;
        if (speaking.current && hold.current < cur.durationMs) {
          // Hold the frame until the narrator finishes — but never more than
          // one extra step-length, so a voice that never reports "done"
          // cannot stall the tour.
          e = cur.durationMs;
        } else if (p.index < all.length - 1) {
          goTo(p.index + 1, 0);
          frame = requestAnimationFrame(tick);
          return;
        } else {
          pos.current = { index: p.index, elapsed: cur.durationMs };
          setElapsed(cur.durationMs);
          setPlaying(false);
          return;
        }
      }
      pos.current = { index: p.index, elapsed: e };
      setElapsed(e);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, goTo]);

  // --- narration (tier 1); captions are always rendered below -------------
  useEffect(() => {
    if (!playing || muted || !speechSupported()) {
      speaking.current = false;
      return;
    }
    speaking.current = true;
    const cancel = speak(step.script, speedRef.current, () => {
      speaking.current = false;
    });
    return cancel;
  }, [playing, muted, step.script, index]);

  useEffect(() => () => silence(), []);

  // --- drive the host's trace cursor, report the step ----------------------
  const traceCb = useRef(onTraceCursor);
  traceCb.current = onTraceCursor;
  const stepCb = useRef(onStepChange);
  stepCb.current = onStepChange;
  useEffect(() => {
    if (step.traceCursor !== null) traceCb.current?.(step.traceCursor);
    stepCb.current?.(step.id);
  }, [step.id, step.traceCursor]);

  // --- take-over -------------------------------------------------------------
  const takeOver = useCallback(() => {
    setPlaying(false);
    setTakenOver(true);
  }, []);

  const resume = useCallback(() => {
    setTakenOver(false);
    setFreeView(false);
    const p = pos.current;
    const all = stepsRef.current;
    if (p.index === all.length - 1 && p.elapsed >= all[p.index].durationMs) goTo(0, 0);
    setPlaying(true);
  }, [goTo]);

  const togglePlay = useCallback(() => {
    if (playing) setPlaying(false);
    else resume();
  }, [playing, resume]);

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden && playingRef.current) takeOver();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [takeOver]);

  // --- keyboard ---------------------------------------------------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey || isTyping(e.target)) return;
      if (e.key === " ") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goTo(pos.current.index + 1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        goTo(pos.current.index - 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [togglePlay, goTo]);

  // --- stage -----------------------------------------------------------------
  const whole: CameraBox = { x: 0, y: 0, w: bounds.width, h: bounds.height };
  const target = freeView ? whole : step.camera;
  const viewBox = useCameraTween(target, CAMERA_MS / speed, reduced);
  const lit = useMemo(() => new Set(step.regionIds), [step.regionIds]);
  const reveal = freeView ? 0 : step.layerReveal;
  const regionLook = useMemo(
    () => makeRegionLook(regions, layers, reveal, lit, bounds, reduced),
    [regions, layers, reveal, lit, bounds, reduced],
  );
  const stage: TourStage = {
    viewBox,
    lit,
    regionLook,
    onRegionClick: takeOver,
    takenOver,
    reducedMotion: reduced,
  };

  const photo = step.photoId ? tour.photos.find((p) => p.id === step.photoId) ?? null : null;
  const position = offsets.starts[index] + Math.min(elapsed, step.durationMs);
  const finished = !playing && index === steps.length - 1 && elapsed >= step.durationMs;

  const seek = (ms: number) => {
    let i = 0;
    while (i < steps.length - 1 && offsets.starts[i + 1] <= ms) i += 1;
    goTo(i, ms - offsets.starts[i]);
  };

  const caption = (
    <p className={captionOver ? "tour-caption tour-caption-over" : "tour-caption"} aria-live="polite">
      <strong>{step.title}.</strong> {step.script}
    </p>
  );

  return (
    <div className="tour">
      <div className="tour-main">
        <div
          className={reduced ? "tour-stage tour-reduced" : "tour-stage"}
          style={{ "--tour-aspect": String(stageAspect ?? bounds.width / bounds.height) } as CSSProperties}
        >
          {renderStage(stage)}
          {photo && showPhoto && (
            <figure className="tour-photo">
              <img src={photo.url} alt={photo.caption} />
              <figcaption>
                {photo.caption} <span className="tour-credit">Photo: {photo.credit}</span>
              </figcaption>
            </figure>
          )}
          {captionOver && caption}
        </div>
        {!captionOver && caption}

        {takenOver && (
          <div className="tour-takeover" role="status">
            <span>The tour is paused so you can look around.</span>
            <button className="primary" onClick={resume}>
              Resume tour
            </button>
            {!freeView && <button onClick={() => setFreeView(true)}>Show the whole map</button>}
          </div>
        )}

        <div className="tour-transport">
          <div className="tour-buttons">
            <button onClick={() => goTo(index - 1)} disabled={index === 0}>
              Previous
            </button>
            <button className="primary" onClick={togglePlay}>
              {playing ? "Pause" : finished ? "Replay" : "Play"}
            </button>
            <button onClick={() => goTo(index + 1)} disabled={index === steps.length - 1}>
              Next
            </button>
          </div>
          <div className="tour-scrub">
            <input
              type="range"
              min={0}
              max={offsets.total}
              step={100}
              value={position}
              aria-label="Tour position"
              aria-valuetext={step.title}
              onChange={(e) => seek(Number(e.target.value))}
            />
            <div className="tour-ticks" aria-hidden="true">
              {offsets.starts.map((t, i) => (
                <i
                  key={steps[i].id}
                  className={i <= index ? "tour-tick tour-tick-past" : "tour-tick"}
                  style={{ left: `${(t / offsets.total) * 100}%` }}
                />
              ))}
            </div>
          </div>
          <div className="tour-options">
            <label>
              Speed
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                aria-label="Playback speed"
              >
                {SPEEDS.map((s) => (
                  <option key={s} value={s}>
                    {s}×
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={() => setMuted((m) => !m)}
              disabled={!speechSupported()}
              aria-pressed={!muted}
              title={speechSupported() ? undefined : "This browser has no speech synthesis; captions carry the narration."}
            >
              {muted ? "Turn narration on" : "Turn narration off"}
            </button>
            <button onClick={() => setCaptionOver((c) => !c)} aria-pressed={captionOver}>
              {captionOver ? "Captions below" : "Captions on the diagram"}
            </button>
            {photo && (
              <button onClick={() => setShowPhoto((v) => !v)} aria-pressed={showPhoto}>
                {showPhoto ? "Hide the photo" : "Show the real product"}
              </button>
            )}
          </div>
        </div>
      </div>

      <aside className="tour-side">
        <h2>{tour.title}</h2>
        <p className="tour-intro">{tour.intro}</p>
        <ul className="tour-steps">
          {steps.map((s, i) => (
            <li key={s.id}>
              <button
                className={i === index ? "tour-step tour-step-current" : "tour-step"}
                aria-current={i === index ? "step" : undefined}
                onClick={() => goTo(i)}
              >
                {s.title}
              </button>
            </li>
          ))}
        </ul>
        {aside}
        {tour.sources.length > 0 && (
          <div className="tour-sources">
            <h2>Sources</h2>
            {tour.sources.map((s) => (
              <a key={s.url} href={s.url} target="_blank" rel="noreferrer">
                {s.label}
              </a>
            ))}
          </div>
        )}
        <p className="tour-keys">Space plays and pauses; the arrow keys move between beats.</p>
      </aside>
    </div>
  );
}
