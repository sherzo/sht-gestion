"use client";

// Inicio: saludo, rol y vencimiento de la jornada (RF-44/FR-005, FR-030), tarjetas del
// inventario para Admin y Almacén (RF-11, RN-19; research R11) y accesos a Vender y Caja
// para quien vende (etapa 1.3).
import { ROLE_LABELS, formatDateTime } from "@sht/shared";
import { AlertTriangle, BadgePercent, ClipboardCheck, ClipboardList, FilePen, Inbox, ShieldAlert, ShoppingBag, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/use-auth";

type Summary = Schemas["AdminSummary"] | Schemas["WarehouseSummary"];
type Card = { href: string; label: string; count: number; icon: LucideIcon; tone: "warning" | "info" };

function cards(summary: Summary): Card[] {
  const result: Card[] = [{ href: "/inventario/stock-bajo/", label: "Productos con stock bajo", count: summary.low_stock, icon: AlertTriangle, tone: "warning" }];
  if ("pending_adjustments" in summary) {
    result.push(
      { href: "/pendientes/", label: "Salidas por aprobar", count: summary.pending_adjustments, icon: Inbox, tone: "info" },
      { href: "/pendientes/", label: "Conteos listos para revisión", count: summary.counts_ready_for_review, icon: ClipboardCheck, tone: "info" },
      { href: "/pendientes/", label: "Alertas por revisar", count: summary.open_alerts, icon: ShieldAlert, tone: "warning" },
      { href: "/pendientes/", label: "Descuentos por aprobar", count: summary.pending_discount_requests, icon: BadgePercent, tone: "warning" },
    );
  } else {
    result.push(
      { href: "/inventario/mis-solicitudes/", label: "Mis salidas pendientes", count: summary.my_pending_requests, icon: ClipboardList, tone: "info" },
      { href: "/inventario/conteos/", label: "Conteos abiertos", count: summary.open_counts, icon: ClipboardCheck, tone: "info" },
    );
  }
  result.push({ href: "/compras/", label: "Compras en borrador", count: summary.draft_purchases, icon: FilePen, tone: "info" });
  return result;
}

function InventoryCards() {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    apiFetch<Summary>("/inventory/summary")
      .then(setSummary)
      .catch(() => setSummary(null));
  }, []);

  if (!summary) return null;
  return (
    <ul className="mt-6 grid gap-3 sm:grid-cols-3">
      {cards(summary).map(({ href, label, count, icon: Icon, tone }) => (
        <li key={label}>
          <Link
            href={href}
            className="flex min-h-11 items-center gap-3 rounded-xl border border-line bg-surface p-4 hover:bg-neutral-50"
          >
            <span
              className={`inline-flex size-11 shrink-0 items-center justify-center rounded-lg ${
                count > 0 && tone === "warning" ? "bg-warning-soft text-warning" : "bg-info-soft text-info"
              }`}
            >
              <Icon aria-hidden className="size-5" />
            </span>
            <span>
              <span className="block text-2xl font-bold tabular-nums">{count}</span>
              <span className="text-sm text-ink-muted">{label}</span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

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
      {(user.role === "admin" || user.role === "seller") && (
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/vender/" className="inline-flex min-h-14 items-center gap-2 rounded-xl bg-accent px-5 text-lg font-semibold text-on-accent hover:bg-accent-hover">
            <ShoppingBag aria-hidden className="size-6" /> Vender
          </Link>
          <Link href="/caja/" className="inline-flex min-h-14 items-center gap-2 rounded-xl border border-line bg-surface px-5 text-lg font-semibold hover:bg-neutral-50">
            <Wallet aria-hidden className="size-6" /> Caja
          </Link>
        </div>
      )}
      {(user.role === "admin" || user.role === "warehouse") && <InventoryCards />}
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
