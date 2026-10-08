"use client";

// Instalación del primer administrador con el código secreto (RF-44/FR-001).
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AuthCard } from "@/components/auth-card";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

const EMPTY = { setup_code: "", full_name: "", username: "", password: "", confirm: "" };

export default function SetupPage() {
  const { status, setSession } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/");
    if (status === "anonymous") router.replace("/ingresar/");
  }, [status, router]);

  function update(name: keyof typeof EMPTY, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFields({});
    if (form.password !== form.confirm) {
      setFields({ confirm: "Las contraseñas no coinciden" });
      return;
    }
    setSubmitting(true);
    try {
      const { confirm: _confirm, ...body } = form;
      const session = await apiFetch<Schemas["SessionResponse"]>("/setup", {
        method: "POST",
        body,
        authenticated: false,
      });
      setSession(session);
      router.replace("/");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        setFields(caught.fields);
      } else {
        setError("Ocurrió un error inesperado");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title="Instalación">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <p className="text-ink-muted">
          Crea la cuenta del administrador. Necesitas el código de instalación configurado en el
          servidor.
        </p>
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField
          label="Código de instalación"
          name="setup_code"
          type="password"
          autoComplete="off"
          required
          value={form.setup_code}
          error={fields.setup_code}
          onChange={(event) => update("setup_code", event.target.value)}
        />
        <TextField
          label="Nombre completo"
          name="full_name"
          autoComplete="name"
          required
          value={form.full_name}
          error={fields.full_name}
          onChange={(event) => update("full_name", event.target.value)}
        />
        <TextField
          label="Usuario"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          hint="De 3 a 30 caracteres: letras sin acento, números, punto, guion o guion bajo."
          required
          value={form.username}
          error={fields.username}
          onChange={(event) => update("username", event.target.value)}
        />
        <TextField
          label="Contraseña"
          name="password"
          type="password"
          autoComplete="new-password"
          hint="Mínimo 8 caracteres."
          required
          value={form.password}
          error={fields.password}
          onChange={(event) => update("password", event.target.value)}
        />
        <TextField
          label="Confirmar contraseña"
          name="confirm"
          type="password"
          autoComplete="new-password"
          required
          value={form.confirm}
          error={fields.confirm}
          onChange={(event) => update("confirm", event.target.value)}
        />
        <Button type="submit" loading={submitting}>
          Crear administrador
        </Button>
      </form>
    </AuthCard>
  );
}
