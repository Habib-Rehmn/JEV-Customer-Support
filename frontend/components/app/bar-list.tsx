import { cn } from "@/lib/utils";

export interface BarItem {
  label: string;
  value: number;
  /** Text shown at the end of the bar, e.g. "91%" or "12". */
  display: string;
  /** Extra line in the hover tooltip. */
  detail?: string;
  emphasis?: boolean;
}

/**
 * Horizontal single-series bars: 12px marks, square at the baseline, 4px rounded data-end,
 * value labels as text (never colored). Emphasised rows use the accent, the rest the muted gray.
 * With `emphasisMode` off every bar uses the accent.
 */
export function BarList({
  items,
  max,
  emphasisMode = false,
  label,
}: {
  items: BarItem[];
  max?: number;
  emphasisMode?: boolean;
  label: string;
}) {
  const scale = max ?? Math.max(...items.map((i) => i.value), 0);
  return (
    <ul className="space-y-2.5" aria-label={label}>
      {items.map((item) => {
        const width = scale > 0 ? (item.value / scale) * 100 : 0;
        const accent = !emphasisMode || item.emphasis;
        return (
          <li key={item.label} className="group relative grid grid-cols-[8.5rem_1fr_3rem] items-center gap-3 text-sm">
            <span className={cn("truncate", item.emphasis ? "font-medium" : "text-muted-foreground")}>
              {item.label}
            </span>
            <div className="h-3 rounded-r-[4px] bg-viz-track">
              <div
                className={cn("h-3 rounded-r-[4px]", accent ? "bg-viz-accent" : "bg-viz-muted")}
                style={{ width: `${width}%`, minWidth: item.value > 0 ? 2 : 0 }}
              />
            </div>
            <span className="text-right tabular-nums">{item.display}</span>
            <span
              role="tooltip"
              className="pointer-events-none absolute -top-9 left-36 z-10 hidden rounded-md border bg-popover px-2 py-1 text-xs whitespace-nowrap text-popover-foreground shadow-md group-hover:block"
            >
              <span className="font-medium">{item.label}</span>: {item.display}
              {item.detail && <span className="text-muted-foreground"> · {item.detail}</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
