import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { inter, montserrat } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "Catálogo — Suministros Hidráulicos Turmero",
  description: "Mangueras hidráulicas, conexiones, ferrules y ferretería en Turmero",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#03045e",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es-VE" className={`${inter.variable} ${montserrat.variable}`}>
      <body>{children}</body>
    </html>
  );
}
