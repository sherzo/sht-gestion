import { Inter, Montserrat } from "next/font/google";

// Fuentes de la guía de estilos (ADR-0007). next/font las descarga al construir y las
// sirve desde la propia app, así que funcionan sin conexión.
export const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
export const montserrat = Montserrat({
  subsets: ["latin"],
  variable: "--font-montserrat",
  display: "swap",
});
