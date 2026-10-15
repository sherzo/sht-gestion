"use client";

// Estado del equipo de mostrador para Caja y Vender (FR-001 a FR-008; research R3, R5): lee
// la identidad local y la confirma con el servidor (`GET /devices/current`), que devuelve la
// caja abierta y el último correlativo registrado.
import { useCallback, useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";
import { getDevice, syncSequence } from "@/lib/device/device-store";
import type { DeviceRecord } from "@/lib/device/device-store";

export type ServerDevice = Schemas["DeviceOut"];

export type DeviceState =
  | { status: "loading" }
  | { status: "unregistered" }
  | { status: "revoked"; local: DeviceRecord }
  | { status: "offline"; local: DeviceRecord; message: string }
  | { status: "ready"; local: DeviceRecord; server: ServerDevice };

/** Llamada a la API con el token del equipo (operaciones de mostrador). */
export function deviceFetch<T>(device: DeviceRecord, path: string, options: Parameters<typeof apiFetch>[1] = {}): Promise<T> {
  return apiFetch<T>(path, { ...options, headers: { ...options.headers, "X-Device-Token": device.token } });
}

export function useCounterDevice(): DeviceState & { reload: () => Promise<void> } {
  const [state, setState] = useState<DeviceState>({ status: "loading" });

  const reload = useCallback(async () => {
    const local = await getDevice();
    if (!local) {
      setState({ status: "unregistered" });
      return;
    }
    try {
      const server = await deviceFetch<ServerDevice>(local, "/devices/current");
      await syncSequence(server.last_sequence_number);
      setState({ status: "ready", local: (await getDevice()) ?? local, server });
    } catch (caught) {
      if (caught instanceof ApiError && (caught.code === "device_revoked" || caught.code === "device_required")) {
        setState({ status: "revoked", local });
      } else {
        setState({
          status: "offline",
          local,
          message: caught instanceof ApiError ? caught.message : "No se pudo consultar el equipo",
        });
      }
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { ...state, reload };
}
