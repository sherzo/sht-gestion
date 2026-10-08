"use client";

// Gestión de usuarios por el admin (RF-45/FR-015 a FR-019).
import { ROLE_LABELS, ROLES, formatDateTime } from "@sht/shared";
import type { Role } from "@sht/shared";
import { KeyRound, Pencil, UserPlus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import type { Column } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { SelectField, TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

type User = Schemas["UserSummary"];

const EMPTY_USER = { full_name: "", username: "", role: "seller" as Role, password: "" };
const ROLE_OPTIONS = ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }));

function Badge({ tone, children }: { tone: "success" | "danger" | "warning"; children: string }) {
  const styles = {
    success: "bg-success-soft text-success",
    danger: "bg-danger-soft text-danger",
    warning: "bg-warning-soft text-warning",
  };
  return <span className={`inline-block rounded-md px-2 py-0.5 text-sm font-medium ${styles[tone]}`}>{children}</span>;
}

type FormState = { error: string | null; fields: Record<string, string>; submitting: boolean };
const IDLE: FormState = { error: null, fields: {}, submitting: false };

function failed(caught: unknown): FormState {
  if (caught instanceof ApiError) return { error: caught.message, fields: caught.fields, submitting: false };
  return { error: "Ocurrió un error inesperado", fields: {}, submitting: false };
}

function CreateUserDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (user: User) => void }) {
  const [form, setForm] = useState(EMPTY_USER);
  const [state, setState] = useState<FormState>(IDLE);

  useEffect(() => {
    if (open) {
      setForm(EMPTY_USER);
      setState(IDLE);
    }
  }, [open]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setState({ ...IDLE, submitting: true });
    try {
      const user = await apiFetch<User>("/users", { method: "POST", body: form });
      onCreated(user);
    } catch (caught) {
      setState(failed(caught));
    }
  }

  return (
    <Dialog open={open} title="Nuevo usuario" onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {state.error && <Alert variant="danger">{state.error}</Alert>}
        <TextField label="Nombre completo" required value={form.full_name} error={state.fields.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <TextField
          label="Usuario"
          autoCapitalize="none"
          hint="De 3 a 30 caracteres: letras sin acento, números, punto, guion o guion bajo."
          required
          value={form.username}
          error={state.fields.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
        <SelectField label="Rol" options={ROLE_OPTIONS} value={form.role} error={state.fields.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })} />
        <TextField
          label="Contraseña inicial"
          type="text"
          autoComplete="off"
          hint="Mínimo 8 caracteres. Es temporal: el usuario deberá cambiarla al entrar."
          required
          value={form.password}
          error={state.fields.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <Button type="submit" loading={state.submitting}>
          Crear usuario
        </Button>
      </form>
    </Dialog>
  );
}

function EditUserDialog({ user, onClose, onSaved }: { user: User | null; onClose: () => void; onSaved: (user: User) => void }) {
  const [form, setForm] = useState({ full_name: "", role: "seller" as Role, is_active: true });
  const [state, setState] = useState<FormState>(IDLE);

  useEffect(() => {
    if (user) {
      setForm({ full_name: user.full_name, role: user.role, is_active: user.is_active });
      setState(IDLE);
    }
  }, [user]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    const changes: Record<string, unknown> = {};
    if (form.full_name !== user.full_name) changes.full_name = form.full_name;
    if (form.role !== user.role) changes.role = form.role;
    if (form.is_active !== user.is_active) changes.is_active = form.is_active;
    if (Object.keys(changes).length === 0) {
      onClose();
      return;
    }
    setState({ ...IDLE, submitting: true });
    try {
      onSaved(await apiFetch<User>(`/users/${user.id}`, { method: "PATCH", body: changes }));
    } catch (caught) {
      setState(failed(caught));
    }
  }

  return (
    <Dialog open={user !== null} title={`Editar a ${user?.full_name ?? ""}`} onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {state.error && <Alert variant="danger">{state.error}</Alert>}
        <p className="text-ink-muted">Usuario: {user?.username}</p>
        <TextField label="Nombre completo" required value={form.full_name} error={state.fields.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <SelectField
          label="Rol"
          options={ROLE_OPTIONS}
          value={form.role}
          hint={user?.role === "admin" && form.role !== "admin" ? "Al dejar de ser administrador se borrará su PIN." : undefined}
          onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
        />
        <label className="flex min-h-11 items-center gap-3">
          <input type="checkbox" className="size-5" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Activo (puede iniciar sesión)
        </label>
        {user?.is_active && !form.is_active && <Alert variant="warning">Al desactivarlo se cerrarán sus sesiones de inmediato.</Alert>}
        <Button type="submit" loading={state.submitting}>
          Guardar cambios
        </Button>
      </form>
    </Dialog>
  );
}

function ResetPasswordDialog({ user, onClose, onDone }: { user: User | null; onClose: () => void; onDone: (user: User) => void }) {
  const [password, setPassword] = useState("");
  const [state, setState] = useState<FormState>(IDLE);

  useEffect(() => {
    if (user) {
      setPassword("");
      setState(IDLE);
    }
  }, [user]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    setState({ ...IDLE, submitting: true });
    try {
      await apiFetch(`/users/${user.id}/password`, { method: "POST", body: { new_password: password } });
      onDone(user);
    } catch (caught) {
      setState(failed(caught));
    }
  }

  return (
    <Dialog open={user !== null} title="Restablecer contraseña" onClose={onClose}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {state.error && <Alert variant="danger">{state.error}</Alert>}
        <p>
          Asigna una contraseña temporal a <strong>{user?.full_name}</strong>. Se cerrarán sus sesiones y
          deberá cambiarla al entrar.
        </p>
        <TextField
          label="Contraseña temporal"
          type="text"
          autoComplete="off"
          hint="Mínimo 8 caracteres."
          required
          value={password}
          error={state.fields.new_password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" loading={state.submitting}>
          Restablecer
        </Button>
      </form>
    </Dialog>
  );
}

function UsersContent() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [resetting, setResetting] = useState<User | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const query = { role: role || undefined, is_active: status === "" ? undefined : status === "active" };
      setUsers(await apiFetch<User[]>("/users", { query }));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cargar la lista");
    }
  }, [role, status]);

  useEffect(() => {
    void load();
  }, [load]);

  const columns: Column<User>[] = [
    {
      key: "name",
      header: "Nombre",
      render: (user) => (
        <>
          <span className="font-medium">{user.full_name}</span>
          <span className="block text-sm text-ink-muted">{user.username}</span>
        </>
      ),
    },
    { key: "role", header: "Rol", render: (user) => ROLE_LABELS[user.role] },
    {
      key: "status",
      header: "Estado",
      render: (user) => (
        <span className="flex flex-wrap gap-1">
          {user.is_active ? <Badge tone="success">Activo</Badge> : <Badge tone="danger">Inactivo</Badge>}
          {user.must_change_password && <Badge tone="warning">Contraseña temporal</Badge>}
        </span>
      ),
    },
    { key: "last_login", header: "Último ingreso", render: (user) => (user.last_login_at ? formatDateTime(user.last_login_at) : "Nunca") },
    {
      key: "actions",
      header: "Acciones",
      render: (user) => (
        <span className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setEditing(user)}>
            <Pencil aria-hidden className="size-4" /> Editar
          </Button>
          <Button variant="secondary" onClick={() => setResetting(user)}>
            <KeyRound aria-hidden className="size-4" /> Contraseña
          </Button>
        </span>
      ),
    },
  ];

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Usuarios</h1>
        <Button onClick={() => setCreating(true)}>
          <UserPlus aria-hidden className="size-5" /> Nuevo usuario
        </Button>
      </div>
      <div className="mb-4 grid gap-3 sm:max-w-md sm:grid-cols-2">
        <SelectField label="Rol" options={[{ value: "", label: "Todos" }, ...ROLE_OPTIONS]} value={role} onChange={(e) => setRole(e.target.value)} />
        <SelectField
          label="Estado"
          options={[
            { value: "", label: "Todos" },
            { value: "active", label: "Activos" },
            { value: "inactive", label: "Inactivos" },
          ]}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        />
      </div>
      <div className="mb-4 flex flex-col gap-2">
        {notice && <Alert variant="success">{notice}</Alert>}
        {error && <Alert variant="danger">{error}</Alert>}
      </div>
      {users && <DataTable caption="Usuarios" columns={columns} rows={users} rowKey={(user) => user.id} emptyMessage="No hay usuarios con estos filtros." />}

      <CreateUserDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(user) => {
          setCreating(false);
          setNotice(`Usuario ${user.username} creado. Comunícale la contraseña inicial; deberá cambiarla al entrar.`);
          void load();
        }}
      />
      <EditUserDialog
        user={editing}
        onClose={() => setEditing(null)}
        onSaved={(user) => {
          setEditing(null);
          setNotice(`Cambios guardados para ${user.username}.`);
          void load();
        }}
      />
      <ResetPasswordDialog
        user={resetting}
        onClose={() => setResetting(null)}
        onDone={(user) => {
          setResetting(null);
          setNotice(`Contraseña de ${user.username} restablecida. Deberá cambiarla al entrar.`);
          void load();
        }}
      />
    </AppShell>
  );
}

export default function UsersPage() {
  return (
    <RequireAuth roles={["admin"]}>
      <UsersContent />
    </RequireAuth>
  );
}
