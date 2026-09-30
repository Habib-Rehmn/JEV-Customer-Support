"use client";

import { useState } from "react";

import { NativeSelect } from "@/components/app/native-select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import type { User } from "@/types/api";

export default function UsersPage() {
  const { user: me } = useAuth();
  const { data: users, error, reload } = useApi(() => api.listUsers(), "users");

  if (me?.role !== "ADMIN") {
    return (
      <Alert>
        <AlertDescription>Only admins can manage users.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Users</h1>
        <p className="text-sm text-muted-foreground">
          Agents answer tickets. Admins can also manage users and edit ticket fields directly.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Support team</CardTitle>
            <CardDescription>{users ? `${users.length} users` : "Loading…"}</CardDescription>
          </CardHeader>
          <CardContent>
            {users ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Added</TableHead>
                    <TableHead className="text-right">Password</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <UserRow key={user.id} user={user} isMe={user.id === me.id} onChanged={reload} />
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Skeleton className="h-40" />
            )}
          </CardContent>
        </Card>

        <AddUserCard onCreated={reload} />
      </div>
    </div>
  );
}

function UserRow({ user, isMe, onChanged }: { user: User; isMe: boolean; onChanged: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function save(data: { role?: User["role"]; password?: string }, done: string): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      await api.updateUser(user.id, data);
      setNotice(done);
      setResetting(false);
      setPassword("");
      onChanged();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <TableRow>
      <TableCell>
        <p className="font-medium">
          {user.name} {isMe && <span className="text-xs text-muted-foreground">(you)</span>}
        </p>
        <p className="text-muted-foreground">{user.email}</p>
        {(error || notice) && (
          <p className={error ? "text-xs text-destructive" : "text-xs text-muted-foreground"}>{error ?? notice}</p>
        )}
      </TableCell>
      <TableCell>
        <NativeSelect
          aria-label={`Role for ${user.name}`}
          value={user.role}
          disabled={busy}
          onChange={(e) => {
            const role = e.target.value as User["role"];
            if (isMe && role === "AGENT" && !window.confirm("Remove your own admin access?")) return;
            save({ role }, `Role changed to ${role.toLowerCase()}`).then((ok) => {
              // Your own permissions changed: reload so the whole app picks them up.
              if (ok && isMe) window.location.reload();
            });
          }}
        >
          <option value="AGENT">Agent</option>
          <option value="ADMIN">Admin</option>
        </NativeSelect>
      </TableCell>
      <TableCell className="text-muted-foreground">{dateTime(user.created_at)}</TableCell>
      <TableCell className="text-right">
        {resetting ? (
          <form
            className="flex justify-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              save({ password }, "Password updated");
            }}
          >
            <Input
              type="password"
              aria-label={`New password for ${user.name}`}
              placeholder="New password"
              minLength={8}
              required
              autoComplete="new-password"
              className="h-8 w-40"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button size="sm" type="submit" disabled={busy}>
              Save
            </Button>
            <Button size="sm" variant="ghost" type="button" onClick={() => setResetting(false)}>
              Cancel
            </Button>
          </form>
        ) : (
          <Button size="sm" variant="outline" onClick={() => setResetting(true)}>
            Reset
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}

function AddUserCard({ onCreated }: { onCreated: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    setBusy(true);
    setError(null);
    setCreated(null);
    try {
      const user = await api.createUser({
        name: String(form.get("name")).trim(),
        email: String(form.get("email")).trim(),
        password: String(form.get("password")),
        role: form.get("role") as User["role"],
      });
      setCreated(`${user.name} can now sign in.`);
      formEl.reset();
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create user");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add user</CardTitle>
        <CardDescription>Share the password with them securely.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="new-name">Name</Label>
            <Input id="new-name" name="name" required maxLength={200} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-email">Email</Label>
            <Input id="new-email" name="email" type="email" required autoComplete="off" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-password">Password</Label>
            <Input id="new-password" name="password" type="password" required minLength={8} autoComplete="new-password" />
            <p className="text-xs text-muted-foreground">At least 8 characters.</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-role">Role</Label>
            <NativeSelect id="new-role" name="role" defaultValue="AGENT" className="w-full">
              <option value="AGENT">Agent</option>
              <option value="ADMIN">Admin</option>
            </NativeSelect>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {created && (
            <Alert>
              <AlertDescription>{created}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Adding…" : "Add user"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
