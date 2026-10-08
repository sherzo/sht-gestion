"use client";

// Mi cuenta: datos del usuario, cambio de contraseña y PIN del admin
// (RF-44, RN-07/FR-026 a FR-028).
import { ROLE_LABELS, formatDateTime, formatTime } from "@sht/shared";
import { KeyRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

type Message = { variant: "success" | "danger" | "warning"; text: string } | null;

function errorMessage(caught: unknown): Message {
  if (caught instanceof ApiError) {
    if (caught.code === "pin_locked" && typeof caught.extra.locked_until === "string") {
      return { variant: "warning", text: `PIN bloqueado por demasiados intentos. Podrás usarlo de nuevo a las ${formatTime(caught.extra.locked_until)}.` };
    }
    return { variant: "danger", text: caught.message };
  }
  return { variant: "danger", text: "Ocurrió un error inesperado" };
}

function PinSection({ userId, username }: { userId: string; username: string }) {
  const [hasPin, setHasPin] = useState<boolean | null>(null);
  const [form, setForm] = useState({ current_password: "", pin: "", confirm: "" });
  const [fields, setFields] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<Message>(null);
  const [saving, setSaving] = useState(false);
  const [testPin, setTestPin] = useState("");
  const [testMessage, setTestMessage] = useState<Message>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    apiFetch<Schemas["UserSummary"]>(`/users/${userId}`)
      .then((user) => setHasPin(user.has_pin))
      .catch(() => setHasPin(null));
  }, [userId]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setFields({});
    if (form.pin !== form.confirm) {
      setFields({ confirm: "Los PIN no coinciden" });
      return;
    }
    setSaving(true);
    try {
      await apiFetch("/auth/pin", { method: "PUT", body: { current_password: form.current_password, pin: form.pin } });
      setHasPin(true);
      setForm({ current_password: "", pin: "", confirm: "" });
      setMessage({ variant: "success", text: "PIN guardado." });
    } catch (caught) {
      setMessage(errorMessage(caught));
      if (caught instanceof ApiError) {
        setFields(caught.code === "invalid_current_password" ? { current_password: caught.message } : caught.fields);
      }
    } finally {
      setSaving(false);
    }
  }

  async function onTest(event: FormEvent) {
    event.preventDefault();
    setTestMessage(null);
    setTesting(true);
    try {
      const result = await apiFetch<Schemas["VerifyPinResponse"]>("/auth/pin/verify", {
        method: "POST",
        body: { admin_username: username, pin: testPin },
      });
      setTestMessage({ variant: "success", text: `PIN correcto: autorizado por ${result.authorized_by.full_name}.` });
    } catch (caught) {
      setTestMessage(errorMessage(caught));
    } finally {
      setTesting(false);
      setTestPin("");
    }
  }

  return (
    <section className="rounded-xl border border-line bg-surface p-4 shadow-sm sm:p-6">
      <h2 className="mb-2 flex items-center gap-2 text-xl font-semibold">
        <KeyRound aria-hidden className="size-5" /> PIN de autorización
      </h2>
      <p className="mb-4 text-ink-muted">
        Con tu PIN autorizas en el momento acciones de otros usuarios, como los descuentos del vendedor.
        {hasPin === false && " Todavía no tienes un PIN."}
      </p>
      <form onSubmit={onSave} className="mb-6 flex flex-col gap-4" noValidate>
        {message && <Alert variant={message.variant}>{message.text}</Alert>}
        <TextField
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          value={form.current_password}
          error={fields.current_password}
          onChange={(e) => setForm({ ...form, current_password: e.target.value })}
        />
        <TextField
          label={hasPin ? "PIN nuevo" : "PIN"}
          type="password"
          inputMode="numeric"
          autoComplete="off"
          maxLength={6}
          hint="De 4 a 6 dígitos."
          value={form.pin}
          error={fields.pin}
          onChange={(e) => setForm({ ...form, pin: e.target.value.replace(/\D/g, "") })}
        />
        <TextField
          label="Confirmar PIN"
          type="password"
          inputMode="numeric"
          autoComplete="off"
          maxLength={6}
          value={form.confirm}
          error={fields.confirm}
          onChange={(e) => setForm({ ...form, confirm: e.target.value.replace(/\D/g, "") })}
        />
        <Button type="submit" loading={saving} disabled={!form.current_password || form.pin.length < 4}>
          {hasPin ? "Cambiar PIN" : "Definir PIN"}
        </Button>
      </form>

      {hasPin && (
        <form onSubmit={onTest} className="flex flex-col gap-4 border-t border-line pt-4" noValidate>
          <h3 className="text-lg font-semibold">Probar PIN</h3>
          {testMessage && <Alert variant={testMessage.variant}>{testMessage.text}</Alert>}
          <TextField
            label="PIN"
            type="password"
            inputMode="numeric"
            autoComplete="off"
            maxLength={6}
            value={testPin}
            onChange={(e) => setTestPin(e.target.value.replace(/\D/g, ""))}
          />
          <Button type="submit" variant="secondary" loading={testing} disabled={testPin.length < 4}>
            Probar
          </Button>
        </form>
      )}
    </section>
  );
}

function AccountContent() {
  const { user, sessionExpiresAt } = useAuth();
  if (!user) return null;
  return (
    <AppShell>
      <div className="flex max-w-xl flex-col gap-6">
        <h1 className="text-2xl font-bold">Mi cuenta</h1>
        <section className="rounded-xl border border-line bg-surface p-4 shadow-sm sm:p-6">
          <dl className="grid gap-2 sm:grid-cols-[10rem_1fr]">
            <dt className="text-ink-muted">Nombre</dt>
            <dd>{user.full_name}</dd>
            <dt className="text-ink-muted">Usuario</dt>
            <dd>{user.username}</dd>
            <dt className="text-ink-muted">Rol</dt>
            <dd>{ROLE_LABELS[user.role]}</dd>
            {sessionExpiresAt && (
              <>
                <dt className="text-ink-muted">Jornada hasta</dt>
                <dd>{formatDateTime(sessionExpiresAt)}</dd>
              </>
            )}
          </dl>
          <Link
            href="/cambiar-clave/"
            className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-line px-4 font-semibold text-ink hover:bg-neutral-100"
          >
            Cambiar contraseña
          </Link>
        </section>
        {user.role === "admin" && <PinSection userId={user.id} username={user.username} />}
      </div>
    </AppShell>
  );
}

export default function AccountPage() {
  return (
    <RequireAuth>
      <AccountContent />
    </RequireAuth>
  );
}
