import { useEffect, useState } from "react";
import { fetchAtlas, fetchLessonTour, fetchTourRecording } from "../api";
import { useLevel } from "../level";
import type { Atlas, GpuProfile, LessonTour as Tour, LiveState } from "../types";
import { dieForDevice } from "../types";
import { GanttStrip } from "./GanttStrip";
import { dieGrid, LiveCounters, LiveDieView } from "./LiveViz";

// spec_18: the CUDA curriculum as a narrated, GPU-free tour. Each step pins
// a frame of a golden lesson recording, replayed through the same pipeline
// as any live session. Provenance is always shown — a representative
// recording must never pass as captured hardware.

export function LessonTour({
  profile,
  onExit,
}: {
  profile: GpuProfile;
  onExit: () => void;
}) {
  const [tour, setTour] = useState<Tour | null>(null);
  const [stepIdx, setStepIdx] = useState(0);
  const [frame, setFrame] = useState<LiveState | null>(null);
  const [error, setError] = useState<string | null>(null);
  // spec_30: the atlas drives the recording's die-anatomy badge.
  const [atlas, setAtlas] = useState<Atlas | null>(null);
  // spec_29: the tour's prose rides the reading level. A level change
  // refetches the tour but never resets the reader's step (house rule —
  // step count is level-invariant), and never refetches the recording.
  const level = useLevel();

  useEffect(() => {
    fetchLessonTour().then(setTour).catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    fetchAtlas().then(setAtlas).catch(() => setAtlas(null));
  }, []);

  const step = tour?.steps[stepIdx] ?? null;
  const lessonId = step?.lessonId ?? null;
  const cursor = step?.cursor ?? 0;

  useEffect(() => {
    if (!lessonId) return;
    setFrame(null);
    fetchTourRecording(lessonId)
      .then((trace) => setFrame(trace[cursor] ?? null))
      .catch((e) => setError(String(e)));
    // spec_29: keyed on the lesson, not the step object — a level change
    // swaps prose only and must not re-run this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId]);

  if (error) return <div className="mini an-error">{error}</div>;
  if (!tour || !step) return <p className="mini">loading tour…</p>;

  const last = stepIdx === tour.steps.length - 1;
  const smCount = frame ? dieGrid(frame, profile).count : 24;
  // spec_30: badge the recorded device with its die's anatomy when the
  // atlas recognizes the name (the lesson-07 H100/B300 goldens).
  const badgeDie = dieForDevice(atlas, frame?.device?.name);
  // spec_30: the authored step link, rendered as a real button.
  const linkLabel = (link: string) =>
    link.startsWith("#anatomy")
      ? link.includes("/vs/")
        ? "Compare the dies →"
        : "Open in die anatomy →"
      : link.startsWith("#live")
        ? "Open live →"
        : "Open the simulator →";

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h3 style={{ margin: 0 }}>{tour.title}</h3>
        <span className="mini">
          {stepIdx + 1} / {tour.steps.length}
        </span>
        <button onClick={onExit}>Exit tour</button>
      </div>
      {stepIdx === 0 && <p className="mini">{tour.intro}</p>}
      <h4 style={{ marginBottom: 4 }}>{step.title}</h4>
      <p>{step.script}</p>
      <p className="mini">
        {step.provenance === "hardware"
          ? "recorded on real hardware"
          : "representative recording — capture your own with make run-" +
            step.lessonId.slice(0, 2)}
        {badgeDie && (
          <>
            {" · "}
            <a href={`#anatomy/${badgeDie}`}>die anatomy →</a>
          </>
        )}
      </p>
      <LiveDieView profile={profile} state={frame} />
      <LiveCounters state={frame} />
      <GanttStrip state={frame} smCount={smCount} />
      {step.experiment && (
        <p className="mini">
          <strong>Try it:</strong> {step.experiment}
        </p>
      )}
      {step.link != null && (
        <button
          onClick={() => {
            // spec_30: a real button where the prose used to name tabs in
            // words. Setting the hash lets App's hashchange sync switch tabs.
            window.location.hash = step.link!;
          }}
        >
          {linkLabel(step.link)}
        </button>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
        <button
          disabled={stepIdx === 0}
          onClick={() => setStepIdx((i) => Math.max(0, i - 1))}
        >
          Back
        </button>
        {!last ? (
          <button onClick={() => setStepIdx((i) => i + 1)}>Next</button>
        ) : (
          <button onClick={onExit}>Now you: go live</button>
        )}
      </div>
    </div>
  );
}
