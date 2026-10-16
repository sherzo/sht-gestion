"use client";

// Estructura de las pantallas con sesión: barra superior con la marca y menú según el rol
// (RF-44, US2 escenario 5). El menú solo oculta; los permisos los verifica el servidor.
import { ROLE_LABELS } from "@sht/shared";
import type { Role } from "@sht/shared";
import {
  AlertTriangle,
  ClipboardCheck,
  CloudUpload,
  ClipboardList,
  History,
  Home,
  Inbox,
  Landmark,
  LogOut,
  Menu,
  Package,
  ReceiptText,
  Settings,
  ShoppingBag,
  ShoppingCart,
  SlidersHorizontal,
  Truck,
  UserCog,
  Users,
  Vault,
  Wallet,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { Dialog } from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth/use-auth";
import { dismissRejected, hasPending, startOutbox, useOutboxAttention, waitsForOwner } from "@/lib/outbox/outbox";

type NavItem = { href: string; label: string; icon: LucideIcon; roles: Role[] };

const ALL_ROLES: Role[] = ["admin", "seller", "warehouse"];

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Inicio", icon: Home, roles: ALL_ROLES },
  { href: "/vender/", label: "Vender", icon: ShoppingBag, roles: ["admin", "seller"] },
  { href: "/ventas/", label: "Ventas", icon: ReceiptText, roles: ["admin", "seller"] },
  { href: "/caja/", label: "Caja", icon: Wallet, roles: ["admin", "seller"] },
  { href: "/cajas/", label: "Cajas", icon: Vault, roles: ["admin"] },
  { href: "/productos/", label: "Productos", icon: Package, roles: ALL_ROLES },
  { href: "/inventario/ajuste/", label: "Ajuste de inventario", icon: SlidersHorizontal, roles: ["admin", "warehouse"] },
  { href: "/inventario/stock-bajo/", label: "Stock bajo", icon: AlertTriangle, roles: ["admin", "warehouse"] },
  { href: "/inventario/conteos/", label: "Conteos", icon: ClipboardCheck, roles: ["admin", "warehouse"] },
  { href: "/inventario/mis-solicitudes/", label: "Mis solicitudes", icon: ClipboardList, roles: ["warehouse"] },
  { href: "/compras/", label: "Compras", icon: ShoppingCart, roles: ["admin", "warehouse"] },
  { href: "/proveedores/", label: "Proveedores", icon: Truck, roles: ["admin", "warehouse"] },
  { href: "/pendientes/", label: "Pendientes", icon: Inbox, roles: ["admin"] },
  { href: "/tasas/", label: "Tasa BCV", icon: Landmark, roles: ["admin"] },
  { href: "/configuracion/categorias/", label: "Configuración", icon: Settings, roles: ["admin"] },
  { href: "/usuarios/", label: "Usuarios", icon: Users, roles: ["admin"] },
  { href: "/auditoria/", label: "Auditoría", icon: History, roles: ["admin"] },
  { href: "/mi-cuenta/", label: "Mi cuenta", icon: UserCog, roles: ALL_ROLES },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href.replace(/\/$/, ""));
}

