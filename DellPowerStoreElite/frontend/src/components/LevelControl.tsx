import { LEVELS, LEVEL_HINT, LEVEL_LABEL, setLevel, useLevel } from "../level";
import type { Level } from "../level";

// The reading-level control. Shared verbatim across every twin in this
// repo — if you change one, change them all.
//
// Rendered as five discrete positions rather than a slider, because the
// levels are named registers rather than a continuum, and because a reader
// should be able to see that "Standard" is the middle before they move off
// it. The current label is spelled out next to the scale: a row of five
// unlabelled squares would make people guess which end is which.

export function LevelControl() {
  const level = useLevel();
  return (
    <div className="levelctl" role="group" aria-label="Reading level">
      <span className="levelctl-caption">Reading level</span>
      <div className="levelctl-scale">
        {LEVELS.map((l) => (
          <button
            key={l}
            type="button"
            className={l === level ? "active" : ""}
            aria-pressed={l === level}
            aria-label={`${LEVEL_LABEL[l]} — ${LEVEL_HINT[l]}`}
            title={`${LEVEL_LABEL[l]} — ${LEVEL_HINT[l]}`}
            onClick={() => setLevel(l as Level)}
          >
            {l}
          </button>
        ))}
      </div>
      <span className="levelctl-name">{LEVEL_LABEL[level]}</span>
    </div>
  );
}
