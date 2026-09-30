"use client";

import { MoonIcon, SunIcon } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { applyTheme, savedTheme, saveTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

/**
 * Switches between light and dark. Until the user picks one, the OS setting is followed (live).
 * The icon is chosen by CSS from the <html> class, so server and client render the same markup.
 */
export function ThemeToggle({ className }: { className?: string }) {
  useEffect(() => {
    if (savedTheme()) return;
    const media = matchMedia("(prefers-color-scheme: dark)");
    const follow = () => !savedTheme() && applyTheme(media.matches ? "dark" : "light");
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  function toggle() {
    const next = document.documentElement.classList.contains("dark") ? "light" : "dark";
    applyTheme(next);
    saveTheme(next);
  }

  return (
    <Button variant="ghost" size="icon" onClick={toggle} className={cn(className)} aria-label="Toggle dark mode">
      <SunIcon className="hidden dark:block" />
      <MoonIcon className="block dark:hidden" />
    </Button>
  );
}
