"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { Logo } from "@/components/app/logo";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Overview", adminOnly: false },
  { href: "/dashboard/tickets", label: "Tickets", adminOnly: false },
  { href: "/dashboard/rules", label: "Rules", adminOnly: true },
  { href: "/dashboard/users", label: "Users", adminOnly: true },
];

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (!user) {
    return <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b bg-card">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-6 px-4">
          <Link href="/dashboard">
            <Logo />
          </Link>
          <nav className="flex gap-1">
            {NAV.filter((item) => !item.adminOnly || user.role === "ADMIN").map(({ href, label }) => {
              const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground",
                    active && "bg-primary/10 font-medium text-primary hover:text-primary",
                  )}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden text-muted-foreground sm:inline">
              {user.name} · {user.role.toLowerCase()}
            </span>
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
