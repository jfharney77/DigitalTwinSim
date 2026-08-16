// spec_30: the #anatomy deep-link grammar, parsed in one place so the vs
// form cannot drift from the single form. The grammar (additive over what
// existed before spec_30 — every old link keeps meaning what it meant):
//
//   #anatomy                     → single view, default die
//   #anatomy/<die>               → single view, that die
//   #anatomy/<die>/<region>      → single view, region pinned
//   #anatomy/<a>/vs/<b>          → compare view (NEW; "vs" is a reserved,
//                                  never-authored region id — test_anatomy.py)
//
// parse/build round-trip by construction: buildAnatomyHash(parseAnatomyHash(h))
// === h for every well-formed h. There is no frontend test runner in this
// app, so the round-trip is held by the typecheck + hand verification.

export type AnatomyHash =
  | { kind: "single"; dieId: string | null; regionId: string | null }
  | { kind: "compare"; a: string; b: string };

export function parseAnatomyHash(hash: string): AnatomyHash {
  const parts = hash.replace(/^#/, "").split("/");
  // parts[0] is "anatomy" whenever this page is mounted.
  if (parts.length === 4 && parts[2] === "vs" && parts[1] && parts[3]) {
    return { kind: "compare", a: parts[1], b: parts[3] };
  }
  return {
    kind: "single",
    dieId: parts[1] || null,
    regionId: parts[2] || null,
  };
}

export function buildAnatomyHash(h: AnatomyHash): string {
  if (h.kind === "compare") return `anatomy/${h.a}/vs/${h.b}`;
  if (h.dieId && h.regionId) return `anatomy/${h.dieId}/${h.regionId}`;
  if (h.dieId) return `anatomy/${h.dieId}`;
  return "anatomy";
}
