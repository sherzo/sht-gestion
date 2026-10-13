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
        post?: never;
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
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
        /** AdminSummary */
        AdminSummary: {
            /** Low Stock */
            low_stock: number;
            /** Pending Adjustments */
            pending_adjustments: number;
            /** Counts Ready For Review */
            counts_ready_for_review: number;
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
        /** OpenCountRequest */
        OpenCountRequest: {
            scope: components["schemas"]["Scope"];
            /** Notes */
            notes?: string | null;
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
        /** RecordLineRequest */
        RecordLineRequest: {
            /** Counted Quantity */
            counted_quantity: number | string;
        };
        /** RejectBody */
        RejectBody: {
            /** Reason */
            reason: string;
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
        /** WarehouseSummary */
        WarehouseSummary: {
            /** Low Stock */
            low_stock: number;
            /** My Pending Requests */
            my_pending_requests: number;
            /** Open Counts */
            open_counts: number;
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
}
