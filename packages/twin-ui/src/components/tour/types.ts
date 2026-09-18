// Wire types for GET /api/tour — they mirror twinkit/tour.py (camelCase on
// the wire). Nothing in this folder imports from the twin that hosts it.

/** A viewBox in the map's own normalized coordinate space. */
export interface CameraBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface TourStep {
  id: string;
  title: string;
  script: string;
  camera: CameraBox;
  regionIds: string[];
  layerReveal: number;
  traceCursor: number | null;
  durationMs: number;
  photoId: string | null;
  audioUrl: string | null;
}

export interface TourPhoto {
  id: string;
  url: string;
  caption: string;
  credit: string;
}

export interface TourSource {
  label: string;
  url: string;
}

export interface Tour {
  id: string;
  title: string;
  intro: string;
  steps: TourStep[];
  photos: TourPhoto[];
  sources: TourSource[];
}

export interface TourResponse {
  tour: Tour;
  layers: Record<string, number>;
  mapWidth: number;
  mapHeight: number;
}

/** Any map region: every twin's region/block/pillar has these fields. */
export interface TourRegion {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

/** How one region should be drawn at this moment of the tour. */
export interface RegionLook {
  opacity: number;
  /** Explode offset, in map units. Zero under prefers-reduced-motion. */
  dx: number;
  dy: number;
}

/** What the player hands the twin's own diagram through `renderStage`. */
export interface TourStage {
  /** The tweened camera, in map coordinates (the renderer adds its margin). */
  viewBox: CameraBox;
  /** Regions the current step lights. */
  lit: Set<string>;
  /** Layer peel for any region id: ghost opacity plus explode offset. */
  regionLook: (id: string) => RegionLook;
  /** Call from the diagram's region click: pauses the tour (take-over). */
  onRegionClick: (id: string) => void;
  /** True while the viewer has taken over (tour paused by a click or tab switch). */
  takenOver: boolean;
  /** prefers-reduced-motion, so the renderer can drop its own transitions. */
  reducedMotion: boolean;
}
