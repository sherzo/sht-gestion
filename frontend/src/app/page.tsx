"use client";

// Inicio: saludo, rol y vencimiento de la jornada (RF-44/FR-005, FR-030).
import { ROLE_LABELS, formatDateTime } from "@sht/shared";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/lib/auth/use-auth";

function HomeContent() {
  const { user, sessionExpiresAt } = useAuth();
  if (!user) return null;
  return (
    <AppShell>
      <h1 className="mb-2 text-2xl font-bold">Hola, {user.full_name}</h1>
      <p className="text-ink-muted">Rol: {ROLE_LABELS[user.role]}</p>
      {sessionExpiresAt && (
        <p className="mt-4 rounded-xl border border-line bg-surface p-4">
          Tu jornada vence el <strong>{formatDateTime(sessionExpiresAt)}</strong>. Después tendrás
          que volver a ingresar tu contraseña.
        </p>
      )}
    </AppShell>
  );
}

export default function HomePage() {
  return (
    <RequireAuth>
      <HomeContent />
    </RequireAuth>
  );
}
