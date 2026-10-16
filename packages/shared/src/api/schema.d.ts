/**
 * Tipos de la API generados con `pnpm api:types` desde el OpenAPI de FastAPI.
 * No editar a mano: se regeneran cuando cambia el backend.
 */
export interface paths {
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/db": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Db */
        get: operations["health_db_api_v1_health_db_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/setup/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Setup Status */
        get: operations["setup_status_api_v1_setup_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/setup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Setup */
        post: operations["setup_api_v1_setup_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh */
        post: operations["refresh_api_v1_auth_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Password */
        post: operations["change_password_api_v1_auth_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/pin": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Pin */
        put: operations["set_pin_api_v1_auth_pin_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/pin/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify Pin */
        post: operations["verify_pin_api_v1_auth_pin_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Users */
        get: operations["list_users_api_v1_users_get"];
        put?: never;
        /** Create User */
        post: operations["create_user_api_v1_users_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get User */
        get: operations["get_user_api_v1_users__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update User */
        patch: operations["update_user_api_v1_users__user_id__patch"];
        trace?: never;
    };
    "/api/v1/users/{user_id}/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reset Password */
        post: operations["reset_password_api_v1_users__user_id__password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/audit-log": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Audit */
        get: operations["list_audit_api_v1_audit_log_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/units": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Units */
        get: operations["list_units_api_v1_units_get"];
        put?: never;
        /** Create Unit */
        post: operations["create_unit_api_v1_units_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Categories */
        get: operations["list_categories_api_v1_categories_get"];
        put?: never;
        /** Create Category */
        post: operations["create_category_api_v1_categories_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/units/{unit_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Unit */
        patch: operations["update_unit_api_v1_units__unit_id__patch"];
        trace?: never;
    };
    "/api/v1/categories/{category_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Category */
        patch: operations["update_category_api_v1_categories__category_id__patch"];
        trace?: never;
    };
    "/api/v1/categories/{category_id}/attributes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Attribute */
        post: operations["create_attribute_api_v1_categories__category_id__attributes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/attributes/{attribute_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Attribute */
        patch: operations["update_attribute_api_v1_attributes__attribute_id__patch"];
        trace?: never;
    };
    "/api/v1/products": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Products
         * @description Búsqueda (FR-032, FR-033). Los filtros por atributo llegan como `attr.<clave>=<valor>`
         *     y solo se admiten las claves marcadas como filtrables.
         */
        get: operations["list_products_api_v1_products_get"];
        put?: never;
        /** Create Product */
        post: operations["create_product_api_v1_products_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Product */
        get: operations["get_product_api_v1_products__product_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Product */
        patch: operations["update_product_api_v1_products__product_id__patch"];
        trace?: never;
    };
    "/api/v1/products/{product_id}/photos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Photo */
        post: operations["add_photo_api_v1_products__product_id__photos_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/photos/{photo_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Photo */
        delete: operations["remove_photo_api_v1_products__product_id__photos__photo_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/photos/order": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Reorder Photos */
        put: operations["reorder_photos_api_v1_products__product_id__photos_order_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/movements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Movements
         * @description Kardex del producto para Admin y Almacén; el Vendedor solo ve el stock (FR-022).
         */
        get: operations["list_movements_api_v1_products__product_id__movements_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/price": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Price */
        put: operations["set_price_api_v1_products__product_id__price_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/prices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Prices
         * @description Historial de precios, más reciente primero (FR-012).
         */
        get: operations["list_prices_api_v1_products__product_id__prices_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/initial-cost": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Initial Cost */
        put: operations["set_initial_cost_api_v1_products__product_id__initial_cost_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/products/{product_id}/publication": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Publication */
        put: operations["set_publication_api_v1_products__product_id__publication_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/adjustments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register Adjustment */
        post: operations["register_adjustment_api_v1_inventory_adjustments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/adjustment-requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Adjustment Requests */
        get: operations["list_adjustment_requests_api_v1_inventory_adjustment_requests_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/adjustment-requests/{request_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Request */
        post: operations["approve_request_api_v1_inventory_adjustment_requests__request_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/adjustment-requests/{request_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject Request */
        post: operations["reject_request_api_v1_inventory_adjustment_requests__request_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/adjustment-requests/{request_id}/withdraw": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Withdraw Request */
        post: operations["withdraw_request_api_v1_inventory_adjustment_requests__request_id__withdraw_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/low-stock": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Low Stock
         * @description Productos activos con stock menor o igual al mínimo, por categoría (RF-11/FR-023).
         */
        get: operations["low_stock_api_v1_inventory_low_stock_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/inventory/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Summary
         * @description Contadores de las tarjetas del inicio (research R11).
         */
        get: operations["summary_api_v1_inventory_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Counts */
        get: operations["list_counts_api_v1_stock_counts_get"];
        put?: never;
        /** Open Count */
        post: operations["open_count_api_v1_stock_counts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts/{count_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Count */
        get: operations["get_count_api_v1_stock_counts__count_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts/{count_id}/lines/{line_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Record Line */
        put: operations["record_line_api_v1_stock_counts__count_id__lines__line_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts/{count_id}/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark Ready */
        post: operations["mark_ready_api_v1_stock_counts__count_id__ready_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts/{count_id}/reopen": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reopen */
        post: operations["reopen_api_v1_stock_counts__count_id__reopen_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts/{count_id}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply Count */
        post: operations["apply_count_api_v1_stock_counts__count_id__apply_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/stock-counts/{count_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Count */
        post: operations["cancel_count_api_v1_stock_counts__count_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/suppliers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Suppliers */
        get: operations["list_suppliers_api_v1_suppliers_get"];
        put?: never;
        /** Create Supplier */
        post: operations["create_supplier_api_v1_suppliers_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/suppliers/{supplier_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Supplier */
        get: operations["get_supplier_api_v1_suppliers__supplier_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Supplier */
        patch: operations["update_supplier_api_v1_suppliers__supplier_id__patch"];
        trace?: never;
    };
    "/api/v1/purchases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Purchases */
        get: operations["list_purchases_api_v1_purchases_get"];
        put?: never;
        /** Create Purchase */
        post: operations["create_purchase_api_v1_purchases_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/purchases/{purchase_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Purchase */
        get: operations["get_purchase_api_v1_purchases__purchase_id__get"];
        /** Save Purchase */
        put: operations["save_purchase_api_v1_purchases__purchase_id__put"];
        post?: never;
        /** Discard Purchase */
        delete: operations["discard_purchase_api_v1_purchases__purchase_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/purchases/{purchase_id}/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Purchase */
        post: operations["confirm_purchase_api_v1_purchases__purchase_id__confirm_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/purchases/{purchase_id}/void-preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Void Preview */
        get: operations["void_preview_api_v1_purchases__purchase_id__void_preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/purchases/{purchase_id}/void": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Void Purchase */
        post: operations["void_purchase_api_v1_purchases__purchase_id__void_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/exchange-rates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Rates */
        get: operations["list_rates_api_v1_exchange_rates_get"];
        put?: never;
        /** Create Rate */
        post: operations["create_rate_api_v1_exchange_rates_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/exchange-rates/applicable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Applicable Rate
         * @description La tasa que usaría una compra o una venta con esa fecha (FR-012 de la 1.2; RF-18,
         *     FR-007 y FR-014 de la 1.3: el Vendedor la consulta al abrir caja y al vender).
         */
        get: operations["applicable_rate_api_v1_exchange_rates_applicable_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/exchange-rates/{business_date}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Correct Rate */
        put: operations["correct_rate_api_v1_exchange_rates__business_date__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/charge-templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Templates
         * @description Activos; con `include_inactive` también los inactivos, solo para el Admin.
         */
        get: operations["list_templates_api_v1_charge_templates_get"];
        put?: never;
        /** Create Template */
        post: operations["create_template_api_v1_charge_templates_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/charge-templates/{template_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Template */
        patch: operations["update_template_api_v1_charge_templates__template_id__patch"];
        trace?: never;
    };
    "/api/v1/alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Alerts */
        get: operations["list_alerts_api_v1_alerts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/alerts/{alert_id}/resolve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resolve Alert */
        post: operations["resolve_alert_api_v1_alerts__alert_id__resolve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/devices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Devices */
        get: operations["list_devices_api_v1_devices_get"];
        put?: never;
        /** Register Device */
        post: operations["register_device_api_v1_devices_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/devices/{device_id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke Device */
        post: operations["revoke_device_api_v1_devices__device_id__revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/devices/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Current Device
         * @description El equipo del token, con su caja abierta y el último correlativo registrado.
         */
        get: operations["current_device_api_v1_devices_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/customers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Customers
         * @description Por documento (exacto) o por nombre (contiene, sin acentos); como máximo 20.
         */
        get: operations["search_customers_api_v1_customers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/discount-authorizations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Pending
         * @description Solicitudes por decidir, más antiguas primero.
         */
        get: operations["list_pending_api_v1_discount_authorizations_get"];
        put?: never;
        /** Request Authorization */
        post: operations["request_authorization_api_v1_discount_authorizations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/discount-authorizations/{authorization_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Authorization */
        get: operations["get_authorization_api_v1_discount_authorizations__authorization_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/discount-authorizations/{authorization_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve */
        post: operations["approve_api_v1_discount_authorizations__authorization_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/discount-authorizations/{authorization_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject */
        post: operations["reject_api_v1_discount_authorizations__authorization_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sales": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Sales
         * @description Más recientes primero. El Vendedor siempre recibe solo sus ventas de hoy: los
         *     filtros de fecha y vendedor se ignoran (FR-046).
         */
        get: operations["list_sales_api_v1_sales_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sales/{sale_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Sale */
        get: operations["get_sale_api_v1_sales__sale_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sales/{sale_id}/void": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Void Sale
         * @description Si la caja de la venta ya está cerrada, la devolución va a la caja abierta del
         *     equipo de `X-Device-Token` (RF-27, PRD v0.11); sin él, 409 `cash_session_required`.
         */
        post: operations["void_sale_api_v1_sales__sale_id__void_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/cash-sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Cash Sessions
         * @description Más recientes primero. El Vendedor recibe solo la caja abierta del equipo desde el
         *     que consulta y las cajas que él cerró hoy: los filtros se ignoran (FR-025).
         */
        get: operations["list_cash_sessions_api_v1_cash_sessions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/cash-sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cash Session */
        get: operations["get_cash_session_api_v1_cash_sessions__session_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/cash-sessions/{session_id}/close": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Close Cash Session
         * @description Cierre de una caja de otro equipo, vigente o revocado (caja huérfana, FR-018). La
         *     observación es obligatoria y el cierre queda marcado como hecho fuera del equipo.
         */
        post: operations["close_cash_session_api_v1_cash_sessions__session_id__close_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/cash-outflows/{outflow_id}/void": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Void Outflow */
        post: operations["void_outflow_api_v1_cash_outflows__outflow_id__void_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sync/operations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Post Operation
         * @description Procesa una operación del mostrador. 200 con el resultado; los rechazos
         *     permanentes (403 `device_revoked`, 409, 422) llevan el formato de error común.
         */
        post: operations["post_operation_api_v1_sync_operations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AdjustmentRequestBody */
        AdjustmentRequestBody: {
            /**
             * Product Id
             * Format: uuid
             */
            product_id: string;
            /** Quantity Delta */
            quantity_delta: number | string;
            /**
             * Reason
             * @enum {string}
             */
            reason: "physical_count" | "damage" | "loss" | "correction";
            /** Note */
            note?: string | null;
        };
        /** AdjustmentRequestOut */
        AdjustmentRequestOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            product: components["schemas"]["RequestProduct"];
            /** Quantity Delta */
            quantity_delta: string;
            /** Adjustment Reason */
            adjustment_reason: string;
            /** Note */
            note: string | null;
            /** Status */
            status: string;
            requested_by: components["schemas"]["UserRef"];
            /**
             * Requested At
             * Format: date-time
             */
            requested_at: string;
            decided_by: components["schemas"]["UserRef"] | null;
            /** Decided At */
            decided_at: string | null;
            /** Rejection Reason */
            rejection_reason: string | null;
            /** Stock Movement Id */
            stock_movement_id: string | null;
        };
        /** AdjustmentRequestPage */
        AdjustmentRequestPage: {
            /** Items */
            items: components["schemas"]["AdjustmentRequestOut"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** AdjustmentResultOut */
        AdjustmentResultOut: {
            /**
             * Status
             * @enum {string}
             */
            status: "applied" | "pending";
            /** Movement */
            movement?: components["schemas"]["StockMovementAdmin"] | components["schemas"]["StockMovementWarehouse"] | null;
            request?: components["schemas"]["AdjustmentRequestOut"] | null;
        };
        /** AdminCloseIn */
        AdminCloseIn: {
            /** Counts */
            counts: components["schemas"]["AdminCountIn"][];
            /** Note */
            note: string;
        };
        /** AdminCountIn */
        AdminCountIn: {
            /** Method */
            method: string;
            /** Counted */
            counted: number | string;
        };
        /** AdminSummary */
        AdminSummary: {
            /** Low Stock */
            low_stock: number;
            /** Pending Adjustments */
            pending_adjustments: number;
            /** Counts Ready For Review */
            counts_ready_for_review: number;
            /** Open Alerts */
            open_alerts: number;
            /** Draft Purchases */
            draft_purchases: number;
            /** Pending Discount Requests */
            pending_discount_requests: number;
        };
        /** AlertOut */
        AlertOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Type */
            type: string;
            /** Entity Type */
            entity_type: string;
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /** Details */
            details: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Resolved At */
            resolved_at: string | null;
            resolved_by: components["schemas"]["UserRef"] | null;
            sale?: components["schemas"]["SaleRef"] | null;
            cash_session?: components["schemas"]["CashSessionAlertRef"] | null;
        };
        /** AlertPage */
        AlertPage: {
            /** Items */
            items: components["schemas"]["AlertOut"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** ApplicableRateOut */
        ApplicableRateOut: {
            /** Rate */
            rate: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
        };
        /** ApplyRequest */
        ApplyRequest: {
            /**
             * Acknowledge Uncounted
             * @default false
             */
            acknowledge_uncounted: boolean;
        };
        /** ApplyResult */
        ApplyResult: {
            count: components["schemas"]["StockCountAdmin"];
            /** Adjustments */
            adjustments: number;
            /** Negative Products */
            negative_products: components["schemas"]["NegativeProduct"][];
        };
        /** ApproveIn */
        ApproveIn: {
            /** Discount Value */
            discount_value?: number | string | null;
        };
        /** AttributeOption */
        AttributeOption: {
            /** Value */
            value: string;
            /** Is Active */
            is_active: boolean;
        };
        /** AttributeOut */
        AttributeOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Data Type */
            data_type: string;
            /** Options */
            options: components["schemas"]["AttributeOption"][];
            /** Is Required */
            is_required: boolean;
            /** Is Filterable */
            is_filterable: boolean;
            /** Sort Order */
            sort_order: number;
            /** Is Active */
            is_active: boolean;
        };
        /** AuditEntry */
        AuditEntry: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            user: components["schemas"]["AuditUser"] | null;
            /** Action */
            action: string;
            /** Entity Type */
            entity_type: string | null;
            /** Entity Id */
            entity_id: string | null;
            /** Before */
            before: {
                [key: string]: unknown;
            } | null;
            /** After */
            after: {
                [key: string]: unknown;
            } | null;
            /** Reason */
            reason: string | null;
            /** Details */
            details: {
                [key: string]: unknown;
            } | null;
        };
        /** AuditPage */
        AuditPage: {
            /** Items */
            items: components["schemas"]["AuditEntry"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** AuditUser */
        AuditUser: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Username */
            username: string;
            /** Full Name */
            full_name: string;
        };
        /** AuthorizationDevice */
        AuthorizationDevice: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** AuthorizationIn */
        AuthorizationIn: {
            /**
             * Method
             * @enum {string}
             */
            method: "pin" | "request";
            /** Admin Username */
            admin_username?: string | null;
            /** Pin */
            pin?: string | null;
            /**
             * Sale Id
             * Format: uuid
             */
            sale_id: string;
            /** Sale Item Id */
            sale_item_id?: string | null;
            /** Product Id */
            product_id?: string | null;
            /**
             * Discount Type
             * @enum {string}
             */
            discount_type: "amount" | "percent";
            /** Discount Value */
            discount_value: number | string;
            /** Base Usd */
            base_usd: number | string;
        };
        /** AuthorizationProduct */
        AuthorizationProduct: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
        };
        /** Authorizer */
        Authorizer: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Full Name */
            full_name: string;
        };
        /** Body_add_photo_api_v1_products__product_id__photos_post */
        Body_add_photo_api_v1_products__product_id__photos_post: {
            /** File */
            file: string;
        };
        /** CancelRequest */
        CancelRequest: {
            /** Reason */
            reason: string;
        };
        /** CashMovementOut */
        CashMovementOut: {
            sale: components["schemas"]["SaleRefOut"];
            /** Kind */
            kind: string;
            /** Method */
            method: string;
            /** Currency */
            currency: string;
            /** Amount */
            amount: string;
            /** Reference */
            reference: string | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** After Close */
            after_close: boolean;
        };
        /** CashOutflowOut */
        CashOutflowOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Cash Session Id
             * Format: uuid
             */
            cash_session_id: string;
            /** Method */
            method: string;
            /** Currency */
            currency: string;
            /** Amount */
            amount: string;
            /** Reason */
            reason: string;
            /** Reference */
            reference: string | null;
            created_by: components["schemas"]["UserRef"];
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            void: components["schemas"]["OutflowVoidOut"] | null;
        };
        /** CashSessionAlertRef */
        CashSessionAlertRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Device Name */
            device_name: string;
        };
        /**
         * CashSessionClosed
         * @description Respuesta del cierre: el detalle de la caja cerrada y las alertas creadas.
         */
        CashSessionClosed: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            device: components["schemas"]["DeviceBrief"];
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /** Status */
            status: string;
            opened_by: components["schemas"]["UserRef"];
            /**
             * Opened At
             * Format: date-time
             */
            opened_at: string;
            closed_by: components["schemas"]["UserRef"] | null;
            /** Closed At */
            closed_at: string | null;
            /** Closed Outside Device */
            closed_outside_device: boolean | null;
            /** Has Differences */
            has_differences: boolean;
            /** Opened On Previous Day */
            opened_on_previous_day: boolean;
            /** Opening Float Ves */
            opening_float_ves: string;
            /** Opening Float Usd */
            opening_float_usd: string;
            closed_from_device: components["schemas"]["DeviceName"] | null;
            /** Closing Note */
            closing_note: string | null;
            /** Reconciliation */
            reconciliation: components["schemas"]["ReconciliationRowOut"][];
            /** Movements */
            movements: components["schemas"]["CashMovementOut"][];
            /** Outflows */
            outflows: components["schemas"]["CashOutflowOut"][];
            /** Voided After Close */
            voided_after_close: components["schemas"]["VoidedAfterCloseOut"][];
            /** Post Close Operations */
            post_close_operations: components["schemas"]["PostCloseOperationOut"][];
            /** Alerts Created */
            alerts_created: string[];
        };
        /** CashSessionDetail */
        CashSessionDetail: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            device: components["schemas"]["DeviceBrief"];
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /** Status */
            status: string;
            opened_by: components["schemas"]["UserRef"];
            /**
             * Opened At
             * Format: date-time
             */
            opened_at: string;
            closed_by: components["schemas"]["UserRef"] | null;
            /** Closed At */
            closed_at: string | null;
            /** Closed Outside Device */
            closed_outside_device: boolean | null;
            /** Has Differences */
            has_differences: boolean;
            /** Opened On Previous Day */
            opened_on_previous_day: boolean;
            /** Opening Float Ves */
            opening_float_ves: string;
            /** Opening Float Usd */
            opening_float_usd: string;
            closed_from_device: components["schemas"]["DeviceName"] | null;
            /** Closing Note */
            closing_note: string | null;
            /** Reconciliation */
            reconciliation: components["schemas"]["ReconciliationRowOut"][];
            /** Movements */
            movements: components["schemas"]["CashMovementOut"][];
            /** Outflows */
            outflows: components["schemas"]["CashOutflowOut"][];
            /** Voided After Close */
            voided_after_close: components["schemas"]["VoidedAfterCloseOut"][];
            /** Post Close Operations */
            post_close_operations: components["schemas"]["PostCloseOperationOut"][];
        };
        /** CashSessionOut */
        CashSessionOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Device Id
             * Format: uuid
             */
            device_id: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            opened_by: components["schemas"]["UserRef"];
            /**
             * Opened At
             * Format: date-time
             */
            opened_at: string;
            /** Opening Float Ves */
            opening_float_ves: string;
            /** Opening Float Usd */
            opening_float_usd: string;
            /** Status */
            status: string;
        };
        /** CashSessionPage */
        CashSessionPage: {
            /** Items */
            items: components["schemas"]["CashSessionSummary"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** CashSessionSummary */
        CashSessionSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            device: components["schemas"]["DeviceBrief"];
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /** Status */
            status: string;
            opened_by: components["schemas"]["UserRef"];
            /**
             * Opened At
             * Format: date-time
             */
            opened_at: string;
            closed_by: components["schemas"]["UserRef"] | null;
            /** Closed At */
            closed_at: string | null;
            /** Closed Outside Device */
            closed_outside_device: boolean | null;
            /** Has Differences */
            has_differences: boolean;
            /** Opened On Previous Day */
            opened_on_previous_day: boolean;
        };
        /** CategoryOut */
        CategoryOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Sku Prefix */
            sku_prefix: string;
            /**
             * Default Unit Id
             * Format: uuid
             */
            default_unit_id: string;
            /** Unit Locked */
            unit_locked: boolean;
            /** Is Active */
            is_active: boolean;
            /** Has Products */
            has_products: boolean;
            /** Attributes */
            attributes: components["schemas"]["AttributeOut"][];
        };
        /** CategoryRef */
        CategoryRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Sku Prefix */
            sku_prefix: string;
        };
        /** ChangePasswordRequest */
        ChangePasswordRequest: {
            /** Current Password */
            current_password: string;
            /** New Password */
            new_password: string;
        };
        /** ChargeTemplateOut */
        ChargeTemplateOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Charge Type */
            charge_type: string;
            /** Default Value */
            default_value: string | null;
            /** Currency */
            currency: string | null;
            /** Is Active */
            is_active: boolean;
        };
        /** ConfirmInput */
        ConfirmInput: {
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** CostChangeOut */
        CostChangeOut: {
            /**
             * Product Id
             * Format: uuid
             */
            product_id: string;
            /** Sku */
            sku: string;
            /** Cost Before Usd */
            cost_before_usd: string | null;
            /** Cost After Usd */
            cost_after_usd: string | null;
        };
        /** CreateAttributeRequest */
        CreateAttributeRequest: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * Data Type
             * @enum {string}
             */
            data_type: "text" | "number" | "option";
            /** Options */
            options?: components["schemas"]["AttributeOption"][] | null;
            /**
             * Is Required
             * @default false
             */
            is_required: boolean;
            /**
             * Is Filterable
             * @default false
             */
            is_filterable: boolean;
            /**
             * Sort Order
             * @default 0
             */
            sort_order: number;
        };
        /** CreateCategoryRequest */
        CreateCategoryRequest: {
            /** Name */
            name: string;
            /** Sku Prefix */
            sku_prefix: string;
            /**
             * Default Unit Id
             * Format: uuid
             */
            default_unit_id: string;
            /**
             * Unit Locked
             * @default false
             */
            unit_locked: boolean;
        };
        /** CreateProductRequest */
        CreateProductRequest: {
            /**
             * Category Id
             * Format: uuid
             */
            category_id: string;
            /** Unit Id */
            unit_id?: string | null;
            /** Name */
            name: string;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Attributes
             * @default {}
             */
            attributes: {
                [key: string]: string | number | null;
            };
            /**
             * Min Stock
             * @default 0
             */
            min_stock: number | string;
        };
        /** CreateUnitRequest */
        CreateUnitRequest: {
            /** Code */
            code: string;
            /** Name */
            name: string;
            /**
             * Decimals
             * @enum {integer}
             */
            decimals: 0 | 2;
        };
        /** CreateUserRequest */
        CreateUserRequest: {
            /** Full Name */
            full_name: string;
            /** Username */
            username: string;
            /**
             * Role
             * @enum {string}
             */
            role: "admin" | "seller" | "warehouse";
            /** Password */
            password: string;
        };
        /** CustomerOut */
        CustomerOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Document Id */
            document_id: string | null;
            /** Phone */
            phone: string | null;
        };
        /** DeviceBrief */
        DeviceBrief: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Series */
            series: string;
        };
        /** DeviceCreate */
        DeviceCreate: {
            /** Name */
            name: string;
        };
        /** DeviceName */
        DeviceName: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** DeviceOut */
        DeviceOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Series */
            series: string;
            /** Last Sequence Number */
            last_sequence_number: number;
            registered_by: components["schemas"]["UserRef"];
            /**
             * Registered At
             * Format: date-time
             */
            registered_at: string;
            /** Revoked At */
            revoked_at: string | null;
            open_cash_session: components["schemas"]["OpenCashSessionRef"] | null;
        };
        /** DeviceRef */
        DeviceRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Series */
            series: string;
        };
        /**
         * DeviceRegistered
         * @description Respuesta del registro: única vez que se entrega el token (research R3).
         */
        DeviceRegistered: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Series */
            series: string;
            /** Last Sequence Number */
            last_sequence_number: number;
            registered_by: components["schemas"]["UserRef"];
            /**
             * Registered At
             * Format: date-time
             */
            registered_at: string;
            /** Revoked At */
            revoked_at: string | null;
            open_cash_session: components["schemas"]["OpenCashSessionRef"] | null;
            /** Token */
            token: string;
        };
        /** DiscountAuthorizationOut */
        DiscountAuthorizationOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Sale Id
             * Format: uuid
             */
            sale_id: string;
            /** Sale Item Id */
            sale_item_id: string | null;
            product: components["schemas"]["AuthorizationProduct"] | null;
            /** Discount Type */
            discount_type: string;
            /** Requested Value */
            requested_value: string;
            /** Discount Value */
            discount_value: string;
            /** Base Usd */
            base_usd: string;
            /** Discount Usd */
            discount_usd: string;
            /** Method */
            method: string;
            /** Status */
            status: string;
            requested_by: components["schemas"]["UserRef"];
            /**
             * Requested At
             * Format: date-time
             */
            requested_at: string;
            device: components["schemas"]["AuthorizationDevice"];
            decided_by: components["schemas"]["UserRef"] | null;
            /** Decided At */
            decided_at: string | null;
            /** Rejection Reason */
            rejection_reason: string | null;
        };
        /** DiscountOut */
        DiscountOut: {
            /** Type */
            type: string;
            /** Value */
            value: string;
            /** Amount Usd */
            amount_usd: string;
            authorized_by: components["schemas"]["UserRef"] | null;
            /** Method */
            method: string | null;
        };
        /** ExchangeRateOut */
        ExchangeRateOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Rate Type */
            rate_type: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /** Rate */
            rate: string;
            created_by: components["schemas"]["UserRef"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            updated_by: components["schemas"]["UserRef"] | null;
            /** Updated At */
            updated_at: string | null;
        };
        /** ExchangeRatePage */
        ExchangeRatePage: {
            /** Items */
            items: components["schemas"]["ExchangeRateOut"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** InitialCostRequest */
        InitialCostRequest: {
            /** Avg Cost Usd */
            avg_cost_usd: number | string;
        };
        /** LineProduct */
        LineProduct: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            unit: components["schemas"]["LineUnit"];
        };
        /** LineUnit */
        LineUnit: {
            /** Code */
            code: string;
            /** Decimals */
            decimals: number;
        };
        /** LoginRequest */
        LoginRequest: {
            /** Username */
            username: string;
            /** Password */
            password: string;
        };
        /** MeResponse */
        MeResponse: {
            user: components["schemas"]["SessionUser"];
            /**
             * Session Expires At
             * Format: date-time
             */
            session_expires_at: string;
        };
        /** MovementPage */
        MovementPage: {
            /** Items */
            items: (components["schemas"]["StockMovementAdmin"] | components["schemas"]["StockMovementWarehouse"])[];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /**
         * MovementPurchaseRef
         * @description Compra de la que viene una entrada o un reverso, para enlazarla (FR-021).
         */
        MovementPurchaseRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string | null;
        };
        /**
         * MovementSaleRef
         * @description Venta de la que viene una salida o su reverso por anulación (FR-048 de la 1.3).
         */
        MovementSaleRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string;
        };
        /** NegativeProduct */
        NegativeProduct: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
        };
        /** OpenCashSessionRef */
        OpenCashSessionRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            opened_by: components["schemas"]["UserRef"];
            /**
             * Opened At
             * Format: date-time
             */
            opened_at: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /** Opening Float Ves */
            opening_float_ves: string;
            /** Opening Float Usd */
            opening_float_usd: string;
            /** Opened On Previous Day */
            opened_on_previous_day: boolean;
        };
        /** OpenCountRequest */
        OpenCountRequest: {
            scope: components["schemas"]["Scope"];
            /** Notes */
            notes?: string | null;
        };
        /** OutboxOperationIn */
        OutboxOperationIn: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Operation Type */
            operation_type: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
        };
        /** OutflowVoidIn */
        OutflowVoidIn: {
            /** Reason */
            reason: string;
        };
        /** OutflowVoidOut */
        OutflowVoidOut: {
            /** Reason */
            reason: string;
            voided_by: components["schemas"]["UserRef"];
            /**
             * Voided At
             * Format: date-time
             */
            voided_at: string;
        };
        /** PaymentOut */
        PaymentOut: {
            /** Kind */
            kind: string;
            /** Method */
            method: string;
            /** Currency */
            currency: string;
            /** Amount */
            amount: string;
            /** Amount Usd */
            amount_usd: string;
            /** Reference */
            reference: string | null;
        };
        /** PhotoOut */
        PhotoOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Url */
            url: string;
            /** Sort Order */
            sort_order: number;
            /** Width */
            width: number;
            /** Height */
            height: number;
        };
        /** PostCloseOperationOut */
        PostCloseOperationOut: {
            /** Type */
            type: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number?: string | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Method */
            method?: string | null;
            /** Amount */
            amount?: string | null;
        };
        /** PriceOut */
        PriceOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Price Usd */
            price_usd: string;
            /**
             * Valid From
             * Format: date-time
             */
            valid_from: string;
            set_by: components["schemas"]["UserRef"] | null;
        };
        /** PriceRequest */
        PriceRequest: {
            /** Sale Price Usd */
            sale_price_usd: number | string;
        };
        /** ProductAdmin */
        ProductAdmin: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            /** Description */
            description: string;
            category: components["schemas"]["CategoryRef"];
            unit: components["schemas"]["UnitRef"];
            /** Attributes */
            attributes: {
                [key: string]: string;
            };
            /** Stock */
            stock: string;
            /** Min Stock */
            min_stock: string;
            /** Is Low Stock */
            is_low_stock: boolean;
            /** Is Active */
            is_active: boolean;
            /** Is Published */
            is_published: boolean;
            /** Has Movements */
            has_movements: boolean;
            /** Photos */
            photos: components["schemas"]["PhotoOut"][];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Warnings
             * @default []
             */
            warnings: string[];
            /** Sale Price Usd */
            sale_price_usd: string | null;
            /** Avg Cost Usd */
            avg_cost_usd: string | null;
            /** Cost Locked */
            cost_locked: boolean;
        };
        /** ProductPage */
        ProductPage: {
            /** Items */
            items: (components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"])[];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** ProductRefOut */
        ProductRefOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            /** Unit Code */
            unit_code: string;
            /** Unit Decimals */
            unit_decimals: number;
        };
        /** ProductSeller */
        ProductSeller: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            /** Description */
            description: string;
            category: components["schemas"]["CategoryRef"];
            unit: components["schemas"]["UnitRef"];
            /** Attributes */
            attributes: {
                [key: string]: string;
            };
            /** Stock */
            stock: string;
            /** Min Stock */
            min_stock: string;
            /** Is Low Stock */
            is_low_stock: boolean;
            /** Is Active */
            is_active: boolean;
            /** Is Published */
            is_published: boolean;
            /** Has Movements */
            has_movements: boolean;
            /** Photos */
            photos: components["schemas"]["PhotoOut"][];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Warnings
             * @default []
             */
            warnings: string[];
            /** Sale Price Usd */
            sale_price_usd: string | null;
        };
        /** ProductWarehouse */
        ProductWarehouse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            /** Description */
            description: string;
            category: components["schemas"]["CategoryRef"];
            unit: components["schemas"]["UnitRef"];
            /** Attributes */
            attributes: {
                [key: string]: string;
            };
            /** Stock */
            stock: string;
            /** Min Stock */
            min_stock: string;
            /** Is Low Stock */
            is_low_stock: boolean;
            /** Is Active */
            is_active: boolean;
            /** Is Published */
            is_published: boolean;
            /** Has Movements */
            has_movements: boolean;
            /** Photos */
            photos: components["schemas"]["PhotoOut"][];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Warnings
             * @default []
             */
            warnings: string[];
        };
        /** PublicationRequest */
        PublicationRequest: {
            /** Is Published */
            is_published: boolean;
        };
        /** PurchaseChargeInput */
        PurchaseChargeInput: {
            /** Description */
            description: string;
            /**
             * Charge Type
             * @enum {string}
             */
            charge_type: "percent" | "fixed";
            /** Percent */
            percent?: number | string | null;
            /** Amount */
            amount?: number | string | null;
            /** Currency */
            currency?: ("USD" | "VES") | null;
            /** Charge Template Id */
            charge_template_id?: string | null;
        };
        /** PurchaseChargeOut */
        PurchaseChargeOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Line Number */
            line_number: number;
            /** Description */
            description: string;
            /** Charge Type */
            charge_type: string;
            /** Percent */
            percent: string | null;
            /** Amount */
            amount: string | null;
            /** Currency */
            currency: string | null;
            /** Amount Usd */
            amount_usd: string;
            /** Allocation Method */
            allocation_method: string;
            /** Charge Template Id */
            charge_template_id: string | null;
        };
        /**
         * PurchaseConfirmedAdmin
         * @description Respuesta de confirmar para el Admin: el costo promedio antes y después (R7).
         */
        PurchaseConfirmedAdmin: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string | null;
            /** Status */
            status: string;
            supplier: components["schemas"]["SupplierRef"];
            /**
             * Purchase Date
             * Format: date
             */
            purchase_date: string;
            /** Supplier Invoice Number */
            supplier_invoice_number: string | null;
            /** Currency */
            currency: string;
            /** Exchange Rate */
            exchange_rate: string | null;
            /** Exchange Rate Date */
            exchange_rate_date: string | null;
            /** Notes */
            notes: string | null;
            /** Items */
            items: components["schemas"]["PurchaseItemOut"][];
            /** Charges */
            charges: components["schemas"]["PurchaseChargeOut"][];
            /** Merchandise Total Usd */
            merchandise_total_usd: string;
            /** Merchandise Total Ves */
            merchandise_total_ves: string | null;
            /** Charges Total Usd */
            charges_total_usd: string;
            /** Total Usd */
            total_usd: string;
            created_by: components["schemas"]["UserRef"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            confirmed_by: components["schemas"]["UserRef"] | null;
            /** Confirmed At */
            confirmed_at: string | null;
            void: components["schemas"]["PurchaseVoidOut"] | null;
            /**
             * Warnings
             * @default []
             */
            warnings: components["schemas"]["PurchaseWarning"][];
            /** Cost Changes */
            cost_changes: components["schemas"]["CostChangeOut"][];
        };
        /** PurchaseInput */
        PurchaseInput: {
            /**
             * Supplier Id
             * Format: uuid
             */
            supplier_id: string;
            /**
             * Purchase Date
             * Format: date
             */
            purchase_date: string;
            /**
             * Currency
             * @enum {string}
             */
            currency: "USD" | "VES";
            /** Supplier Invoice Number */
            supplier_invoice_number?: string | null;
            /** Notes */
            notes?: string | null;
            /** Items */
            items: components["schemas"]["PurchaseItemInput"][];
            /**
             * Charges
             * @default []
             */
            charges: components["schemas"]["PurchaseChargeInput"][];
            /** Updated At */
            updated_at?: string | null;
        };
        /** PurchaseItemInput */
        PurchaseItemInput: {
            /**
             * Product Id
             * Format: uuid
             */
            product_id: string;
            /** Quantity */
            quantity: number | string;
            /** Unit Cost */
            unit_cost: number | string;
        };
        /** PurchaseItemOut */
        PurchaseItemOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Line Number */
            line_number: number;
            product: components["schemas"]["PurchaseProductRef"];
            /** Quantity */
            quantity: string;
            /** Unit Cost Ves */
            unit_cost_ves: string | null;
            /** Unit Cost Usd */
            unit_cost_usd: string;
            /** Line Total Ves */
            line_total_ves: string | null;
            /** Line Total Usd */
            line_total_usd: string;
            /** Allocated Charges Usd */
            allocated_charges_usd: string;
            /** Landed Unit Cost Usd */
            landed_unit_cost_usd: string;
        };
        /** PurchaseOut */
        PurchaseOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string | null;
            /** Status */
            status: string;
            supplier: components["schemas"]["SupplierRef"];
            /**
             * Purchase Date
             * Format: date
             */
            purchase_date: string;
            /** Supplier Invoice Number */
            supplier_invoice_number: string | null;
            /** Currency */
            currency: string;
            /** Exchange Rate */
            exchange_rate: string | null;
            /** Exchange Rate Date */
            exchange_rate_date: string | null;
            /** Notes */
            notes: string | null;
            /** Items */
            items: components["schemas"]["PurchaseItemOut"][];
            /** Charges */
            charges: components["schemas"]["PurchaseChargeOut"][];
            /** Merchandise Total Usd */
            merchandise_total_usd: string;
            /** Merchandise Total Ves */
            merchandise_total_ves: string | null;
            /** Charges Total Usd */
            charges_total_usd: string;
            /** Total Usd */
            total_usd: string;
            created_by: components["schemas"]["UserRef"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            confirmed_by: components["schemas"]["UserRef"] | null;
            /** Confirmed At */
            confirmed_at: string | null;
            void: components["schemas"]["PurchaseVoidOut"] | null;
            /**
             * Warnings
             * @default []
             */
            warnings: components["schemas"]["PurchaseWarning"][];
        };
        /** PurchasePage */
        PurchasePage: {
            /** Items */
            items: components["schemas"]["PurchaseSummary"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** PurchaseProductRef */
        PurchaseProductRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            unit: components["schemas"]["UnitRef"];
        };
        /** PurchaseSummary */
        PurchaseSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string | null;
            /** Status */
            status: string;
            /**
             * Purchase Date
             * Format: date
             */
            purchase_date: string;
            supplier: components["schemas"]["SupplierRef"];
            /** Supplier Invoice Number */
            supplier_invoice_number: string | null;
            /** Currency */
            currency: string;
            /** Total Usd */
            total_usd: string;
            /** Items Count */
            items_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** PurchaseVoidOut */
        PurchaseVoidOut: {
            /** Reason */
            reason: string;
            voided_by: components["schemas"]["UserRef"] | null;
            /**
             * Voided At
             * Format: date-time
             */
            voided_at: string;
        };
        /** PurchaseVoidedOut */
        PurchaseVoidedOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string | null;
            /** Status */
            status: string;
            supplier: components["schemas"]["SupplierRef"];
            /**
             * Purchase Date
             * Format: date
             */
            purchase_date: string;
            /** Supplier Invoice Number */
            supplier_invoice_number: string | null;
            /** Currency */
            currency: string;
            /** Exchange Rate */
            exchange_rate: string | null;
            /** Exchange Rate Date */
            exchange_rate_date: string | null;
            /** Notes */
            notes: string | null;
            /** Items */
            items: components["schemas"]["PurchaseItemOut"][];
            /** Charges */
            charges: components["schemas"]["PurchaseChargeOut"][];
            /** Merchandise Total Usd */
            merchandise_total_usd: string;
            /** Merchandise Total Ves */
            merchandise_total_ves: string | null;
            /** Charges Total Usd */
            charges_total_usd: string;
            /** Total Usd */
            total_usd: string;
            created_by: components["schemas"]["UserRef"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            confirmed_by: components["schemas"]["UserRef"] | null;
            /** Confirmed At */
            confirmed_at: string | null;
            void: components["schemas"]["PurchaseVoidOut"] | null;
            /**
             * Warnings
             * @default []
             */
            warnings: components["schemas"]["PurchaseWarning"][];
            /** Alerts Created */
            alerts_created: number;
        };
        /** PurchaseWarning */
        PurchaseWarning: {
            /** Code */
            code: string;
            /** Message */
            message: string;
            /** Purchase Number */
            purchase_number?: string | null;
        };
        /** RateCorrection */
        RateCorrection: {
            /** Rate */
            rate: number | string;
        };
        /** RateCreate */
        RateCreate: {
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /** Rate */
            rate: number | string;
        };
        /** ReconciliationRowOut */
        ReconciliationRowOut: {
            /** Method */
            method: string;
            /** Method Name */
            method_name: string;
            /** Currency */
            currency: string;
            /** Opening */
            opening: string;
            /** Collected */
            collected: string;
            /** Change Given */
            change_given: string;
            /** Refunded */
            refunded: string;
            /** Change Recovered */
            change_recovered: string;
            /** Outflows */
            outflows: string;
            /** Expected */
            expected: string;
            /** Device Expected */
            device_expected: string | null;
            /** Counted */
            counted: string | null;
            /** Difference */
            difference: string | null;
        };
        /** RecordLineRequest */
        RecordLineRequest: {
            /** Counted Quantity */
            counted_quantity: number | string;
        };
        /**
         * RefundCashSessionRef
         * @description Caja que recibió la devolución: la de la venta, o la abierta del equipo desde el que
         *     se anuló si la de la venta ya estaba cerrada (RF-27, FR-023).
         */
        RefundCashSessionRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            device: components["schemas"]["RefundDeviceRef"];
        };
        /** RefundDeviceRef */
        RefundDeviceRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** RefundSessionOut */
        RefundSessionOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            device: components["schemas"]["DeviceName"];
        };
        /** RejectBody */
        RejectBody: {
            /** Reason */
            reason: string;
        };
        /** RejectIn */
        RejectIn: {
            /** Reason */
            reason?: string | null;
        };
        /** ReorderPhotosRequest */
        ReorderPhotosRequest: {
            /** Photo Ids */
            photo_ids: string[];
        };
        /** RequestProduct */
        RequestProduct: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Sku */
            sku: string;
            /** Name */
            name: string;
            unit: components["schemas"]["UnitRef"];
            /** Stock */
            stock: string;
        };
        /** ResetPasswordRequest */
        ResetPasswordRequest: {
            /** New Password */
            new_password: string;
        };
        /** SaleAdmin */
        SaleAdmin: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string;
            /** Status */
            status: string;
            /** Needs Review */
            needs_review: boolean;
            device: components["schemas"]["DeviceRef"];
            /**
             * Cash Session Id
             * Format: uuid
             */
            cash_session_id: string;
            seller: components["schemas"]["UserRef"];
            customer: components["schemas"]["CustomerOut"] | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /**
             * Synced At
             * Format: date-time
             */
            synced_at: string;
            /** Exchange Rate */
            exchange_rate: string;
            /**
             * Exchange Rate Date
             * Format: date
             */
            exchange_rate_date: string;
            /** Items */
            items: components["schemas"]["SaleItemAdmin"][];
            /** Subtotal Usd */
            subtotal_usd: string;
            discount: components["schemas"]["DiscountOut"] | null;
            /** Discount Usd */
            discount_usd: string;
            /** Total Usd */
            total_usd: string;
            /** Total Ves */
            total_ves: string;
            /** Paid Usd */
            paid_usd: string;
            /** Change Usd */
            change_usd: string;
            /** Overpaid Usd */
            overpaid_usd: string;
            /** Device Total Usd */
            device_total_usd: string;
            /** Payments */
            payments: components["schemas"]["PaymentOut"][];
            void: components["schemas"]["SaleVoidOut"] | null;
            /** Cost Usd */
            cost_usd: string | null;
            /** Margin Usd */
            margin_usd: string | null;
        };
        /** SaleItemAdmin */
        SaleItemAdmin: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Line Number */
            line_number: number;
            product: components["schemas"]["ProductRefOut"];
            /** Quantity */
            quantity: string;
            /** Entered Unit */
            entered_unit: string;
            /** Unit Price Usd */
            unit_price_usd: string;
            /** Server Price Usd */
            server_price_usd: string | null;
            /** Line Subtotal Usd */
            line_subtotal_usd: string;
            item_discount: components["schemas"]["DiscountOut"] | null;
            /** Allocated Sale Discount Usd */
            allocated_sale_discount_usd: string;
            /** Line Total Usd */
            line_total_usd: string;
            /** Unit Cost Usd */
            unit_cost_usd: string | null;
            /** Margin Usd */
            margin_usd: string | null;
        };
        /** SaleItemSeller */
        SaleItemSeller: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Line Number */
            line_number: number;
            product: components["schemas"]["ProductRefOut"];
            /** Quantity */
            quantity: string;
            /** Entered Unit */
            entered_unit: string;
            /** Unit Price Usd */
            unit_price_usd: string;
            /** Server Price Usd */
            server_price_usd: string | null;
            /** Line Subtotal Usd */
            line_subtotal_usd: string;
            item_discount: components["schemas"]["DiscountOut"] | null;
            /** Allocated Sale Discount Usd */
            allocated_sale_discount_usd: string;
            /** Line Total Usd */
            line_total_usd: string;
        };
        /** SalePage */
        SalePage: {
            /** Items */
            items: components["schemas"]["SaleSummary"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** SaleRef */
        SaleRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string;
        };
        /** SaleRefOut */
        SaleRefOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string;
        };
        /** SaleSeller */
        SaleSeller: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string;
            /** Status */
            status: string;
            /** Needs Review */
            needs_review: boolean;
            device: components["schemas"]["DeviceRef"];
            /**
             * Cash Session Id
             * Format: uuid
             */
            cash_session_id: string;
            seller: components["schemas"]["UserRef"];
            customer: components["schemas"]["CustomerOut"] | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            /**
             * Synced At
             * Format: date-time
             */
            synced_at: string;
            /** Exchange Rate */
            exchange_rate: string;
            /**
             * Exchange Rate Date
             * Format: date
             */
            exchange_rate_date: string;
            /** Items */
            items: components["schemas"]["SaleItemSeller"][];
            /** Subtotal Usd */
            subtotal_usd: string;
            discount: components["schemas"]["DiscountOut"] | null;
            /** Discount Usd */
            discount_usd: string;
            /** Total Usd */
            total_usd: string;
            /** Total Ves */
            total_ves: string;
            /** Paid Usd */
            paid_usd: string;
            /** Change Usd */
            change_usd: string;
            /** Overpaid Usd */
            overpaid_usd: string;
            /** Device Total Usd */
            device_total_usd: string;
            /** Payments */
            payments: components["schemas"]["PaymentOut"][];
            void: components["schemas"]["SaleVoidOut"] | null;
        };
        /** SaleSummary */
        SaleSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Number */
            number: string;
            /** Status */
            status: string;
            /** Needs Review */
            needs_review: boolean;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /**
             * Business Date
             * Format: date
             */
            business_date: string;
            seller: components["schemas"]["UserRef"];
            /** Customer Name */
            customer_name: string | null;
            /** Device Name */
            device_name: string;
            /** Total Usd */
            total_usd: string;
            /** Total Ves */
            total_ves: string;
        };
        /** SaleVoidOut */
        SaleVoidOut: {
            /** Reason */
            reason: string;
            voided_by: components["schemas"]["UserRef"];
            /**
             * Voided At
             * Format: date-time
             */
            voided_at: string;
            refund_cash_session?: components["schemas"]["RefundCashSessionRef"] | null;
        };
        /** Scope */
        Scope: {
            /**
             * Type
             * @enum {string}
             */
            type: "all" | "categories" | "products";
            /**
             * Ids
             * @default []
             */
            ids: string[];
        };
        /** SessionResponse */
        SessionResponse: {
            /** Access Token */
            access_token: string;
            /**
             * Token Type
             * @default bearer
             * @constant
             */
            token_type: "bearer";
            /** Expires In */
            expires_in: number;
            /**
             * Session Expires At
             * Format: date-time
             */
            session_expires_at: string;
            user: components["schemas"]["SessionUser"];
        };
        /** SessionUser */
        SessionUser: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Username */
            username: string;
            /** Full Name */
            full_name: string;
            /**
             * Role
             * @enum {string}
             */
            role: "admin" | "seller" | "warehouse";
            /** Must Change Password */
            must_change_password: boolean;
        };
        /** SetPinRequest */
        SetPinRequest: {
            /** Current Password */
            current_password: string;
            /** Pin */
            pin: string;
        };
        /** SetupRequest */
        SetupRequest: {
            /** Setup Code */
            setup_code: string;
            /** Full Name */
            full_name: string;
            /** Username */
            username: string;
            /** Password */
            password: string;
        };
        /** SetupStatus */
        SetupStatus: {
            /** Setup Required */
            setup_required: boolean;
        };
        /** StockCountAdmin */
        StockCountAdmin: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Status */
            status: string;
            /** Scope */
            scope: {
                [key: string]: unknown;
            };
            /** Notes */
            notes: string | null;
            started_by: components["schemas"]["UserRef"] | null;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Ready At */
            ready_at: string | null;
            closed_by: components["schemas"]["UserRef"] | null;
            /** Closed At */
            closed_at: string | null;
            /** Cancel Reason */
            cancel_reason: string | null;
            /** Lines Total */
            lines_total: number;
            /** Lines Counted */
            lines_counted: number;
            /** Lines */
            lines: components["schemas"]["StockCountLineOut"][];
            /** Lines With Difference */
            lines_with_difference: number;
        };
        /**
         * StockCountLineBlind
         * @description Línea para el Almacén: sin stock esperado ni diferencia (conteo a ciegas).
         */
        StockCountLineBlind: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            product: components["schemas"]["LineProduct"];
            /** Counted Quantity */
            counted_quantity: string | null;
            /** Counted At */
            counted_at: string | null;
            counted_by: components["schemas"]["UserRef"] | null;
        };
        /** StockCountLineOut */
        StockCountLineOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            product: components["schemas"]["LineProduct"];
            /** Counted Quantity */
            counted_quantity: string | null;
            /** Counted At */
            counted_at: string | null;
            counted_by: components["schemas"]["UserRef"] | null;
            /** Expected Quantity */
            expected_quantity: string | null;
            /** Difference */
            difference: string | null;
        };
        /** StockCountSummary */
        StockCountSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Status */
            status: string;
            /** Scope */
            scope: {
                [key: string]: unknown;
            };
            /** Notes */
            notes: string | null;
            started_by: components["schemas"]["UserRef"] | null;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Ready At */
            ready_at: string | null;
            closed_by: components["schemas"]["UserRef"] | null;
            /** Closed At */
            closed_at: string | null;
            /** Cancel Reason */
            cancel_reason: string | null;
            /** Lines Total */
            lines_total: number;
            /** Lines Counted */
            lines_counted: number;
        };
        /** StockCountWarehouse */
        StockCountWarehouse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Status */
            status: string;
            /** Scope */
            scope: {
                [key: string]: unknown;
            };
            /** Notes */
            notes: string | null;
            started_by: components["schemas"]["UserRef"] | null;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Ready At */
            ready_at: string | null;
            closed_by: components["schemas"]["UserRef"] | null;
            /** Closed At */
            closed_at: string | null;
            /** Cancel Reason */
            cancel_reason: string | null;
            /** Lines Total */
            lines_total: number;
            /** Lines Counted */
            lines_counted: number;
            /** Lines */
            lines: components["schemas"]["StockCountLineBlind"][];
        };
        /** StockMovementAdmin */
        StockMovementAdmin: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Type */
            type: string;
            /** Quantity Delta */
            quantity_delta: string;
            /** Balance After */
            balance_after: string;
            /** Adjustment Reason */
            adjustment_reason: string | null;
            /** Note */
            note: string | null;
            /** Reference Type */
            reference_type: string | null;
            /** Reference Id */
            reference_id: string | null;
            created_by: components["schemas"]["UserRef"] | null;
            requested_by: components["schemas"]["UserRef"] | null;
            purchase?: components["schemas"]["MovementPurchaseRef"] | null;
            sale?: components["schemas"]["MovementSaleRef"] | null;
            /** Cost Before Usd */
            cost_before_usd: string | null;
            /** Cost After Usd */
            cost_after_usd: string | null;
        };
        /** StockMovementWarehouse */
        StockMovementWarehouse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Type */
            type: string;
            /** Quantity Delta */
            quantity_delta: string;
            /** Balance After */
            balance_after: string;
            /** Adjustment Reason */
            adjustment_reason: string | null;
            /** Note */
            note: string | null;
            /** Reference Type */
            reference_type: string | null;
            /** Reference Id */
            reference_id: string | null;
            created_by: components["schemas"]["UserRef"] | null;
            requested_by: components["schemas"]["UserRef"] | null;
            purchase?: components["schemas"]["MovementPurchaseRef"] | null;
            sale?: components["schemas"]["MovementSaleRef"] | null;
        };
        /** SupplierCreate */
        SupplierCreate: {
            /** Name */
            name: string;
            /** Rif */
            rif?: string | null;
            /** Phone */
            phone?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** SupplierOut */
        SupplierOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Rif */
            rif: string | null;
            /** Phone */
            phone: string | null;
            /** Notes */
            notes: string | null;
            /** Is Active */
            is_active: boolean;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** SupplierPage */
        SupplierPage: {
            /** Items */
            items: components["schemas"]["SupplierOut"][];
            /** Total */
            total: number;
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
        };
        /** SupplierRef */
        SupplierRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Rif */
            rif: string | null;
        };
        /** SupplierUpdate */
        SupplierUpdate: {
            /** Name */
            name?: string | null;
            /** Rif */
            rif?: string | null;
            /** Phone */
            phone?: string | null;
            /** Notes */
            notes?: string | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** TemplateCreate */
        TemplateCreate: {
            /** Name */
            name: string;
            /**
             * Charge Type
             * @enum {string}
             */
            charge_type: "percent" | "fixed";
            /** Default Value */
            default_value?: number | string | null;
            /** Currency */
            currency?: ("USD" | "VES") | null;
        };
        /**
         * TemplateUpdate
         * @description `charge_type` no cambia: no existe en este esquema (422 si se envía).
         */
        TemplateUpdate: {
            /** Name */
            name?: string | null;
            /** Default Value */
            default_value?: number | string | null;
            /** Currency */
            currency?: ("USD" | "VES") | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** UnitOut */
        UnitOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Code */
            code: string;
            /** Name */
            name: string;
            /** Decimals */
            decimals: number;
            /** Is Active */
            is_active: boolean;
        };
        /** UnitRef */
        UnitRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Code */
            code: string;
            /** Name */
            name: string;
            /** Decimals */
            decimals: number;
        };
        /**
         * UpdateAttributeRequest
         * @description La clave y el tipo no se cambian; las opciones se agregan o se desactivan.
         */
        UpdateAttributeRequest: {
            /** Label */
            label?: string | null;
            /** Options */
            options?: components["schemas"]["AttributeOption"][] | null;
            /** Is Required */
            is_required?: boolean | null;
            /** Is Filterable */
            is_filterable?: boolean | null;
            /** Sort Order */
            sort_order?: number | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** UpdateCategoryRequest */
        UpdateCategoryRequest: {
            /** Name */
            name?: string | null;
            /** Sku Prefix */
            sku_prefix?: string | null;
            /** Default Unit Id */
            default_unit_id?: string | null;
            /** Unit Locked */
            unit_locked?: boolean | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** UpdateProductRequest */
        UpdateProductRequest: {
            /** Name */
            name?: string | null;
            /** Description */
            description?: string | null;
            /** Attributes */
            attributes?: {
                [key: string]: string | number | null;
            } | null;
            /** Min Stock */
            min_stock?: number | string | null;
            /** Category Id */
            category_id?: string | null;
            /** Unit Id */
            unit_id?: string | null;
            /** Is Active */
            is_active?: boolean | null;
            /** Updated At */
            updated_at?: string | null;
        };
        /**
         * UpdateUnitRequest
         * @description El código y los decimales no se cambian: enviarlos es un error de validación.
         */
        UpdateUnitRequest: {
            /** Name */
            name?: string | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** UpdateUserRequest */
        UpdateUserRequest: {
            /** Full Name */
            full_name?: string | null;
            /** Role */
            role?: ("admin" | "seller" | "warehouse") | null;
            /** Is Active */
            is_active?: boolean | null;
        };
        /** UserRef */
        UserRef: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Full Name */
            full_name: string;
        };
        /** UserSummary */
        UserSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Username */
            username: string;
            /** Full Name */
            full_name: string;
            /**
             * Role
             * @enum {string}
             */
            role: "admin" | "seller" | "warehouse";
            /** Is Active */
            is_active: boolean;
            /** Must Change Password */
            must_change_password: boolean;
            /** Has Pin */
            has_pin: boolean;
            /** Last Login At */
            last_login_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** VerifyPinRequest */
        VerifyPinRequest: {
            /** Admin Username */
            admin_username: string;
            /** Pin */
            pin: string;
        };
        /** VerifyPinResponse */
        VerifyPinResponse: {
            authorized_by: components["schemas"]["Authorizer"];
        };
        /** VoidIn */
        VoidIn: {
            /** Reason */
            reason: string;
        };
        /** VoidInput */
        VoidInput: {
            /** Reason */
            reason: string;
        };
        /** VoidPreview */
        VoidPreview: {
            /** Items */
            items: components["schemas"]["VoidPreviewItem"][];
        };
        /** VoidPreviewItem */
        VoidPreviewItem: {
            /**
             * Product Id
             * Format: uuid
             */
            product_id: string;
            /** Sku */
            sku: string;
            /** Stock Before */
            stock_before: string;
            /** Stock After */
            stock_after: string;
            /** Cost Before Usd */
            cost_before_usd: string | null;
            /** Cost After Usd */
            cost_after_usd: string | null;
            /** Keeps Cost */
            keeps_cost: boolean;
        };
        /** VoidedAfterCloseOut */
        VoidedAfterCloseOut: {
            sale: components["schemas"]["SaleRefOut"];
            /**
             * Voided At
             * Format: date-time
             */
            voided_at: string;
            refund_cash_session: components["schemas"]["RefundSessionOut"] | null;
        };
        /** WarehouseSummary */
        WarehouseSummary: {
            /** Low Stock */
            low_stock: number;
            /** My Pending Requests */
            my_pending_requests: number;
            /** Open Counts */
            open_counts: number;
            /** Draft Purchases */
            draft_purchases: number;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    health_db_api_v1_health_db_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    setup_status_api_v1_setup_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SetupStatus"];
                };
            };
        };
    };
    setup_api_v1_setup_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetupRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_api_v1_auth_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionResponse"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    me_api_v1_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MeResponse"];
                };
            };
        };
    };
    change_password_api_v1_auth_password_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChangePasswordRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_pin_api_v1_auth_pin_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SetPinRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    verify_pin_api_v1_auth_pin_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VerifyPinRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VerifyPinResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_users_api_v1_users_get: {
        parameters: {
            query?: {
                role?: ("admin" | "seller" | "warehouse") | null;
                is_active?: boolean | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_user_api_v1_users_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateUserRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_user_api_v1_users__user_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_user_api_v1_users__user_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateUserRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserSummary"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reset_password_api_v1_users__user_id__password_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResetPasswordRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_audit_api_v1_audit_log_get: {
        parameters: {
            query?: {
                user_id?: string | null;
                action?: string | null;
                date_from?: string | null;
                date_to?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_units_api_v1_units_get: {
        parameters: {
            query?: {
                include_inactive?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_unit_api_v1_units_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateUnitRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_categories_api_v1_categories_get: {
        parameters: {
            query?: {
                include_inactive?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_category_api_v1_categories_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateCategoryRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_unit_api_v1_units__unit_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                unit_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateUnitRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_category_api_v1_categories__category_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                category_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateCategoryRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_attribute_api_v1_categories__category_id__attributes_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                category_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateAttributeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttributeOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_attribute_api_v1_attributes__attribute_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attribute_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateAttributeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttributeOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_products_api_v1_products_get: {
        parameters: {
            query?: {
                q?: string | null;
                category_id?: string | null;
                is_active?: boolean | null;
                is_published?: boolean | null;
                low_stock?: boolean | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_product_api_v1_products_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateProductRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_product_api_v1_products__product_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_product_api_v1_products__product_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpdateProductRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_photo_api_v1_products__product_id__photos_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_add_photo_api_v1_products__product_id__photos_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_photo_api_v1_products__product_id__photos__photo_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
                photo_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reorder_photos_api_v1_products__product_id__photos_order_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReorderPhotosRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_movements_api_v1_products__product_id__movements_get: {
        parameters: {
            query?: {
                from?: string | null;
                to?: string | null;
                type?: ("purchase" | "sale" | "sale_void" | "purchase_void" | "adjustment") | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MovementPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_price_api_v1_products__product_id__price_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PriceRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_prices_api_v1_products__product_id__prices_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PriceOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_initial_cost_api_v1_products__product_id__initial_cost_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InitialCostRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_publication_api_v1_products__product_id__publication_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PublicationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductAdmin"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    register_adjustment_api_v1_inventory_adjustments_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdjustmentRequestBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustmentResultOut"];
                };
            };
            /** @description Salida pendiente */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustmentResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_adjustment_requests_api_v1_inventory_adjustment_requests_get: {
        parameters: {
            query?: {
                status?: ("pending" | "approved" | "rejected" | "withdrawn") | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustmentRequestPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_request_api_v1_inventory_adjustment_requests__request_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustmentRequestOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_request_api_v1_inventory_adjustment_requests__request_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RejectBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustmentRequestOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    withdraw_request_api_v1_inventory_adjustment_requests__request_id__withdraw_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdjustmentRequestOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    low_stock_api_v1_inventory_low_stock_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": (components["schemas"]["ProductAdmin"] | components["schemas"]["ProductSeller"] | components["schemas"]["ProductWarehouse"])[];
                };
            };
        };
    };
    summary_api_v1_inventory_summary_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminSummary"] | components["schemas"]["WarehouseSummary"];
                };
            };
        };
    };
    list_counts_api_v1_stock_counts_get: {
        parameters: {
            query?: {
                status?: ("open" | "ready_for_review" | "applied" | "cancelled") | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountSummary"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    open_count_api_v1_stock_counts_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpenCountRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountAdmin"] | components["schemas"]["StockCountWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_count_api_v1_stock_counts__count_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                count_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountAdmin"] | components["schemas"]["StockCountWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    record_line_api_v1_stock_counts__count_id__lines__line_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                count_id: string;
                line_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecordLineRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountLineOut"] | components["schemas"]["StockCountLineBlind"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_ready_api_v1_stock_counts__count_id__ready_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                count_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountAdmin"] | components["schemas"]["StockCountWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reopen_api_v1_stock_counts__count_id__reopen_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                count_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountAdmin"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    apply_count_api_v1_stock_counts__count_id__apply_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                count_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApplyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplyResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_count_api_v1_stock_counts__count_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                count_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CancelRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StockCountAdmin"] | components["schemas"]["StockCountWarehouse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_suppliers_api_v1_suppliers_get: {
        parameters: {
            query?: {
                q?: string | null;
                is_active?: boolean | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SupplierPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_supplier_api_v1_suppliers_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SupplierCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SupplierOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_supplier_api_v1_suppliers__supplier_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                supplier_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SupplierOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_supplier_api_v1_suppliers__supplier_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                supplier_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SupplierUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SupplierOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_purchases_api_v1_purchases_get: {
        parameters: {
            query?: {
                status?: ("draft" | "confirmed" | "voided") | null;
                supplier_id?: string | null;
                from?: string | null;
                to?: string | null;
                product_id?: string | null;
                q?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurchasePage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_purchase_api_v1_purchases_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PurchaseInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurchaseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_purchase_api_v1_purchases__purchase_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                purchase_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurchaseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_purchase_api_v1_purchases__purchase_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                purchase_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PurchaseInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurchaseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    discard_purchase_api_v1_purchases__purchase_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                purchase_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    confirm_purchase_api_v1_purchases__purchase_id__confirm_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                purchase_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConfirmInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurchaseConfirmedAdmin"] | components["schemas"]["PurchaseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    void_preview_api_v1_purchases__purchase_id__void_preview_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                purchase_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VoidPreview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    void_purchase_api_v1_purchases__purchase_id__void_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                purchase_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VoidInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PurchaseVoidedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_rates_api_v1_exchange_rates_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExchangeRatePage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_rate_api_v1_exchange_rates_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RateCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExchangeRateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    applicable_rate_api_v1_exchange_rates_applicable_get: {
        parameters: {
            query: {
                date: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicableRateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    correct_rate_api_v1_exchange_rates__business_date__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                business_date: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RateCorrection"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExchangeRateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_templates_api_v1_charge_templates_get: {
        parameters: {
            query?: {
                include_inactive?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChargeTemplateOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_template_api_v1_charge_templates_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChargeTemplateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_template_api_v1_charge_templates__template_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                template_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChargeTemplateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_alerts_api_v1_alerts_get: {
        parameters: {
            query?: {
                status?: "open" | "resolved";
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AlertPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resolve_alert_api_v1_alerts__alert_id__resolve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                alert_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AlertOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_devices_api_v1_devices_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceOut"][];
                };
            };
        };
    };
    register_device_api_v1_devices_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeviceCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceRegistered"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_device_api_v1_devices__device_id__revoke_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                device_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    current_device_api_v1_devices_current_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeviceOut"];
                };
            };
        };
    };
    search_customers_api_v1_customers_get: {
        parameters: {
            query?: {
                q?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomerOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_pending_api_v1_discount_authorizations_get: {
        parameters: {
            query?: {
                status?: "pending";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiscountAuthorizationOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    request_authorization_api_v1_discount_authorizations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AuthorizationIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiscountAuthorizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_authorization_api_v1_discount_authorizations__authorization_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                authorization_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiscountAuthorizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_api_v1_discount_authorizations__authorization_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                authorization_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApproveIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiscountAuthorizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_api_v1_discount_authorizations__authorization_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                authorization_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RejectIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiscountAuthorizationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_sales_api_v1_sales_get: {
        parameters: {
            query?: {
                from?: string | null;
                to?: string | null;
                q?: string | null;
                seller_id?: string | null;
                customer_id?: string | null;
                device_id?: string | null;
                status?: ("registered" | "voided" | "needs_review") | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SalePage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_sale_api_v1_sales__sale_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sale_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SaleAdmin"] | components["schemas"]["SaleSeller"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    void_sale_api_v1_sales__sale_id__void_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sale_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VoidIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SaleAdmin"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_cash_sessions_api_v1_cash_sessions_get: {
        parameters: {
            query?: {
                from?: string | null;
                to?: string | null;
                device_id?: string | null;
                opened_by?: string | null;
                closed_by?: string | null;
                status?: ("open" | "closed") | null;
                with_differences?: boolean | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CashSessionPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_cash_session_api_v1_cash_sessions__session_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CashSessionDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    close_cash_session_api_v1_cash_sessions__session_id__close_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdminCloseIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CashSessionClosed"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    void_outflow_api_v1_cash_outflows__outflow_id__void_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                outflow_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutflowVoidIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CashOutflowOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_operation_api_v1_sync_operations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutboxOperationIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SaleAdmin"] | components["schemas"]["SaleSeller"] | components["schemas"]["CashSessionOut"] | components["schemas"]["CashOutflowOut"] | components["schemas"]["CashSessionClosed"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
