import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";

// Mensajes de estado: color del estado sobre su fondo suave, siempre con ícono y texto
// (guía de estilos §2.4).
type Variant = "success" | "warning" | "danger" | "info";

const STYLES: Record<Variant, string> = {
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
};

const ICONS = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: Info,
} as const;

export function Alert({ variant, children }: { variant: Variant; children: ReactNode }) {
  const Icon = ICONS[variant];
  const urgent = variant === "danger" || variant === "warning";
  return (
    <div
      role={urgent ? "alert" : "status"}
      className={`flex items-start gap-2 rounded-lg px-3 py-2 ${STYLES[variant]}`}
    >
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}
