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
    <main>
      <h1>SHT Gestión</h1>
      <p>Suministros Hidráulicos Turmero</p>
      {status.state === "checking" && <p>Comprobando conexión con la API…</p>}
      {status.state === "ok" && (
        <p>
          API conectada: versión {status.version} ({status.environment})
        </p>
      )}
      {status.state === "error" && <p>No se pudo conectar con la API.</p>}
    </main>
  );
}
