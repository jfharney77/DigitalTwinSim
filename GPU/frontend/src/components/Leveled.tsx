import type { ReactNode } from "react";
import { useLevel } from "../level";

/**
 * Reading-level switch for prose authored in the frontend (info dots and
 * hints — text the backend's L(...) registry never sees). Three registers,
 * resolved the way leveling.py resolves a gap: away from Standard, in the
 * direction the reader asked for. Levels 1–2 read `novice`, 3 reads
 * `standard`, 4–5 read `expert`; a missing register falls back to Standard.
 */
export function Leveled({
  novice,
  standard,
  expert,
}: {
  novice?: ReactNode;
  standard: ReactNode;
  expert?: ReactNode;
}) {
  const level = useLevel();
  if (level <= 2) return <>{novice ?? standard}</>;
  if (level >= 4) return <>{expert ?? standard}</>;
  return <>{standard}</>;
}
