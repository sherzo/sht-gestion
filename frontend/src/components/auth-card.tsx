import type { ReactNode } from "react";

// Marco de las pantallas sin sesión (instalación, ingreso, cambio obligatorio de clave).
export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <section className="w-full max-w-md rounded-xl border border-line bg-surface p-4 shadow-sm sm:p-6">
        <img
          src="/marca/logo-horizontal.svg"
          alt="Suministros Hidráulicos Turmero"
          width={220}
          height={65}
          className="mb-6 h-auto w-55"
        />
        <h1 className="mb-4 text-2xl font-bold">{title}</h1>
        {children}
      </section>
    </main>
  );
}
