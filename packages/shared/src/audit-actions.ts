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
  {
    label: "Productos",
    actions: {
      "product.created": "Producto creado",
      "product.updated": "Producto modificado",
      "product.category_changed": "Cambio de categoría (SKU nuevo)",
      "product.activated": "Producto reactivado",
      "product.deactivated": "Producto desactivado",
      "product.published": "Publicado en el catálogo",
      "product.unpublished": "Retirado del catálogo",
      "product.price_set": "Precio de venta fijado",
      "product.initial_cost_set": "Costo inicial fijado",
      "product.photo_added": "Foto agregada",
      "product.photo_removed": "Foto quitada",
      "product.photos_reordered": "Fotos reordenadas",
    },
  },
  {
    label: "Inventario",
    actions: {
      "inventory.adjustment_applied": "Ajuste de inventario",
      "inventory.adjustment_requested": "Salida solicitada (pendiente)",
      "inventory.adjustment_approved": "Salida aprobada",
      "inventory.adjustment_rejected": "Salida rechazada",
      "inventory.adjustment_withdrawn": "Salida retirada",
      "stock_count.opened": "Conteo abierto",
      "stock_count.ready": "Conteo listo para revisión",
      "stock_count.returned": "Conteo devuelto para recontar",
      "stock_count.applied": "Conteo aplicado",
      "stock_count.cancelled": "Conteo cancelado",
    },
  },
  {
    label: "Compras y tasas",
    actions: {
      "supplier.created": "Proveedor creado",
      "supplier.updated": "Proveedor modificado",
      "purchase.confirmed": "Compra confirmada",
      "purchase.voided": "Compra anulada",
      "product.cost_updated": "Costo actualizado por compra",
      "exchange_rate.created": "Tasa BCV cargada",
      "exchange_rate.corrected": "Tasa BCV corregida",
      "charge_template.created": "Gasto frecuente creado",
      "charge_template.updated": "Gasto frecuente modificado",
      "alert.resolved": "Alerta revisada",
    },
  },
  {
    label: "Configuración",
    actions: {
      "category.created": "Categoría creada",
      "category.updated": "Categoría modificada",
      "attribute.created": "Atributo creado",
      "attribute.updated": "Atributo modificado",
      "unit.created": "Unidad creada",
      "unit.updated": "Unidad modificada",
    },
  },
] as const;

export const AUDIT_ACTION_LABELS: Record<string, string> = Object.fromEntries(
  AUDIT_ACTION_GROUPS.flatMap((group) => Object.entries(group.actions)),
);

export function auditActionLabel(action: string): string {
  return AUDIT_ACTION_LABELS[action] ?? action;
}
