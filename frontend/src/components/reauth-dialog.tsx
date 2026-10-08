"use client";

// Reingreso sin perder lo escrito (caso límite "Sesión vencida a mitad de un trabajo").
// Si la sesión termina durante una petición, se abre este diálogo sobre la página actual;
// al volver a entrar con el mismo usuario, la petición pendiente se reintenta. Solo
// permite el mismo usuario, para que nada quede registrado a nombre de otro.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { TextField } from "@/components/ui/field";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

export function ReauthDialog() {
  const { user, login, endLocalSession, setSessionEndedHandler } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pending = useRef<Promise<boolean> | null>(null);
  const resolver = useRef<((value: boolean) => void) | null>(null);
  const userRef = useRef(user);
  userRef.current = user ?? userRef.current;

  const finish = useCallback((value: boolean) => {
    resolver.current?.(value);
    resolver.current = null;
    pending.current = null;
    setOpen(false);
    setPassword("");
    setError(null);
  }, []);

  useEffect(() => {
    setSessionEndedHandler(() => {
      if (!userRef.current) return Promise.resolve(false);
      // Varias peticiones pueden fallar a la vez: comparten el mismo diálogo.
      pending.current ??= new Promise<boolean>((resolve) => {
        resolver.current = resolve;
        setOpen(true);
      });
      return pending.current;
    });
    return () => setSessionEndedHandler(null);
  }, [setSessionEndedHandler]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const previous = userRef.current;
    if (!previous) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(previous.username, password);
      finish(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Ocurrió un error inesperado");
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  function onExit() {
    finish(false);
    userRef.current = null;
    endLocalSession();
    router.replace("/ingresar/");
  }

  const current = userRef.current;
  return (
    <Dialog open={open} title="Tu sesión terminó" onClose={onExit} dismissible={false}>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <p className="text-ink-muted">
          Vuelve a ingresar tu contraseña para continuar donde estabas. Lo que escribiste no se
          pierde.
        </p>
        {error && <Alert variant="danger">{error}</Alert>}
        <p>
          Usuario: <strong>{current?.username}</strong>
        </p>
        <TextField
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onExit}>
            Salir
          </Button>
          <Button type="submit" loading={submitting} disabled={!password}>
            Continuar
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
