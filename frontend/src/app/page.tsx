"use client";

import { useEffect, useState } from "react";

type ApiStatus =
  | { state: "checking" }
  | { state: "ok"; version: string; environment: string }
  | { state: "error" };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// Página mínima de la etapa 1.0: comprueba que la app publicada llega a la API.
export default function Home() {
  const [status, setStatus] = useState<ApiStatus>({ state: "checking" });

  useEffect(() => {
    fetch(`${API_URL}/api/v1/health`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response)))
      .then((data: { version: string; environment: string }) =>
        setStatus({ state: "ok", version: data.version, environment: data.environment }),
      )
      .catch(() => setStatus({ state: "error" }));
  }, []);

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <section className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-sm">
        <img
          src="/marca/logo-horizontal.svg"
          alt="Suministros Hidráulicos Turmero"
          width={240}
          height={71}
          className="mb-6 h-auto w-60"
        />
        <h1 className="mb-4 text-2xl font-bold">SHT Gestión</h1>
        {status.state === "checking" && (
          <p className="text-ink-muted">Comprobando conexión con la API…</p>
        )}
        {status.state === "ok" && (
          <p className="rounded-lg bg-success-soft px-3 py-2 text-success">
            API conectada: versión {status.version} ({status.environment})
          </p>
        )}
        {status.state === "error" && (
          <p className="rounded-lg bg-danger-soft px-3 py-2 text-danger">
            No se pudo conectar con la API.
          </p>
        )}
      </section>
    </main>
  );
}
