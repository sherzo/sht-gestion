// Genera los tipos TypeScript de la API a partir del OpenAPI de FastAPI (arquitectura §2).
// Uso: pnpm api:types
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = join(root, "packages", "shared", "src", "api", "schema.d.ts");

const openapi = execFileSync(
  "uv",
  ["run", "python", "-c", "import json; from app.main import app; print(json.dumps(app.openapi()))"],
  { cwd: join(root, "backend"), encoding: "utf8", env: { ...process.env, ENVIRONMENT: "local" } },
);

const ast = await openapiTS(JSON.parse(openapi));
const header = [
  "/**",
  " * Tipos de la API generados con `pnpm api:types` desde el OpenAPI de FastAPI.",
  " * No editar a mano: se regeneran cuando cambia el backend.",
  " */",
  "",
].join("\n");
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, header + astToString(ast));
console.log(`Tipos de la API generados en ${output}`);
