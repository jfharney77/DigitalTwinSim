import { useEffect, useState } from "react";
import { fetchLessonTour, fetchTourRecording } from "../api";
import type { GpuProfile, LessonTour as Tour, LiveState } from "../types";
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

  useEffect(() => {
    fetchLessonTour().then(setTour).catch((e) => setError(String(e)));
  }, []);

  const step = tour?.steps[stepIdx] ?? null;

  useEffect(() => {
    if (!step) return;
    setFrame(null);
    fetchTourRecording(step.lessonId)
      .then((trace) => setFrame(trace[step.cursor] ?? null))
      .catch((e) => setError(String(e)));
  }, [step]);

  if (error) return <div className="mini an-error">{error}</div>;
  if (!tour || !step) return <p className="mini">loading tour…</p>;

  const last = stepIdx === tour.steps.length - 1;
  const smCount = frame ? dieGrid(frame, profile).count : 24;

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
      </p>
      <LiveDieView profile={profile} state={frame} />
      <LiveCounters state={frame} />
      <GanttStrip state={frame} smCount={smCount} />
      {step.experiment && (
        <p className="mini">
          <strong>Try it:</strong> {step.experiment}
        </p>
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
