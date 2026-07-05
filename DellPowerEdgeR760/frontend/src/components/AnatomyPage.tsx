import { useCallback, useEffect, useState } from "react";
import { fetchAnatomy } from "../api";
import { ChassisView } from "./ChassisView";
import type { ChassisAnatomy, Photo, RegionKind } from "../types";

const TOOLTIP_W = 280; // px; keep in sync with .an-tooltip width

function PhotoCard({ photo, small }: { photo: Photo; small?: boolean }) {
  return (
    <figure className={small ? "an-photo an-photo-small" : "an-photo"}>
      <img src={photo.url} alt={photo.caption} loading="lazy" />
      <figcaption>
        {photo.caption}
        <span className="an-credit">{photo.credit}</span>
      </figcaption>
    </figure>
  );
}

const KIND_LABEL: Record<RegionKind, string> = {
  storage: "drive bays & storage controllers",
  cooling: "hot-swap fan",
  cpu: "CPU socket + heatsink",
  memory: "DDR5 DIMM bank",
  power: "power delivery",
  expansion: "PCIe risers & OCP slot",
  management: "iDRAC service processor",
  board: "system board",
};

// Swatches for the legend; keep in sync with KIND_STYLE in ChassisView.
const KIND_SWATCH: Record<RegionKind, string> = {
  storage: "#12233a",
  cooling: "#122b2b",
  cpu: "#2b2412",
  memory: "#241f33",
  power: "#2b1a1a",
  expansion: "#16281a",
  management: "#12282e",
  board: "#1a2433",
};

export function AnatomyPage() {
  const [anatomy, setAnatomy] = useState<ChassisAnatomy | null>(null);
  // Honor a /#anatomy/<regionId> deep link for the initial selection.
  const [regionId, setRegionId] = useState<string | null>(
    () => window.location.hash.split("/")[1] ?? null,
  );
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const onHover = useCallback((id: string | null, x: number, y: number) => {
    setHover(id ? { id, x, y } : null);
  }, []);

  useEffect(() => {
    fetchAnatomy()
      .then(setAnatomy)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    window.location.hash = regionId ? `anatomy/${regionId}` : "anatomy";
  }, [regionId]);

  const region = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const hovered = anatomy?.regions.find((r) => r.id === hover?.id) ?? null;

  // Legend shows only the kinds this chassis actually has.
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <>
      {anatomy && (
        <div className="an-hero">
          <h2>{anatomy.name}</h2>
          <p>
            {anatomy.vendor} · {anatomy.formFactor} · {anatomy.generation} ·{" "}
            {anatomy.year}
          </p>
        </div>
      )}
      <div className="stage">
        {error && <div className="mini an-error">{error}</div>}
        {anatomy && (
          <div className="an-card">
            <ChassisView
              anatomy={anatomy}
              selected={regionId}
              onSelect={setRegionId}
              onHover={onHover}
            />
            <div className="mini an-hint">
              Hover a block to see what it is; click to pin its details. The
              layout is a stylized top-down view with the lid off — front
              (drive bay) on the left, rear (power and I/O) on the right.
            </div>
          </div>
        )}
        {hovered && hover && (
          <div
            className="an-tooltip"
            style={{
              left: Math.min(hover.x + 16, window.innerWidth - TOOLTIP_W - 16),
              top: hover.y + 16,
            }}
          >
            <div className="an-tooltip-label">
              {hovered.label || KIND_LABEL[hovered.kind]}
            </div>
            <div className="mini">{KIND_LABEL[hovered.kind]}</div>
            {hovered.photo && <PhotoCard photo={hovered.photo} small />}
          </div>
        )}
      </div>

      <aside className="controls">
        <section className="an-panel">
          <h2>{region ? region.label || KIND_LABEL[region.kind] : "Overview"}</h2>
          {region && (
            <div className="mini an-kind">{KIND_LABEL[region.kind]}</div>
          )}
          <p className="an-desc">
            {region ? region.description : anatomy?.overview}
          </p>
          {region?.photo && <PhotoCard photo={region.photo} />}
          {!region && anatomy?.photo && <PhotoCard photo={anatomy.photo} />}
        </section>

        {anatomy && (
          <section className="an-panel">
            <h2>Specs</h2>
            {anatomy.stats.map((s) => (
              <div className="stat" key={s.label}>
                <span>{s.label}</span>
                <span>{s.value}</span>
              </div>
            ))}
          </section>
        )}

        {anatomy && (
          <section className="legend an-panel">
            <h2>Blocks</h2>
            {kinds.map((k) => (
              <span key={k}>
                <i
                  style={{
                    background: KIND_SWATCH[k],
                    border: "1px solid var(--sm-edge)",
                  }}
                />
                {KIND_LABEL[k]}
              </span>
            ))}
          </section>
        )}

        {anatomy && anatomy.sources.length > 0 && (
          <section className="an-panel">
            <h2>Sources</h2>
            <div className="an-sources">
              {anatomy.sources.map((s) => (
                <a key={s.url} href={s.url} target="_blank" rel="noreferrer">
                  {s.label} ↗
                </a>
              ))}
            </div>
          </section>
        )}
      </aside>
    </>
  );
}
