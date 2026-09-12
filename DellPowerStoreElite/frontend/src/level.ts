// Reading level (1–5) for the twin's prose. Shared verbatim across every
// twin in this repo — if you change one, change them all.
//
// The level lives in one module-level variable rather than in React state
// at the composition root, for a practical reason: every page fetches its
// own data independently (AnatomyPage, CatalogPage, UseCasePage all call
// the API directly), so threading a prop through would mean touching every
// component signature. A tiny store with a subscribe hook lets `api.ts`
// read the current level when it builds a request, and lets each page
// re-fetch by listing `level` in its effect dependencies.
//
// The choice is persisted, because a reader who wants plain language wants
// it on the next page too, and on the next visit.

import { useEffect, useState } from "react";

export const LEVELS = [1, 2, 3, 4, 5] as const;
export type Level = (typeof LEVELS)[number];

export const DEFAULT_LEVEL: Level = 3;

// Short labels for the control; the longer ones explain what changes.
export const LEVEL_LABEL: Record<Level, string> = {
  1: "Novice",
  2: "Plain",
  3: "Standard",
  4: "Technical",
  5: "Expert",
};

export const LEVEL_HINT: Record<Level, string> = {
  1: "No assumed vocabulary — every term is opened up as it appears.",
  2: "Plain language, with the technical terms briefly explained.",
  3: "The register this twin was written in.",
  4: "Assumes the vocabulary; the explanations are removed.",
  5: "Terse and dense — the argument only, for a specialist.",
};

const STORAGE_KEY = "twin-reading-level";

function load(): Level {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = Number(raw);
    if ((LEVELS as readonly number[]).includes(parsed)) return parsed as Level;
  } catch {
    // Private browsing, storage disabled, etc. The default is fine.
  }
  return DEFAULT_LEVEL;
}

let current: Level = load();
const subscribers = new Set<(level: Level) => void>();

export function getLevel(): Level {
  return current;
}

export function setLevel(level: Level): void {
  if (level === current) return;
  current = level;
  try {
    window.localStorage.setItem(STORAGE_KEY, String(level));
  } catch {
    // Not being able to remember the choice is not a reason to ignore it.
  }
  subscribers.forEach((fn) => fn(level));
}

/** Current reading level, re-rendering the caller when it changes. */
export function useLevel(): Level {
  const [level, setLocal] = useState<Level>(current);
  useEffect(() => {
    // Re-sync in case the level changed between render and subscribe.
    setLocal(current);
    subscribers.add(setLocal);
    return () => {
      subscribers.delete(setLocal);
    };
  }, []);
  return level;
}
