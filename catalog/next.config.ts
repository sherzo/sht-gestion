import type { NextConfig } from "next";

// Catálogo público estático (ADR-0001): se reconstruye cada X horas (RF-38) y nunca
// consulta la base de datos desde el navegador.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
