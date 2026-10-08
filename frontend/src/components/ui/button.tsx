import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

// Botón base de la guía de estilos: alto mínimo de 44 px para uso táctil.
type Variant = "primary" | "accent" | "secondary" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary text-on-primary hover:bg-primary-hover",
  accent: "bg-accent text-on-accent hover:bg-accent-hover",
  secondary: "border border-line bg-surface text-ink hover:bg-neutral-100",
  danger: "bg-danger text-white hover:opacity-90",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
};

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  className = "",
  children,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {loading && <Loader2 aria-hidden className="size-4 animate-spin" />}
      {children}
    </button>
  );
}
