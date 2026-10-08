// Roles del sistema (PRD §4) y sus nombres en la interfaz.

export type Role = "admin" | "seller" | "warehouse";

export const ROLES: readonly Role[] = ["admin", "seller", "warehouse"];

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrador",
  seller: "Vendedor",
  warehouse: "Almacén",
};
