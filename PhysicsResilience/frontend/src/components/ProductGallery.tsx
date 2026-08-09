import { Facsimile, type FacsimileShape } from "./Facsimile";

// V1 (hero panel) + V9 (photo-card picker), per
// physics_specs/VISUAL_IMPROVEMENTS.md. Cards for every product
// personality with a thumbnail (ship-safe photo or labeled facsimile),
// and a hero strip for the selected one with the mandatory credit line.

export interface ProductMedia {
  name: string;
  tagline: string;
  kind: "photo" | "illustration";
  src?: string | null;
  shape?: string | null;
  credit: string;
  underlay?: string | null;
  caption?: string | null;
}

function Thumb({ m, size }: { m: ProductMedia; size: number }) {
  if (m.src) {
    return (
      <img
        src={m.src}
        alt={m.name}
        style={{
          width: size,
          height: size * 0.62,
          objectFit: "cover",
          borderRadius: 4,
          display: "block",
        }}
      />
    );
  }
  return <Facsimile shape={(m.shape ?? "server") as FacsimileShape} size={size} />;
}

export function ProductGallery({
  media,
  selected,
  onSelect,
}: {
  media: Record<string, ProductMedia>;
  selected: string;
  onSelect?: (id: string) => void;
}) {
  const ids = Object.keys(media);
  const cur = media[selected];
  if (!cur) return null;
  const multi = ids.length > 1 && !!onSelect;

  return (
    <div className="an-panel product-gallery">
      {multi && (
        <div className="gallery-cards">
          {ids.map((id) => {
            const m = media[id];
            const active = id === selected;
            return (
              <button
                key={id}
                className={`gallery-card${active ? " active" : ""}`}
                title={`${m.name} — ${m.tagline}`}
                onClick={() => onSelect(id)}
              >
                <Thumb m={m} size={72} />
                <span className="gallery-card-name">{m.name}</span>
              </button>
            );
          })}
        </div>
      )}
      <div className="gallery-hero">
        <Thumb m={cur} size={150} />
        <div className="gallery-hero-text">
          <strong>{cur.name}</strong>
          <div className="mini">{cur.tagline}</div>
          <div className="mini gallery-credit">
            {cur.kind === "photo"
              ? cur.credit
              : `Illustration — not a Dell product photo. ${cur.credit}`}
          </div>
        </div>
      </div>
    </div>
  );
}
