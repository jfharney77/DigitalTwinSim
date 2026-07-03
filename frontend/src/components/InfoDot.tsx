import { useEffect, useState } from "react";

/**
 * Small "ⓘ" affordance next to a control. Click opens a modal with a plain-language
 * explanation of what the widget means / implies. Purely presentational — no sim state.
 */
export function InfoDot({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="infodot"
        aria-label={`What is ${title}?`}
        title={`What is ${title}?`}
        onClick={() => setOpen(true)}
      >
        i
      </button>
      {open && (
        <div className="info-backdrop" onClick={() => setOpen(false)}>
          <div
            className="info-modal"
            role="dialog"
            aria-modal="true"
            aria-label={title}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="info-modal-head">
              <h3>{title}</h3>
              <button
                type="button"
                className="info-close"
                aria-label="Close"
                onClick={() => setOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="info-modal-body">{children}</div>
          </div>
        </div>
      )}
    </>
  );
}
