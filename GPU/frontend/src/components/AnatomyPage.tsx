import { useCallback, useEffect, useState } from "react";
import { fetchAnatomies } from "../api";
import { useLevel } from "../level";
import { AnatomyView } from "./AnatomyView";
import type { DieAnatomy, Photo, RegionKind } from "../types";

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
  compute: "compute cluster (GPC / shader engine)",
  l2: "L2 / last-level cache",
  mem: "memory controller + PHY",
  nvlink: "NVLink",
  io: "host / display I/O",
  media: "media engine",
  cache: "cache chiplet (MCD)",
  fabric: "package interconnect",
};

// Swatches for the legend; keep in sync with KIND_STYLE in AnatomyView.
const KIND_SWATCH: Record<RegionKind, string> = {
  compute: "var(--sm-idle)",
  l2: "#141d2c",
  mem: "var(--mem)",
  nvlink: "#15282a",
  io: "#1d1a2b",
  media: "#281f2a",
  cache: "#12233a",
  fabric: "#241f33",
};

export function AnatomyPage() {
  const [dies, setDies] = useState<DieAnatomy[]>([]);
  // Honor a /#anatomy/<dieId> deep link for the initial selection.
  const [dieId, setDieId] = useState<string | null>(
    () => window.location.hash.split("/")[1] ?? null,
  );
  const [regionId, setRegionId] = useState<string | null>(null);
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  const onHover = useCallback((id: string | null, x: number, y: number) => {
    setHover(id ? { id, x, y } : null);
  }, []);

  useEffect(() => {
    fetchAnatomies()
      .then((ds) => {
        setDies(ds);
        setDieId((cur) =>
          ds.some((d) => d.id === cur) ? cur : ds[0]?.id ?? null,
        );
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    if (dieId) window.location.hash = `anatomy/${dieId}`;
  }, [dieId]);

  const die = dies.find((d) => d.id === dieId) ?? null;
  const region = die?.regions.find((r) => r.id === regionId) ?? null;
  const hovered = die?.regions.find((r) => r.id === hover?.id) ?? null;

  // Legend shows only the kinds this die actually has.
  const kinds = die
    ? ([...new Set(die.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <>
      {die && (
        <div className="an-hero">
          <h2>{die.name}</h2>
          <p>
            {die.vendor} · {die.architecture} · {die.year} · {die.process} ·{" "}
            {die.dieSize} · {die.transistors} transistors
          </p>
        </div>
      )}
      <div className="stage">
        {error && <div className="mini an-error">{error}</div>}
        {die && (
          <div className="an-card">
            <AnatomyView
              anatomy={die}
              selected={regionId}
              onSelect={setRegionId}
              onHover={onHover}
            />
            <div className="mini an-hint">
              Hover a block to see a photo of the part; click to pin its
              details. Block placement is traced from the vendor documents
              listed under Sources.
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
            <div className="an-tooltip-label">{hovered.label || KIND_LABEL[hovered.kind]}</div>
            {hovered.photo && <PhotoCard photo={hovered.photo} small />}
          </div>
        )}
      </div>

      <aside className="controls">
        <section className="an-panel">
          <h2>Die</h2>
          <label className="field">
            <select
              value={dieId ?? ""}
              onChange={(e) => {
                setDieId(e.target.value);
                setRegionId(null);
              }}
            >
              {dies.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.vendor} {d.name}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="an-panel">
          <h2>{region ? region.label || KIND_LABEL[region.kind] : "Overview"}</h2>
          {region && (
            <div className="mini an-kind">{KIND_LABEL[region.kind]}</div>
          )}
          <p className="an-desc">{region ? region.description : die?.overview}</p>
          {region?.photo && <PhotoCard photo={region.photo} />}
          {!region && die?.photo && <PhotoCard photo={die.photo} />}
        </section>

        {die && (
          <section className="an-panel">
            <h2>Specs</h2>
            {die.stats.map((s) => (
              <div className="stat" key={s.label}>
                <span>{s.label}</span>
                <span>{s.value}</span>
              </div>
            ))}
          </section>
        )}

        {die && (
          <section className="legend an-panel">
            <h2>Blocks</h2>
            {kinds.map((k) => (
              <span key={k}>
                <i style={{ background: KIND_SWATCH[k], border: "1px solid var(--sm-edge)" }} />
                {KIND_LABEL[k]}
              </span>
            ))}
          </section>
        )}

        {die && (
          <section className="an-panel">
            <h2>Sources</h2>
            <div className="an-sources">
              {die.sources.map((s) => (
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
