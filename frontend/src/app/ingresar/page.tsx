"use client";

// Inicio de sesión (RF-44/FR-002 a FR-004).
import { formatTime } from "@sht/shared";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AuthCard } from "@/components/auth-card";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "account_locked" && typeof error.extra.locked_until === "string") {
      return `Demasiados intentos fallidos. Podrás intentar de nuevo a las ${formatTime(error.extra.locked_until)}.`;
    }
    return error.message;
  }
  return "Ocurrió un error inesperado";
}

export default function LoginPage() {
  const { status, login, connectionError } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [online, setOnline] = useState(true);

  useEffect(() => {
    if (status === "authenticated") router.replace("/");
    if (status === "setup_required") router.replace("/instalacion/");
  }, [status, router]);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      router.replace("/");
    } catch (caught) {
      setError(loginErrorMessage(caught));
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title="Iniciar sesión">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {!online && <Alert variant="warning">Para iniciar sesión necesitas conexión a internet.</Alert>}
        {online && connectionError && (
          <Alert variant="danger">No se pudo conectar con el servidor. Inténtalo de nuevo en unos minutos.</Alert>
        )}
        {error && <Alert variant="danger">{error}</Alert>}
        <TextField
          label="Usuario"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <TextField
          label="Contraseña"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Button type="submit" loading={submitting} disabled={!username || !password}>
          Entrar
        </Button>
      </form>
    </AuthCard>
  );
}
