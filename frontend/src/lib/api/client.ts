// Cliente HTTP único de la app (research R12): agrega el token de acceso, renueva una vez
// ante un 401 y, si la sesión terminó, delega en la sesión (diálogo de reingreso).
import type { components } from "@sht/shared";

export type Schemas = components["schemas"];

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string>;
  readonly extra: Record<string, unknown>;

  constructor(status: number, code: string, message: string, extra: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    const { fields, ...rest } = extra;
    this.fields = (fields as Record<string, string> | undefined) ?? {};
    this.extra = rest;
  }
}

/** Lo que el cliente necesita de la sesión; lo registra el proveedor de autenticación. */
export type SessionBridge = {
  getAccessToken: () => string | null;
  /** Renueva el token con la cookie; devuelve el nuevo token o null si no se pudo. */
  refresh: () => Promise<string | null>;
  /** La sesión terminó: devuelve true si el mismo usuario volvió a entrar y se puede reintentar. */
  onSessionEnded: () => Promise<boolean>;
};

let bridge: SessionBridge | null = null;

export function connectSession(next: SessionBridge | null): void {
  bridge = next;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null> | URLSearchParams;
  /** false para endpoints públicos (instalación, ingreso). */
  authenticated?: boolean;
  /** true para no abrir el reingreso si la sesión ya terminó (por ejemplo, al cerrar sesión). */
  skipReauth?: boolean;
};

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_URL}/api/v1${path}`, window.location.origin);
  // URLSearchParams permite repetir claves (filtros `attr.<clave>` de la búsqueda).
  const entries = query instanceof URLSearchParams ? [...query.entries()] : Object.entries(query ?? {});
  for (const [key, value] of entries) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.append(key, String(value));
  }
  return url.toString();
}

function requestBody(options: RequestOptions): BodyInit | undefined {
  // Los archivos (fotos) viajan en multipart/form-data; el navegador pone el encabezado.
  if (options.body instanceof FormData) return options.body;
  if (options.body !== undefined) return JSON.stringify(options.body);
  return options.method === "POST" ? "{}" : undefined;
}

async function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const isForm = options.body instanceof FormData;
  if (!isForm && (options.body !== undefined || options.method === "POST")) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  // La cookie de renovación solo viaja a /auth y /setup (ruta de la cookie).
  const withCookie = path.startsWith("/auth") || path.startsWith("/setup");
  return fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: requestBody(options),
    credentials: withCookie ? "include" : "same-origin",
  });
}

async function toError(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as { detail?: { code?: string; message?: string } };
    const detail = data.detail ?? {};
    const { code = "unknown_error", message = "Ocurrió un error inesperado", ...extra } = detail;
    return new ApiError(response.status, code, message, extra);
  } catch {
    return new ApiError(response.status, "unknown_error", "Ocurrió un error inesperado");
  }
}

export async function apiFetch<T = void>(path: string, options: RequestOptions = {}): Promise<T> {
  const authenticated = options.authenticated ?? true;
  let response: Response;
  try {
    response = await send(path, options, authenticated ? (bridge?.getAccessToken() ?? null) : null);
  } catch {
    throw new ApiError(0, "network_error", "No hay conexión con el servidor. Revisa tu internet");
  }

  if (response.status === 401 && authenticated && bridge) {
    let error = await toError(response);
    if (error.code === "not_authenticated") {
      const token = await bridge.refresh();
      if (token) {
        response = await send(path, options, token);
        if (response.ok) return parse<T>(response);
        error = await toError(response);
      } else {
        error = new ApiError(401, "session_ended", "Tu sesión terminó");
      }
    }
    if (!options.skipReauth && (error.code === "session_ended" || error.code === "not_authenticated")) {
      if (await bridge.onSessionEnded()) {
        response = await send(path, options, bridge.getAccessToken());
        if (response.ok) return parse<T>(response);
        throw await toError(response);
      }
    }
    throw error;
  }

  if (!response.ok) throw await toError(response);
  return parse<T>(response);
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
