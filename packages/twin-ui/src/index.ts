/**
 * twin-ui — the Dell clean-design skin and the shell every twin reuses.
 *
 * Import the stylesheets once, in the frontend's `main.tsx`, before the
 * component's own `styles.css`:
 *
 *     import "@twinsim/twin-ui/tokens.css";
 *     import "./styles.css";
 *
 * `npm run gallery` in packages/twin-ui renders every component below on one
 * page — the visual reference the dell-clean-design skill checks against.
 *
 * TourPlayer is the narrated tour mode (ACTIVE_TWIN_SPEC.md); it imports its
 * own stylesheet. The backend half is twinkit.tour, and the recipe for adding
 * a tour to a twin is DellPowerStore/TOUR_PATTERN.md.
 */
export { TwinLayout } from "./components/TwinLayout";
export type { TwinTab } from "./components/TwinLayout";
export { ControlPanel } from "./components/ControlPanel";
export { Timeline } from "./components/Timeline";
export type { TimelineStep } from "./components/Timeline";
export { MetricReadout } from "./components/MetricReadout";
export type { Metric } from "./components/MetricReadout";
export { TourPlayer, useCameraTween, useReducedMotion, makeRegionLook, speak, silence, speechSupported } from "./components/tour";
export type {
  TourPlayerProps,
  CameraBox,
  Tour,
  TourStep,
  TourPhoto,
  TourSource,
  TourResponse,
  TourRegion,
  RegionLook,
  TourStage,
} from "./components/tour";
// Static hosting (docs/STATIC_HOSTING.md): the fetch shim a twin's api.ts uses
// so the same build can run against a backend or with none.
export { apiFetch, assetUrl, hostedHref, warmEngine, isStatic, bodyKey } from "./staticApi";
