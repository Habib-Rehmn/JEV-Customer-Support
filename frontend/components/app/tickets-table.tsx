"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { ActionBadge, PriorityBadge, StatusBadge } from "@/components/app/badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { timeAgo } from "@/lib/format";
import type { TicketListItem } from "@/types/api";

export function TicketsTable({ tickets }: { tickets: TicketListItem[] }) {
  const router = useRouter();

  if (tickets.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No tickets here.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">#</TableHead>
          <TableHead>Subject</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tickets.map((ticket) => (
          <TableRow
            key={ticket.id}
            className="cursor-pointer"
            onClick={() => router.push(`/dashboard/tickets/${ticket.id}`)}
          >
            <TableCell className="text-muted-foreground">{ticket.id}</TableCell>
            <TableCell className="max-w-80">
              <Link
                href={`/dashboard/tickets/${ticket.id}`}
                className="block truncate font-medium hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {ticket.subject}
              </Link>
            </TableCell>
            <TableCell>
              <ActionBadge action={ticket.final_action ?? ticket.current_action} />
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1.5">
                <StatusBadge status={ticket.status} />
                <PriorityBadge priority={ticket.priority} />
              </div>
            </TableCell>
            <TableCell className="text-right text-muted-foreground">{timeAgo(ticket.created_at)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
