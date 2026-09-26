import { useEffect, useState } from "react";
import { gradeLab, readBest, recordBest } from "../labs";
import type { Lab, LabResult } from "../labs";
import { useLevel } from "../level";
import type { Explain, Scenario } from "../types";
import "../labs.css";

// A graded lab (docs/LAB_PATTERN.md): the goal card, Run and grade, the
// per-criterion results, and progressive hints. The learner builds the
// scenario with the page's ordinary controls; this panel only reads it.
// Grading is the backend's pure function — the panel holds no rules.

function fmt(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(Math.abs(n) < 10 ? 2 : 1);
}

export function LabPanel({
  labs,
  lab,
  scenario,
  explains,
  onSelect,
  onLoadStart,
  onExplain,
  onClose,
}: {
  labs: Lab[];
  lab: Lab | null;
  scenario: Scenario;
  explains: Explain[];
  onSelect: (lab: Lab) => void;
  onLoadStart: (lab: Lab) => void;
  onExplain: () => void;
  onClose: () => void;
}) {
  const level = useLevel();
  const [result, setResult] = useState<LabResult | null>(null);
  const [graded, setGraded] = useState<Scenario | null>(null);
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hintsShown, setHintsShown] = useState(0);
  const [best, setBest] = useState<Record<string, number>>(() => readBest());

  // A different lab starts clean.
  useEffect(() => {
    setResult(null);
    setGraded(null);
    setHintsShown(0);
    setError(null);
  }, [lab?.id]);

  const run = (sc: Scenario) => {
    if (!lab) return;
    setGrading(true);
    gradeLab(lab.id, sc)
      .then((r) => {
        setResult(r);
        setGraded(sc);
        setBest(recordBest(lab.id, r.score));
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setGrading(false));
  };

  // The result carries leveled prose: a level change re-grades the same
  // scenario (grading is deterministic, so only the words change).
  useEffect(() => {
    if (graded) run(graded);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level]);

  const stale = result !== null && graded !== scenario;
  const explainTitle = (id: string) => explains.find((e) => e.id === id)?.title ?? id;

  return (
    <div className="an-panel lab-panel">
      <h2>Labs</h2>
      <p className="mini">
        A lab gives you a goal instead of a script. Build the scenario with the
        controls below, then run and grade it. Work delivered is always part of
        the grade, so an idle array passes nothing. Scores and the work
        measure are illustrative.
      </p>
      <div className="lab-list">
        {labs.map((l) => (
          <button
            key={l.id}
            className={lab?.id === l.id ? "active" : ""}
            onClick={() => onSelect(l)}
          >
            {l.title}
            <span className="lab-best">
              {"●".repeat(l.difficulty)}
              {l.id in best ? ` best ${best[l.id]}` : ""}
            </span>
          </button>
        ))}
        <button onClick={onClose}>Close labs</button>
      </div>

      {lab && (
        <div className="lab-grid">
          <div className="lab-goal">
            <h3>{lab.title}</h3>
            <p>{lab.goal.statement}</p>
            <ul>
              {lab.goal.constraints.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
              <li>{lab.goal.deliveredWork}</li>
            </ul>
            {lab.objective && (
              <p className="lab-meta">
                Beyond a pass: {lab.objective.direction} {lab.objective.label.toLowerCase()}{" "}
                — full marks at {fmt(lab.objective.par)} {lab.objective.unit}.
              </p>
            )}
            <div className="btnrow lab-actions">
              <button className="primary lab-run" disabled={grading} onClick={() => run(scenario)}>
                {grading ? "Grading…" : "Run and grade"}
              </button>
              <button onClick={() => onLoadStart(lab)}>Reset to the lab's start</button>
              {hintsShown < lab.hints.length && (
                <button className="lab-hint-btn" onClick={() => setHintsShown(hintsShown + 1)}>
                  {hintsShown === 0 ? "Show a hint" : "Show another hint"}
                </button>
              )}
            </div>
            {lab.hints.slice(0, hintsShown).map((h, i) => (
              <p key={i} className="lab-hint">{h}</p>
            ))}
          </div>

          <div className="lab-results">
            {error && <div className="mini an-error">{error}</div>}
            {grading && (
              <p className="mini lab-grading">
                Grading — running the engine. On the hosted site the first run
                loads the engine into the browser, which takes a moment.
              </p>
            )}
            {!grading && !result && !error && (
              <p className="mini">
                No grade yet. The start scenario does not pass — change the
                build, the workload or the run, then run and grade.
              </p>
            )}
            {result && (
              <>
                <p className={`lab-score ${result.passed ? "pass" : "fail"}`}>
                  {result.score} / 100
                </p>
                <p className="lab-verdict">
                  {result.verdict}
                  {stale && " The scenario has changed since this grade."}
                </p>
                {result.objective && result.passed && (
                  <>
                    <div className="mini">
                      {result.objective.label}: {fmt(result.objective.measured)}{" "}
                      {result.objective.unit} (full marks at {fmt(result.objective.par)})
                    </div>
                    <div className="lab-objective-bar">
                      <div
                        className="lab-objective-fill"
                        style={{ width: `${Math.round(100 * result.objective.fraction)}%` }}
                      />
                    </div>
                  </>
                )}
                {result.criteria.map((c) => (
                  <details key={c.id} className="lab-criterion" open={!c.passed}>
                    <summary>
                      <span className={c.passed ? "mark-pass" : "mark-fail"}>
                        {c.passed ? "✓" : "✗"}
                      </span>{" "}
                      {c.label}
                      <span className="lab-measured">
                        measured {fmt(c.measured)} {c.unit} (needs {c.op} {fmt(c.threshold)})
                      </span>
                    </summary>
                    <div className="lab-why">
                      <span className="lab-eq">{c.equation}</span>
                      {c.why}
                      <div>
                        <button onClick={onExplain}>
                          Open “{explainTitle(c.explainId)}” in Explain mode
                        </button>
                      </div>
                    </div>
                  </details>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
