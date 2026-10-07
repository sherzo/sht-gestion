import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Catálogo — Suministros Hidráulicos Turmero",
  description: "Mangueras hidráulicas, conexiones, ferrules y ferretería en Turmero",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es-VE">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: 16 }}>
        {children}
      </body>
    </html>
  );
}
