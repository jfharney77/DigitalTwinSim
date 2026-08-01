// Shared SVG download helper (spec_21 #3): serialize the first <svg> inside
// a container to a standalone file, with the app's CSS variables inlined so
// the export renders outside the app. Used by the Live tab and the simulator.

const THEME_VARS = [
  "--sm-idle",
  "--sm-edge",
  "--core-on",
  "--core-hot",
  "--core-off",
  "--stall",
  "--mem",
  "--mem-active",
];

export function downloadSvgFrom(
  container: HTMLElement | null,
  filename: string,
): void {
  const svg = container?.querySelector("svg");
  if (!svg) return;
  const clone = svg.cloneNode(true) as SVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const styles = getComputedStyle(document.documentElement);
  for (const v of THEME_VARS) {
    clone.innerHTML = clone.innerHTML
      .split(`var(${v})`)
      .join(styles.getPropertyValue(v).trim() || "#888");
  }
  const blob = new Blob([clone.outerHTML], { type: "image/svg+xml" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename.endsWith(".svg") ? filename : `${filename}.svg`;
  a.click();
  URL.revokeObjectURL(a.href);
}
