"use client";

// Guardia de rutas de la app. Solo oculta: los permisos los verifica el servidor (RNF-05).
import type { Role } from "@sht/shared";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";

import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth/use-auth";

type RequireAuthProps = {
  children: ReactNode;
  roles?: Role[];
  /** true en /cambiar-clave: se permite con contraseña temporal. */
  allowTemporaryPassword?: boolean;
};

export function RequireAuth({ children, roles, allowTemporaryPassword = false }: RequireAuthProps) {
  const { status, user } = useAuth();
  const router = useRouter();
  const mustChange = Boolean(user?.must_change_password);

  useEffect(() => {
    if (status === "setup_required") router.replace("/instalacion/");
    else if (status === "anonymous") router.replace("/ingresar/");
    else if (status === "authenticated" && mustChange && !allowTemporaryPassword) {
      router.replace("/cambiar-clave/");
    }
  }, [status, mustChange, allowTemporaryPassword, router]);

  if (status !== "authenticated" || !user || (mustChange && !allowTemporaryPassword)) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-ink-muted" role="status">
        <Loader2 aria-hidden className="mr-2 size-5 animate-spin" />
        Cargando…
      </div>
    );
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div className="p-4">
        <Alert variant="danger">No tienes permiso para ver esta sección.</Alert>
      </div>
    );
  }

  return <>{children}</>;
}
