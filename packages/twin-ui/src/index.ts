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
 */
export { TwinLayout } from "./components/TwinLayout";
export type { TwinTab } from "./components/TwinLayout";
export { ControlPanel } from "./components/ControlPanel";
export { Timeline } from "./components/Timeline";
export type { TimelineStep } from "./components/Timeline";
export { MetricReadout } from "./components/MetricReadout";
export type { Metric } from "./components/MetricReadout";
