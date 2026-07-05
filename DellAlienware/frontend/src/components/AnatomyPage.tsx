import { useCallback, useEffect, useState } from "react";
import { fetchAnatomies } from "../api";
import { AnatomyView, KIND_STYLE } from "./AnatomyView";
import type { Anatomy, Photo, RegionKind } from "../types";

const TOOLTIP_W = 280; // px; keep in sync with .an-tooltip width

export function PhotoCard({
  photo,
  small,
  hero,
}: {
  photo: Photo;
  small?: boolean;
  hero?: boolean;
}) {
  const cls = hero ? "an-photo an-photo-hero" : small ? "an-photo an-photo-small" : "an-photo";
  return (
    <figure className={cls}>
      <img src={photo.url} alt={photo.caption} loading="lazy" />
      <figcaption>
        {photo.caption}
        <span className="an-credit">{photo.credit}</span>
      </figcaption>
    </figure>
  );
}

const KIND_LABEL: Record<RegionKind, string> = {
  board: "motherboard / logic",
  power: "power delivery (DC-in, charger, EC)",
  battery: "battery pack",
  cooling: "cooling (fans, heat pipes, vapor chamber)",
  memory: "memory (DDR5 SO-DIMM, VRAM)",
  storage: "storage (M.2 SSD)",
  io: "ports & connectors",
  display: "display path",
  wireless: "wireless (WLAN card, antennas)",
};

export function AnatomyPage() {
  const [anatomies, setAnatomies] = useState<Anatomy[]>([]);
  // Honor a /#anatomy/<anatomyId> deep link for the initial selection.
  const [anatomyId, setAnatomyId] = useState<string | null>(
    () => window.location.hash.split("/")[1] ?? null,
  );
  const [regionId, setRegionId] = useState<string | null>(null);
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onHover = useCallback((id: string | null, x: number, y: number) => {
    setHover(id ? { id, x, y } : null);
  }, []);

  useEffect(() => {
    fetchAnatomies()
      .then((list) => {
        setAnatomies(list);
        setAnatomyId((cur) =>
          list.some((a) => a.id === cur) ? cur : list[0]?.id ?? null,
        );
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    window.location.hash = anatomyId ? `anatomy/${anatomyId}` : "anatomy";
  }, [anatomyId]);

  const anatomy = anatomies.find((a) => a.id === anatomyId) ?? null;
  const region = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const hovered = anatomy?.regions.find((r) => r.id === hover?.id) ?? null;

  // Legend shows only the kinds this machine actually has.
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <>
      {anatomy && (
        <div className="an-hero">
          <h2>{anatomy.name}</h2>
          <p>
            {anatomy.vendor} · {anatomy.platform} · {anatomy.year}
          </p>
        </div>
      )}
      <div className="stage">
        {error && <div className="mini an-error">{error}</div>}
        {anatomies.length > 1 && (
          <nav className="uc-tabs">
            {anatomies.map((a) => (
              <button
                key={a.id}
                className={a.id === anatomyId ? "active" : ""}
                onClick={() => {
                  setAnatomyId(a.id);
                  setRegionId(null);
                }}
              >
                {a.name}
              </button>
            ))}
          </nav>
        )}
        {anatomy && (
          <div className="an-card">
            {/* The real thing first: the service photo the floorplan is
                traced from. Credit always rendered. */}
            {anatomy.photo && <PhotoCard photo={anatomy.photo} hero />}
            <AnatomyView
              anatomy={anatomy}
              selected={regionId}
              onSelect={setRegionId}
              onHover={onHover}
            />
            <div className="mini an-hint">
              Hover a block to see what it is; click to pin its details. The
              floorplan is a stylized view with the bottom cover off — fans and
              DC-in along the hinge edge at the top, battery across the bottom
              third — matching the photo above, not drawn to the millimeter.
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
          {region && <div className="mini an-kind">{KIND_LABEL[region.kind]}</div>}
          <p className="an-desc">{region ? region.description : anatomy?.overview}</p>
          {region?.photo && <PhotoCard photo={region.photo} />}
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
                    background: KIND_STYLE[k].fill,
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
