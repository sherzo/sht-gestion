// Nombres en español de las acciones de la auditoría (RF-46). Los códigos viven en el
// backend (ADR-0006); cada etapa agrega aquí los suyos.

export const AUDIT_ACTION_GROUPS = [
  {
    label: "Instalación",
    actions: {
      "setup.admin_created": "Administrador inicial creado",
      "setup.failed": "Instalación con código incorrecto",
    },
  },
  {
    label: "Sesión",
    actions: {
      "auth.login_succeeded": "Inicio de sesión",
      "auth.login_failed": "Inicio de sesión fallido",
      "auth.login_locked": "Inicio de sesión bloqueado",
      "auth.password_changed": "Cambio de contraseña propia",
      "auth.password_check_failed": "Contraseña actual incorrecta",
    },
  },
  {
    label: "PIN",
    actions: {
      "auth.pin_set": "PIN definido o cambiado",
      "auth.pin_verified": "Autorización con PIN",
      "auth.pin_failed": "PIN incorrecto",
      "auth.pin_locked": "PIN bloqueado",
    },
  },
  {
    label: "Usuarios",
    actions: {
      "user.created": "Usuario creado",
      "user.updated": "Nombre modificado",
      "user.role_changed": "Cambio de rol",
      "user.deactivated": "Usuario desactivado",
      "user.reactivated": "Usuario reactivado",
      "user.password_reset": "Contraseña restablecida",
    },
  },
] as const;

export const AUDIT_ACTION_LABELS: Record<string, string> = Object.fromEntries(
  AUDIT_ACTION_GROUPS.flatMap((group) => Object.entries(group.actions)),
);

export function auditActionLabel(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? action;
}
