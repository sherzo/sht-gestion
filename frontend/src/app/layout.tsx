import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { inter, montserrat } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHT Gestión",
  description: "Inventario, ventas y caja de Suministros Hidráulicos Turmero",
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
