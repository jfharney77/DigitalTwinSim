// Narrated tour mode (ACTIVE_TWIN_SPEC.md). Built in the DellPowerStore pilot
// and lifted here unchanged: it imports nothing from the twin that hosts it.
// The twin supplies its map through `regions`/`layers`/`bounds` and draws its
// own diagram in `renderStage`. Recipe: DellPowerStore/TOUR_PATTERN.md.
export { TourPlayer } from "./TourPlayer";
export type { TourPlayerProps } from "./TourPlayer";
export { useCameraTween, useReducedMotion, makeRegionLook } from "./motion";
export { speak, silence, speechSupported } from "./narration";
export type * from "./types";
