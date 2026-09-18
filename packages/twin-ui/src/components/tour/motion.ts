import { useEffect, useRef, useState } from "react";
import type { CameraBox, RegionLook, TourRegion } from "./types";

/** prefers-reduced-motion, live. */
export function useReducedMotion(): boolean {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && !!window.matchMedia?.(query).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia?.(query);
    if (!mq) return;
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduced;
}

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

const lerp = (a: CameraBox, b: CameraBox, t: number): CameraBox => ({
  x: a.x + (b.x - a.x) * t,
  y: a.y + (b.y - a.y) * t,
  w: a.w + (b.w - a.w) * t,
  h: a.h + (b.h - a.h) * t,
});

/**
 * The camera rig: tweens a viewBox toward `target` (ease-in-out). Under
 * reduced motion the camera cuts instead. The tween restarts from wherever
 * the camera is, so retargeting mid-flight never jumps.
 */
export function useCameraTween(
  target: CameraBox,
  durationMs: number,
  reduced: boolean,
): CameraBox {
  const [box, setBox] = useState<CameraBox>(target);
  const current = useRef(box);
  current.current = box;
  const key = `${target.x},${target.y},${target.w},${target.h}`;
  useEffect(() => {
    if (reduced || durationMs <= 0) {
      setBox(target);
      return;
    }
    const from = current.current;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      setBox(lerp(from, target, ease(t)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, reduced, durationMs]);
  return box;
}

const GHOST = 0.14;
const EXPLODE = 1.6; // map units per layer peeled past

/**
 * Layer peel. A region on a layer shallower than `reveal` becomes a ghost
 * outline and slides a little away from the map centre; lit regions are
 * never ghosted — the narration is about them.
 */
export function makeRegionLook(
  regions: TourRegion[],
  layers: Record<string, number>,
  reveal: number,
  lit: Set<string>,
  bounds: { width: number; height: number },
  reduced: boolean,
): (id: string) => RegionLook {
  const byId = new Map(regions.map((r) => [r.id, r]));
  const cx = bounds.width / 2;
  const cy = bounds.height / 2;
  return (id: string) => {
    const layer = layers[id] ?? 0;
    if (lit.has(id) || layer >= reveal) return { opacity: 1, dx: 0, dy: 0 };
    if (reduced) return { opacity: GHOST, dx: 0, dy: 0 };
    const r = byId.get(id);
    if (!r) return { opacity: GHOST, dx: 0, dy: 0 };
    const vx = r.x + r.w / 2 - cx;
    const vy = r.y + r.h / 2 - cy;
    const len = Math.hypot(vx, vy) || 1;
    const push = (reveal - layer) * EXPLODE;
    return { opacity: GHOST, dx: (vx / len) * push, dy: (vy / len) * push };
  };
}
