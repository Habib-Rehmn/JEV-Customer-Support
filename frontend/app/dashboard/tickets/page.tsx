"use client";

import { SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { TicketsTable } from "@/components/app/tickets-table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { STATUS_LABELS } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { TicketStatus } from "@/types/api";

const PAGE_SIZE = 25;
const FILTERS: (TicketStatus | null)[] = [
  null,
  "WAITING_FOR_AGENT",
  "ESCALATED",
  "JEV_FAILED",
  "WAITING_FOR_CUSTOMER",
  "RESOLVED",
];

export default function TicketsPage() {
  const [status, setStatus] = useState<TicketStatus | null>("WAITING_FOR_AGENT");
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");

  // Search 300ms after the agent stops typing.
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, error } = useApi(
    () => api.listTickets({ status: status ?? undefined, q: query, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    `tickets:${status}:${query}:${page}`,
  );
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Tickets</h1>
        <p className="text-sm text-muted-foreground">Start with the ones waiting for you.</p>
      </div>

      <div className="relative max-w-md">
        <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          value={search}
          onChange={(e) => {
            // Searching usually means "find it anywhere", so start from all statuses.
            if (!search && e.target.value) setStatus(null);
            setSearch(e.target.value);
          }}
          placeholder="Search by #number, subject, message, customer or order"
          aria-label="Search tickets"
          className="pl-8"
        />
      </div>

      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filter by status">
        {FILTERS.map((value) => (
          <button
            key={value ?? "all"}
            role="tab"
            aria-selected={status === value}
            onClick={() => {
              setStatus(value);
              setPage(0);
            }}
            className={cn(
              "rounded-full border px-3 py-1 text-sm text-muted-foreground hover:text-foreground",
              status === value && "border-foreground bg-foreground text-background hover:text-background",
            )}
          >
            {value ? STATUS_LABELS[value] : "All"}
          </button>
        ))}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent>
          {data ? (
            query && data.total === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No tickets match &ldquo;{query}&rdquo;{status ? ` in ${STATUS_LABELS[status]}` : ""}.
              </p>
            ) : (
              <TicketsTable tickets={data.items} />
            )
          ) : (
            <Skeleton className="h-60" />
          )}
        </CardContent>
      </Card>

      {data && data.total > PAGE_SIZE && (
        <div className="flex items-center justify-end gap-3 text-sm">
          <span className="text-muted-foreground">
            Page {page + 1} of {pages} · {data.total} tickets
          </span>
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
