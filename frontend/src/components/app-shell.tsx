"use client";

// Estructura de las pantallas con sesión: barra superior con la marca y menú según el rol
// (RF-44, US2 escenario 5). El menú solo oculta; los permisos los verifica el servidor.
import { ROLE_LABELS } from "@sht/shared";
import type { Role } from "@sht/shared";
import { History, Home, LogOut, Menu, UserCog, Users, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth/use-auth";

type NavItem = { href: string; label: string; icon: LucideIcon; roles: Role[] };

const ALL_ROLES: Role[] = ["admin", "seller", "warehouse"];

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Inicio", icon: Home, roles: ALL_ROLES },
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

  if (!user) return null;
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  async function onLogout() {
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
    </div>
  );
}
