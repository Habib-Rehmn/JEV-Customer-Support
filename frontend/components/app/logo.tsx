import { LifeBuoyIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** Brand mark: a small blue tile with the product name. */
export function Logo({ className, size = "sm" }: { className?: string; size?: "sm" | "lg" }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold", className)}>
      <span
        className={cn(
          "flex items-center justify-center rounded-lg bg-primary text-primary-foreground",
          size === "lg" ? "size-10" : "size-7",
        )}
      >
        <LifeBuoyIcon className={size === "lg" ? "size-5" : "size-4"} />
      </span>
      Jev Support
    </span>
  );
}
