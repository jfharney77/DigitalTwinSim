import { useCallback, useEffect, useState } from "react";
import { fetchAnatomies, fetchAtlas } from "../api";
import { buildAnatomyHash, parseAnatomyHash } from "../anatomyHash";
import { useLevel } from "../level";
import { AnatomyView } from "./AnatomyView";
import type { Atlas, DieAnatomy, Photo, RegionKind } from "../types";

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

// spec_30: one-click compare presets — data, not UI-invented pairings.
const COMPARE_CHIPS: { a: string; b: string; label: string }[] = [
  { a: "gb200", b: "gb300", label: "GB200 vs GB300 — the Blackwell refresh" },
  { a: "gh100", b: "gb200", label: "GH100 vs GB200 — Hopper → Blackwell" },
];

export function AnatomyPage({
  onSimulate,
}: {
  // spec_30: "simulate this die" — App sets the mapped profile and switches
  // to the simulator tab. Optional so the page stands alone in isolation.
  onSimulate?: (profileName: string) => void;
}) {
  const [dies, setDies] = useState<DieAnatomy[]>([]);
  // Honor the deep link for the initial state. The grammar (spec_30) is
  // parsed in anatomyHash.ts; every pre-spec_30 form means what it meant.
  const initial = parseAnatomyHash(window.location.hash);
  const [dieId, setDieId] = useState<string | null>(
    initial.kind === "single" ? initial.dieId : initial.a,
  );
  // spec_21 #6: /#anatomy/<die>/<region> pins a region on load.
  const [regionId, setRegionId] = useState<string | null>(
    initial.kind === "single" ? initial.regionId : null,
  );
  // spec_30: /#anatomy/<a>/vs/<b> — two floorplans side by side.
  const [compare, setCompare] = useState<{ a: string; b: string } | null>(
    initial.kind === "compare" ? { a: initial.a, b: initial.b } : null,
  );
  const [atlas, setAtlas] = useState<Atlas | null>(null);
  useEffect(() => {
    fetchAtlas().then(setAtlas).catch(() => setAtlas(null));
  }, []);
  const [query, setQuery] = useState(""); // spec_21 #7: region search
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
        // spec_30: a compare link naming an unknown die falls back to the
        // ordinary single view rather than two blank floorplans.
        setCompare((c) =>
          c && ds.some((d) => d.id === c.a) && ds.some((d) => d.id === c.b)
            ? c
            : null,
        );
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    if (compare) {
      window.location.hash = buildAnatomyHash({ kind: "compare", ...compare });
    } else if (dieId) {
      window.location.hash = buildAnatomyHash({ kind: "single", dieId, regionId });
    }
  }, [dieId, regionId, compare]);

  const die = dies.find((d) => d.id === dieId) ?? null;
  const region = die?.regions.find((r) => r.id === regionId) ?? null;
  // spec_30: compare view state + this die's mapped simulator profile.
  const compareA = compare ? dies.find((d) => d.id === compare.a) ?? null : null;
  const compareB = compare ? dies.find((d) => d.id === compare.b) ?? null : null;
  const profileFor = (id: string | null | undefined): string | null =>
    (id && atlas?.pairs.find((p) => p.dieId === id)?.profileName) || null;
  const simProfile = profileFor(dieId);

  // spec_21 #7: text search over this die's regions (label + description).
  const q = query.trim().toLowerCase();
  const matches =
    die && q
      ? die.regions
          .filter(
            (r) =>
              r.label.toLowerCase().includes(q) ||
              r.description.toLowerCase().includes(q),
          )
          .slice(0, 8)
      : [];
  const hovered = die?.regions.find((r) => r.id === hover?.id) ?? null;

  // Legend shows only the kinds this die actually has.
  const kinds = die
    ? ([...new Set(die.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  // --- spec_30: die-compare view (#anatomy/<a>/vs/<b>) -----------------------
  if (compareA && compareB) {
    // Aligned stats: A's labels in order, then any label only B carries.
    const labels = [
      ...compareA.stats.map((s) => s.label),
      ...compareB.stats
        .map((s) => s.label)
        .filter((l) => !compareA.stats.some((s) => s.label === l)),
    ];
    const value = (d: DieAnatomy, label: string) =>
      d.stats.find((s) => s.label === label)?.value ?? "—";
    const headline = (d: DieAnatomy) =>
      `${d.vendor} · ${d.architecture} · ${d.year} · ${d.process} · ${d.dieSize}`;
    // Clicking a region drops into that die's ordinary single view — the
    // compare form is derived from two plain die fetches, nothing more.
    const open = (id: string, rid: string | null) => {
      setCompare(null);
      setDieId(id);
      setRegionId(rid);
    };
    return (
      <>
        <div className="an-hero">
          <h2>
            {compareA.name} vs {compareB.name}
          </h2>
          <p>
            {headline(compareA)} — against — {headline(compareB)}. Click a
            block to open it in the single-die view.
          </p>
        </div>
        <div className="stage">
          {error && <div className="mini an-error">{error}</div>}
          <div style={{ display: "flex", gap: 12, alignItems: "stretch" }}>
            {[compareA, compareB].map((d) => (
              <div className="an-card" key={d.id} style={{ flex: 1, minWidth: 0 }}>
                <div className="mini" style={{ marginBottom: 4 }}>
                  {d.vendor} {d.name}
                </div>
                <AnatomyView
                  anatomy={d}
                  selected={null}
                  onSelect={(rid) => open(d.id, rid)}
                  onHover={() => {}}
                />
              </div>
            ))}
          </div>
        </div>
        <aside className="controls">
          <section className="an-panel">
            <h2>Compare</h2>
            {COMPARE_CHIPS.map((c) => (
              <button
                key={`${c.a}-${c.b}`}
                className={
                  compare && compare.a === c.a && compare.b === c.b ? "active" : ""
                }
                style={{ display: "block", marginBottom: 6 }}
                onClick={() => setCompare({ a: c.a, b: c.b })}
              >
                {c.label}
              </button>
            ))}
            <button onClick={() => setCompare(null)}>Back to single die</button>
          </section>
          <section className="an-panel">
            <h2>Side by side</h2>
            <table className="an-compare-stats" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left" }}></th>
                  <th style={{ textAlign: "left" }}>{compareA.name}</th>
                  <th style={{ textAlign: "left" }}>{compareB.name}</th>
                </tr>
              </thead>
              <tbody>
                {labels.map((l) => (
                  <tr key={l}>
                    <td className="mini">{l}</td>
                    <td>{value(compareA, l)}</td>
                    <td>{value(compareB, l)}</td>
                  </tr>
                ))}
                <tr>
                  <td className="mini">Transistors</td>
                  <td>{compareA.transistors}</td>
                  <td>{compareB.transistors}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </aside>
      </>
    );
  }

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
          <div className="mini" style={{ marginBottom: 6 }}>
            <input
              placeholder="find a region (e.g. NVLink, cache, tensor)…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search regions on this die"
            />
            {q &&
              (matches.length ? (
                matches.map((r) => (
                  <button
                    key={r.id}
                    style={{ marginLeft: 6 }}
                    onClick={() => {
                      setRegionId(r.id);
                      setQuery("");
                    }}
                  >
                    {r.label || r.id}
                  </button>
                ))
              ) : (
                <span style={{ marginLeft: 8 }}>no matching regions on this die</span>
              ))}
          </div>
        )}
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
          {/* spec_30: only when the atlas maps this die to a simulator
              profile — museum-only dies show nothing, honestly. */}
          {simProfile && onSimulate && (
            <button
              style={{ marginTop: 8 }}
              title={`open the simulator on ${simProfile}; your N / tile size / dtype survive`}
              onClick={() => onSimulate(simProfile)}
            >
              Simulate this die →
            </button>
          )}
          <div className="mini" style={{ marginTop: 10 }}>Compare dies</div>
          {COMPARE_CHIPS.map((c) => (
            <button
              key={`${c.a}-${c.b}`}
              className="mini"
              style={{ display: "block", marginTop: 4 }}
              onClick={() => {
                setRegionId(null);
                setCompare({ a: c.a, b: c.b });
              }}
            >
              {c.label}
            </button>
          ))}
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
