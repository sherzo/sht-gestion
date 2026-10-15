import { AlertTriangle, Ban, CheckCircle2, CircleSlash, Clock, FilePen, Globe, MinusCircle, Undo2, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

// Etiqueta de estado con ícono y texto, nunca solo color (guía de estilos §2.4).
export type StatusChipVariant =
  | "low_stock"
  | "negative_stock"
  | "inactive"
  | "published"
  | "pending"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "draft"
  | "confirmed"
  | "voided"
  | "active"
  | "revoked"
  | "needs_review";

const VARIANTS: Record<StatusChipVariant, { label: string; icon: LucideIcon; className: string }> = {
  low_stock: { label: "Stock bajo", icon: AlertTriangle, className: "bg-warning-soft text-warning" },
  negative_stock: { label: "Stock negativo", icon: MinusCircle, className: "bg-danger-soft text-danger" },
  inactive: { label: "Inactivo", icon: CircleSlash, className: "bg-neutral-100 text-ink-muted" },
  published: { label: "Publicado", icon: Globe, className: "bg-info-soft text-info" },
  pending: { label: "Pendiente", icon: Clock, className: "bg-warning-soft text-warning" },
  approved: { label: "Aprobada", icon: CheckCircle2, className: "bg-success-soft text-success" },
  rejected: { label: "Rechazada", icon: XCircle, className: "bg-danger-soft text-danger" },
  withdrawn: { label: "Retirada", icon: Undo2, className: "bg-neutral-100 text-ink-muted" },
  draft: { label: "Borrador", icon: FilePen, className: "bg-warning-soft text-warning" },
  confirmed: { label: "Confirmada", icon: CheckCircle2, className: "bg-success-soft text-success" },
  voided: { label: "Anulada", icon: Ban, className: "bg-danger-soft text-danger" },
  active: { label: "Vigente", icon: CheckCircle2, className: "bg-success-soft text-success" },
  revoked: { label: "Revocado", icon: Ban, className: "bg-danger-soft text-danger" },
  needs_review: { label: "Para revisar", icon: AlertTriangle, className: "bg-warning-soft text-warning" },
};

export function StatusChip({ variant, label }: { variant: StatusChipVariant; label?: string }) {
  const { label: defaultLabel, icon: Icon, className } = VARIANTS[variant];
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-sm font-medium ${className}`}>
      <Icon aria-hidden className="size-4" />
      {label ?? defaultLabel}
    </span>
  );
}