function NavLinks({ items, pathname, onNavigate }: { items: NavItem[]; pathname: string; onNavigate?: () => void }) {
  return (
    <ul className="flex flex-col gap-1">
      {items.map(({ href, label, icon: Icon }) => {
        const active = isActive(pathname, href);
        return (
          <li key={href}>
            <Link
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-11 items-center gap-3 rounded-lg px-3 font-medium ${
                active ? "bg-accent text-on-accent" : "text-ink hover:bg-neutral-100"
              }`}
            >
              <Icon aria-hidden className="size-5" />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [outboxOpen, setOutboxOpen] = useState(false);
  const attention = useOutboxAttention();

  // La cola de salida se reintenta mientras la app esté abierta (ADR-0003).
  useEffect(() => {
    if (user && user.role !== "warehouse") startOutbox(user.id);
  }, [user]);

  if (!user) return null;
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  async function onLogout() {
    if (
      (await hasPending()) &&
      !window.confirm(
        "Hay operaciones pendientes de envío en este equipo. Se enviarán cuando alguien vuelva a ingresar. ¿Cerrar sesión de todos modos?",
      )
    ) {
      return;
    }
    await logout();
    router.replace("/ingresar/");
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="bg-primary text-on-primary">
        <div className="flex items-center justify-between gap-3 px-4 py-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex size-11 items-center justify-center rounded-lg hover:bg-primary-hover md:hidden"
              aria-label={menuOpen ? "Cerrar menú" : "Abrir menú"}
              aria-expanded={menuOpen}
              aria-controls="menu-movil"
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? <X aria-hidden className="size-6" /> : <Menu aria-hidden className="size-6" />}
            </button>
            <Link href="/" aria-label="Inicio">
              <img
                src="/marca/logo-horizontal-negativo.svg"
                alt="Suministros Hidráulicos Turmero"
                width={150}
                height={45}
                className="h-auto w-37.5"
              />
            </Link>
          </div>
          <div className="flex items-center gap-3">
            {attention.length > 0 && (
              <button
                type="button"
                onClick={() => setOutboxOpen(true)}
                className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-3 font-semibold text-on-accent"
              >
                <CloudUpload aria-hidden className="size-5" />
                <span className="hidden sm:inline">Pendientes de envío:</span>
                <span className="sr-only sm:hidden">Pendientes de envío:</span> {attention.length}
              </button>
            )}
            <div className="hidden text-right text-sm sm:block">
              <p className="font-semibold">{user.full_name}</p>
              <p className="text-navy-200">{ROLE_LABELS[user.role]}</p>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 font-medium hover:bg-primary-hover"
            >
              <LogOut aria-hidden className="size-5" />
              <span className="hidden sm:inline">Cerrar sesión</span>
              <span className="sr-only sm:hidden">Cerrar sesión</span>
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <nav id="menu-movil" aria-label="Menú principal" className="border-b border-line bg-surface p-2 md:hidden">
          <NavLinks items={items} pathname={pathname} onNavigate={() => setMenuOpen(false)} />
        </nav>
      )}

      <div className="flex flex-1">
        <nav aria-label="Menú principal" className="hidden w-56 shrink-0 border-r border-line bg-surface p-3 md:block">
          <NavLinks items={items} pathname={pathname} />
        </nav>
        <main className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
      </div>

      <Dialog open={outboxOpen} title="Pendientes de envío" onClose={() => setOutboxOpen(false)}>
        {attention.length === 0 ? (
          <p>No hay operaciones pendientes.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {attention.map((record) => (
              <li key={record.id} className="rounded-lg border border-line p-3">
                <p className="font-semibold">{OPERATION_LABELS[record.type] ?? record.type}</p>
                <p className="text-sm text-ink-muted">
                  {new Date(record.createdAt).toLocaleString("es-VE", { timeZone: "America/Caracas" })}
                </p>
                {record.status === "pending" && waitsForOwner(record) ? (
                  <p className="text-sm">Se enviará cuando el usuario que la hizo vuelva a ingresar en este equipo.</p>
                ) : record.status === "pending" ? (
                  <p className="text-sm">Se enviará al haber conexión ({record.attempts} intentos).</p>
                ) : (
                  <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm text-danger">Rechazada: {record.error?.message}</p>
                    <button
                      type="button"
                      className="min-h-11 rounded-lg px-3 text-sm font-medium text-primary hover:bg-neutral-100"
                      onClick={() => void dismissRejected(record.id)}
                    >
                      Quitar de la lista
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Dialog>
    </div>
  );
}

const OPERATION_LABELS: Record<string, string> = {
  "sale.create": "Venta",
  "cash_session.open": "Apertura de caja",
  "cash_outflow.create": "Egreso de caja",
  "cash_session.close": "Cierre de caja",
};
