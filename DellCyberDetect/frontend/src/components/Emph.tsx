import { Fragment, type ReactNode } from "react";

// Backend prose marks emphasis the way the docstrings do — *word* — so the
// stress survives every reading level. Render those spans as <em> instead of
// showing the asterisks; everything else passes through as plain text.
export function emph(text: string): ReactNode {
  const parts = text.split(/\*([^*\n]+)\*/g);
  if (parts.length === 1) return text;
  return parts.map((p, i) =>
    i % 2 === 1 ? <em key={i}>{p}</em> : <Fragment key={i}>{p}</Fragment>,
  );
}
