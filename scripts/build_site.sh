#!/usr/bin/env bash
# Assemble site/ — the whole tutorial as static files, for GitLab/GitHub Pages.
#
#   scripts/build_site.sh                       every static-ready component
#   scripts/build_site.sh DellPowerStore PhysicsME5   just these (plus the static pages)
#   SITE_DIR=/tmp/site scripts/build_site.sh    somewhere other than ./site
#
# A component is static-ready when its frontend/src/api.ts uses apiFetch
# (docs/STATIC_HOSTING.md is the per-component recipe). Others are skipped and
# listed; links to them on the hosted pages are disabled, not broken.
#
# site/ is generated and gitignored. Nothing here starts a server.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="${SITE_DIR:-$REPO/site}"
cd "$REPO"

if [ "$#" -gt 0 ]; then
  wanted=("$@")
else
  mapfile -t wanted < <(python3 - <<'PY'
import json
for c in json.load(open("components.json"))["components"]:
    if c["status"] in ("reference", "built", "partial") and c["frontendPort"]:
        print(c["directory"])
PY
)
fi

rm -rf "$SITE"; mkdir -p "$SITE"
built=(); skipped=()

for comp in "${wanted[@]}"; do
  comp="${comp%/}"
  if ! grep -q "apiFetch" "$comp/frontend/src/api.ts" 2>/dev/null; then
    skipped+=("$comp"); continue
  fi
  echo "== $comp"
  out="$REPO/$comp/frontend/dist-static"
  rm -rf "$out"
  # --base=./ makes the bundle relocatable: /<Component>/ on GitLab Pages,
  # /<repo>/<Component>/ on GitHub Pages, no per-host configuration.
  (cd "$comp/frontend" && npx tsc --noEmit && VITE_STATIC=1 npx vite build --base=./ --outDir dist-static --emptyOutDir >/dev/null)
  python3 scripts/build_static.py "$comp" --out "$out"
  cp -r "$out" "$SITE/$comp"
  built+=("$comp")
done

# The static pages: copies, with the hosted-link resolver injected.
cp index.html "$SITE/index.html"
for d in Learn CustomerSetup; do
  mkdir -p "$SITE/$d"
  (cd "$d" && tar cf - --exclude=tests --exclude=scripts --exclude=__pycache__ --exclude='*.py' .) | (cd "$SITE/$d" && tar xf -)
done
cp components.json "$SITE/components.json" 2>/dev/null || true
cp scripts/static/twin-hosted.js "$SITE/twin-hosted.js"
touch "$SITE/.nojekyll"

python3 - "$SITE" "${built[@]}" <<'PY'
import json, os, re, sys
site, built = sys.argv[1], sys.argv[2:]
comps = json.load(open("components.json"))["components"]
by_port, trace = {}, {}
for c in comps:
    if c.get("frontendPort"):
        # First registered wins on a shared port; hosted ones take precedence.
        p = str(c["frontendPort"])
        if p not in by_port or (c["directory"] in built and by_port[p] not in built):
            by_port[p] = c["directory"]
hosted = {"byPort": by_port, "byDir": {d: True for d in built}}
for root, _, files in os.walk(site):
    if any(os.path.relpath(root, site).split(os.sep)[0] == b for b in built):
        continue
    for f in files:
        if not f.endswith(".html"):
            continue
        path = os.path.join(root, f)
        depth = os.path.relpath(root, site)
        rel = "./" if depth == "." else "../" * (depth.count(os.sep) + 1)
        tag = ("<script>window.TWIN_HOSTED=" + json.dumps({**hosted, "root": rel}) +
               "</script><script src=\"" + rel + "twin-hosted.js\"></script>")
        html = open(path, encoding="utf-8").read()
        if "twin-hosted.js" in html:
            continue
        html, n = re.subn(r"(<head[^>]*>)", lambda m: m.group(1) + tag, html, count=1, flags=re.I)
        if not n:
            html = tag + html
        open(path, "w", encoding="utf-8").write(html)
json.dump({**hosted, "built": built}, open(os.path.join(site, "hosted.json"), "w"), indent=1)
PY

# Apps that can fall back to the in-browser engine pay a one-off cost the first
# time a snapshot cannot answer: Pyodide from its CDN (~7 MB compressed, then
# cached by the browser for every app on the site, since they all name the same
# URL) plus the app's own ~70 KiB engine bundle. Measured here: first paint
# under 150 ms (a prebaked snapshot answers it), ~4.5 s cold to the first
# engine answer, ~0.2 s for every answer after. Nothing prefetches the 7 MB —
# that would tax every visit to pay for some — so the only thing injected is
# the preconnect, which buys the DNS and TLS handshake early. Prefetching
# bundle.zip was tried and removed: the worker's own fetch did not reuse it,
# so it cost a second download and saved nothing measurable.
python3 - "$SITE" "${built[@]}" <<'PY'
import json, os, re, sys
site, built = sys.argv[1], sys.argv[2:]
CDN = "https://cdn.jsdelivr.net"
for comp in built:
    index = os.path.join(site, comp, "api-static", "index.json")
    page = os.path.join(site, comp, "index.html")
    try:
        if not json.load(open(index)).get("engine"):
            continue
    except (OSError, ValueError):
        continue
    html = open(page, encoding="utf-8").read()
    if CDN in html:           # already injected (the pages preconnect fonts too)
        continue
    tag = f'<link rel="preconnect" href="{CDN}" crossorigin>'
    html, n = re.subn(r"(<head[^>]*>)", lambda m: m.group(1) + tag, html, count=1, flags=re.I)
    if n:
        open(page, "w", encoding="utf-8").write(html)
PY

echo
echo "site: $SITE"
echo "hosted (${#built[@]}): ${built[*]:-none}"
[ "${#skipped[@]}" -eq 0 ] || echo "not static-ready yet (${#skipped[@]}): ${skipped[*]}"
