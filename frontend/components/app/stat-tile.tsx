import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type TileTone = "blue" | "orange" | "green" | "violet";

const TONES: Record<TileTone, string> = {
  blue: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  orange: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  green: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  violet: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
};

export function StatTile({
  label,
  value,
  hint,
  icon: Icon,
  tone = "blue",
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: React.ComponentType<{ className?: string }>;
  tone?: TileTone;
}) {
  return (
    <Card size="sm">
      <CardContent className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold tabular-nums">{value}</p>
          {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        </div>
        {Icon && (
          <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", TONES[tone])} aria-hidden>
            <Icon className="size-4.5" />
          </span>
        )}
      </CardContent>
    </Card>
  );
}
