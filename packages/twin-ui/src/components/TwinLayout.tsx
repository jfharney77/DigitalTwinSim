import { useEffect, type ReactNode } from "react";

export type TwinTab<Id extends string = string> = {
  id: Id;
  label: string;
};

/**
 * The page shell every twin frontend opens with: the `.app dell` grid, a flat
 * white header carrying the twin's name and its tabs, and the `dell-body`
 * class on `<body>` that paints the page ground.
 *
 * The skin's rules live here so they cannot drift per component: no eyebrow
 * text above the title, no numbering on the tabs, no divider rule between
 * header and content beyond the single border the tokens define.
 */
export function TwinLayout<Id extends string>({
  title,
  subtitle,
  tabs,
  active,
  onTab,
  aside,
  children,
}: {
  title: string;
  /** The one-line "what this is". Optional — some twins put it in the page. */
  subtitle?: ReactNode;
  tabs?: readonly TwinTab<Id>[];
  active?: Id;
  onTab?: (id: Id) => void;
  /** Header right-hand slot: the reading-level control, usually. */
  aside?: ReactNode;
  children: ReactNode;
}) {
  useEffect(() => {
    document.body.classList.add("dell-body");
    return () => document.body.classList.remove("dell-body");
  }, []);

  return (
    <div className="app dell">
      <header>
        <h1>{title}</h1>
        {tabs && tabs.length > 0 && (
          <nav className="nav">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={tab.id === active ? "active" : ""}
                onClick={() => onTab?.(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        )}
        {subtitle && <span className="sub">{subtitle}</span>}
        {aside && <span className="tw-header-aside">{aside}</span>}
      </header>
      {children}
    </div>
  );
}
