import type { NextConfig } from "next";

// Sitio estático (ADR-0001): sin SSR ni funciones de servidor, para que la app
// funcione sin conexión y se aloje en Cloudflare Pages.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
