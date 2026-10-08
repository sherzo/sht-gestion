"use client";

// Cambio de la propia contraseña (RF-44/FR-007). Obligatorio con contraseña temporal
// (RF-45/FR-016a): en ese caso no se muestra el menú.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { AuthCard } from "@/components/auth-card";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

const EMPTY = { current_password: "", new_password: "", confirm: "" };

function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const { reloadUser } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFields({});
    if (form.new_password !== form.confirm) {
      setFields({ confirm: "Las contraseñas no coinciden" });
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch("/auth/password", {
        method: "POST",
        body: { current_password: form.current_password, new_password: form.new_password },
      });
      await reloadUser();
      onDone();
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(
          caught.code === "invalid_current_password"
            ? { current_password: caught.message }
            : caught.fields,
        );
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      {error && <Alert variant="danger">{error}</Alert>}
      <TextField
        label="Contraseña actual"
        type="password"
        autoComplete="current-password"
        required
        value={form.current_password}
        error={fields.current_password}
        onChange={(event) => setForm({ ...form, current_password: event.target.value })}
      />
      <TextField
        label="Contraseña nueva"
        type="password"
        autoComplete="new-password"
        hint="Mínimo 8 caracteres y distinta de la actual."
        required
        value={form.new_password}
        error={fields.new_password}
        onChange={(event) => setForm({ ...form, new_password: event.target.value })}
      />
      <TextField
        label="Confirmar contraseña nueva"
        type="password"
        autoComplete="new-password"
        required
        value={form.confirm}
        error={fields.confirm}
        onChange={(event) => setForm({ ...form, confirm: event.target.value })}
      />
      <Button type="submit" loading={submitting}>
        Cambiar contraseña
      </Button>
    </form>
  );
}

function ChangePasswordContent() {
  const { user } = useAuth();
  const router = useRouter();
  const goHome = () => router.replace("/");

  if (user?.must_change_password) {
    return (
      <AuthCard title="Cambia tu contraseña">
        <p className="mb-4 text-ink-muted">
          Tu contraseña la asignó un administrador. Antes de continuar, elige una propia que solo
          tú conozcas.
        </p>
        <ChangePasswordForm onDone={goHome} />
      </AuthCard>
    );
  }

  return (
    <AppShell>
      <div className="max-w-md">
        <h1 className="mb-4 text-2xl font-bold">Cambiar contraseña</h1>
        <p className="mb-4 text-ink-muted">
          Al cambiarla se cerrarán tus sesiones en otros equipos. <Link href="/mi-cuenta/" className="text-primary underline">Volver a mi cuenta</Link>
        </p>
        <ChangePasswordForm onDone={goHome} />
      </div>
    </AppShell>
  );
}

export default function ChangePasswordPage() {
  return (
    <RequireAuth allowTemporaryPassword>
      <ChangePasswordContent />
    </RequireAuth>
  );
}
